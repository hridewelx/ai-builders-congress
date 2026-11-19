"""Detector backend contract: explicit ONNX must fail loudly, auto may fall back."""
from __future__ import annotations

import pytest

from app.services import detector


def test_explicit_onnx_with_missing_artifact_fails(monkeypatch, tmp_path):
    monkeypatch.setenv("LOTLINE_DETECTOR", "onnx")
    monkeypatch.setattr(detector, "ONNX_PATH", str(tmp_path / "missing.onnx"))
    with pytest.raises(RuntimeError, match="detector is unavailable"):
        detector.require_available()


def test_auto_with_missing_artifact_is_allowed(monkeypatch, tmp_path):
    monkeypatch.setenv("LOTLINE_DETECTOR", "auto")
    monkeypatch.setattr(detector, "ONNX_PATH", str(tmp_path / "missing.onnx"))
    detector.require_available()  # auto is allowed to use the numpy baseline


def test_unknown_backend_falls_back_to_auto(monkeypatch):
    monkeypatch.setenv("LOTLINE_DETECTOR", "banana")
    assert detector.backend() == "auto"
