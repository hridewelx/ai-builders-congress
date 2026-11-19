"""Deterministic decision, override and second-approval endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ..core import db
from ..domain import engine
from ..domain.reason_catalog import REASON_CATALOG
from ..services import review as service
from .deps import check_csrf, current_user, role_required
from .serializers import clean, decision_payload, report_context

router = APIRouter(tags=["decision"])


def _decision_page(lot_id: int, session: dict) -> dict:
    lot = service.lot(lot_id)
    if not lot:
        raise HTTPException(status_code=404, detail="not_found")
    like = service.latest_decision(lot_id)
    decision = decision_payload(like)
    override = service.override_for(like["id"]) if like else None
    history_rows = db.q("SELECT d.*, u.display_name AS decided_by FROM decision d"
                        " JOIN app_user u ON u.id=d.created_by WHERE d.lot_id=?"
                        " ORDER BY d.sequence DESC", (lot_id,))
    from ..core.permissions import can_write_lot
    return {
        "lot": clean(lot),
        "plan": service.plan_dict(service.active_plan(lot_id)),
        "decision": decision,
        "override": clean(override),
        "final": service.final_disposition(like, override) if like else None,
        "history": [decision_payload(row) for row in history_rows],
        "progress": service.progress(lot_id),
        "is_supervisor": session["user"]["role"] == "supervisor",
        "can_write": can_write_lot(session, lot) and lot["status"] != "decided",
        "reason_catalog": REASON_CATALOG,
        "engine_reasons": {code: {"outcome": pair[0], "text": pair[1]}
                           for code, pair in engine.REASONS.items()},
        "user": clean(session["user"]),
    }


@router.get("/lots/{lot_id}/decision")
def decision_page(request: Request, lot_id: int):
    session = current_user(request)
    return _decision_page(lot_id, session)


@router.post("/lots/{lot_id}/decisions")
async def compute(request: Request, lot_id: int):
    session = role_required(current_user(request), "inspector", "supervisor")
    check_csrf(request, session)
    lot = service.lot(lot_id)
    if not lot:
        raise HTTPException(status_code=404, detail="not_found")
    from ..core.permissions import can_write_lot
    if not can_write_lot(session, lot):
        raise HTTPException(status_code=403, detail="not_allowed")
    if lot["status"] == "decided":
        raise HTTPException(status_code=409, detail="locked")
    data = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    result = service.compute_decision(lot_id, session["user"]["id"], str(data.get("note") or "").strip())
    return {"ok": True, "unchanged": bool(result.get("unchanged")),
            "decision": decision_payload(result)}


@router.post("/decisions/{decision_id}/override")
async def override(request: Request, decision_id: int):
    session = role_required(current_user(request), "supervisor")
    check_csrf(request, session)
    decision = db.one("SELECT * FROM decision WHERE id=?", (decision_id,))
    if not decision:
        raise HTTPException(status_code=404, detail="not_found")
    data = await request.json()
    disposition = str(data.get("disposition") or "")
    reason = str(data.get("reason") or "")
    if decision["outcome"] not in ("ACCEPT", "REJECT"):
        raise HTTPException(status_code=409, detail="override_not_allowed")
    if decision["primary_reason"] == "REJECT_CRITICAL_NONVISUAL_FAILED":
        raise HTTPException(status_code=409, detail="override_not_allowed")
    if disposition not in ("OVERRIDE_ACCEPT", "OVERRIDE_REJECT"):
        raise HTTPException(status_code=422, detail="invalid")
    if disposition == "OVERRIDE_ACCEPT" and decision["outcome"] == "ACCEPT":
        raise HTTPException(status_code=409, detail="override_not_allowed")
    if len(reason.strip()) < 20:
        raise HTTPException(status_code=422, detail="reason_short")
    if db.one("SELECT id FROM override WHERE decision_id=?", (decision_id,)):
        raise HTTPException(status_code=409, detail="already_overridden")
    high_risk = disposition == "OVERRIDE_ACCEPT" and decision["outcome"] == "REJECT"
    status = "pending_approval" if high_risk else "effective"
    override_id = db.x("INSERT INTO override(decision_id,supervisor_id,final_disposition,reason,status,"
                       "created_at) VALUES (?,?,?,?,?,?)",
                       (decision_id, session["user"]["id"], disposition, reason.strip(), status, db.now()))
    if not high_risk:
        db.x("UPDATE lot SET status='decided', version=version+1 WHERE id=?", (decision["lot_id"],))
    db.audit(session["user"]["id"], session["user"]["display_name"], "decision.overridden", "override",
             override_id, after={"disposition": disposition, "system": decision["outcome"],
                                 "status": status})
    return {"ok": True, "override_id": override_id, "status": status}


@router.post("/overrides/{override_id}/approval")
async def approve(request: Request, override_id: int):
    session = role_required(current_user(request), "supervisor")
    check_csrf(request, session)
    override_row = db.one("SELECT * FROM override WHERE id=?", (override_id,))
    if not override_row:
        raise HTTPException(status_code=404, detail="not_found")
    if override_row["supervisor_id"] == session["user"]["id"]:
        raise HTTPException(status_code=409, detail="self_approval")
    if db.one("SELECT id FROM override_approval WHERE override_id=?", (override_id,)):
        raise HTTPException(status_code=409, detail="already_approved")
    data = await request.json()
    decision = str(data.get("decision") or "approved")
    db.x("INSERT INTO override_approval(override_id,approver_id,decision,created_at) VALUES (?,?,?,?)",
         (override_id, session["user"]["id"], "approved" if decision == "approved" else "refused",
          db.now()))
    row = db.one("SELECT * FROM decision WHERE id=?", (override_row["decision_id"],))
    if decision == "approved":
        db.x("UPDATE override SET status='effective' WHERE id=?", (override_id,))
        db.x("UPDATE lot SET status='decided', version=version+1 WHERE id=?", (row["lot_id"],))
    db.audit(session["user"]["id"], session["user"]["display_name"],
             "decision.override_approved", "override", override_id, after={"decision": decision})
    return {"ok": True}


@router.get("/lots/{lot_id}/report")
def report(request: Request, lot_id: int):
    session = current_user(request)
    if session["user"]["role"] == "admin":
        raise HTTPException(status_code=403, detail="not_allowed")
    context = report_context(lot_id)
    if not context:
        raise HTTPException(status_code=404, detail="not_found")
    return {"rc": context, "reason_catalog": REASON_CATALOG}
