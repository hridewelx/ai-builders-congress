"""Fetch and verify a packaged model before it is used.

Two sources, one rule: the SHA-256 must match before a single file is written.

    python scripts/fetch_model.py --zip dist/lotline-det-v2.zip --sha256 <hex>
    python scripts/fetch_model.py --url https://.../lotline-det-v2.zip --sha256 <hex>

The zip is unpacked into `--dest` (default `data/models`) and only the members
listed in the package's own manifest are written. Anything with a path
separator, an absolute path or a `..` component is refused, so a tampered
archive cannot write outside the destination.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import urllib.request
import zipfile
from pathlib import Path

ALLOWED = {"det_v2.onnx", "calibration_v2.json", "operating_point_v2.json",
           "MODEL_CARD.md", "eval_test_v2.json"}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_source(zip_path: Path | None, url: str | None) -> bytes:
    if zip_path is not None:
        return zip_path.read_bytes()
    if not url:
        raise SystemExit("pass --zip or --url")
    with urllib.request.urlopen(url, timeout=120) as response:  # noqa: S310 - explicit operator URL
        return response.read()


def safe_name(name: str) -> str:
    """Reject traversal, absolute paths and anything outside the allow-list."""
    pure = Path(name)
    if len(pure.parts) != 1 or name in {"", ".", ".."} or pure.is_absolute():
        raise SystemExit(f"refusing unsafe member name: {name!r}")
    if name not in ALLOWED and name != "manifest.json":
        raise SystemExit(f"refusing unexpected member: {name!r}")
    return name


def install(data: bytes, expected: str, dest: Path, dry_run: bool = False) -> list[Path]:
    actual = sha256_bytes(data)
    if actual != expected:
        raise SystemExit(f"checksum mismatch: expected {expected}, got {actual}")
    written: list[Path] = []
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        manifest = json.loads(zf.read("manifest.json"))
        for name, meta in manifest.get("files", {}).items():
            safe_name(name)
            payload = zf.read(name)
            if sha256_bytes(payload) != meta.get("sha256"):
                raise SystemExit(f"member {name} does not match the manifest hash")
            target = dest / name
            written.append(target)
            if not dry_run:
                dest.mkdir(parents=True, exist_ok=True)
                target.write_bytes(payload)
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify and install a packaged model.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--zip", type=Path)
    source.add_argument("--url")
    parser.add_argument("--sha256", required=True, help="SHA-256 of the zip itself")
    parser.add_argument("--dest", type=Path, default=Path("data/models"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    data = read_source(args.zip, args.url)
    written = install(data, args.sha256, args.dest, args.dry_run)
    for path in written:
        print(f"{'would write' if args.dry_run else 'wrote'} {path}")
    if not args.dry_run:
        print("model ready: /readyz should now report detector=onnx")
    return 0


if __name__ == "__main__":
    sys.exit(main())
