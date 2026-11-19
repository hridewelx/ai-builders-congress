"""Turn one working image into proposals, a heat map and quality flags."""
from __future__ import annotations

import io
import math

import numpy as np
from PIL import Image

from .embedding import _ae_forward, _features
from .model import _train_or_load
from .params import FEATURE_DIM, MODEL_NAME, PATCH, STRIDE


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
