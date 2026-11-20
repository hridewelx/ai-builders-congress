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
    # the effective threshold follows the environment; the record is untouched
    assert detector.review_threshold() == 0.9
    assert detector.DEFAULT_THRESHOLD == _record()["chosen_threshold"]


def test_default_threshold_is_the_recorded_one(monkeypatch):
    monkeypatch.delenv("LOTLINE_DETECT_THRESHOLD", raising=False)
    assert detector.review_threshold() == _record()["chosen_threshold"]


def test_the_sweep_divides_recall_by_ground_truth_not_by_matches():
    from ml.operating_point import measure, review_queue

    record = {"gt_boxes": [[0, 0, 10, 10], [20, 20, 30, 30], [40, 40, 50, 50]],
              "gt_labels": [1, 1, 1],
              "detections": [{"box": [0, 0, 10, 10], "score": 0.9, "label": 1}]}
    result = measure([record], 0.5)
    assert result["true_positives"] == 1
    assert result["recall"] == round(1 / 3, 4), "recall must use all three ground-truth boxes"
    assert len(review_queue(record["detections"], 0.5)) == 1


def test_the_sweep_counts_the_review_cap():
    from ml.operating_point import REVIEW_CAP, review_queue

    detections = [{"box": [i * 40, 0, i * 40 + 20, 20], "score": 0.9 - i / 100, "label": 1}
                  for i in range(REVIEW_CAP + 4)]
    assert len(review_queue(detections, 0.5)) == REVIEW_CAP


def test_overlapping_boxes_are_suppressed_like_the_review_ui():
    from ml.operating_point import review_queue

    detections = [{"box": [0, 0, 100, 100], "score": 0.9, "label": 1},
                  {"box": [5, 5, 95, 95], "score": 0.8, "label": 1}]
    assert len(review_queue(detections, 0.5)) == 1
