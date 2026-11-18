"""Backwards-compatible import path. Canonical module: app.services.vision."""
from app.services.vision import *  # noqa: F401,F403
from app.services.vision import (  # noqa: F401
    HUMAN_CLASSES,
    MODEL_DIR,
    MODEL_NAME,
    _state,
    _train_or_load,
    detect,
    evaluate_staged,
    knit_texture,
    model_sha,
    selftest,
    staged_photo,
)
