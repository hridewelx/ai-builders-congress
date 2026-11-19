"""Read-only counters used by the dashboard, admin and explainer screens."""
from __future__ import annotations

import json
import os

from ..config import MODEL_DIR
from ..core import db


def load_model_card() -> dict:
    """Load the generated model card, or an empty card when none exists yet."""
    path = os.path.join(MODEL_DIR, "model_card.json")
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


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
