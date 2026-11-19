"""Sampling capture: units, photo upload, and detector runs."""
from __future__ import annotations

import hashlib
import io
import os

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError

from ...config import MAX_BYTES, MAX_IMAGE_EDGE, MAX_PIXELS
from ...core import db
from ...core.permissions import lot_for
from ...services import inference
from ...services import review as service
from ..deps import check_csrf, current_user, role_required
from ..serializers import clean
from .shared import _ensure_write, _lot_or_404

router = APIRouter(tags=["lots"])

@router.get("/lots/{lot_id}/capture")
def capture(request: Request, lot_id: int):
    session = current_user(request)
    lot = _lot_or_404(lot_id, session)
    if session["user"]["role"] == "admin":
        raise HTTPException(status_code=403, detail="not_allowed")
    from ...core.permissions import can_write_lot
    return {
        "lot": clean(lot),
        "units": clean(service.units_with_views(lot_id)),
        "progress": service.progress(lot_id),
        "can_write": can_write_lot(session, lot) and lot["status"] != "decided",
        "user": clean(session["user"]),
    }


@router.post("/lots/{lot_id}/units")
async def add_unit(request: Request, lot_id: int):
    session = role_required(current_user(request), "inspector", "supervisor")
    check_csrf(request, session)
    lot = _lot_or_404(lot_id, session)
    _ensure_write(request, session, lot)
    data = await request.json()
    plan = service.active_plan(lot_id)
    required = min(plan["n"], lot["lot_size"]) if plan else lot["lot_size"]
    have = db.one("SELECT COUNT(*) AS n FROM sample_unit WHERE lot_id=?", (lot_id,))["n"]
    if have >= required:
        raise HTTPException(status_code=409, detail="units_full")
    code = str(data.get("garment_code") or "").strip() or f"G-{have + 1:02d}"
    if db.one("SELECT id FROM sample_unit WHERE lot_id=? AND garment_code=?", (lot_id, code)):
        raise HTTPException(status_code=409, detail="exists")
    unit_id = db.x("INSERT INTO sample_unit(lot_id,garment_code,created_at) VALUES (?,?,?)",
                   (lot_id, code, db.now()))
    for side in ("front", "back"):
        db.x("INSERT INTO unit_view(sample_unit_id,side,required) VALUES (?,?,1)", (unit_id, side))
    db.audit(session["user"]["id"], session["user"]["display_name"], "unit.created", "lot", lot_id,
             after={"garment": code})
    return {"ok": True, "unit_id": unit_id}


@router.post("/lots/{lot_id}/views/{view_id}/upload")
async def upload(request: Request, lot_id: int, view_id: int, file: UploadFile = File(...)):
    session = role_required(current_user(request), "inspector", "supervisor")
    check_csrf(request, session)
    lot = _lot_or_404(lot_id, session)
    _ensure_write(request, session, lot)
    view = db.one("SELECT v.* FROM unit_view v JOIN sample_unit u ON u.id=v.sample_unit_id"
                  " WHERE v.id=? AND u.lot_id=?", (view_id, lot_id))
    if not view:
        raise HTTPException(status_code=404, detail="not_found")
    raw = await file.read()
    if len(raw) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="too_big")
    if not raw:
        raise HTTPException(status_code=422, detail="bad_type")
    if not (raw.startswith(b"\xff\xd8\xff") or raw.startswith(b"\x89PNG\r\n\x1a\n")):
        raise HTTPException(status_code=422, detail="bad_type")
    sha_original = hashlib.sha256(raw).hexdigest()
    duplicate = db.one("SELECT id FROM image WHERE lot_id=? AND sha256_original=? AND purged=0",
                       (lot_id, sha_original))
    if duplicate:
        raise HTTPException(status_code=409, detail="duplicate")
    try:
        image = Image.open(io.BytesIO(raw))
        if image.width * image.height > MAX_PIXELS:
            raise HTTPException(status_code=413, detail="too_big")
        image = ImageOps.exif_transpose(image).convert("RGB")
        image.thumbnail((MAX_IMAGE_EDGE, MAX_IMAGE_EDGE), Image.LANCZOS)
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(status_code=422, detail="bad_type")
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=88, optimize=True)
    data = buffer.getvalue()
    sha_working = hashlib.sha256(data).hexdigest()
    os.makedirs(service.STORE, exist_ok=True)
    name = f"{os.urandom(16).hex()}.jpg"
    with open(os.path.join(service.STORE, name), "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    db.x("UPDATE image SET is_current=0 WHERE view_id=? AND is_current=1", (view_id,))
    image_id = db.x(
        "INSERT INTO image(lot_id,view_id,stored_name,original_name,sha256_original,sha256_working,"
        "width,height,bytes,is_current,purged,uploaded_by,created_at)"
        " VALUES (?,?,?,?,?,?,?,?,?,1,0,?,?)",
        (lot_id, view_id, name, (file.filename or "upload.jpg")[:120], sha_original, sha_working,
         image.width, image.height, len(data), session["user"]["id"], db.now()))
    db.audit(session["user"]["id"], session["user"]["display_name"], "image.uploaded", "lot", lot_id,
             after={"image_id": image_id, "view_id": view_id, "bytes": len(data),
                    "sha256": sha_working[:16]})
    status = inference.enqueue(image_id, session["user"]["id"])
    return {"ok": status in ("ok", "queued"), "image_id": image_id, "status": status}



@router.post("/images/{image_id}/infer")
def infer_again(request: Request, image_id: int):
    session = role_required(current_user(request), "inspector", "supervisor")
    check_csrf(request, session)
    image = db.one("SELECT * FROM image WHERE id=?", (image_id,))
    if not image:
        raise HTTPException(status_code=404, detail="not_found")
    _ensure_write(request, session, lot_for(session, image["lot_id"]))
    status = inference.enqueue(image_id, session["user"]["id"])
    return {"ok": status in ("ok", "queued"), "status": status}
