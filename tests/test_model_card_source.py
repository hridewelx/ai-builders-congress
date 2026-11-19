"""The model card and the explainer page read the same numbers.

`docs/MODEL_CARD.md` is generated for judges, `data/models/model_card_trained.json`
for the page. Both are written by `ml.model_card.write` from the same metrics, so
a change to one without the other is impossible by construction. These tests pin
that, and pin the merge the page performs.
"""
from __future__ import annotations

import json

import pytest

from app.services import detector
from app.web import stats
from ml import model_card


@pytest.fixture()
def artefacts():
    from ml.config import MODELS

    metrics_path = MODELS / "eval_test_v2.json"
    parity_path = MODELS / "runtime_parity_v2.json"
    checkpoint_path = MODELS / "det_v2b.pt"
    if not (metrics_path.exists() and parity_path.exists() and checkpoint_path.exists()):
        pytest.skip("trained artefacts are not in this checkout")
    return (json.loads(metrics_path.read_text(encoding="utf-8")),
            json.loads(parity_path.read_text(encoding="utf-8")),
            {"model_card": {"architecture": "fasterrcnn_mobilenet_v3_large_fpn"}})


def _calibration():
    return {"temperature": 0.87, "ece_before": 0.1061, "ece_after": 0.1179,
            "applied": False, "runtime_temperature": 1.0}


def test_markdown_and_json_come_from_the_same_metrics(tmp_path, artefacts):
    metrics, parity, checkpoint = artefacts
    operating_point = {"chosen_threshold": 0.55, "objective": "maximum recall subject to precision >= 0.75",
                       "split": "val", "table": [], "detections": 222}
    card = model_card.write(tmp_path / "MODEL_CARD.md", tmp_path / "card.json", metrics,
                            checkpoint, _calibration(), parity,
                            operating_point=operating_point, source="eval_test_v2.json")
    text = (tmp_path / "MODEL_CARD.md").read_text(encoding="utf-8")
    headline = metrics["per_source"]["bdfd9"]["map50"]
    assert card["live_evaluation"]["map50"] == headline
    assert card["live_evaluation"]["source"] == "bdfd9"
    assert str(headline) in text, "the markdown must cite the same headline as the JSON"
    # The pooled number is a diagnostic; the card forbids quoting it, and so
    # does the page. It is carried, but only under `pooled_diagnostic`.
    assert card["live_evaluation"]["pooled_diagnostic"]["map50"] == metrics["map50"]
    assert card["live_threshold"] == operating_point["chosen_threshold"]
    assert card["live_parity"]["split"] == "val", "parity is never measured on test"
    assert "not applied" in card["live_calibration"]
    assert set(card["classes"]) == set(detector.CLASSES)


def test_json_card_never_names_a_retired_model(artefacts):
    metrics, parity, checkpoint = artefacts
    card = model_card.json_card(metrics, checkpoint, _calibration(), parity)
    blob = json.dumps(card).lower()
    assert "det_v1" not in blob
    assert card["model"] == detector.MODEL_NAME == "frcnn-mnv3-v2"


def test_explainer_prefers_the_generated_card(monkeypatch, tmp_path, artefacts):
    """The page must show the trained facts, not the strings typed into the seeder."""
    metrics, parity, checkpoint = artefacts
    card = model_card.json_card(metrics, checkpoint, _calibration(), parity)
    (tmp_path / "model_card_trained.json").write_text(
        json.dumps(card, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "model_card.json").write_text(json.dumps({
        "model": "ae-knit-v1", "live_model": "stale text from the seeder"}), encoding="utf-8")
    monkeypatch.setattr(stats, "MODEL_DIR", str(tmp_path))
    monkeypatch.setattr(detector, "available", lambda: True)

    merged = stats.load_model_card()
    assert merged["live_model"] == "frcnn-mnv3-v2"
    assert merged["live_evaluation"]["map50"] == metrics["per_source"]["bdfd9"]["map50"]
    assert merged.get("live_threshold") in (0.55, None)


def test_without_the_generated_card_the_page_still_renders(monkeypatch, tmp_path):
    monkeypatch.setattr(stats, "MODEL_DIR", str(tmp_path))
    monkeypatch.setattr(detector, "available", lambda: False)
    merged = stats.load_model_card()
    assert merged["live_model"] == "not enabled (numpy baseline)"


def test_reliability_reaches_the_page(monkeypatch, tmp_path, artefacts):
    """The page must say a score is a ranking, with the measured ECE behind it."""
    metrics, parity, checkpoint = artefacts
    reliability = {"ece": 0.1346, "detections": 85, "split": "val",
                   "bins": [{"bin": "0.95-1.00", "count": 39, "mean_score": 0.9769,
                             "measured_precision": 0.9487, "gap": -0.0282}]}
    card = model_card.json_card(metrics, checkpoint, _calibration(), parity,
                                reliability=reliability)
    assert card["live_reliability"]["ece"] == 0.1346
    assert card["live_reliability"]["top_band"]["bin"] == "0.95-1.00"

    (tmp_path / "model_card_trained.json").write_text(
        json.dumps(card, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "model_card.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(stats, "MODEL_DIR", str(tmp_path))
    monkeypatch.setattr(detector, "available", lambda: True)
    merged = stats.load_model_card()
    assert merged["live_reliability"]["detections"] == 85
