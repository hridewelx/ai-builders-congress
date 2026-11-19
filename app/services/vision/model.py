"""Training, loading and hashing the on-device anomaly model."""
from __future__ import annotations

import hashlib
import os
import time

import numpy as np

from ...config import MODEL_DIR
from .embedding import _ae_forward, _ae_train, _features
from .params import FEATURE_DIM, MODEL_CLASSES, MODEL_PATH
from .state import _state
from .textures import knit_texture


def _train_or_load(force=False) -> dict:
    if _state.get("model") and not force:
        return _state["model"]
    os.makedirs(MODEL_DIR, exist_ok=True)
    if os.path.exists(MODEL_PATH) and not force:
        z = np.load(MODEL_PATH)
        model = {k: z[k] for k in z.files if k != "meta"}
        meta = np.load(MODEL_PATH, allow_pickle=True)["meta"].item()
        model["meta"] = meta
        _state["model"] = model
        return model

    t0 = time.time()
    clean = []
    for i in range(26):
        tex = knit_texture(360, 360, base=(150, 160, 175) if i % 2 else (110, 120, 96), seed=1000 + i,
                           period=6 + (i % 4))
        clean.append(_features(tex)[0].reshape(-1, FEATURE_DIM))
    X = np.concatenate(clean)
    mu, sd = X.mean(0), X.std(0) + 1e-6
    Xn = (X - mu) / sd
    par = _ae_train(Xn, steps=1100)
    # calibrate on held-out clean patches (different seeds)
    hold = []
    for i in range(8):
        tex = knit_texture(360, 360, base=(90, 100, 120), seed=5000 + i, period=5 + (i % 5))
        hold.append(_features(tex)[0].reshape(-1, FEATURE_DIM))
    H = (np.concatenate(hold) - mu) / sd
    _, rec = _ae_forward(par, H)
    err = ((rec - H) ** 2).mean(1)
    model = {**par, "mu": mu, "sd": sd, "thr": float(np.quantile(err, 0.995)),
             "meta": {"trained_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                      "train_patches": int(len(X)), "calib_patches": int(len(H)),
                      "train_seconds": round(time.time() - t0, 1),
                      "classes": list(MODEL_CLASSES)}}
    np.savez_compressed(MODEL_PATH, **{k: v for k, v in model.items() if k != "meta"},
                        meta=np.array(model["meta"], dtype=object))
    _state["model"] = model
    return model


def model_sha() -> str:
    _train_or_load()
    h = hashlib.sha256()
    with open(MODEL_PATH, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
