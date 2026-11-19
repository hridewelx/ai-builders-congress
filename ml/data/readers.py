"""Read each source's labels and map its class names onto the four classes."""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from ..config import CLASS_TO_ID, SOURCE_CLASS_MAP
from .records import IMAGE_EXTS, Record


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
        parts = [part.lower() for part in img.relative_to(root).parts]
        source_split = ("test" if "test" in parts else
                        "val" if "valid" in parts or "val" in parts else
                        "train" if "train" in parts else "")
        records.append(Record(path=img, boxes=boxes, source=source, split=source_split))
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
        split = str(row.get("split", "")).strip().lower()
        if split in {"valid", "validation"}:
            split = "val"
        if split not in {"train", "val", "test"}:
            parts = [part.lower() for part in Path(row["file"]).parts]
            split = ("test" if "test" in parts else
                     "val" if "valid" in parts or "val" in parts else
                     "train" if "train" in parts else "")
        records.append(Record(path=path, boxes=boxes, source=source, split=split,
                              group=str(row["seed"] // 1000 * 1000)))
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
