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
    from ...core import security
    from ...core.permissions import can_write_lot
    from ...services import cloudinary
    from ...web.pages import get_lan_ip, get_public_base_url

    can_write = can_write_lot(session, lot) and lot["status"] != "decided"
    units = service.units_with_views(lot_id)
    if not units and can_write:
        code = "G-01"
        unit_id = db.x("INSERT INTO sample_unit(lot_id,garment_code,created_at) VALUES (?,?,?)",
                       (lot_id, code, db.now()))
        for side in ("front", "back"):
            db.x("INSERT INTO unit_view(sample_unit_id,side,required) VALUES (?,?,1)", (unit_id, side))
        db.audit(session["user"]["id"], session["user"]["display_name"], "unit.created", "lot", lot_id,
                 after={"garment": code})
        units = service.units_with_views(lot_id)

    public_base_url, is_tunnel = get_public_base_url(request)
    raw_token = request.cookies.get(security.COOKIE) or request.query_params.get("session_token") or ""

    return {
        "lot": clean(lot),
        "units": clean(units),
        "progress": service.progress(lot_id),
        "can_write": can_write,
        "user": clean(session["user"]),
        "cloudinary_configured": cloudinary.is_configured(),
        "lan_ip": get_lan_ip(),
        "public_base_url": public_base_url,
        "is_tunnel": is_tunnel,
        "session_token": raw_token,
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


@router.get("/tunnel-status")
def tunnel_status(request: Request):
    from ...config import get_active_tunnel_url
    from ...web.pages import get_lan_ip, get_public_base_url

    tunnel_url = get_active_tunnel_url()
    public_base_url, is_tunnel = get_public_base_url(request)
    return {
        "active": is_tunnel,
        "tunnel_url": tunnel_url,
        "public_base_url": public_base_url,
        "lan_ip": get_lan_ip(),
    }


@router.get("/lots/{lot_id}/views/{view_id}/cloudinary-sign")
def cloudinary_sign(request: Request, lot_id: int, view_id: int):
    session = role_required(current_user(request), "inspector", "supervisor")
    lot = _lot_or_404(lot_id, session)
    _ensure_write(request, session, lot)
    view = db.one(
        "SELECT v.*, u.garment_code FROM unit_view v JOIN sample_unit u ON u.id=v.sample_unit_id"
        " WHERE v.id=? AND u.lot_id=?",
        (view_id, lot_id),
    )
    if not view:
        raise HTTPException(status_code=404, detail="not_found")
    from ...services import cloudinary
    return cloudinary.sign_upload_params(lot_id, view_id, garment_code=view["garment_code"])


@router.post("/lots/{lot_id}/views/{view_id}/register-cloudinary")
async def register_cloudinary(request: Request, lot_id: int, view_id: int):
    session = role_required(current_user(request), "inspector", "supervisor")
    check_csrf(request, session)
    lot = _lot_or_404(lot_id, session)
    _ensure_write(request, session, lot)
    view = db.one(
        "SELECT v.*, u.garment_code FROM unit_view v JOIN sample_unit u ON u.id=v.sample_unit_id"
        " WHERE v.id=? AND u.lot_id=?",
        (view_id, lot_id),
    )
    if not view:
        raise HTTPException(status_code=404, detail="not_found")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid_json")

    public_id = str(body.get("public_id") or "").strip()
    secure_url = str(body.get("secure_url") or "").strip()
    captured_at = str(body.get("captured_at") or db.now()).strip()
    client_b64 = body.get("image_base64")

    if not public_id or not secure_url:
        raise HTTPException(status_code=400, detail="missing_cloudinary_ref")

    dup = db.one(
        "SELECT id FROM image WHERE lot_id=? AND cloudinary_public_id=? AND purged=0",
        (lot_id, public_id),
    )
    if dup:
        return {"ok": False, "error": "duplicate_image", "image_id": dup["id"]}

    raw = None
    if client_b64:
        if "," in client_b64:
            client_b64 = client_b64.split(",", 1)[1]
        try:
            import base64
            raw = base64.b64decode(client_b64)
        except Exception:
            raw = None

    if not raw and secure_url.startswith("http"):
        try:
            import httpx
            async with httpx.AsyncClient(timeout=20.0) as client:
                res = await client.get(secure_url)
                if res.status_code == 200:
                    raw = res.content
        except Exception:
            raw = None

    if not raw:
        raise HTTPException(status_code=400, detail="failed_to_fetch_image")

    sha_orig = hashlib.sha256(raw).hexdigest()
    dup_sha = db.one(
        "SELECT id FROM image WHERE lot_id=? AND sha256_original=? AND purged=0",
        (lot_id, sha_orig),
    )
    if dup_sha:
        return {"ok": False, "error": "duplicate_image_sha", "image_id": dup_sha["id"]}

    try:
        im = Image.open(io.BytesIO(raw))
        im = ImageOps.exif_transpose(im).convert("RGB")
        im.thumbnail((MAX_IMAGE_EDGE, MAX_IMAGE_EDGE), Image.LANCZOS)
    except Exception:
        raise HTTPException(status_code=400, detail="bad_image_format")

    work = io.BytesIO()
    im.save(work, "JPEG", quality=88, optimize=True)
    data = work.getvalue()
    sha_work = hashlib.sha256(data).hexdigest()

    os.makedirs(service.STORE, exist_ok=True)
    stored_name = f"{os.urandom(16).hex()}.jpg"
    path = os.path.join(service.STORE, stored_name)
    with open(path, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())

    db.x("UPDATE image SET is_current=0 WHERE view_id=? AND is_current=1", (view_id,))
    img_id = db.x(
        "INSERT INTO image(lot_id,view_id,stored_name,original_name,sha256_original,sha256_working,"
        "width,height,bytes,is_current,purged,uploaded_by,cloudinary_url,cloudinary_public_id,"
        "captured_at,inspection_id,inspector_id,created_at)"
        " VALUES (?,?,?,?,?,?,?,?,?,1,0,?,?,?,?,?,?,?)",
        (
            lot_id,
            view_id,
            stored_name,
            f"cld_{public_id}.jpg"[:120],
            sha_orig,
            sha_work,
            im.width,
            im.height,
            len(data),
            session["user"]["id"],
            secure_url,
            public_id,
            captured_at,
            view_id,
            session["user"]["id"],
            db.now(),
        ),
    )

    db.audit(
        session["user"]["id"],
        session["user"]["display_name"],
        "image.cloudinary_registered",
        "lot",
        lot_id,
        after={"image_id": img_id, "view_id": view_id, "public_id": public_id, "bytes": len(data)},
    )

    status = inference.enqueue(img_id, session["user"]["id"])

    next_view = None
    for u in service.units_with_views(lot_id):
        for v in u["views"]:
            if not v["image"]:
                next_view = {
                    "unit_id": u["id"],
                    "garment_code": u["garment_code"],
                    "view_id": v["id"],
                    "side": v["side"],
                }
                break
        if next_view:
            break

    return {
        "ok": True,
        "image_id": img_id,
        "view_id": view_id,
        "public_id": public_id,
        "secure_url": secure_url,
        "next_view": next_view,
        "lot_complete": next_view is None,
        "status": status,
    }


@router.get("/lots/{lot_id}/views-status")
def views_status(request: Request, lot_id: int):
    session = current_user(request)
    lot = _lot_or_404(lot_id, session)
    units = service.units_with_views(lot_id)
    progress = service.progress(lot_id)
    out_units = []
    for u in units:
        views = []
        for v in u["views"]:
            img = v["image"]
            views.append({
                "view_id": v["id"],
                "side": v["side"],
                "has_image": bool(img),
                "image_id": img["id"] if img else None,
                "cloudinary_url": img.get("cloudinary_url") if img else None,
                "thumbnail_url": f"/api/images/{img['id']}" if img else None,
                "review_state": v["review_state"],
                "inference_status": v["inference_status"],
                "open_proposals": v["open_proposals"],
            })
        out_units.append({
            "unit_id": u["id"],
            "garment_code": u["garment_code"],
            "views": views,
        })
    from ...web.pages import get_public_base_url

    public_base_url, is_tunnel = get_public_base_url(request)
    return {
        "lot_id": lot_id,
        "lot_code": lot["lot_code"],
        "status": lot["status"],
        "progress": progress,
        "units": out_units,
        "public_base_url": public_base_url,
        "is_tunnel": is_tunnel,
    }
