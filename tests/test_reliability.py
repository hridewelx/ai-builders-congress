"""Reliability bins must be arithmetic, not vibes."""
from __future__ import annotations

from ml import reliability


def _record(score: float, matched: bool) -> dict:
    return {"score": score, "label": 1, "matched": matched}


def test_bins_are_fifty_points_wide_and_group_correctly():
    assert reliability.bin_index(0.30) == 0
    assert reliability.bin_index(0.50) == 0
    assert reliability.bin_index(0.55) == 1, "an edge score must not fall into the next band"
    assert reliability.bin_index(0.60) == 2
    assert reliability.bin_index(0.999) == 9


def test_ece_is_the_weighted_gap():
    records = [_record(0.55, False), _record(0.55, False),
               _record(0.95, True), _record(0.95, True)]
    report = reliability.summarise(records)
    assert report["detections"] == 4
    low = next(row for row in report["bins"] if row["bin"].startswith("0.55"))
    high = next(row for row in report["bins"] if row["bin"].startswith("0.95"))
    assert low["measured_precision"] == 0.0
    assert high["measured_precision"] == 1.0
    # (0.5 * |0 - 0.55|) + (0.5 * |1 - 0.95|)
    assert report["ece"] == 0.3


def test_a_perfectly_matching_band_has_no_gap():
    report = reliability.summarise([_record(0.80, True)] * 4 + [_record(0.80, False)])
    band = report["bins"][0]
    assert band["mean_score"] == 0.8
    assert band["measured_precision"] == 0.8
    assert band["gap"] == 0.0


def test_report_says_it_is_not_a_calibration_claim():
    report = reliability.summarise([_record(0.7, True)])
    assert "not a calibration claim" in report["note"]


def test_matching_prefers_a_higher_iou_and_respects_class():
    boxes_gt = [[0, 0, 10, 10], [50, 50, 60, 60]]
    labels_gt = [1, 2]
    boxes_p = [[50, 50, 60, 60], [0, 0, 10, 10]]
    scores_p = [0.9, 0.8]
    labels_p = [2, 1]
    out = reliability.matches_for_image(boxes_gt, labels_gt, boxes_p, scores_p, labels_p)
    assert [row["matched"] for row in out] == [True, True]
    wrong_class = reliability.matches_for_image(
        boxes_gt, labels_gt, [[50, 50, 60, 60]], [0.9], [1])
    assert wrong_class[0]["matched"] is False


def test_per_class_breakdown_uses_the_real_class_names():
    records = [{"score": 0.9, "label": 1, "matched": True},
               {"score": 0.9, "label": 1, "matched": False},
               {"score": 0.9, "label": 3, "matched": False}]
    report = reliability.summarise(records)
    assert report["per_class"]["hole"]["detections"] == 2
    assert report["per_class"]["needle_line"]["detections"] == 1
    # one detection at score 0.9 that matched nothing: |0 - 0.9| = 0.9
    assert report["per_class"]["needle_line"]["ece"] == 0.9
    assert sum(row["detections"] for row in report["per_class"].values()) == report["detections"]


def test_a_class_with_no_detections_is_absent_not_zero():
    report = reliability.summarise([{"score": 0.9, "label": 1, "matched": True}])
    assert "oil_stain" not in report["per_class"]
