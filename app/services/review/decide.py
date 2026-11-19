"""Run the pure engine and apply the override rule."""
from __future__ import annotations

import json

from ...core import db
from ...domain import engine
from .evidence import build_evidence, units_with_views
from .lookups import lot


def compute_decision(lot_id: int, user_id: int, note: str = "", allow_decided: bool = False) -> dict:
    L = lot(lot_id)
    if L["status"] == "decided" and not allow_decided:
        raise PermissionError("lot_locked")
    ev = build_evidence(lot_id)
    res = engine.decide(ev)
    eligible = [d for d in ev["defects"] if d["severity"] and d["current_image"] and d["view_reviewed"]]
    snap = engine.snapshot_hash(eligible)
    plan = ev["plan"]
    plan_snapshot = json.dumps(plan, sort_keys=True) if plan else None
    counts_json = json.dumps(res["counts"])
    reasons_json = json.dumps(res["reasons"])

    # Idempotent append-only history: identical inputs must not create a second
    # decision row or a duplicate audit event.
    latest = db.one("SELECT * FROM decision WHERE lot_id=? ORDER BY sequence DESC LIMIT 1", (lot_id,))
    if latest and not allow_decided:
        unchanged = (
            latest["snapshot_hash"] == snap
            and latest["outcome"] == res["outcome"]
            and latest["primary_reason"] == res["primary_reason"]
            and (latest["plan_snapshot"] or None) == plan_snapshot
            and latest["counts"] == counts_json
            and latest["reasons"] == reasons_json
        )
        if unchanged:
            row = dict(latest)
            row["unchanged"] = True
            return row

    seq = int((latest["sequence"] if latest else 0)) + 1
    class_limits = {c: {"ac": plan[c]["ac"], "re": plan[c]["re"]} for c in engine.CLASSES} if plan else {}
    manual = any(v["inference_status"] != "ok" and v["review_state"] in ("confirmed_defects", "reviewed_clean")
                 for u in units_with_views(lot_id) for v in u["views"])
    did = db.x(
        "INSERT INTO decision(lot_id,sequence,outcome,primary_reason,reasons,counts,class_limits,plan_snapshot,"
        "snapshot_hash,completeness,engine_version,manual_inspection,note,created_by,created_at,supersedes_id)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (lot_id, seq, res["outcome"], res["primary_reason"], reasons_json,
         counts_json, json.dumps(class_limits), plan_snapshot, snap, json.dumps(res["completeness"]),
         res["engine_version"], 1 if manual else 0, note, user_id, db.now(), latest["id"] if latest else None))
    if res["outcome"] in ("ACCEPT", "REJECT"):
        db.x("UPDATE lot SET status='decided', version=version+1 WHERE id=?", (lot_id,))
    actor = db.one("SELECT display_name FROM app_user WHERE id=?", (user_id,))
    db.audit(user_id, actor["display_name"] if actor else str(user_id), "decision.computed", "decision", did,
             after={"outcome": res["outcome"], "reasons": res["reasons"], "counts": res["counts"]})
    row = db.one("SELECT * FROM decision WHERE id=?", (did,))
    return dict(row)



def final_disposition(decision_row, override) -> str:
    if override and override["effective"]:
        return override["final_disposition"].replace("OVERRIDE_", "")
    return decision_row["outcome"]
