"""Lotline Vision: an on-device, unsupervised knit-texture anomaly detector.

This is a real model, not a stub:
  * features are computed from pixels (16-dim intensity thumbnail + colour,
    texture and gradient statistics per patch),
  * a small autoencoder (23 -> 12 -> 23, tanh) is trained with Adam on clean
    knit patches only -- no defect labels are used,
  * anomaly = reconstruction error, thresholded from a held-out clean
    calibration set, clustered into boxes, and classified by simple,
    documented heuristics into the four trained proposal classes.

It runs in-process over the canonical working copy and never writes a
severity, a count or a verdict. The detector only proposes; a human confirms.

The implementation is split by stage: params, state, textures, embedding,
model, detect, selftest. This module is the stable import surface.
"""
from __future__ import annotations

from .detect import _classify, _components, _heat_png, _iou, detect, quality  # noqa: F401
from .embedding import _ae_forward, _ae_init, _ae_train, _features  # noqa: F401
from .model import _train_or_load, model_sha  # noqa: F401
from .params import (
    FEATURE_DIM,
    HUMAN_CLASSES,
    MAX_SIDE,
    MODEL_CLASSES,
    MODEL_NAME,
    MODEL_PATH,
    PATCH,
    STRIDE,
)
from .selftest import evaluate_staged, selftest
from .state import _state  # noqa: F401
from .textures import _draw_defect, knit_texture, staged_photo  # noqa: F401

__all__ = [
    "MODEL_NAME", "MODEL_CLASSES", "HUMAN_CLASSES", "PATCH", "STRIDE", "FEATURE_DIM",
    "MAX_SIDE", "MODEL_PATH", "knit_texture", "staged_photo", "detect", "quality",
    "model_sha", "selftest", "evaluate_staged",
]
