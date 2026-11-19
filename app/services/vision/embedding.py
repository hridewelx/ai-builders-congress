"""Per-patch features and the small autoencoder that learns clean knit only."""
from __future__ import annotations

import math

import numpy as np
from PIL import Image

from .params import FEATURE_DIM, PATCH, STRIDE


def _features(rgb: np.ndarray) -> tuple[np.ndarray, int, int]:
    """Per-patch appearance embedding, robust to exposure and fabric colour.

    Includes a contrast-normalised 3x3 thumbnail (texture), luminance relative
    to the image median (darkness), chroma ratios (stain), and gradient
    statistics (lines). A uniform dark hole still deviates through `lum`.
    """
    h, w = rgb.shape[:2]
    f = rgb.astype(np.float32)
    g = f @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    med_lum = float(np.median(g)) + 1e-3
    chroma = f.sum(axis=2) + 1e-3
    r_ref = float(np.median(f[..., 0] / chroma)) + 1e-3
    g_ref = float(np.median(f[..., 1] / chroma)) + 1e-3
    gx = np.abs(np.diff(g, axis=1, prepend=g[:, :1]))
    gy = np.abs(np.diff(g, axis=0, prepend=g[:1, :]))
    gradf = (gx + gy) * 0.5
    rows = []
    for y in range(0, h - PATCH + 1, STRIDE):
        row = []
        for x in range(0, w - PATCH + 1, STRIDE):
            pg = g[y:y + PATCH, x:x + PATCH]
            pp = f[y:y + PATCH, x:x + PATCH]
            m = float(pg.mean()) + 1e-3
            thumb = np.array(Image.fromarray(pg.astype(np.uint8)).resize((3, 3), Image.BILINEAR),
                             dtype=np.float32).ravel() / 255.0
            thumb = thumb / (thumb.mean() + 1e-6) - 1.0
            lum = m / med_lum
            chroma_d = np.array([float((pp[..., 0] / (pp.sum(axis=2) + 1e-3)).mean()) - r_ref,
                                 float((pp[..., 1] / (pp.sum(axis=2) + 1e-3)).mean()) - g_ref]) * 8.0
            contrast = float(pg.std()) / m
            grad = float(gradf[y:y + PATCH, x:x + PATCH].mean()) / m
            aniso = float(abs(gx[y:y + PATCH, x:x + PATCH].mean() - gy[y:y + PATCH, x:x + PATCH].mean())) / m
            row.append(np.concatenate([thumb, [lum, contrast, grad, aniso], chroma_d]))
        rows.append(np.array(row, dtype=np.float32))
    return np.stack(rows), len(rows), (len(rows[0]) if rows else 0)


def _ae_init(rng):
    return {
        "W1": (rng.normal(0, 1 / math.sqrt(FEATURE_DIM), (FEATURE_DIM, 12))).astype(np.float32),
        "b1": np.zeros(12, np.float32),
        "W2": (rng.normal(0, 1 / math.sqrt(12), (12, FEATURE_DIM))).astype(np.float32),
        "b2": np.zeros(FEATURE_DIM, np.float32),
    }


def _ae_forward(par, X):
    z = np.tanh(X @ par["W1"] + par["b1"])
    return z, z @ par["W2"] + par["b2"]


def _ae_train(X, steps=900, lr=0.01, seed=7):
    rng = np.random.default_rng(seed)
    par = _ae_init(rng)
    m = {k: np.zeros_like(v) for k, v in par.items()}
    v = {k: np.zeros_like(x) for k, x in par.items()}
    b1, b2, eps = 0.9, 0.999, 1e-8
    n = len(X)
    for t in range(1, steps + 1):
        idx = rng.integers(0, n, min(256, n))
        xb = X[idx]
        z, out = _ae_forward(par, xb)
        err = out - xb
        gW2 = z.T @ err / len(xb)
        gb2 = err.mean(axis=0)
        dz = (err @ par["W2"].T) * (1 - z ** 2)
        gW1 = xb.T @ dz / len(xb)
        gb1 = dz.mean(axis=0)
        for k, gk in (("W1", gW1), ("b1", gb1), ("W2", gW2), ("b2", gb2)):
            m[k] = b1 * m[k] + (1 - b1) * gk
            v[k] = b2 * v[k] + (1 - b2) * (gk ** 2)
            mh = m[k] / (1 - b1 ** t)
            vh = v[k] / (1 - b2 ** t)
            par[k] -= (lr * mh / (np.sqrt(vh) + eps)).astype(np.float32)
    return par
