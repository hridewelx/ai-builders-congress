"""Procedural knit fabric and the defects drawn onto it.

Used for training patches, threshold calibration and staged demo photos.
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter


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
