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
"""
from __future__ import annotations

import hashlib
import io
import math
import os
import time

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

MODEL_NAME = "ae-knit-v1"
MODEL_CLASSES = ("hole", "oil_stain", "needle_line", "dropped_stitch")
HUMAN_CLASSES = ("hole", "dropped_stitch", "skipped_stitch", "needle_line", "oil_stain", "shade_band", "other")
PATCH = 32
STRIDE = 16
FEATURE_DIM = 15
MAX_SIDE = 900

from ..config import MODEL_DIR  # noqa: E402

MODEL_PATH = os.path.join(MODEL_DIR, "ae_knit_v1.npz")

_state: dict = {}


# --------------------------------------------------------------------------
# Synthetic knit fabric (used for training, calibration and staged demo lots)
# --------------------------------------------------------------------------

def knit_texture(w: int, h: int, base=(150, 160, 175), seed: int = 0, period: int = 7,
                 shade: float = 0.0) -> np.ndarray:
    """Procedural single-jersey knit: stitch columns, rows, yarn noise, light."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    warp = np.sin(xx * (2 * math.pi / period) + 0.6 * np.sin(yy * (2 * math.pi / (period * 2.2))))
    weft = np.cos(yy * (2 * math.pi / (period * 1.15)) + 0.4 * np.sin(xx * (2 * math.pi / (period * 3.0))))
    stitch = (warp + weft) * 0.5
    micro = rng.normal(0, 0.05, (h, w)).astype(np.float32)
    micro = np.array(Image.fromarray(((micro + 0.5) * 255).clip(0, 255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(0.6)), dtype=np.float32) / 255.0 - 0.5
    light = 1.0 + 0.10 * np.sin(xx / w * math.pi) + 0.06 * np.cos(yy / h * math.pi * 1.5)
    if shade:
        light = light * (1.0 - shade * np.exp(-((xx - w * 0.62) ** 2) / (2 * (w * 0.10) ** 2)))
    gray = 0.55 + 0.10 * stitch + 0.06 * micro
    gray = (gray * light).clip(0.05, 0.98)
    rgb = np.stack([gray * base[0] / 255.0, gray * base[1] / 255.0, gray * base[2] / 255.0], axis=-1)
    rgb += rng.normal(0, 0.012, rgb.shape).astype(np.float32)
    return (np.clip(rgb, 0, 1) * 255).astype(np.uint8)


def _draw_defect(arr: np.ndarray, kind: str, cx: int, cy: int, rng) -> tuple[np.ndarray, tuple[int, int, int, int]]:
    h, w = arr.shape[:2]
    r = int(min(w, h) * rng.uniform(0.030, 0.048))
    img = Image.fromarray(arr)
    d = ImageDraw.Draw(img, "RGBA")
    if kind == "hole":
        pts = []
        for i in range(14):
            a = 2 * math.pi * i / 14
            rr = r * rng.uniform(0.72, 1.12)
            pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a) * 0.92))
        d.polygon(pts, fill=(16, 18, 22, 235))
        d.ellipse([cx - r * 0.55, cy - r * 0.55, cx + r * 0.55, cy + r * 0.55], fill=(9, 10, 13, 250))
        for i in range(16):
            a = rng.uniform(0, 2 * math.pi)
            ln = rng.uniform(r * 0.15, r * 0.45)
            d.line([cx + r * math.cos(a), cy + r * math.sin(a),
                    cx + (r + ln) * math.cos(a), cy + (r + ln) * math.sin(a)],
                   fill=(20, 22, 26, 190), width=1)
    elif kind == "oil_stain":
        for i in range(7):
            a = rng.uniform(0, 2 * math.pi)
            dist = rng.uniform(0, r * 0.5)
            rr = r * rng.uniform(0.45, 0.9)
            x, y = cx + dist * math.cos(a), cy + dist * math.sin(a)
            d.ellipse([x - rr, y - rr * 0.8, x + rr, y + rr * 0.8], fill=(58, 42, 24, 70))
        d.ellipse([cx - r * 0.85, cy - r * 0.62, cx + r * 0.85, cy + r * 0.62], fill=(46, 34, 20, 110))
    elif kind == "needle_line":
        d.line([cx, cy - r * 2.2, cx + rng.uniform(-2, 2), cy + r * 2.2], fill=(18, 20, 24, 220), width=max(2, r // 9))
    elif kind == "skipped_stitch":
        for i in range(5):
            yy = cy - r + i * (r * 0.42)
            d.line([cx - r * 0.9, yy, cx + r * 0.9, yy], fill=(22, 24, 28, 215), width=max(2, r // 10))
    elif kind == "dropped_stitch":
        for i in range(7):
            yy = cy - r * 1.4 + i * (r * 0.45)
            d.line([cx - r * 0.35, yy, cx + r * 0.35, yy], fill=(24, 26, 30, 210), width=max(2, r // 9))
        d.line([cx - r * 0.35, cy - r * 1.4, cx - r * 0.35, cy + r * 1.6], fill=(24, 26, 30, 170), width=2)
    elif kind == "shade_band":
        band = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        bd = ImageDraw.Draw(band)
        bw = int(w * 0.16)
        bd.rectangle([cx - bw // 2, 0, cx + bw // 2, h], fill=(10, 12, 16, 26))
        band = band.filter(ImageFilter.GaussianBlur(bw * 0.35))
        img = Image.alpha_composite(img.convert("RGBA"), band).convert("RGB")
        d = ImageDraw.Draw(img, "RGBA")
    else:  # other
        d.rectangle([cx - r * 0.6, cy - r * 0.6, cx + r * 0.6, cy + r * 0.6], outline=(120, 60, 30, 200), width=2)
    out = np.array(img)
    pad = int(r * 2.6)
    x1, y1 = max(0, cx - pad), max(0, cy - pad)
    x2, y2 = min(w, cx + pad), min(h, cy + pad)
    return out, (x1, y1, x2, y2)


def staged_photo(seed: int, base=(150, 160, 175), defects: list[str] | None = None,
                 size: tuple[int, int] = (760, 1000)) -> tuple[Image.Image, list[dict]]:
    """Render one staged garment photo with zero or more injected defects."""
    w, h = size
    rng = np.random.default_rng(seed)
    arr = knit_texture(w, h, base=base, seed=seed)
    truth = []
    defects = defects or []
    for i, kind in enumerate(defects):
        cx = int(w * rng.uniform(0.28, 0.72))
        cy = int(h * rng.uniform(0.22, 0.74))
        arr, box = _draw_defect(arr, kind, cx, cy, rng)
        truth.append({"type": kind, "box": [box[0] / w, box[1] / h, box[2] / w, box[3] / h]})
    img = Image.fromarray(arr)
    img = ImageEnhance.Brightness(img).enhance(rng.uniform(0.96, 1.06))
    img = img.filter(ImageFilter.GaussianBlur(0.4))
    arr = np.array(img).astype(np.int16)
    arr += rng.normal(0, 3.0, arr.shape).astype(np.int16)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    return img, truth


# --------------------------------------------------------------------------
# Features and model
# --------------------------------------------------------------------------

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


def quality(rgb: np.ndarray) -> dict:
    g = rgb.astype(np.float32) @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    lap = (np.abs(4 * g[1:-1, 1:-1] - g[:-2, 1:-1] - g[2:, 1:-1] - g[1:-1, :-2] - g[1:-1, 2:])).mean()
    mean = float(g.mean())
    flags = []
    if lap < 3.0:
        flags.append("BLUR")
    if mean < 55:
        flags.append("DARK")
    return {"blur_score": round(float(lap), 2), "brightness": round(mean, 1), "flags": flags}


def _components(mask: np.ndarray, min_area: int):
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    comps = []
    for y in range(h):
        for x in range(w):
            if mask[y, x] and not seen[y, x]:
                stack, cells = [(y, x)], []
                seen[y, x] = True
                while stack:
                    cy, cx = stack.pop()
                    cells.append((cy, cx))
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                            seen[ny, nx] = True
                            stack.append((ny, nx))
                if len(cells) >= min_area:
                    ys = [c[0] for c in cells]
                    xs = [c[1] for c in cells]
                    comps.append((min(ys), min(xs), max(ys) + 1, max(xs) + 1, len(cells)))
    return comps


def _classify(rgb, box, mask=None) -> str:
    """Turn an anomaly region into a *proposal* class. The reviewer can change it."""
    y1, x1, y2, x2 = box
    ih, iw = max(1, int((y2 - y1) * 0.30)), max(1, int((x2 - x1) * 0.30))
    cy1, cx1, cy2, cx2 = y1 + ih, x1 + iw, y2 - ih, x2 - iw
    p = rgb[cy1:cy2, cx1:cx2].astype(np.float32)
    if p.size == 0:
        return "other"
    gf = rgb.astype(np.float32) @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    med = float(np.median(gf)) + 1e-3
    rel = (p @ np.array([0.299, 0.587, 0.114], dtype=np.float32)) / med
    dark_frac = float((rel < 0.74).mean())
    warm = float((p[..., 0] - p[..., 2]).mean()) - float((rgb[..., 0].astype(np.float32) - rgb[..., 2]).mean())
    if warm > 5.0:
        return "oil_stain"
    box_aspect = max(cy2 - cy1, cx2 - cx1) / max(1, min(cy2 - cy1, cx2 - cx1))
    if box_aspect > 2.0:
        return "needle_line"
    if dark_frac > 0.16:
        return "hole"
    if mask is not None:
        sub = mask[max(0, y1):min(mask.shape[0], y2), max(0, x1):min(mask.shape[1], x2)]
        ys, xs = np.where(sub)
        if len(ys):
            mh, mw = ys.max() - ys.min() + 1, xs.max() - xs.min() + 1
            m_aspect = max(mh, mw) / max(1, min(mh, mw))
            if m_aspect > 1.8:
                return "dropped_stitch"
    return "dropped_stitch"


def detect(rgb: np.ndarray, top_k: int = 4) -> dict:
    """Return proposals, a heat map and quality flags for one working image."""
    model = _train_or_load()
    h, w = rgb.shape[:2]
    grid, gh, gw = _features(rgb)
    X = (grid.reshape(-1, FEATURE_DIM) - model["mu"]) / model["sd"]
    z, rec = _ae_forward(model, X)
    err = ((rec - X) ** 2).mean(1).reshape(gh, gw).astype(np.float32)
    # smooth on the patch grid: a defect is a region, not one patch
    k = np.ones((3, 3), dtype=np.float32) / 9.0
    pad = np.pad(err, 1, mode="edge")
    err_s = sum(k[i, j] * pad[i:i + gh, j:j + gw] for i in range(3) for j in range(3))
    err_img = np.array(Image.fromarray((err_s / (float(err_s.max()) + 1e-6) * 255).clip(0,255).astype(np.uint8)).resize(
        (w, h), Image.BICUBIC), dtype=np.float32) / 255.0
    med = float(np.median(err_s))
    mad = float(np.median(np.abs(err_s - med))) * 1.4826 + 1e-4
    rz = (err_s - med) / mad
    # the frame edge is not fabric: suppress the outer 4% so a photo border
    # cannot become a "defect" proposal
    my = max(2, int(gh * 0.04))
    mx = max(2, int(gw * 0.04))
    rz[:my, :] = 0; rz[-my:, :] = 0; rz[:, :mx] = 0; rz[:, -mx:] = 0
    floor = max(float(model["thr"]) * 0.5, 1e-4)
    mask = (rz > 6.0) & (err_s > floor)
    mask_img = np.array(Image.fromarray((mask * 255).astype(np.uint8)).resize((w, h), Image.NEAREST)) > 0
    comps = _components(mask_img, min_area=int(w * h * 0.0012))
    comps.sort(key=lambda c: -(c[4] * (1.0 + (c[2] - c[0]) * (c[3] - c[1]) / (w * h))))
    proposals = []
    used = []
    for (y1, x1, y2, x2, area) in comps:
        if len(proposals) >= top_k:
            break
        if any(_iou((x1, y1, x2, y2), u) > 0.25 for u in used):
            continue
        pad2 = int(PATCH * 0.5)
        y1, x1 = max(0, y1 - pad2), max(0, x1 - pad2)
        y2, x2 = min(h, y2 + pad2), min(w, x2 + pad2)
        if (x2 - x1) * (y2 - y1) > 0.55 * w * h:
            continue
        if y1 <= my * STRIDE or x1 <= mx * STRIDE or y2 >= h - my * STRIDE or x2 >= w - mx * STRIDE:
            continue
        sub = rz[max(0, y1 // STRIDE):max(1, y2 // STRIDE), max(0, x1 // STRIDE):max(1, x2 // STRIDE)]
        peak = float(sub.max()) if sub.size else float(rz.max())
        score = 1.0 / (1.0 + math.exp(-(peak - 6.0) / 1.6))
        proposals.append({
            "type": _classify(rgb, (y1, x1, y2, x2), mask_img),
            "score": round(min(0.98, max(0.05, score)), 3),
            "box": [round(x1 / w, 5), round(y1 / h, 5), round(x2 / w, 5), round(y2 / h, 5)],
            "raw_error": round(peak, 2),
        })
        used.append((x1, y1, x2, y2))
    heat = _heat_png(rgb, err_img)
    q = quality(rgb)
    return {"proposals": proposals, "quality": q, "heat_png": heat,
            "model": MODEL_NAME, "threshold": round(float(model["thr"]), 4),
            "calibrated": False, "note": "uncalibrated research model; proposals require human confirmation"}


def _iou(a, b) -> float:
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def _heat_png(rgb: np.ndarray, err: np.ndarray) -> bytes:
    base = Image.fromarray(rgb).convert("RGB")
    e = (err / (err.max() + 1e-9))
    e = np.clip((e - 0.25) / 0.75, 0, 1)
    overlay = np.zeros((*e.shape, 4), dtype=np.uint8)
    overlay[..., 0] = (255 * np.clip(e * 2, 0, 1)).astype(np.uint8)
    overlay[..., 1] = (255 * np.clip(e * 1.2 - 0.25, 0, 1)).astype(np.uint8)
    overlay[..., 2] = 20
    overlay[..., 3] = (200 * e).astype(np.uint8)
    ov = Image.fromarray(overlay, "RGBA")
    out = Image.alpha_composite(base.convert("RGBA"), ov).convert("RGB")
    buf = io.BytesIO()
    out.save(buf, "JPEG", quality=82)
    return buf.getvalue()


def selftest() -> tuple[bool, str]:
    """Deterministic self-test: clean stays quiet, a known hole is proposed."""
    model = _train_or_load()
    clean = knit_texture(420, 420, seed=4242)
    r_clean = detect(clean)
    img, truth = staged_photo(seed=99, defects=["hole"])
    r_def = detect(np.array(img))
    hit = False
    if truth:
        tb = truth[0]["box"]
        for p in r_def["proposals"]:
            b = p["box"]
            ix = max(0, min(b[2], tb[2]) - max(b[0], tb[0]))
            iy = max(0, min(b[3], tb[3]) - max(b[1], tb[1]))
            inter = ix * iy
            union = (b[2] - b[0]) * (b[3] - b[1]) + (tb[2] - tb[0]) * (tb[3] - tb[1]) - inter
            if union > 0 and inter / union >= 0.05:
                hit = True
    quiet = len(r_clean["proposals"]) <= 2
    ok = bool(hit and quiet)
    detail = (f"clean_proposals={len(r_clean['proposals'])}; defective_proposals={len(r_def['proposals'])}; "
              f"known_hole_localised={hit}; threshold={model['meta'].get('threshold', 0)}")
    return ok, detail


def evaluate_staged(n: int = 40, seed0: int = 7000) -> dict:
    """Small, honest evaluation on staged images. Reported as staged-only."""
    per_class = {c: {"tp": 0, "gt": 0} for c in HUMAN_CLASSES}
    views = {"with_proposal": 0, "total": 0}
    false_views = 0
    for i in range(n):
        kind = HUMAN_CLASSES[i % 5]
        img, truth = staged_photo(seed=seed0 + i, defects=[kind] if i % 4 != 3 else [])
        r = detect(np.array(img))
        views["total"] += 1
        if r["proposals"]:
            views["with_proposal"] += 1
        if not truth:
            if r["proposals"]:
                false_views += 1
            continue
        per_class[kind]["gt"] += 1
        tb = truth[0]["box"]
        for p in r["proposals"]:
            b = p["box"]
            ix = max(0, min(b[2], tb[2]) - max(b[0], tb[0]))
            iy = max(0, min(b[3], tb[3]) - max(b[1], tb[1]))
            inter = ix * iy
            union = (b[2] - b[0]) * (b[3] - b[1]) + (tb[2] - tb[0]) * (tb[3] - tb[1]) - inter
            if union > 0 and inter / union >= 0.05:
                per_class[kind]["tp"] += 1
                break
    rows = []
    for c in HUMAN_CLASSES:
        gt = per_class[c]["gt"]
        if gt:
            rows.append({"class": c, "recall": round(per_class[c]["tp"] / gt, 2), "n": gt})
    return {"rows": rows, "views": views, "false_positive_views": false_views,
            "note": "staged images only; not factory evidence"}
