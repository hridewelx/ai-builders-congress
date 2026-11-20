"""One-page inspection report: HTML and PDF."""
from __future__ import annotations

import json

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response

from ...core import db
from ...domain import engine
from ...services import detector, report, vision
from ...services import review as service
from ..deps import Denied, lot_required, require_user
from ..pages import page

router = APIRouter(tags=["report"])


def _model_summary(lot_id: int) -> tuple[str, str]:
    """Report the model that actually produced this lot's proposals."""
    rows = db.q("SELECT DISTINCT ij.model_version FROM inference_job ij"
                " JOIN image i ON i.id=ij.image_id"
                " WHERE i.lot_id=? AND ij.status='succeeded'"
                " ORDER BY ij.model_version", (lot_id,))
    names = sorted({str(row["model_version"]) for row in rows
                    if row["model_version"] and row["model_version"] != "manual"})
    if not names:
        return "manual only", "no model proposal used in this decision"
    if names == [vision.MODEL_NAME]:
        return names[0], "staged knit panels only (unsupervised baseline)"
    if names == [detector.MODEL_NAME]:
        return names[0], detector.MODEL_DOMAIN
    return ", ".join(names), "mixed model provenance; inspect the inference jobs for this lot"


def _report_ctx(lot_id: int, s: dict | None = None) -> dict:
    L = lot_required(s, lot_id) if s is not None else service.lot(lot_id)
    if not L:
        raise Denied(404, "not_found")
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
    model_name, model_domains = _model_summary(lot_id)
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
        "model": model_name, "model_domains": model_domains,
        "manual": bool(d["manual_inspection"]), "selection": L["selection_method"],
        "snapshot_hash": d["snapshot_hash"], "lot": L, "decision": d, "progress": service.progress(lot_id),
        "reasons_raw": reasons,
    }


@router.get("/lots/{lot_id}/report", response_class=HTMLResponse)
def report_page(request: Request, lot_id: int):
    s = require_user(request)
    if s["user"]["role"] == "admin":
        raise Denied(403, "not_allowed")
    rc = _report_ctx(lot_id, s)
    return page(request, "report.html", active="lots", rc=rc, lot=rc["lot"])


@router.get("/lots/{lot_id}/report.pdf")
def report_pdf(request: Request, lot_id: int):
    s = require_user(request)
    if s["user"]["role"] == "admin":
        raise Denied(403, "not_allowed")
    rc = _report_ctx(lot_id, s)
    data = report.build(rc)
    return Response(data, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="lotline-{rc["lot_code"]}-decision-{rc["sequence"]}.pdf"',
                             "Cache-Control": "no-store"})
