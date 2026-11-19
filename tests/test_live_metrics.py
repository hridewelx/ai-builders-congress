"""Live metrics describe the product, and must not be called accuracy."""
from __future__ import annotations

from pathlib import Path

import pytest

from ml import live_metrics


def _rows() -> list[dict]:
    return [
        {"defect_type": "hole", "review_state": "confirmed", "score": 0.9, "confirmed_type": "hole"},
        {"defect_type": "hole", "review_state": "rejected", "score": 0.7, "confirmed_type": None},
        {"defect_type": "oil_stain", "review_state": "proposed", "score": 0.4, "confirmed_type": None},
        {"defect_type": "dropped_stitch", "review_state": "confirmed", "score": 0.8, "confirmed_type": "hole"},
    ]


def test_confirmation_rate_ignores_open_proposals():
    report = live_metrics.summarise(_rows(), threshold=0.55)
    assert report["proposals"] == 4
    assert report["confirmed"] == 2 and report["rejected"] == 1
    assert report["confirmation_rate"] == pytest.approx(2 / 3, abs=1e-4)
    # A corrected type wins: the reviewer relabelled a dropped_stitch box as a
    # hole, so it is counted with the holes, not with the stitches.
    assert report["per_class"]["hole"]["proposed"] == 3
    assert "dropped_stitch" not in report["per_class"]


def test_drift_share_counts_below_threshold():
    report = live_metrics.summarise(_rows(), threshold=0.55)
    assert report["per_class"]["oil_stain"]["proposed"] == 1
    assert report["per_class"]["oil_stain"]["below_threshold"] == 1
    assert report["per_class"]["oil_stain"]["confirmation_rate"] is None


def test_report_refuses_to_call_it_accuracy():
    report = live_metrics.summarise(_rows(), threshold=0.55)
    assert "not recall or precision" in report["note"]


def test_reads_the_seeded_database_when_present():
    db = Path("data/lotline.db")
    if not db.exists():
        pytest.skip("no seeded database in this checkout")
    raw = live_metrics._query(db, days=3650)
    report = live_metrics.summarise([dict(row) for row in raw], threshold=0.55)
    assert report["proposals"] > 0
    assert report["confirmation_rate"] is None or 0 <= report["confirmation_rate"] <= 1
