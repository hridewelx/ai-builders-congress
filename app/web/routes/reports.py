"""One-page inspection report: HTML and PDF."""
from __future__ import annotations

import json

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response

from ...core import db
from ...domain import engine
from ...services import report, vision
from ...services import review as service
from ..deps import Denied, require_user
from ..pages import page

router = APIRouter(tags=["report"])


def _report_ctx(lot_id: int) -> dict:
    L = service.lot(lot_id)
    d = service.latest_decision(lot_id)
    if not d:
        raise Denied(404, "not_found")
    ov = service.override_for(d["id"])
    plan = json.loads(d["plan_snapshot"]) if d["plan_snapshot"] else None
    reasons = json.loads(d["reasons"])
    comp = json.loads(d["completeness"])
    counts = json.loads(d["counts"])
    limits = json.loads(d["class_limits"] or "{}")
    class_status = {c: {"count": counts.get(c, 0), "ac": limits.get(c, {}).get("ac"),
                        "re": limits.get(c, {}).get("re"),
                        "status": "FAIL" if limits.get(c) and counts.get(c, 0) >= limits[c]["re"] else "PASS"}
                    for c in engine.CLASSES} if limits else {}
    images = db.one("SELECT COUNT(*) AS n FROM image WHERE lot_id=? AND purged=0", (lot_id,))["n"]
    units = db.one("SELECT COUNT(*) AS n FROM sample_unit WHERE lot_id=?", (lot_id,))["n"]
    return {
        "lot_code": L["lot_code"], "product": L["product_name"], "buyer": L["buyer_name"],
        "sequence": d["sequence"], "created_at": d["created_at"], "engine_version": d["engine_version"],
        "outcome": d["outcome"], "override": ov
        and {"final_disposition": ov["final_disposition"], "reason": ov["reason"], "approved": ov["effective"]},
        "plan": plan, "n_effective": (plan or {}).get("n"), "counts": counts, "class_status": class_status,
        "reasons": [{"code": r, "text": engine.REASONS.get(r, ("", r))[1]} for r in reasons],
        "units_present": comp.get("units_present"), "required_units": comp.get("required_units"),
        "views_pending": comp.get("views_pending"), "evidence_bad": comp.get("evidence_bad"),
        "nonvisual": L["critical_nonvisual_status"], "images": images, "units": units,
        "model": vision.MODEL_NAME, "model_domains": "staged knit panels (synthetic), no factory images",
        "manual": bool(d["manual_inspection"]), "selection": L["selection_method"],
        "snapshot_hash": d["snapshot_hash"], "lot": L, "decision": d, "progress": service.progress(lot_id),
        "reasons_raw": reasons,
    }


@router.get("/lots/{lot_id}/report", response_class=HTMLResponse)
def report_page(request: Request, lot_id: int):
    s = require_user(request)
    if s["user"]["role"] == "admin":
        raise Denied(403, "not_allowed")
    rc = _report_ctx(lot_id)
    return page(request, "report.html", active="lots", rc=rc, lot=rc["lot"])


@router.get("/lots/{lot_id}/report.pdf")
def report_pdf(request: Request, lot_id: int):
    s = require_user(request)
    if s["user"]["role"] == "admin":
        raise Denied(403, "not_allowed")
    rc = _report_ctx(lot_id)
    data = report.build(rc)
    return Response(data, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="lotline-{rc["lot_code"]}-decision-{rc["sequence"]}.pdf"',
                             "Cache-Control": "no-store"})
