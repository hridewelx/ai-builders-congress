"""Read-only counters used by the dashboard, admin and explainer screens."""
from __future__ import annotations

import json
import os

from ..config import MODEL_DIR
from ..core import db


def load_model_card() -> dict:
    """Load the generated model card, filling live-model fields from the runtime.

    ``model_card.json`` is written by the seeder and can be older than the code.
    The explainer page must never show "same as seeded" when a trained ONNX
    detector is actually serving uploads, so the live fields are derived here.
    """
    path = os.path.join(MODEL_DIR, "model_card.json")
    try:
        with open(path, encoding="utf-8") as fh:
            card = json.load(fh)
    except (OSError, ValueError):
        card = {}
    from ..services import detector

    # The trained facts (numbers, domains, calibration) come from the card that
    # ml/model_card.py writes with docs/MODEL_CARD.md. Retping them in the
    # seeder is how the page and the card drift apart.
    trained = {}
    try:
        with open(os.path.join(MODEL_DIR, "model_card_trained.json"), encoding="utf-8") as fh:
            trained = json.load(fh)
    except (OSError, ValueError):
        trained = {}

    live = detector.available()
    if live and trained:
        for key in ("live_model", "live_labels", "live_training", "live_domains",
                    "live_device", "live_calibration", "live_threshold",
                    "live_evaluation", "live_parity"):
            if trained.get(key) is not None:
                card[key] = trained[key]
        card["live_sha256"] = (trained.get("artifacts") or {}).get("onnx_sha256") or ""
    card.setdefault("live_model", detector.MODEL_NAME if live else "not enabled (numpy baseline)")
    card.setdefault("live_labels", "supervised: BDFD9 factory fabric (CC BY 4.0) plus staged panels"
                    if live else "none")
    card.setdefault("live_training", "BDFD9 train/valid plus staged train; official test held out"
                    if live else "n/a")
    card.setdefault("live_domains", detector.MODEL_DOMAIN if live else "n/a")
    return card


def demo_stats() -> dict:
    """Aggregate counts shown on the dashboard and explainer page."""
    images = db.one("SELECT COUNT(*) AS n FROM image WHERE purged=0")["n"]
    predictions = db.one("SELECT COUNT(*) AS n FROM prediction")["n"]
    confirmed = db.one("SELECT COUNT(*) AS n FROM prediction WHERE review_state='confirmed'")["n"]
    rejected = db.one("SELECT COUNT(*) AS n FROM prediction WHERE review_state='rejected'")["n"]
    proposed = db.one("SELECT COUNT(*) AS n FROM prediction WHERE review_state='proposed'")["n"]
    decisions = db.q("SELECT outcome, COUNT(*) AS n FROM decision GROUP BY outcome")
    return {
        "images": images,
        "proposals": predictions,
        "proposed": proposed,
        "confirmed": confirmed,
        "rejected": rejected,
        "decisions": {row["outcome"]: row["n"] for row in decisions},
        "lots": db.one("SELECT COUNT(*) AS n FROM lot")["n"],
        "audit": db.one("SELECT COUNT(*) AS n FROM audit_event")["n"],
    }
