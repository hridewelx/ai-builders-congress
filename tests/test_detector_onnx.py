"""ONNX backend edge cases: clean fabric must return no proposals, not an error.

The exported graph raises an ONNX Runtime reshape error when the ROI head sees a
zero-row tensor (a perfectly flat image). The detector converts exactly that
failure into "no proposals"; anything else must surface as a real error.
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


def test_only_the_typed_reshape_error_means_no_proposals():
    """A message that merely resembles the reshape error must not be swallowed."""
    from onnxruntime.capi import onnxruntime_pybind11_state as ort_state

    generic = RuntimeError("Reshape node failed: zero elements")
    assert detector._is_empty_roi_failure(generic) is False
    typed = ort_state.Fail("Non-zero status code returned while running Reshape node.")
    assert detector._is_empty_roi_failure(typed) is True


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
