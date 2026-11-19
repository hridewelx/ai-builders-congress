"""Assign records to train/val/test and write the dataset folder."""
from __future__ import annotations

import json
import random
import shutil
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image

from ..config import CLASSES, SEED, VAL_FRACTION


def split_records(records: list[Record], val_fraction: float = VAL_FRACTION, seed: int = SEED,
                  preserve_splits: bool = True) -> None:
    """Assign whole duplicate groups to train/val/test.

    With ``preserve_splits`` (the default), each source's own train/valid/test
    folders are kept. Only records without a source split are assigned by the
    grouped 80/20 rule. This is what keeps BDFD9's official test set out of
    training.
    """
    random.seed(seed)
    for record in records:
        value = record.split.strip().lower()
        if value in {"valid", "validation"}:
            record.split = "val"
        elif value in {"train", "val", "test"}:
            record.split = value
        else:
            record.split = ""

    unassigned = records if not preserve_splits else [record for record in records if not record.split]
    groups: dict[str, list[Record]] = defaultdict(list)
    for record in unassigned:
        groups[record.group or record.phash or str(record.path)].append(record)
    ordered = sorted(groups.values(), key=lambda g: (-len(g), g[0].group))
    random.shuffle(ordered)
    total = len(unassigned)
    val_target = max(1, int(total * val_fraction))
    val_count = 0
    val_classes: Counter[int] = Counter()
    total_classes: Counter[int] = Counter()
    for record in unassigned:
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
    for split in ("train", "val", "test"):
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
        "path: .\ntrain: images/train\nval: images/val\ntest: images/test\n"
        f"nc: {len(CLASSES)}\nnames: {CLASSES}\n", encoding="utf-8")
    manifest = {
        **source_meta,
        "classes": CLASSES,
        "images": dict(counts),
        "splits": {split: counts.get(split, 0) for split in ("train", "val", "test")},
        "boxes_per_class": {CLASSES[c - 1]: n for c, n in sorted(boxes_per_class.items())},
        "duplicates_removed": sum(len(r.duplicates) for r in records),
        "annotations": "YOLO normalised cx cy w h",
        "split_policy": "source train/valid/test preserved; test isolated from train/val",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
