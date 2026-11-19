"""The review queue and a single photo's review workspace."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ...config import ZONES
from ...core import db
from ...services import review as service
from ...services import vision
from ..deps import current_user
from ..serializers import clean
from .shared import _lot_or_404

router = APIRouter(tags=["lots"])

@router.get("/lots/{lot_id}/review")
def review_queue(request: Request, lot_id: int):
    session = current_user(request)
    lot = _lot_or_404(lot_id)
    if session["user"]["role"] == "admin":
        raise HTTPException(status_code=403, detail="not_allowed")
    return {"lot": clean(lot), "queue": clean(service.review_queue(lot_id))}


@router.get("/review/{image_id}")
def review_detail(request: Request, image_id: int):
    session = current_user(request)
    if session["user"]["role"] == "admin":
        raise HTTPException(status_code=403, detail="not_allowed")
    image = db.one("SELECT * FROM image WHERE id=?", (image_id,))
    if not image:
        raise HTTPException(status_code=404, detail="not_found")
    lot = service.lot(image["lot_id"])
    view = db.one("SELECT v.*, u.garment_code, u.id AS unit_id FROM unit_view v"
                  " JOIN sample_unit u ON u.id=v.sample_unit_id WHERE v.id=?", (image["view_id"],))
    review = db.one("SELECT rr.*, a.display_name AS reviewer FROM view_review rr"
                    " LEFT JOIN app_user a ON a.id=rr.reviewed_by WHERE rr.image_id=?", (image_id,))
    job = db.one("SELECT * FROM inference_job WHERE image_id=? ORDER BY id DESC LIMIT 1", (image_id,))
    preds = db.q("SELECT p.*, a.display_name AS reviewer FROM prediction p"
                 " LEFT JOIN app_user a ON a.id=p.reviewed_by WHERE p.image_id=? ORDER BY p.id",
                 (image_id,))
    clauses = db.q("SELECT * FROM clause_mapping WHERE buyer_id=? ORDER BY defect_type, zone_code",
                   (lot["buyer_id"],))
    queue = service.review_queue(image["lot_id"])
    next_item = next((item for item in queue
                      if item["view"]["image"] and item["view"]["image"]["id"] != image_id), None)
    from ...core.permissions import can_write_lot
    return {
        "lot": clean(lot),
        "image": clean(image),
        "view": clean(view),
        "review": clean(review),
        "job": clean(job),
        "preds": clean(preds),
        "clauses": clean(clauses),
        "status": service.derive_status(job),
        "next_item": clean(next_item),
        "can_write": can_write_lot(session, lot) and lot["status"] != "decided",
        "is_supervisor": session["user"]["role"] == "supervisor",
        "user": clean(session["user"]),
        "zones": ZONES,
        "human_classes": list(vision.HUMAN_CLASSES),
    }
