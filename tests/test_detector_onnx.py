"""ONNX backend edge cases: clean fabric must return no proposals, not an error.

The ROI head reshapes a zero-length tensor when a frame has no proposals. The
export sets `allowzero=1` so that reshape is legal and the graph returns empty
tensors; the detector no longer catches the crash, so any other failure surfaces
as a real error instead of looking like a clean frame.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from app.services import detector

pytestmark = pytest.mark.skipif(
    not Path(detector.ONNX_PATH).exists(), reason="no ONNX artifact in this checkout")


@pytest.fixture()
def onnx_backend(monkeypatch):
    monkeypatch.setenv("LOTLINE_DETECTOR", "onnx")
    detector._session = None
    yield
    detector._session = None


def test_clean_flat_image_returns_no_proposals(onnx_backend):
    """A featureless frame is a normal empty result, not a caught exception."""
    flat = np.full((640, 640, 3), 128, dtype=np.uint8)
    result = detector.detect(flat)
    assert result["proposals"] == []
    assert result["model"] == detector.MODEL_NAME


def test_clean_texture_returns_no_proposals(onnx_backend):
    rng = np.random.default_rng(0)
    texture = rng.integers(100, 140, (640, 640, 3), dtype=np.uint8)
    assert detector.detect(texture)["proposals"] == []


def test_backend_reports_onnx_when_artifact_present(onnx_backend):
    assert detector.active_backend() == "onnx"


def test_missing_artifact_falls_back_to_numpy(monkeypatch):
    monkeypatch.setenv("LOTLINE_DETECTOR", "auto")
    monkeypatch.setattr(detector, "ONNX_PATH", "data/models/does-not-exist.onnx")
    assert detector.active_backend() == "numpy"


def test_readyz_does_not_claim_trained_weights_when_missing(monkeypatch):
    """A hosted build without the ONNX file must not report a live trained model."""
    from fastapi.testclient import TestClient

    from app.main import app

    monkeypatch.setattr(detector, "active_backend", lambda: "numpy")
    payload = TestClient(app).get("/readyz").json()
    assert payload["detector"] == "numpy"
    assert payload["model"] is None
    assert payload["weights_loaded"] is False


def test_other_onnx_failures_are_not_masked(monkeypatch):
    class Broken:
        def get_inputs(self):
            return [type("Input", (), {"name": "images", "shape": [1, 3, 640, 640]})()]

        def run(self, *_args, **_kwargs):
            raise RuntimeError("CUDA provider exploded")

    monkeypatch.setenv("LOTLINE_DETECTOR", "onnx")
    monkeypatch.setattr(detector, "_load_session", lambda: Broken())
    with pytest.raises(RuntimeError, match="exploded"):
        detector.detect(np.zeros((64, 64, 3), dtype=np.uint8))
