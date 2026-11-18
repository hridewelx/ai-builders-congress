"""Assemble a canonical YOLO detection dataset from public and synthetic sources.

Responsibilities:
  * read YOLO folders (images/ + labels/ pairs) and Lotline's annotation JSONL
  * map each source's class names onto the four v1 detector classes
  * de-duplicate by SHA-256 and by perceptual hash, keeping copies in one split
  * split by image group, never by file name
  * write a canonical folder, a data.yaml and a manifest with licence metadata

Usage:
    python -m ml.data prepare --source data/raw/bdfd9 --name bdfd9 --licence "CC BY 4.0"
    python -m ml.data prepare --source data/dataset/v1 --name staged
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import shutil
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

from .config import CLASS_TO_ID, CLASSES, DET, SEED, SOURCE_CLASS_MAP, VAL_FRACTION

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


@dataclass
class Record:
    """One image and its boxes, before the canonical export."""

    path: Path
    boxes: list[tuple[int, float, float, float, float]]  # class id, x1 y1 x2 y2 (pixels)
    source: str
    group: str = ""
    sha256: str = ""
    phash: str = ""
    split: str = "train"
    duplicates: list[str] = field(default_factory=list)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dhash(path: Path, size: int = 8) -> str:
    """Difference hash, used to catch re-encoded copies that SHA-256 misses."""
    with Image.open(path) as image:
        gray = image.convert("L").resize((size + 1, size), Image.LANCZOS)
    pixels = list(gray.tobytes())
    bits = []
    for row in range(size):
        for col in range(size):
            bits.append("1" if pixels[row * (size + 1) + col] > pixels[row * (size + 1) + col + 1] else "0")
    return f"{int(''.join(bits), 2):016x}"


def hamming(a: str, b: str) -> int:
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def pixel_mae(a: Path, b: Path, size: int = 32) -> float:
    """Mean absolute difference of two thumbnails, 0-255 scale."""
    import numpy as np
    with Image.open(a) as ia, Image.open(b) as ib:
        ta = np.asarray(ia.convert("L").resize((size, size)), dtype=np.float32)
        tb = np.asarray(ib.convert("L").resize((size, size)), dtype=np.float32)
    return float(np.abs(ta - tb).mean())


def _norm(name: str) -> str:
    return " ".join(name.replace("_", " ").replace("-", " ").lower().split())


def map_class(name: str) -> str | None:
    """Map a source class name to a v1 class, or None when it is out of scope."""
    return SOURCE_CLASS_MAP.get(_norm(name))


def read_yolo(root: Path, source: str, names: list[str]) -> list[Record]:
    """Read every image with a matching labels/*.txt in a YOLO tree."""
    records: list[Record] = []
    for img in sorted(root.rglob("*")):
        if img.suffix.lower() not in IMAGE_EXTS:
            continue
        label = img.parent.parent / "labels" / f"{img.stem}.txt"
        if not label.exists():
            label = img.with_suffix(".txt")
        boxes: list[tuple[int, float, float, float, float]] = []
        raw_labels = 0
        if label.exists():
            with Image.open(img) as im:
                width, height = im.size
            for line in label.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
                parts = line.split()
                if len(parts) < 5:
                    continue
                raw_labels += 1
                cls_id = int(float(parts[0]))
                name = names[cls_id] if 0 <= cls_id < len(names) else str(cls_id)
                mapped = map_class(name)
                if mapped is None:
                    continue
                values = [float(v) for v in parts[1:]]
                if len(values) == 4:  # cx cy w h
                    cx, cy, bw, bh = values
                    x1 = max(0.0, (cx - bw / 2) * width)
                    y1 = max(0.0, (cy - bh / 2) * height)
                    x2 = min(float(width), (cx + bw / 2) * width)
                    y2 = min(float(height), (cy + bh / 2) * height)
                else:  # polygon: x1 y1 x2 y2 ... -> bounding box
                    xs = [v * width for v in values[0::2]]
                    ys = [v * height for v in values[1::2]]
                    x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
                if x2 - x1 >= 2 and y2 - y1 >= 2:
                    boxes.append((CLASS_TO_ID[mapped], x1, y1, x2, y2))
        if raw_labels and not boxes:
            continue  # annotated with out-of-scope classes only; never teach it as clean
        records.append(Record(path=img, boxes=boxes, source=source))
    return records


def read_jsonl(root: Path, source: str) -> list[Record]:
    """Read Lotline's staged set: images/ + annotations.jsonl with normalised boxes."""
    records: list[Record] = []
    for line in (root / "annotations.jsonl").read_text(encoding="utf-8-sig").splitlines():
        row = json.loads(line)
        path = root / row["file"]
        with Image.open(path) as im:
            width, height = im.size
        boxes = []
        for defect in row["defects"]:
            mapped = map_class(defect["type"])
            if mapped is None:
                continue
            x1, y1, x2, y2 = defect["box"]
            boxes.append((CLASS_TO_ID[mapped], x1 * width, y1 * height, x2 * width, y2 * height))
        records.append(Record(path=path, boxes=boxes, source=source, group=str(row["seed"] // 1000 * 1000)))
    return records


def discover_names(root: Path, explicit: list[str] | None) -> list[str]:
    """Find class names: explicit, data.yaml, classes.txt, else folder names."""
    if explicit:
        return explicit
    for candidate in (root / "data.yaml", root / "dataset.yaml"):
        if candidate.exists():
            for line in candidate.read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.strip().startswith("names:"):
                    raw = line.split(":", 1)[1].strip()
                    if raw.startswith("["):
                        return [v.strip().strip("'\"") for v in raw.strip("[]").split(",")]
    for candidate in root.rglob("classes.txt"):
        return [v.strip() for v in candidate.read_text(encoding="utf-8", errors="ignore").splitlines() if v.strip()]
    return sorted({p.parent.parent.name for p in root.rglob("images") if p.is_dir()})


def dedupe(records: list[Record]) -> tuple[list[Record], int]:
    """Drop exact and near-duplicate images, recording what was dropped."""
    kept: list[Record] = []
    seen_sha: dict[str, Record] = {}
    hashes: list[tuple[str, Record]] = []
    dropped = 0
    for record in records:
        record.sha256 = sha256_file(record.path)
        if record.sha256 in seen_sha:
            seen_sha[record.sha256].duplicates.append(str(record.path))
            dropped += 1
            continue
        record.phash = dhash(record.path)
        near = next((other for h, other in hashes
                     if hamming(h, record.phash) <= 2 and pixel_mae(other.path, record.path) <= 1.5), None)
        if near is not None:
            near.duplicates.append(str(record.path))
            dropped += 1
            continue
        seen_sha[record.sha256] = record
        hashes.append((record.phash, record))
        record.group = record.phash
        kept.append(record)
    return kept, dropped


def split_records(records: list[Record], val_fraction: float = VAL_FRACTION, seed: int = SEED) -> None:
    """Assign whole duplicate groups to train or val, stratified by class presence."""
    random.seed(seed)
    groups: dict[str, list[Record]] = defaultdict(list)
    for record in records:
        groups[record.group].append(record)
    ordered = sorted(groups.values(), key=lambda g: (-len(g), g[0].group))
    random.shuffle(ordered)
    total = len(records)
    val_target = max(1, int(total * val_fraction))
    val_count = 0
    val_classes: Counter[int] = Counter()
    total_classes: Counter[int] = Counter()
    for record in records:
        for box in record.boxes:
            total_classes[box[0]] += 1
    for group in ordered:
        classes = {box[0] for record in group for box in record.boxes}
        needs_representation = any(
            total_classes[c] >= 5 and val_classes[c] < total_classes[c] * val_fraction for c in classes)
        take = (val_count < val_target and (needs_representation or val_count < val_target // 2))
        target = "val" if take else "train"
        for record in group:
            record.split = target
        if target == "val":
            val_count += len(group)
            for record in group:
                for box in record.boxes:
                    val_classes[box[0]] += 1


def export(records: list[Record], out: Path, source_meta: dict) -> dict:
    """Write images/, labels/, data.yaml and manifest.json."""
    if out.exists():
        shutil.rmtree(out)
    for split in ("train", "val"):
        (out / "images" / split).mkdir(parents=True)
        (out / "labels" / split).mkdir(parents=True)
    counts: Counter[str] = Counter()
    boxes_per_class: Counter[int] = Counter()
    for index, record in enumerate(records):
        name = f"{record.source}_{index:05d}"
        image_target = out / "images" / record.split / f"{name}{record.path.suffix.lower()}"
        shutil.copy2(record.path, image_target)
        with Image.open(record.path) as im:
            width, height = im.size
        lines = []
        for cls, x1, y1, x2, y2 in record.boxes:
            lines.append(f"{cls - 1} {((x1 + x2) / 2) / width:.6f} {((y1 + y2) / 2) / height:.6f} "
                         f"{(x2 - x1) / width:.6f} {(y2 - y1) / height:.6f}")
            boxes_per_class[cls] += 1
        (out / "labels" / record.split / f"{name}.txt").write_text("\n".join(lines), encoding="utf-8")
        counts[record.split] += 1
    (out / "data.yaml").write_text(
        "path: .\ntrain: images/train\nval: images/val\n"
        f"nc: {len(CLASSES)}\nnames: {CLASSES}\n", encoding="utf-8")
    manifest = {
        **source_meta,
        "classes": CLASSES,
        "images": dict(counts),
        "boxes_per_class": {CLASSES[c - 1]: n for c, n in sorted(boxes_per_class.items())},
        "duplicates_removed": sum(len(r.duplicates) for r in records),
        "annotations": "YOLO normalised cx cy w h",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def prepare(source: Path, name: str, out: Path, names: list[str] | None, licence: str,
            val_fraction: float) -> None:
    if (source / "annotations.jsonl").exists():
        records = read_jsonl(source, name)
        names = names or CLASSES
    else:
        found = discover_names(source, names)
        if not found:
            raise SystemExit("could not find class names; pass --names")
        records = read_yolo(source, name, found)
    before = len(records)
    records, dropped = dedupe(records)
    split_records(records, val_fraction)
    manifest = export(records, out, {
        "source": name,
        "source_path": str(source),
        "licence": licence,
        "images_before_dedupe": before,
        "images_after_dedupe": len(records),
    })
    print(f"{name}: {before} -> {len(records)} images ({dropped} duplicates), "
          f"train {manifest['images'].get('train', 0)} / val {manifest['images'].get('val', 0)}")
    print(f"boxes: {manifest['boxes_per_class']}")
    print(f"written -> {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare a canonical detection dataset.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare", help="one source")
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--out", type=Path, default=DET)
    p.add_argument("--names", nargs="*", default=None)
    p.add_argument("--licence", default="unknown")
    p.add_argument("--val-fraction", type=float, default=VAL_FRACTION)

    b = sub.add_parser("build", help="several sources, one canonical dataset")
    b.add_argument("--source", action="append", required=True, metavar="NAME=PATH")
    b.add_argument("--licence", action="append", default=[])
    b.add_argument("--out", type=Path, default=DET)
    b.add_argument("--val-fraction", type=float, default=VAL_FRACTION)
    args = parser.parse_args()

    if args.cmd == "prepare":
        prepare(args.source, args.name, args.out, args.names, args.licence, args.val_fraction)
        return

    records: list[Record] = []
    sources = []
    for index, item in enumerate(args.source):
        name, _, path_text = item.partition("=")
        if not path_text:
            raise SystemExit(f"expected NAME=PATH, got {item}")
        path = Path(path_text)
        licence = args.licence[index] if index < len(args.licence) else "unknown"
        if (path / "annotations.jsonl").exists():
            found = read_jsonl(path, name)
            names = CLASSES
        else:
            names = discover_names(path, None)
            found = read_yolo(path, name, names)
        sources.append({"name": name, "path": str(path), "licence": licence, "class_names": names})
        print(f"{name}: read {len(found)} images")
        records.extend(found)

    before = len(records)
    records, dropped = dedupe(records)
    split_records(records, args.val_fraction)
    manifest = export(records, args.out, {
        "sources": sources,
        "images_before_dedupe": before,
        "images_after_dedupe": len(records),
    })
    print(f"combined: {before} -> {len(records)} images ({dropped} duplicates)")
    print(f"train {manifest['images'].get('train', 0)} / val {manifest['images'].get('val', 0)}")
    print(f"boxes: {manifest['boxes_per_class']}")
    print(f"written -> {args.out}")


if __name__ == "__main__":
    main()
