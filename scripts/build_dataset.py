#!/usr/bin/env python3
"""Build (or download) the staged knitwear dataset used by the demo.

Everything here is synthetic and deterministic: the same seed produces the same
image and the same truth box. Nothing in this dataset comes from a real factory,
worker or buyer.

Usage
-----
    python scripts/build_dataset.py                      # build into data/dataset/v1
    python scripts/build_dataset.py --per-class 40       # bigger held-out set
    python scripts/build_dataset.py --verify             # re-hash an existing set
    python scripts/build_dataset.py --download URL --sha256 <hex>   # fetch a release

Output
------
    data/dataset/v1/images/<split>/<id>.jpg
    data/dataset/v1/annotations.jsonl
    data/dataset/v1/manifest.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tarfile
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services import vision  # noqa: E402

DATASET_VERSION = "v1"
DEFECT_CLASSES = ["hole", "oil_stain", "needle_line", "dropped_stitch", "skipped_stitch"]
FABRICS = [(150, 160, 175), (32, 44, 74), (196, 186, 168), (150, 74, 78), (128, 96, 118)]
SIZE = (560, 720)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build(out: Path, per_class: int, clean: int, seed_start: int) -> None:
    """Generate images, annotations and a manifest."""
    if out.exists():
        shutil.rmtree(out)
    (out / "images").mkdir(parents=True)
    records: list[dict] = []
    index = 0

    def emit(split: str, defects: list[str], seed: int) -> None:
        nonlocal index
        image, truth = vision.staged_photo(
            seed=seed, base=FABRICS[seed % len(FABRICS)], defects=defects, size=SIZE
        )
        name = f"{index:05d}_{seed}"
        rel = Path("images") / split / f"{name}.jpg"
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        image.save(out / rel, "JPEG", quality=90, optimize=True)
        records.append({
            "id": name,
            "split": split,
            "file": str(rel).replace("\\", "/"),
            "seed": seed,
            "defects": truth,
            "label": defects[0] if defects else "clean",
        })
        index += 1

    # held-out split first so the generator never sees evaluation seeds twice
    for i, kind in enumerate(DEFECT_CLASSES):
        for j in range(per_class):
            emit("test" if j % 5 == 0 else "train", [kind], seed_start + i * 1000 + j)
    for j in range(clean):
        emit("test" if j % 5 == 0 else "train", [], seed_start + 90_000 + j)

    with (out / "annotations.jsonl").open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, sort_keys=True) + "\n")

    by_split: dict[str, int] = {}
    for record in records:
        by_split[record["split"]] = by_split.get(record["split"], 0) + 1
    manifest = {
        "dataset": "lotline-knit-staged",
        "version": DATASET_VERSION,
        "generator": f"app.services.vision.staged_photo ({vision.MODEL_NAME})",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "synthetic": True,
        "real_photos": 0,
        "consent_required": False,
        "note": "Procedural knit panels with injected defects. Not factory evidence.",
        "size": list(SIZE),
        "classes": DEFECT_CLASSES,
        "fabric_colours": len(FABRICS),
        "counts": {"total": len(records), **by_split,
                   "by_label": {k: sum(1 for r in records if r["label"] == k)
                                for k in DEFECT_CLASSES + ["clean"]}},
        "annotations_sha256": sha256_file(out / "annotations.jsonl"),
        "files": {record["file"]: sha256_file(out / record["file"]) for record in records},
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"built {manifest['counts']['total']} images -> {out}")
    print(f"  train {by_split.get('train', 0)} · test {by_split.get('test', 0)}")
    print(f"  annotations sha256 {manifest['annotations_sha256'][:16]}…")


def verify(out: Path) -> int:
    """Recompute every hash in the manifest. Returns a process exit code."""
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    bad = 0
    for rel, expected in manifest["files"].items():
        path = out / rel
        if not path.exists():
            print(f"MISSING {rel}")
            bad += 1
        elif sha256_file(path) != expected:
            print(f"CHANGED {rel}")
            bad += 1
    actual = sha256_file(out / "annotations.jsonl")
    if actual != manifest["annotations_sha256"]:
        print("CHANGED annotations.jsonl")
        bad += 1
    print(f"verified {len(manifest['files'])} files, {bad} problems")
    return 1 if bad else 0


def download(url: str, sha256: str, out: Path) -> None:
    """Fetch a released dataset archive and verify its digest before unpacking."""
    if out.exists():
        shutil.rmtree(out)
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(url).suffix) as tmp:
        print(f"downloading {url}")
        with urllib.request.urlopen(url) as response, open(tmp.name, "wb") as fh:
            shutil.copyfileobj(response, fh)
        digest = sha256_file(Path(tmp.name))
        if sha256 and digest != sha256:
            os.unlink(tmp.name)
            raise SystemExit(f"sha256 mismatch: got {digest}, expected {sha256}")
        print(f"sha256 {digest[:16]}… ok")
        out.parent.mkdir(parents=True, exist_ok=True)
        if url.endswith((".tar.gz", ".tgz")):
            with tarfile.open(tmp.name) as archive:
                archive.extractall(out.parent, filter="data")
        elif url.endswith(".zip"):
            with zipfile.ZipFile(tmp.name) as archive:
                archive.extractall(out.parent)
        else:
            raise SystemExit("unsupported archive type (expected .tar.gz, .tgz or .zip)")
        os.unlink(tmp.name)
    print(f"extracted -> {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=ROOT / "data" / "dataset" / DATASET_VERSION)
    parser.add_argument("--per-class", type=int, default=20, help="images per defect class (default 20)")
    parser.add_argument("--clean", type=int, default=40, help="clean images (default 40)")
    parser.add_argument("--seed-start", type=int, default=10_000)
    parser.add_argument("--download", metavar="URL", help="fetch a released dataset archive instead")
    parser.add_argument("--sha256", default="", help="expected digest for --download")
    parser.add_argument("--verify", action="store_true", help="verify an existing dataset and exit")
    args = parser.parse_args()

    if args.verify:
        raise SystemExit(verify(args.out))
    if args.download:
        download(args.download, args.sha256, args.out)
        raise SystemExit(verify(args.out))
    build(args.out, args.per_class, args.clean, args.seed_start)


if __name__ == "__main__":
    main()
