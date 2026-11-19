"""What the detector is doing in the product, not on the test split.

Judges ask about accuracy; a pilot asks "how often do my inspectors confirm the
box, and has that changed this week". Both questions have answerable forms in the
live database:

- **confirmation rate per class** — of the proposals the model made, how many did
  a human confirm. This is not recall (nobody knows what was missed), and this
  script never calls it accuracy.
- **score drift** — the share of proposals near the review threshold. A shift
  upward means the model is less sure about this week's fabric.
- **queue cost** — proposals per photo, which is what the inspector's day costs.

    python -m ml.live_metrics --days 7
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

DEFAULT_DB = Path(os.environ.get("LOTLINE_DATA", "data")) / "lotline.db"


def _query(db_path: Path, days: int) -> list[sqlite3.Row]:
    if not db_path.exists():
        raise SystemExit(f"no database at {db_path}")
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        return con.execute(
            """SELECT p.defect_type, p.review_state, p.score, p.confirmed_type, p.created_at
               FROM prediction p
               WHERE p.created_at >= ?
               ORDER BY p.id""", (since,)).fetchall()
    finally:
        con.close()


def summarise(rows: list[dict], threshold: float) -> dict:
    per_class: dict[str, dict] = {}
    for row in rows:
        name = row.get("confirmed_type") or row.get("defect_type") or "unknown"
        block = per_class.setdefault(name, {"proposed": 0, "confirmed": 0, "rejected": 0,
                                            "open": 0, "below_threshold": 0})
        block["proposed"] += 1
        state = row.get("review_state")
        if state == "confirmed":
            block["confirmed"] += 1
        elif state == "rejected":
            block["rejected"] += 1
        else:
            block["open"] += 1
        if float(row.get("score") or 0) < threshold:
            block["below_threshold"] += 1
    for block in per_class.values():
        decided = block["confirmed"] + block["rejected"]
        block["confirmation_rate"] = round(block["confirmed"] / decided, 4) if decided else None
        block["below_threshold_share"] = round(block["below_threshold"] / block["proposed"], 4)
    total_proposed = len(rows)
    total_confirmed = sum(block["confirmed"] for block in per_class.values())
    total_rejected = sum(block["rejected"] for block in per_class.values())
    return {
        "proposals": total_proposed,
        "confirmed": total_confirmed,
        "rejected": total_rejected,
        "confirmation_rate": (round(total_confirmed / (total_confirmed + total_rejected), 4)
                              if (total_confirmed + total_rejected) else None),
        "threshold": threshold,
        "per_class": per_class,
        "note": ("A confirmation rate is not recall or precision: it measures how often a human "
                 "accepted the model's box, and it cannot see what the model never proposed."),
    }


def operating_threshold() -> float:
    try:
        saved = json.loads((Path("data/models/operating_point_v2.json")).read_text(encoding="utf-8"))
        return float(saved["chosen_threshold"])
    except (OSError, ValueError, KeyError):
        return 0.5


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Live detector metrics from the product database.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--threshold", type=float, default=None)
    args = parser.parse_args(argv)
    threshold = args.threshold if args.threshold is not None else operating_threshold()
    rows = [dict(row) for row in _query(args.db, args.days)]
    report = summarise(rows, threshold)
    report["window_days"] = args.days
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
