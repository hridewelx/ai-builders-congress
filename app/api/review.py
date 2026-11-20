"""Human review actions on model proposals and views."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ..config import ZONES
from ..core import db
from ..core.permissions import image_for, lot_for
from ..services import review as service
from ..services import vision
from .deps import check_csrf, current_user, role_required
from .lots import _ensure_write

router = APIRouter(tags=["review"])


def _image_or_404(image_id: int, session: dict):
    image = image_for(session, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="not_found")
    return image


def _prediction_for(session: dict, image_id: int, prediction_id) -> dict:
    image = _image_or_404(image_id, session)
    prediction = db.one("SELECT * FROM prediction WHERE id=? AND image_id=?",
                        (int(prediction_id or 0), image["id"]))
    if not prediction:
        raise HTTPException(status_code=404, detail="not_found")
    return dict(prediction)


@router.post("/review/{image_id}/confirm")
async def confirm(request: Request, image_id: int):
    session = role_required(current_user(request), "inspector", "supervisor")
    check_csrf(request, session)
    image = _image_or_404(image_id, session)
    lot = lot_for(session, image["lot_id"])
    _ensure_write(request, session, lot)
    data = await request.json()
    prediction = _prediction_for(session, image_id, data.get("prediction_id"))
    defect_type = str(data.get("defect_type") or "")
    zone = str(data.get("zone") or "I")
    if defect_type not in vision.HUMAN_CLASSES or zone not in ZONES:
        raise HTTPException(status_code=422, detail="invalid")
    band = str(data.get("size_band") or "").strip() or None
    clause = service.map_clause(lot["buyer_id"], defect_type, zone, band)
    db.x("UPDATE prediction SET review_state='confirmed', confirmed_type=?, zone_code=?, size_band=?,"
         " severity=?, clause_ref=?, note=?, reviewed_by=?, reviewed_at=? WHERE id=?",
         (defect_type, zone, band, clause["severity"] if clause else None,
          clause["clause_ref"] if clause else None,
          str(data.get("note") or "").strip() or None,
          session["user"]["id"], db.now(), prediction["id"]))
    db.audit(session["user"]["id"], session["user"]["display_name"], "defect.confirmed", "prediction",
             prediction["id"], after={"type": defect_type, "zone": zone,
                                       "severity": clause["severity"] if clause else None,
                                       "clause": clause["clause_ref"] if clause else None})
    return {"ok": True, "severity": clause["severity"] if clause else None}


@router.post("/review/{image_id}/reject")
async def reject(request: Request, image_id: int):
    session = role_required(current_user(request), "inspector", "supervisor")
    check_csrf(request, session)
    image = _image_or_404(image_id, session)
    _ensure_write(request, session, lot_for(session, image["lot_id"]))
    data = await request.json()
    prediction = _prediction_for(session, image_id, data.get("prediction_id"))
    second = None
    if prediction["provisional_critical"]:
        second = "confirmed" if session["user"]["role"] == "supervisor" else "pending"
    db.x("UPDATE prediction SET review_state='rejected', second_review=?, reviewed_by=?,"
         " reviewed_at=? WHERE id=?",
         (second, session["user"]["id"], db.now(), prediction["id"]))
    db.audit(session["user"]["id"], session["user"]["display_name"], "defect.rejected", "prediction",
             prediction["id"], after={"provisional_critical": bool(prediction["provisional_critical"]),
                                       "second_review": second})
    return {"ok": True}


@router.post("/review/{image_id}/second-review")
async def second_review(request: Request, image_id: int):
    session = role_required(current_user(request), "supervisor")
    check_csrf(request, session)
    data = await request.json()
    prediction = _prediction_for(session, image_id, data.get("prediction_id"))
    if prediction["reviewed_by"] == session["user"]["id"]:
        raise HTTPException(status_code=422, detail="different_reviewer")
    outcome = str(data.get("outcome") or "confirm")
    second = "confirmed" if outcome == "confirm" else "overturned"
    db.x("UPDATE prediction SET second_review=? WHERE id=?", (second, prediction["id"]))
    db.audit(session["user"]["id"], session["user"]["display_name"], "defect.second_review",
             "prediction", prediction["id"], after={"second_review": second})
    return {"ok": True}


@router.post("/review/{image_id}/add")
async def add_defect(request: Request, image_id: int):
    session = role_required(current_user(request), "inspector", "supervisor")
    check_csrf(request, session)
    image = _image_or_404(image_id, session)
    lot = lot_for(session, image["lot_id"])
    _ensure_write(request, session, lot)
    data = await request.json()
    defect_type = str(data.get("defect_type") or "")
    zone = str(data.get("zone") or "I")
    if defect_type not in vision.HUMAN_CLASSES or zone not in ZONES:
        raise HTTPException(status_code=422, detail="invalid")
    job = db.one("SELECT * FROM inference_job WHERE image_id=? ORDER BY id DESC LIMIT 1", (image_id,))
    if not job:
        job_id = db.x("INSERT INTO inference_job(image_id,status,model_version,created_at,finished_at)"
                      " VALUES (?,?,?,?,?)", (image_id, "succeeded", "manual", db.now(), db.now()))
    else:
        job_id = job["id"]
    width = height = 0.16
    cx = float(data.get("cx") or 0.5)
    cy = float(data.get("cy") or 0.5)
    band = str(data.get("size_band") or "").strip() or None
    clause = service.map_clause(lot["buyer_id"], defect_type, zone, band)
    prediction_id = db.x(
        "INSERT INTO prediction(job_id,image_id,defect_type,score,x1,y1,x2,y2,review_state,"
        "confirmed_type,zone_code,size_band,severity,clause_ref,provisional_critical,second_review,"
        "note,reviewed_by,reviewed_at,created_at)"
        " VALUES (?,?,?,0.0,?,?,?,?, 'confirmed',?,?,?,?,?,?,?,?,?,?,?)",
        (job_id, image_id, defect_type, max(0.02, cx - width / 2), max(0.02, cy - height / 2),
         min(0.98, cx + width / 2), min(0.98, cy + height / 2), defect_type, zone, band,
         clause["severity"] if clause else None, clause["clause_ref"] if clause else None,
         1 if defect_type in ("hole",) else 0,
         "requested" if data.get("second_opinion") else None,
         str(data.get("note") or "").strip() or None,
         session["user"]["id"], db.now(), db.now()))
    db.audit(session["user"]["id"], session["user"]["display_name"], "defect.added_manually",
             "prediction", prediction_id,
             after={"type": defect_type, "zone": zone,
                    "severity": clause["severity"] if clause else None})
    return {"ok": True, "prediction_id": prediction_id}


@router.post("/review/{image_id}/state")
async def set_state(request: Request, image_id: int):
    session = role_required(current_user(request), "inspector", "supervisor")
    check_csrf(request, session)
    image = _image_or_404(image_id, session)
    lot = lot_for(session, image["lot_id"])
    _ensure_write(request, session, lot)
    data = await request.json()
    state = str(data.get("state") or "")
    note = str(data.get("note") or "")
    if state not in ("reviewed_clean", "confirmed_defects", "needs_retake"):
        raise HTTPException(status_code=422, detail="invalid")
    predictions = db.q("SELECT * FROM prediction WHERE image_id=?", (image_id,))
    open_items = [item for item in predictions if item["review_state"] == "proposed"]
    confirmed = [item for item in predictions if item["review_state"] == "confirmed"]
    if state == "confirmed_defects" and not confirmed:
        raise HTTPException(status_code=409, detail="no_defects")
    if state == "reviewed_clean" and confirmed:
        raise HTTPException(status_code=409, detail="has_defects")
    if open_items:
        raise HTTPException(status_code=409, detail="review_first")
    db.x("INSERT INTO view_review(image_id,state,note,reviewed_by,reviewed_at)"
         " VALUES (?,?,?,?,?) ON CONFLICT(image_id) DO UPDATE SET state=excluded.state,"
         " note=excluded.note, reviewed_by=excluded.reviewed_by, reviewed_at=excluded.reviewed_at",
         (image_id, state, note.strip() or None, session["user"]["id"], db.now()))
    db.audit(session["user"]["id"], session["user"]["display_name"], f"view.{state}", "image", image_id)
    return {"ok": True, "retake": state == "needs_retake", "lot_id": lot["id"]}
