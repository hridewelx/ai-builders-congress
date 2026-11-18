"""Application service: evidence assembly, decisions, overrides, progress."""
from __future__ import annotations

import hashlib
import json
import os

from ..config import STORE_DIR as STORE  # noqa: E402
from ..core import db
from ..domain import engine


def map_clause(buyer_id: int, defect_type: str, zone: str, size_band: str | None):
    """Exact (type, zone, size_band) first, then the row with an empty size band."""
    if defect_type == "other":
        return None
    if size_band:
        row = db.one("SELECT * FROM clause_mapping WHERE buyer_id=? AND defect_type=? AND zone_code=?"
                     " AND size_band=? ORDER BY id LIMIT 1", (buyer_id, defect_type, zone, size_band))
        if row:
            return row
    return db.one("SELECT * FROM clause_mapping WHERE buyer_id=? AND defect_type=? AND zone_code=?"
                  " AND (size_band IS NULL OR size_band='') ORDER BY id LIMIT 1",
                  (buyer_id, defect_type, zone))


def lot(lot_id: int):
    return db.one("SELECT l.*, b.name AS buyer_name, b.id AS buyer_id, p.name AS product_name, p.family"
                  " FROM lot l JOIN buyer b ON b.id=l.buyer_id JOIN product p ON p.id=l.product_id"
                  " WHERE l.id=?", (lot_id,))


def active_plan(lot_id: int):
    return db.one("SELECT * FROM plan WHERE lot_id=? ORDER BY version DESC LIMIT 1", (lot_id,))


def plan_dict(row) -> dict | None:
    if not row:
        return None
    return {
        "id": row["id"], "version": row["version"], "n": row["n"], "counting_mode": row["counting_mode"],
        "critical": {"ac": row["critical_ac"], "re": row["critical_re"]},
        "major": {"ac": row["major_ac"], "re": row["major_re"]},
        "minor": {"ac": row["minor_ac"], "re": row["minor_re"]},
        "critical_aql": row["critical_aql"], "major_aql": row["major_aql"], "minor_aql": row["minor_aql"],
        "source_edition": row["source_edition"], "source_reference": row["source_reference"],
        "is_demo": bool(row["is_demo"]), "inspection_level": row["inspection_level"],
        "sampling_type": row["sampling_type"],
    }


def units_with_views(lot_id: int) -> list[dict]:
    units = db.q("SELECT * FROM sample_unit WHERE lot_id=? ORDER BY id", (lot_id,))
    out = []
    for u in units:
        views = []
        for v in db.q("SELECT * FROM unit_view WHERE sample_unit_id=? ORDER BY id", (u["id"],)):
            img = db.one("SELECT * FROM image WHERE view_id=? AND is_current=1 AND purged=0"
                         " ORDER BY id DESC LIMIT 1", (v["id"],))
            review = db.one("SELECT * FROM view_review WHERE image_id=?", (img["id"],)) if img else None
            job = db.one("SELECT * FROM inference_job WHERE image_id=? ORDER BY id DESC LIMIT 1",
                         (img["id"],)) if img else None
            preds = db.q("SELECT * FROM prediction WHERE image_id=? ORDER BY id", (img["id"],)) if img else []
            review_state = review["state"] if review else (None if img else "no_image")
            views.append({
                "id": v["id"], "side": v["side"], "required": bool(v["required"]),
                "image": dict(img) if img else None,
                "review": dict(review) if review else None,
                "job": dict(job) if job else None,
                "predictions": [dict(p) for p in preds],
                "review_state": review_state,
                "inference_status": derive_status(job),
                "open_proposals": sum(1 for p in preds if p["review_state"] == "proposed"),
            })
        out.append({"id": u["id"], "garment_code": u["garment_code"], "views": views})
    return out


def derive_status(job) -> str:
    if not job:
        return "not_inferred"
    if job["status"] == "succeeded":
        return "ok"
    if job["status"] in ("queued", "running"):
        return "pending"
    return "failed"


def evidence_ok(img) -> bool:
    if not img:
        return True
    path = os.path.join(STORE, img["stored_name"])
    try:
        if not os.path.exists(path):
            return False
        if os.path.getsize(path) != img["bytes"]:
            return False
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest() == img["sha256_working"]
    except OSError:
        return False


def build_evidence(lot_id: int) -> dict:
    L = lot(lot_id)
    plan = plan_dict(active_plan(lot_id))
    units = units_with_views(lot_id)
    defects = []
    for u in units:
        for v in u["views"]:
            if not v["image"]:
                continue
            reviewed = v["review_state"] in ("confirmed_defects", "reviewed_clean")
            for p in v["predictions"]:
                if p["review_state"] == "confirmed":
                    defects.append({
                        "defect_id": p["id"], "unit_id": u["id"], "image_id": v["image"]["id"],
                        "type": p["confirmed_type"] or p["defect_type"], "severity": p["severity"],
                        "zone": p["zone_code"], "size_band": p["size_band"],
                        "current_image": bool(v["image"]["is_current"]), "view_reviewed": reviewed,
                        "retracted": False,
                    })
    eng_units = []
    for u in units:
        views = []
        for v in u["views"]:
            views.append({
                "side": v["side"], "required": v["required"],
                "has_image": bool(v["image"]), "review_state": None if v["review_state"] == "no_image" else v["review_state"],
                "evidence_ok": evidence_ok(v["image"]),
                "live_job": bool(v["job"] and v["job"]["status"] in ("queued", "running")),
                "inference_status": v["inference_status"],
                "predictions": [{
                    "id": p["id"], "provisional_critical": bool(p["provisional_critical"]),
                    "review_state": p["review_state"], "second_review": p["second_review"],
                    "second_opinion": bool(p["second_review"] == "requested"),
                    "confirmed_severity": p["severity"],
                } for p in v["predictions"]],
            })
        eng_units.append({"id": u["id"], "views": views})
    required = int(plan["n"]) if plan else 0
    required_units = min(required, int(L["lot_size"])) if required else 0
    return {
        "plan": plan,
        "lot": {"id": L["id"], "lot_size": L["lot_size"],
                "critical_nonvisual_status": L["critical_nonvisual_status"]},
        "units": eng_units,
        "units_present": len(units),
        "required_units": required_units,
        "defects": defects,
    }


def compute_decision(lot_id: int, user_id: int, note: str = "", allow_decided: bool = False) -> dict:
    L = lot(lot_id)
    if L["status"] == "decided" and not allow_decided:
        raise PermissionError("lot_locked")
    ev = build_evidence(lot_id)
    res = engine.decide(ev)
    seq_row = db.one("SELECT COALESCE(MAX(sequence),0) AS s FROM decision WHERE lot_id=?", (lot_id,))
    seq = int(seq_row["s"]) + 1
    prior = db.one("SELECT id FROM decision WHERE lot_id=? ORDER BY sequence DESC LIMIT 1", (lot_id,))
    eligible = [d for d in ev["defects"] if d["severity"] and d["current_image"] and d["view_reviewed"]]
    snap = engine.snapshot_hash(eligible)
    plan = ev["plan"]
    class_limits = {c: {"ac": plan[c]["ac"], "re": plan[c]["re"]} for c in engine.CLASSES} if plan else {}
    manual = any(v["inference_status"] != "ok" and v["review_state"] in ("confirmed_defects", "reviewed_clean")
                 for u in units_with_views(lot_id) for v in u["views"])
    did = db.x(
        "INSERT INTO decision(lot_id,sequence,outcome,primary_reason,reasons,counts,class_limits,plan_snapshot,"
        "snapshot_hash,completeness,engine_version,manual_inspection,note,created_by,created_at,supersedes_id)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (lot_id, seq, res["outcome"], res["primary_reason"], json.dumps(res["reasons"]),
         json.dumps(res["counts"]), json.dumps(class_limits),
         json.dumps(plan, sort_keys=True) if plan else None, snap, json.dumps(res["completeness"]),
         res["engine_version"], 1 if manual else 0, note, user_id, db.now(), prior["id"] if prior else None))
    if res["outcome"] in ("ACCEPT", "REJECT"):
        db.x("UPDATE lot SET status='decided', version=version+1 WHERE id=?", (lot_id,))
    db.audit(user_id, str(user_id), "decision.computed", "decision", did,
             after={"outcome": res["outcome"], "reasons": res["reasons"], "counts": res["counts"]})
    row = db.one("SELECT * FROM decision WHERE id=?", (did,))
    return dict(row)


def latest_decision(lot_id: int):
    return db.one("SELECT d.*, u.display_name AS decided_by FROM decision d JOIN app_user u ON u.id=d.created_by"
                  " WHERE d.lot_id=? ORDER BY d.sequence DESC LIMIT 1", (lot_id,))


def decision_by_id(did: int):
    return db.one("SELECT * FROM decision WHERE id=?", (did,))


def override_for(decision_id: int):
    o = db.one("SELECT o.*, u.display_name AS supervisor FROM override o JOIN app_user u ON u.id=o.supervisor_id"
               " WHERE o.decision_id=?", (decision_id,))
    if not o:
        return None
    d = dict(o)
    ap = db.one("SELECT a.*, u.display_name AS approver FROM override_approval a"
                " JOIN app_user u ON u.id=a.approver_id WHERE a.override_id=?", (o["id"],))
    d["approval"] = dict(ap) if ap else None
    d["effective"] = o["status"] == "effective" or bool(ap and ap["decision"] == "approved")
    return d


def final_disposition(decision_row, override) -> str:
    if override and override["effective"]:
        return override["final_disposition"].replace("OVERRIDE_", "")
    return decision_row["outcome"]


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
    return [dict(r) for r in rows]


def counters() -> dict:
    rows = db.q("SELECT outcome, COUNT(*) AS n FROM decision WHERE sequence=1 GROUP BY outcome")
    by = {r["outcome"]: r["n"] for r in rows}
    open_lots = db.one("SELECT COUNT(*) AS n FROM lot WHERE status IN ('open','reopened')")["n"]
    return {"open": open_lots, "HOLD": by.get("HOLD", 0), "ESCALATE": by.get("ESCALATE", 0),
            "decided": db.one("SELECT COUNT(*) AS n FROM lot WHERE status='decided'")["n"]}
