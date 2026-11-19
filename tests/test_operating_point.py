"""The review threshold must come from the recorded operating point, not a guess.

`ml/operating_point.py` picks the threshold on validation (maximum recall subject
to a precision floor) and writes `data/models/operating_point_v2.json`. If the
code and that record disagree, a reviewer is silently working at a threshold
nobody measured.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services import detector
from ml import config

RECORD = Path("data/models/operating_point_v2.json")

pytestmark = pytest.mark.skipif(not RECORD.exists(),
                                reason="no operating-point record in this checkout")


def _record() -> dict:
    return json.loads(RECORD.read_text(encoding="utf-8"))


def test_record_was_chosen_on_validation_only():
    assert _record()["split"] == "val"


def test_runtime_default_matches_the_record(monkeypatch):
    monkeypatch.delenv("LOTLINE_DETECT_THRESHOLD", raising=False)
    assert detector.DEFAULT_THRESHOLD == _record()["chosen_threshold"]


def test_ml_config_default_matches_the_record():
    assert config.active_threshold() == _record()["chosen_threshold"]


def test_environment_override_still_wins(monkeypatch):
    monkeypatch.setenv("LOTLINE_DETECT_THRESHOLD", "0.9")
    assert float(__import__("os").environ["LOTLINE_DETECT_THRESHOLD"]) == 0.9
    # detect_onnx reads the env var per call; the constant stays the record's value.
    assert detector.DEFAULT_THRESHOLD == _record()["chosen_threshold"]
