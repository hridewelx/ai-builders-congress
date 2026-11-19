"""Shared configuration for the Lotline detector workstream.

The shipped detector answers one question only: where are visible surface
defects of these four types? Severity, counts and the lot outcome stay in the
human review and the deterministic engine.
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("LOTLINE_DATA", ROOT / "data"))
RAW = DATA / "raw"
DET = DATA / "dataset" / "det_v2"
MODELS = DATA / "models"

# Version-1 detector classes. Skipped stitch, shade band and everything else is
# entered by a human reviewer, because no open dataset labels them reliably.
CLASSES = ["hole", "oil_stain", "needle_line", "dropped_stitch"]
CLASS_TO_ID = {name: i + 1 for i, name in enumerate(CLASSES)}  # 0 is background

# Public class names -> Lotline class. None means "not a v1 class"; images whose
# only labels are None are excluded rather than taught as clean.
SOURCE_CLASS_MAP = {
    "hole": "hole",
    "holes": "hole",
    "oil spot": "oil_stain",
    "oilspot": "oil_stain",
    "oil stain": "oil_stain",
    "stains": "oil_stain",
    "stain": "oil_stain",
    "spot": "oil_stain",
    "dropstitch": "dropped_stitch",
    "dropped stitch": "dropped_stitch",
    "dropped_stitch": "dropped_stitch",
    "loop mark": "dropped_stitch",
    "needle mark": "needle_line",
    "needle line": "needle_line",
    "needle_line": "needle_line",
    "vertical linemark": "needle_line",  # approximate: linear mark, orientation differs
    "horizontal mark": None,
    "knot": None,
    "setup": None,
    "set up": None,
    "slub": None,
    "yarn dust": None,
    "yarn missing": None,
    "contamination": None,
}

# Training defaults; override on the command line.
IMG_SIZE = 640
SEED = 42
SCORE_THRESHOLD = 0.5
IOU_THRESHOLD = 0.5
VAL_FRACTION = 0.2
