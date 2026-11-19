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

MODEL_NAME = "frcnn-mnv3-v2"
MODEL_DOMAIN = ("BDFD9 factory fabric close-ups plus staged knit panels; "
                "not finished-garment inspection")
ONNX_PATH = os.environ.get("LOTLINE_ONNX", "data/models/det_v2.onnx")
CALIBRATION_PATH = os.environ.get("LOTLINE_CALIBRATION", "data/models/calibration_v2.json")
CLASSES = ["hole", "oil_stain", "needle_line", "dropped_stitch"]
OPERATING_POINT = "data/models/operating_point_v2.json"


def recorded_threshold(default: float = 0.5) -> float:
    """Threshold chosen on validation by ``ml.operating_point`` (env still overrides)."""
    try:
        with open(OPERATING_POINT, encoding="utf-8") as fh:
            return float(json.load(fh)["chosen_threshold"])
    except (OSError, KeyError, ValueError, TypeError):
        return default


DEFAULT_THRESHOLD = recorded_threshold()

_session = None
_calibration: dict | None = None


def backend() -> str:
    """``auto`` uses ONNX when present, ``onnx`` requires it, ``numpy`` forces the baseline."""
    value = os.environ.get("LOTLINE_DETECTOR", "auto").strip().lower()
    return value if value in {"auto", "onnx", "numpy"} else "auto"


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
        # Empty-ROI runs emit an expected reshape error; keep it out of server logs.
        options.log_severity_level = 4
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        _session = ort.InferenceSession(ONNX_PATH, sess_options=options,
                                        providers=["CPUExecutionProvider"])
    return _session


def selftest() -> tuple[bool, str]:
    """Load the ONNX session once; used before registering a model version."""
    if not available():
        return False, "ONNX artifact or runtime unavailable"
    try:
        _load_session()
        return True, "ONNX session loaded"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"[:200]


def available() -> bool:
    """True when ONNX is allowed, the artifact is present and the runtime imports."""
    if backend() == "numpy" or not os.path.exists(ONNX_PATH):
        return False
    try:
        import onnxruntime  # noqa: F401
    except ImportError:
        return False
    return True


def active_backend() -> str:
    """The backend that will actually serve the next request ("onnx" or "numpy")."""
    mode = backend()
    if mode == "numpy":
        return "numpy"
    if not os.path.exists(ONNX_PATH) or not _ort_installed():
        if mode == "onnx":
            raise RuntimeError(f"LOTLINE_DETECTOR=onnx but ONNX is unavailable at {ONNX_PATH}")
        return "numpy"
    try:
        _load_session()
    except Exception:
        if mode == "onnx":
            raise
        return "numpy"
    return "onnx"


def require_available() -> None:
    """Fail startup when the operator asked for ONNX but it cannot run."""
    if backend() == "onnx" and not available():
        raise RuntimeError(
            f"LOTLINE_DETECTOR=onnx but the detector is unavailable "
            f"(path={ONNX_PATH}, runtime={'present' if _ort_installed() else 'missing'})")


def _ort_installed() -> bool:
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


def _is_empty_roi_failure(exc: BaseException) -> bool:
    """True only for ONNX Runtime's zero-row ROI reshape error.

    A perfectly clean frame produces no proposals, and the exported graph cannot
    reshape a zero-length tensor. That specific, typed failure means "nothing to
    propose". Any other failure is a real error and must not be swallowed, so the
    check is on the exception class, not on the message text alone.
    """
    try:
        from onnxruntime.capi import onnxruntime_pybind11_state as ort_state
    except ImportError:  # onnxruntime is an optional dependency
        return False
    # ORT reports this as status 1 (Fail) on the CPU provider and as
    # InvalidArgument on some versions; both are ONNX Runtime's own types, so a
    # look-alike exception from elsewhere can never be mistaken for it.
    typed = isinstance(exc, (ort_state.Fail, ort_state.InvalidArgument))
    return typed and "reshape" in str(exc).lower()


def detect_onnx(rgb: np.ndarray, top_k: int = 6) -> dict:
    """Run the trained detector; result contract matches ``vision.detect``."""
    session = _load_session()
    height, width = rgb.shape[:2]
    size = int(session.get_inputs()[0].shape[2] or 640)
    image = Image.fromarray(rgb).convert("RGB").resize((size, size), Image.BILINEAR)
    tensor = np.asarray(image, dtype=np.float32).transpose(2, 0, 1)[None] / 255.0
    try:
        boxes, scores, labels = session.run(None, {session.get_inputs()[0].name: tensor})[:3]
    except Exception as exc:
        if _is_empty_roi_failure(exc):
            # No region survived the ROI head: the honest answer is "no proposal".
            return {"proposals": [], "quality": vision.quality(rgb), "heat_png": _heat(rgb, []),
                    "model": MODEL_NAME, "threshold": float(os.environ.get("LOTLINE_DETECT_THRESHOLD", DEFAULT_THRESHOLD)),
                    "calibrated": False, "note": "no region survived the detector; nothing proposed"}
        raise

    threshold = float(os.environ.get("LOTLINE_DETECT_THRESHOLD", DEFAULT_THRESHOLD))
    calibration = _load_calibration()
    temperature = float(calibration.get("runtime_temperature", calibration.get("temperature", 1.0)))
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
        "note": ("trained detector, temperature-scaled; ECE is reported in the model card, "
                 "not a probability guarantee" if temperature != 1.0 else
                 "trained detector, raw scores; calibration did not improve ECE on validation"),
    }


def detect(rgb: np.ndarray, top_k: int = 6) -> dict:
    """Dispatch to the requested backend.

    ``onnx`` is strict: if the operator asked for the trained model, a failure
    is an error, not a silent downgrade. ``auto`` may fall back to the baseline
    and records that in the result note.
    """
    requested = backend()
    if requested == "onnx" and not available():
        require_available()
    if available():
        try:
            return detect_onnx(rgb, top_k)
        except Exception as exc:  # a broken model must not block an inspection
            if requested == "onnx":
                raise
            result = vision.detect(rgb, top_k)
            result["note"] = f"onnx backend failed ({type(exc).__name__}); numpy baseline used"
            return result
    return vision.detect(rgb, top_k)
