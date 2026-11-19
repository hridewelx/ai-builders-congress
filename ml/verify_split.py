"""Verify that a built dataset does not contain BDFD9's official test images.

This is the guard the model card depends on. It checks exact SHA-256 matches and
the same near-duplicate rule used by ``ml.data`` (dHash within 2 bits plus a
thumbnail mean-absolute-difference of at most 1.5).

Usage:
    python -m ml.verify_split --data data/dataset/det_v2 \
        --raw-test data/raw/bdfd9/BDFD9/test
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .data import IMAGE_EXTS, dhash, hamming, pixel_mae, sha256_file


def images(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.suffix.lower() in IMAGE_EXTS)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check a dataset for official-test leakage.")
    parser.add_argument("--data", type=Path, default=Path("data/dataset/det_v2"))
    parser.add_argument("--raw-test", type=Path, default=Path("data/raw/bdfd9/BDFD9/test"))
    parser.add_argument("--out", type=Path, default=Path("data/models/split_integrity.json"),
                        help="JSON artifact the model card cites")
    args = parser.parse_args()

    test_images = images(args.raw_test)
    if not test_images:
        raise SystemExit(f"no images found under {args.raw_test}")
    by_sha = {sha256_file(path): path for path in test_images}
    by_hash = [(dhash(path), path) for path in test_images]

    checked = exact = near = 0
    examples: list[str] = []
    for split in ("train", "val"):
        for path in images(args.data / "images" / split):
            checked += 1
            digest = sha256_file(path)
            if digest in by_sha:
                exact += 1
                examples.append(f"exact: {path} == {by_sha[digest]}")
                continue
            fingerprint = dhash(path)
            match = next((other for other_hash, other in by_hash
                          if hamming(fingerprint, other_hash) <= 2
                          and pixel_mae(path, other) <= 1.5), None)
            if match is not None:
                near += 1
                examples.append(f"near: {path} ~ {match}")

    print(f"official test images: {len(test_images)}")
    print(f"train/val images checked: {checked}")
    print(f"exact leaks: {exact}")
    print(f"near-duplicate leaks: {near}")
    for line in examples[:20]:
        print(line)
    report = {
        "rule": "SHA-256 exact match plus dHash<=2 bits and thumbnail MAE<=1.5",
        "official_test_images": len(test_images),
        "train_val_images_checked": checked,
        "exact_leaks": exact,
        "near_duplicate_leaks": near,
        "examples": examples[:10],
        "passed": exact == 0 and near == 0,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"wrote {args.out}")
    if exact or near:
        print("FAIL: official test content is present in train/val", file=sys.stderr)
        return 1
    print("PASS: no official test image (exact or near-duplicate) in train/val")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
