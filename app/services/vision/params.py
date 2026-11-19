"""Public identities and patch geometry for the unsupervised detector."""
from __future__ import annotations

import os

from ...config import MODEL_DIR

MODEL_NAME = "ae-knit-v1"
MODEL_CLASSES = ("hole", "oil_stain", "needle_line", "dropped_stitch")
HUMAN_CLASSES = ("hole", "dropped_stitch", "skipped_stitch", "needle_line", "oil_stain", "shade_band", "other")
PATCH = 32
STRIDE = 16
FEATURE_DIM = 15
MAX_SIDE = 900
MODEL_PATH = os.path.join(MODEL_DIR, "ae_knit_v1.npz")
