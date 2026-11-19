"""Counters, review queue, progress and the audit timeline."""
from __future__ import annotations

from ...core import db
from .evidence import build_evidence, units_with_views


def progress(lot_id: int) -> dict:
    ev = build_evidence(lot_id)
    units = ev["units"]
    total_views = sum(len(u["views"]) for u in units)
    reviewed = sum(1 for u in units for v in u["views"] if v["review_state"] in ("confirmed_defects", "reviewed_clean"))
    pending = sum(1 for u in units for v in u["views"] if v["review_state"] not in ("confirmed_defects", "reviewed_clean"))
    return {
        "units": ev["units_present"], "required_units": ev["required_units"],
        "views": total_views, "reviewed": reviewed, "pending": pending,
        "pct_units": int(100 * ev["units_present"] / ev["required_units"]) if ev["required_units"] else 0,
        "pct_views": int(100 * reviewed / total_views) if total_views else 0,
    }


def review_queue(lot_id: int) -> list[dict]:
    out = []
    for u in units_with_views(lot_id):
        for v in u["views"]:
            if v["review_state"] not in ("confirmed_defects", "reviewed_clean"):
                prio = 0
                if any(p["provisional_critical"] and p["review_state"] == "proposed" for p in v["predictions"]):
                    prio = 3
                elif v["inference_status"] == "failed":
                    prio = 2
                elif v["predictions"]:
                    prio = 1
                out.append({"unit": u, "view": v, "priority": prio})
    out.sort(key=lambda r: (-r["priority"], r["unit"]["id"], r["view"]["id"]))
    return out


def timeline(lot_id: int) -> list[dict]:
    rows = db.q(
        "SELECT * FROM audit_event WHERE"
        " (entity='lot' AND entity_id=?)"
        " OR (entity='decision' AND entity_id IN (SELECT id FROM decision WHERE lot_id=?))"
        " OR (entity='image' AND entity_id IN (SELECT id FROM image WHERE lot_id=?))"
        " OR (entity='prediction' AND entity_id IN"
        "     (SELECT p.id FROM prediction p JOIN image i ON i.id=p.image_id WHERE i.lot_id=?))"
        " ORDER BY id DESC LIMIT 60", (str(lot_id), lot_id, lot_id, lot_id))
    out = [dict(r) for r in rows]
    # Older rows stored the numeric actor id in actor_label. The append-only
    # record stays untouched; the read model resolves a display name instead.
    users = {u["id"]: u["display_name"] for u in db.q("SELECT id, display_name FROM app_user")}
    for row in out:
        label = row.get("actor_label")
        if not label or str(label).strip().isdigit():
            aid = row.get("actor_id")
            try:
                aid_int = int(aid) if aid is not None else None
            except (ValueError, TypeError):
                aid_int = None
            name = users.get(aid_int) if aid_int is not None else None
            if name:
                row["actor_label"] = name
    return out


def counters() -> dict:
    rows = db.q("SELECT outcome, COUNT(*) AS n FROM decision WHERE sequence=1 GROUP BY outcome")
    by = {r["outcome"]: r["n"] for r in rows}
    open_lots = db.one("SELECT COUNT(*) AS n FROM lot WHERE status IN ('open','reopened')")["n"]
    return {"open": open_lots, "HOLD": by.get("HOLD", 0), "ESCALATE": by.get("ESCALATE", 0),
            "decided": db.one("SELECT COUNT(*) AS n FROM lot WHERE status='decided'")["n"]}
