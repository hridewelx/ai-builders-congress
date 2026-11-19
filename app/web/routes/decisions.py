"""Deterministic decision, override and second-approval routes."""
from __future__ import annotations

import json

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ...core import db
from ...domain import engine
from ...services import review as service
from ..deps import Denied, assert_csrf, can_write_lot, lot_required, require_role, require_user
from ..pages import page

router = APIRouter(tags=["decision"])


@router.post("/lots/{lot_id}/decisions")
def compute_decision(request: Request, lot_id: int, csrf: str = Form(""), note: str = Form("")):
    s = require_role(request, "inspector", "supervisor")
    assert_csrf(request, s, csrf)
    L = lot_required(s, lot_id)
    if not can_write_lot(s, L):
        raise Denied(403, "not_allowed")
    if L["status"] == "decided":
        return RedirectResponse(f"/lots/{lot_id}/decision?err=locked", status_code=303)
    result = service.compute_decision(lot_id, s["user"]["id"], note.strip())
    if result.get("unchanged"):
        return RedirectResponse(f"/lots/{lot_id}/decision?ok=unchanged", status_code=303)
    return RedirectResponse(f"/lots/{lot_id}/decision?ok=saved", status_code=303)


@router.get("/lots/{lot_id}/decision", response_class=HTMLResponse)
def decision_page(request: Request, lot_id: int):
    s = require_user(request)
    L = lot_required(s, lot_id)
    plan = service.plan_dict(service.active_plan(lot_id))
    d = service.latest_decision(lot_id)
    ov = service.override_for(d["id"]) if d else None
    hist = db.q("SELECT d.*, u.display_name AS decided_by FROM decision d JOIN app_user u ON u.id=d.created_by"
                " WHERE d.lot_id=? ORDER BY d.sequence DESC", (lot_id,))
    d = dict(d) if d else None
    if d:
        d["reasons"] = json.loads(d["reasons"])
        d["counts"] = json.loads(d["counts"])
        d["class_limits"] = json.loads(d["class_limits"] or "{}")
        d["completeness"] = json.loads(d["completeness"] or "{}")
        d["plan_snapshot"] = json.loads(d["plan_snapshot"]) if d["plan_snapshot"] else None
    prog = service.progress(lot_id)
    return page(request, "decision.html", active="lots", lot=L, plan=plan, decision=d, override=ov,
                final=service.final_disposition(db.one("SELECT * FROM decision WHERE id=?", (d["id"],)), ov) if d else None,
                history=[dict(h) | {"counts": json.loads(h["counts"]), "reasons": json.loads(h["reasons"])} for h in hist],
                progress=prog, is_supervisor=s["user"]["role"] == "supervisor",
                can_write=(can_write_lot(s, L) and L["status"] != "decided"),
                reason_text=engine.REASONS)


@router.post("/decisions/{decision_id}/override")
def make_override(request: Request, decision_id: int, csrf: str = Form(""), disposition: str = Form(""),
                  reason: str = Form("")):
    s = require_role(request, "supervisor")
    assert_csrf(request, s, csrf)
    d = db.one("SELECT * FROM decision WHERE id=?", (decision_id,))
    if not d or not lot_required(s, d["lot_id"]):
        raise Denied(404, "not_found")
    if d["outcome"] not in ("ACCEPT", "REJECT"):
        return RedirectResponse(f"/lots/{d['lot_id']}/decision?err=override_not_allowed", status_code=303)
    if d["primary_reason"] == "REJECT_CRITICAL_NONVISUAL_FAILED":
        return RedirectResponse(f"/lots/{d['lot_id']}/decision?err=override_not_allowed", status_code=303)
    if disposition not in ("OVERRIDE_ACCEPT", "OVERRIDE_REJECT"):
        raise Denied(422, "invalid")
    if disposition == "OVERRIDE_ACCEPT" and d["outcome"] == "ACCEPT":
        return RedirectResponse(f"/lots/{d['lot_id']}/decision?err=override_not_allowed", status_code=303)
    if len(reason.strip()) < 20:
        return RedirectResponse(f"/lots/{d['lot_id']}/decision?err=reason_short", status_code=303)
    if db.one("SELECT id FROM override WHERE decision_id=?", (decision_id,)):
        return RedirectResponse(f"/lots/{d['lot_id']}/decision?err=already_overridden", status_code=303)
    high_risk = disposition == "OVERRIDE_ACCEPT" and d["outcome"] == "REJECT"
    status = "pending_approval" if high_risk else "effective"
    oid = db.x("INSERT INTO override(decision_id,supervisor_id,final_disposition,reason,status,created_at)"
               " VALUES (?,?,?,?,?,?)",
               (decision_id, s["user"]["id"], disposition, reason.strip(), status, db.now()))
    if not high_risk:
        db.x("UPDATE lot SET status='decided', version=version+1 WHERE id=?", (d["lot_id"],))
    db.audit(s["user"]["id"], s["user"]["display_name"], "decision.overridden", "override", oid,
             after={"disposition": disposition, "system": d["outcome"], "status": status})
    return RedirectResponse(f"/lots/{d['lot_id']}/decision?ok=saved", status_code=303)


@router.post("/overrides/{override_id}/approval")
def approve_override(request: Request, override_id: int, csrf: str = Form(""), decision: str = Form("approved")):
    s = require_role(request, "supervisor")
    assert_csrf(request, s, csrf)
    o = db.one("SELECT * FROM override WHERE id=?", (override_id,))
    if not o:
        raise Denied(404, "not_found")
    o_decision = db.one("SELECT * FROM decision WHERE id=?", (o["decision_id"],))
    if not o_decision or not lot_required(s, o_decision["lot_id"]):
        raise Denied(404, "not_found")
    if o["supervisor_id"] == s["user"]["id"]:
        return RedirectResponse(f"/lots/{db.one('SELECT lot_id FROM decision WHERE id=?', (o['decision_id'],))['lot_id']}/decision?err=self_approval",
                               status_code=303)
    if db.one("SELECT id FROM override_approval WHERE override_id=?", (override_id,)):
        raise Denied(422, "already_approved")
    db.x("INSERT INTO override_approval(override_id,approver_id,decision,created_at) VALUES (?,?,?,?)",
         (override_id, s["user"]["id"], "approved" if decision == "approved" else "refused", db.now()))
    d = db.one("SELECT * FROM decision WHERE id=?", (o["decision_id"],))
    if decision == "approved":
        db.x("UPDATE override SET status='effective' WHERE id=?", (override_id,))
        db.x("UPDATE lot SET status='decided', version=version+1 WHERE id=?", (d["lot_id"],))
    db.audit(s["user"]["id"], s["user"]["display_name"], "decision.override_approved", "override", override_id,
             after={"decision": decision})
    return RedirectResponse(f"/lots/{d['lot_id']}/decision?ok=saved", status_code=303)
