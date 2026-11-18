"""Detector backend selection.

Two backends answer the same call:

  * ``numpy`` — the in-repo autoencoder baseline, always available, no downloads
  * ``onnx``  — the trained Faster R-CNN exported to ONNX, used when
    ``LOTLINE_DETECTOR=onnx`` and ``data/models/det_v1.onnx`` exists

Both return the same dict shape, so the upload route, the review UI and the
audit trail do not care which one ran. The demo default stays ``numpy`` unless
the environment opts in, so a missing model file can never break a submission.
"""
from __future__ import annotations

import io
import json
import os

import numpy as np
from PIL import Image, ImageFilter

from app.services import vision

MODEL_NAME = "frcnn-mnv3-v1"
ONNX_PATH = os.environ.get("LOTLINE_ONNX", "data/models/det_v1.onnx")
CALIBRATION_PATH = os.environ.get("LOTLINE_CALIBRATION", "data/models/calibration.json")
CLASSES = ["hole", "oil_stain", "needle_line", "dropped_stitch"]
DEFAULT_THRESHOLD = 0.5

_session = None
_calibration: dict | None = None


def backend() -> str:
    return os.environ.get("LOTLINE_DETECTOR", "numpy").strip().lower()


def _load_calibration() -> dict:
    global _calibration
    if _calibration is None:
        try:
            with open(CALIBRATION_PATH, encoding="utf-8") as fh:
                _calibration = json.load(fh)
        except (OSError, ValueError):
            _calibration = {}
    return _calibration


def _load_session():
    global _session
    if _session is None:
        import onnxruntime as ort

        options = ort.SessionOptions()
        options.intra_op_num_threads = int(os.environ.get("LOTLINE_ORT_THREADS", "2"))
        options.log_severity_level = 3  # empty-ROI runs log an expected reshape error
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        _session = ort.InferenceSession(ONNX_PATH, sess_options=options,
                                        providers=["CPUExecutionProvider"])
    return _session


def available() -> bool:
    """True only when the ONNX backend is requested, present and importable."""
    if backend() != "onnx" or not os.path.exists(ONNX_PATH):
        return False
    try:
        import onnxruntime  # noqa: F401
    except ImportError:
        return False
    return True


def _temperature(score: float, temperature: float) -> float:
    if temperature <= 0:
        return score
    p = min(1 - 1e-6, max(1e-6, score))
    logit = np.log(p / (1 - p)) / temperature
    return float(1 / (1 + np.exp(-logit)))


def _overlaps(a: list[float], b: list[float], threshold: float = 0.3) -> bool:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return union > 0 and inter / union > threshold


def _heat(rgb: np.ndarray, detections: list[dict]) -> bytes:
    """Coarse proposal map: painted boxes, blurred. Not a per-pixel attention map."""
    h, w = rgb.shape[:2]
    field = np.zeros((h, w), dtype=np.float32)
    for det in detections:
        x1, y1, x2, y2 = (int(det["box"][0] * w), int(det["box"][1] * h),
                          int(det["box"][2] * w), int(det["box"][3] * h))
        field[max(0, y1):min(h, y2), max(0, x1):min(w, x2)] = max(
            field[max(0, y1):min(h, y2), max(0, x1):min(w, x2)].max(initial=0.0), det["score"])
    if field.max() > 0:
        blurred = Image.fromarray((field * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(radius=max(4, w // 120)))
        field = np.asarray(blurred, dtype=np.float32) / 255.0
    overlay = np.zeros((h, w, 4), dtype=np.uint8)
    overlay[..., 0] = (255 * np.clip(field * 2, 0, 1)).astype(np.uint8)
    overlay[..., 1] = (255 * np.clip(field * 1.2 - 0.25, 0, 1)).astype(np.uint8)
    overlay[..., 2] = 20
    overlay[..., 3] = (200 * field).astype(np.uint8)
    out = Image.alpha_composite(Image.fromarray(rgb).convert("RGBA"), Image.fromarray(overlay, "RGBA")).convert("RGB")
    buffer = io.BytesIO()
    out.save(buffer, "JPEG", quality=82)
    return buffer.getvalue()


def detect_onnx(rgb: np.ndarray, top_k: int = 6) -> dict:
    """Run the trained detector; result contract matches ``vision.detect``."""
    session = _load_session()
    height, width = rgb.shape[:2]
    size = int(session.get_inputs()[0].shape[2] or 640)
    image = Image.fromarray(rgb).convert("RGB").resize((size, size), Image.BILINEAR)
    tensor = np.asarray(image, dtype=np.float32).transpose(2, 0, 1)[None] / 255.0
    try:
        boxes, scores, labels = session.run(None, {session.get_inputs()[0].name: tensor})[:3]
    except Exception as exc:  # ORT cannot reshape a zero-row ROI tensor
        if "Reshape" in str(exc) and "0,20" in str(exc).replace(" ", ""):
            # No region survived the ROI head: the honest answer is "no proposal".
            return {"proposals": [], "quality": vision.quality(rgb), "heat_png": _heat(rgb, []),
                    "model": MODEL_NAME, "threshold": float(os.environ.get("LOTLINE_DETECT_THRESHOLD", DEFAULT_THRESHOLD)),
                    "calibrated": False, "note": "no region survived the detector; nothing proposed"}
        raise

    threshold = float(os.environ.get("LOTLINE_DETECT_THRESHOLD", DEFAULT_THRESHOLD))
    temperature = float(_load_calibration().get("temperature", 1.0))
    detections: list[dict] = []
    for box, score, label in zip(boxes, scores.reshape(-1), labels.reshape(-1)):
        calibrated = _temperature(float(score), temperature)
        if calibrated < threshold:
            continue
        detections.append({
            "type": CLASSES[int(label) - 1] if 1 <= int(label) <= len(CLASSES) else str(int(label)),
            "score": round(min(0.99, max(0.01, calibrated)), 3),
            "box": [round(float(box[0]) / size, 5), round(float(box[1]) / size, 5),
                    round(float(box[2]) / size, 5), round(float(box[3]) / size, 5)],
            "raw_error": None,
        })
    detections.sort(key=lambda item: -item["score"])
    kept: list[dict] = []
    for det in detections:
        if len(kept) >= top_k:
            break
        if any(_overlaps(det["box"], other["box"]) for other in kept):
            continue
        kept.append(det)

    return {
        "proposals": kept,
        "quality": vision.quality(rgb),
        "heat_png": _heat(rgb, kept),
        "model": MODEL_NAME,
        "threshold": threshold,
        "calibrated": bool(temperature != 1.0),
        "note": "trained detector, temperature-calibrated; boxes still require human confirmation",
    }


def detect(rgb: np.ndarray, top_k: int = 6) -> dict:
    """Dispatch to the requested backend, falling back honestly."""
    if available():
        try:
            return detect_onnx(rgb, top_k)
        except Exception as exc:  # a broken model must not block an inspection
            result = vision.detect(rgb, top_k)
            result["note"] = f"onnx backend failed ({type(exc).__name__}); numpy baseline used"
            return result
    return vision.detect(rgb, top_k)
