"""Prepare one dataset: read, map, de-duplicate, split, export."""
from __future__ import annotations

from pathlib import Path

from .dedupe import dedupe, dedupe_preserving_test
from .readers import discover_names, read_jsonl, read_yolo
from .splitting import export, split_records


def prepare(source: Path, name: str, out: Path, names: list[str] | None, licence: str,
            val_fraction: float, resplit: bool = False) -> None:
    if (source / "annotations.jsonl").exists():
        records = read_jsonl(source, name)
        names = names or CLASSES
    else:
        found = discover_names(source, names)
        if not found:
            raise SystemExit("could not find class names; pass --names")
        records = read_yolo(source, name, found)
    before = len(records)
    if resplit:
        records, dropped = dedupe(records)
        split_records(records, val_fraction, preserve_splits=False)
    else:
        records, dropped = dedupe_preserving_test(records)
        split_records(records, val_fraction, preserve_splits=True)
    manifest = export(records, out, {
        "source": name,
        "source_path": str(source),
        "licence": licence,
        "images_before_dedupe": before,
        "images_after_dedupe": len(records),
    })
    print(f"{name}: {before} -> {len(records)} images ({dropped} duplicates), "
          f"train {manifest['images'].get('train', 0)} / val {manifest['images'].get('val', 0)} "
          f"/ test {manifest['images'].get('test', 0)}")
    print(f"boxes: {manifest['boxes_per_class']}")
    print(f"written -> {out}")
