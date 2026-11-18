"""Human review of model proposals."""
from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ...config import ZONES
from ...core import db
from ...services import review as service
from ...services import vision
from ..deps import Denied, assert_csrf, can_write_lot, ensure_write, require_role, require_user
from ..pages import page

router = APIRouter(tags=["review"])


@router.get("/lots/{lot_id}/review", response_class=HTMLResponse)
def review_queue_page(request: Request, lot_id: int):
    s = require_user(request)
    L = service.lot(lot_id)
    if not L:
        raise Denied(404, "not_found")
    if s["user"]["role"] == "admin":
        raise Denied(403, "not_allowed")
    return page(request, "review_queue.html", active="lots", lot=L, queue=service.review_queue(lot_id))


@router.get("/review/{img_id}", response_class=HTMLResponse)
def review_page(request: Request, img_id: int):
    s = require_user(request)
    if s["user"]["role"] == "admin":
        raise Denied(403, "not_allowed")
    img = db.one("SELECT * FROM image WHERE id=?", (img_id,))
    if not img:
        raise Denied(404, "not_found")
    L = service.lot(img["lot_id"])
    view = db.one("SELECT v.*, u.garment_code, u.id AS unit_id FROM unit_view v"
                  " JOIN sample_unit u ON u.id=v.sample_unit_id WHERE v.id=?", (img["view_id"],))
    review = db.one("SELECT rr.*, a.display_name AS reviewer FROM view_review rr"
                    " LEFT JOIN app_user a ON a.id=rr.reviewed_by WHERE rr.image_id=?", (img_id,))
    job = db.one("SELECT * FROM inference_job WHERE image_id=? ORDER BY id DESC LIMIT 1", (img_id,))
    preds = db.q("SELECT p.*, a.display_name AS reviewer FROM prediction p"
                 " LEFT JOIN app_user a ON a.id=p.reviewed_by WHERE p.image_id=? ORDER BY p.id", (img_id,))
    clause_rows = db.q("SELECT * FROM clause_mapping WHERE buyer_id=? ORDER BY defect_type, zone_code",
                       (L["buyer_id"],))
    queue = service.review_queue(img["lot_id"])
    nxt = next((q for q in queue if q["view"]["image"] and q["view"]["image"]["id"] != img_id), None)
    return page(request, "review.html", active="lots", lot=L, image=img, view=view, review=review,
                job=job, preds=[dict(p) for p in preds], clauses=[dict(c) for c in clause_rows],
                status=service.derive_status(job), next_item=nxt,
                can_write=(can_write_lot(s, L) and L["status"] != "decided"),
                is_supervisor=s["user"]["role"] == "supervisor")


@router.post("/review/{img_id}/confirm")
def confirm_prediction(request: Request, img_id: int, csrf: str = Form(""), prediction_id: int = Form(0),
                       defect_type: str = Form(""), zone: str = Form("I"), size_band: str = Form(""),
                       note: str = Form("")):
    s = require_role(request, "inspector", "supervisor")
    assert_csrf(request, s, csrf)
    img = db.one("SELECT * FROM image WHERE id=?", (img_id,))
    if not img:
        raise Denied(404, "not_found")
    L = service.lot(img["lot_id"])
    ensure_write(request, s, L)
    p = db.one("SELECT * FROM prediction WHERE id=? AND image_id=?", (prediction_id, img_id))
    if not p:
        raise Denied(404, "not_found")
    if defect_type not in vision.HUMAN_CLASSES:
        raise Denied(422, "invalid")
    if zone not in ZONES:
        raise Denied(422, "invalid")
    band = size_band.strip() or None
    c = service.map_clause(L["buyer_id"], defect_type, zone, band)
    db.x("UPDATE prediction SET review_state='confirmed', confirmed_type=?, zone_code=?, size_band=?,"
         " severity=?, clause_ref=?, note=?, reviewed_by=?, reviewed_at=? WHERE id=?",
         (defect_type, zone, band, c["severity"] if c else None, c["clause_ref"] if c else None,
          note.strip() or None, s["user"]["id"], db.now(), p["id"]))
    db.audit(s["user"]["id"], s["user"]["display_name"], "defect.confirmed", "prediction", p["id"],
             after={"type": defect_type, "zone": zone, "severity": c["severity"] if c else None,
                    "clause": c["clause_ref"] if c else None})
    return RedirectResponse(f"/review/{img_id}?ok=saved", status_code=303)


@router.post("/review/{img_id}/reject")
def reject_prediction(request: Request, img_id: int, csrf: str = Form(""), prediction_id: int = Form(0)):
    s = require_role(request, "inspector", "supervisor")
    assert_csrf(request, s, csrf)
    img = db.one("SELECT * FROM image WHERE id=?", (img_id,))
    if not img:
        raise Denied(404, "not_found")
    ensure_write(request, s, service.lot(img["lot_id"]))
    p = db.one("SELECT * FROM prediction WHERE id=? AND image_id=?", (prediction_id, img_id))
    if not p:
        raise Denied(404, "not_found")
    second = None
    if p["provisional_critical"]:
        second = "confirmed" if s["user"]["role"] == "supervisor" else "pending"
    db.x("UPDATE prediction SET review_state='rejected', second_review=?, reviewed_by=?, reviewed_at=? WHERE id=?",
         (second, s["user"]["id"], db.now(), p["id"]))
    db.audit(s["user"]["id"], s["user"]["display_name"], "defect.rejected", "prediction", p["id"],
             after={"provisional_critical": bool(p["provisional_critical"]), "second_review": second})
    return RedirectResponse(f"/review/{img_id}?ok=saved", status_code=303)


@router.post("/review/{img_id}/second-review")
def second_review(request: Request, img_id: int, csrf: str = Form(""), prediction_id: int = Form(0),
                  outcome: str = Form("confirm")):
    s = require_role(request, "supervisor")
    assert_csrf(request, s, csrf)
    p = db.one("SELECT * FROM prediction WHERE id=? AND image_id=?", (prediction_id, img_id))
    if not p:
        raise Denied(404, "not_found")
    if p["reviewed_by"] == s["user"]["id"]:
        raise Denied(422, "different_reviewer")
    second = "confirmed" if outcome == "confirm" else "overturned"
    db.x("UPDATE prediction SET second_review=? WHERE id=?", (second, p["id"]))
    db.audit(s["user"]["id"], s["user"]["display_name"], "defect.second_review", "prediction", p["id"],
             after={"second_review": second})
    return RedirectResponse(f"/review/{img_id}?ok=saved", status_code=303)


@router.post("/review/{img_id}/add")
def add_defect(request: Request, img_id: int, csrf: str = Form(""), defect_type: str = Form(""),
               zone: str = Form("I"), size_band: str = Form(""), note: str = Form(""),
               cx: float = Form(0.5), cy: float = Form(0.5), second_opinion: str = Form("")):
    s = require_role(request, "inspector", "supervisor")
    assert_csrf(request, s, csrf)
    img = db.one("SELECT * FROM image WHERE id=?", (img_id,))
    if not img:
        raise Denied(404, "not_found")
    L = service.lot(img["lot_id"])
    ensure_write(request, s, L)
    if defect_type not in vision.HUMAN_CLASSES:
        raise Denied(422, "invalid")
    job = db.one("SELECT * FROM inference_job WHERE image_id=? ORDER BY id DESC LIMIT 1", (img_id,))
    if not job:
        job_id = db.x("INSERT INTO inference_job(image_id,status,model_version,created_at,finished_at)"
                      " VALUES (?,?,?,?,?)", (img_id, "succeeded", "manual", db.now(), db.now()))
    else:
        job_id = job["id"]
    w, h = 0.16, 0.16
    c = service.map_clause(L["buyer_id"], defect_type, zone, size_band.strip() or None)
    crit = 1 if defect_type in ("hole",) else 0
    pid = db.x("INSERT INTO prediction(job_id,image_id,defect_type,score,x1,y1,x2,y2,review_state,"
               "confirmed_type,zone_code,size_band,severity,clause_ref,provisional_critical,second_review,note,"
               "reviewed_by,reviewed_at,created_at)"
               " VALUES (?,?,?,0.0,?,?,?,?, 'confirmed',?,?,?,?,?,?,?,?,?,?,?)",
               (job_id, img_id, defect_type, max(0.02, cx - w / 2), max(0.02, cy - h / 2),
                min(0.98, cx + w / 2), min(0.98, cy + h / 2), defect_type, zone,
                size_band.strip() or None, c["severity"] if c else None, c["clause_ref"] if c else None,
                crit, "requested" if second_opinion else None, note.strip() or None,
                s["user"]["id"], db.now(), db.now()))
    db.audit(s["user"]["id"], s["user"]["display_name"], "defect.added_manually", "prediction", pid,
             after={"type": defect_type, "zone": zone, "severity": c["severity"] if c else None})
    return RedirectResponse(f"/review/{img_id}?ok=saved", status_code=303)


@router.post("/review/{img_id}/state")
def set_view_state(request: Request, img_id: int, csrf: str = Form(""), state: str = Form(""),
                   note: str = Form("")):
    s = require_role(request, "inspector", "supervisor")
    assert_csrf(request, s, csrf)
    img = db.one("SELECT * FROM image WHERE id=?", (img_id,))
    if not img:
        raise Denied(404, "not_found")
    L = service.lot(img["lot_id"])
    ensure_write(request, s, L)
    if state not in ("reviewed_clean", "confirmed_defects", "needs_retake"):
        raise Denied(422, "invalid")
    preds = db.q("SELECT * FROM prediction WHERE image_id=?", (img_id,))
    openp = [p for p in preds if p["review_state"] == "proposed"]
    confirmed = [p for p in preds if p["review_state"] == "confirmed"]
    if state == "confirmed_defects" and not confirmed:
        return RedirectResponse(f"/review/{img_id}?err=no_defects", status_code=303)
    if state == "reviewed_clean" and confirmed:
        return RedirectResponse(f"/review/{img_id}?err=has_defects", status_code=303)
    if openp:
        # finishing manually cancels the queue but never leaves an unanswered proposal
        return RedirectResponse(f"/review/{img_id}?err=review_first", status_code=303)
    db.x("INSERT OR REPLACE INTO view_review(image_id,state,note,reviewed_by,reviewed_at) VALUES (?,?,?,?,?)",
         (img_id, state, note.strip() or None, s["user"]["id"], db.now()))
    db.audit(s["user"]["id"], s["user"]["display_name"], f"view.{state}", "image", img_id)
    if state == "needs_retake":
        return RedirectResponse(f"/lots/{img['lot_id']}/capture?ok=retake", status_code=303)
    return RedirectResponse(f"/review/{img_id}?ok=saved", status_code=303)
