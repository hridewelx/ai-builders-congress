"""An append-only record of which model artifacts actually exist.

mAP tells a pilot nothing about "what changed last Tuesday". This file answers
that with bytes: every run appends one line naming the checkpoint, the ONNX
export, the card and the operating point, each with its hash. It is JSONL on
purpose — append-only, diff-friendly, and readable without a database.
"""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .config import MODEL_NAME, MODEL_VERSION, MODELS

REGISTRY = MODELS / "registry.jsonl"
TRACKED = {
    "checkpoint": MODELS / "det_v2b.pt",
    "onnx": MODELS / "det_v2.onnx",
    "card_md": Path("docs/MODEL_CARD.md"),
    "card_json": MODELS / "model_card_trained.json",
    "evaluation": MODELS / "eval_test_v2.json",
    "operating_point": MODELS / "operating_point_v2.json",
    "calibration": MODELS / "calibration_v2.json",
    "reliability": MODELS / "reliability_v2.json",
}


def _sha(path: Path) -> str | None:
    from .data import sha256_file

    try:
        return sha256_file(path)
    except OSError:
        return None


def git_commit() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True, check=True, timeout=10).stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def entry(note: str = "", tracked: dict[str, Path] | None = None) -> dict:
    """Build one registry record from the artifacts present on disk."""
    tracked = tracked or TRACKED
    return {
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": MODEL_NAME,
        "version": MODEL_VERSION,
        "git_commit": git_commit(),
        "note": note,
        "artifacts": {name: {"path": str(path), "sha256": _sha(path)} for name, path in tracked.items()},
    }


def append(record: dict, path: Path = REGISTRY) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def history(path: Path = REGISTRY) -> list[dict]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    return [json.loads(line) for line in lines if line.strip()]


def latest(path: Path = REGISTRY) -> dict | None:
    entries = history(path)
    return entries[-1] if entries else None


def record(note: str = "") -> dict:
    """Record the current state of the artifacts."""
    return append(entry(note))


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Record or show model artifacts.")
    parser.add_argument("--record", action="store_true", help="append an entry for the current artifacts")
    parser.add_argument("--note", default="")
    args = parser.parse_args()
    if args.record:
        print(json.dumps(record(args.note), indent=2))
        return
    print(json.dumps(latest() or {"registry": "empty"}, indent=2))


if __name__ == "__main__":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    main()
