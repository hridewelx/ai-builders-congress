"""Command line: python -m ml.data prepare --source ... --name ..."""
from __future__ import annotations

import argparse
from pathlib import Path

from ..config import DET, VAL_FRACTION
from .dedupe import dedupe, dedupe_preserving_test
from .prepare import prepare
from .readers import read_jsonl, read_yolo
from .records import Record
from .splitting import export, split_records


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
    p.add_argument("--resplit", action="store_true",
                   help="ignore source train/valid/test folders and re-split 80/20")

    b = sub.add_parser("build", help="several sources, one canonical dataset")
    b.add_argument("--source", action="append", required=True, metavar="NAME=PATH")
    b.add_argument("--licence", action="append", default=[])
    b.add_argument("--out", type=Path, default=DET)
    b.add_argument("--val-fraction", type=float, default=VAL_FRACTION)
    b.add_argument("--resplit", action="store_true",
                   help="ignore source train/valid/test folders and re-split 80/20")
    args = parser.parse_args()

    if args.cmd == "prepare":
        prepare(args.source, args.name, args.out, args.names, args.licence,
                args.val_fraction, args.resplit)
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
    if args.resplit:
        records, dropped = dedupe(records)
        split_records(records, args.val_fraction, preserve_splits=False)
    else:
        records, dropped = dedupe_preserving_test(records)
        split_records(records, args.val_fraction, preserve_splits=True)
    manifest = export(records, args.out, {
        "sources": sources,
        "images_before_dedupe": before,
        "images_after_dedupe": len(records),
    })
    print(f"combined: {before} -> {len(records)} images ({dropped} duplicates)")
    print(f"train {manifest['images'].get('train', 0)} / val {manifest['images'].get('val', 0)} "
          f"/ test {manifest['images'].get('test', 0)}")
    print(f"boxes: {manifest['boxes_per_class']}")
    print(f"written -> {args.out}")
