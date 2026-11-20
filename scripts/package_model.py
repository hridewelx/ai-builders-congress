"""Package the trained detector for hosting, with a verifiable manifest.

The demo runs the numpy baseline today only because the ONNX artifact never
leaves this machine: `data/` is git-ignored, so a hosted build cannot see it.
This script produces one zip that a host can download and verify.

    python scripts/package_model.py --out dist/lotline-det-v2.zip

The zip is self-describing: `manifest.json` lists every member with its size and
SHA-256, plus the evaluation numbers the model card cites.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

VERSION = "det-v2"
MEMBERS = {
    "det_v2.onnx": Path("data/models/det_v2.onnx"),
    "calibration_v2.json": Path("data/models/calibration_v2.json"),
    "operating_point_v2.json": Path("data/models/operating_point_v2.json"),
    "MODEL_CARD.md": Path("docs/MODEL_CARD.md"),
    "eval_test_v2.json": Path("data/models/eval_test_v2.json"),
    "model_card_trained.json": Path("data/models/model_card_trained.json"),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package(out: Path, members: dict[str, Path] | None = None) -> dict:
    """Write the zip and return its manifest. Refuses on any missing member."""
    chosen = members or MEMBERS
    missing = [name for name, path in chosen.items() if not path.exists()]
    if missing:
        raise SystemExit(f"missing artefacts, refusing to package: {', '.join(missing)}")

    entries = {name: {"sha256": sha256(path), "bytes": path.stat().st_size}
               for name, path in chosen.items()}
    metrics: dict = {}
    try:
        saved = json.loads(chosen["eval_test_v2.json"].read_text(encoding="utf-8"))
        metrics = {key: saved.get(key) for key in
                   ("split", "images", "gt_boxes", "map50", "precision", "recall")}
        headline = (saved.get("per_source") or {}).get("bdfd9")
        if headline:
            metrics["bdfd9"] = {key: headline.get(key) for key in
                                ("images", "gt_boxes", "map50", "precision", "recall")}
    except (KeyError, OSError, ValueError):
        metrics = {"note": "no saved evaluation shipped with this package"}

    manifest = {
        "package": VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "classes": ["hole", "oil_stain", "needle_line", "dropped_stitch"],
        "input": "RGB image, resized to 640x640, float32 0-1",
        "output": "boxes, scores, labels; the app applies its own threshold and cap",
        "evaluation": metrics,
        "files": entries,
        "licence": {
            "code": "BSD-3-Clause (torchvision)",
            "training_data": "BDFD9, CC BY 4.0 — attribution required",
        },
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))
        for name, path in chosen.items():
            zf.write(path, name)
    manifest["zip_sha256"] = sha256(out)
    manifest["zip_bytes"] = out.stat().st_size
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Package the detector for hosting.")
    parser.add_argument("--out", type=Path, default=Path("dist/lotline-det-v2.zip"))
    args = parser.parse_args()
    manifest = package(args.out)
    print(json.dumps({k: manifest[k] for k in ("package", "zip_bytes", "zip_sha256")}, indent=2))
    print(f"wrote {args.out}")
    print("host with: python scripts/fetch_model.py --zip <file> --sha256 "
          f"{manifest['zip_sha256']}")


if __name__ == "__main__":
    main()
