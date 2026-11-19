"""Assemble the evidence the engine is allowed to see, and check it is intact."""
from __future__ import annotations

import hashlib
import os

from ...config import STORE_DIR as STORE  # noqa: E402
from ...core import db
from .lookups import active_plan, lot, plan_dict


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
