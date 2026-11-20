"""Photo capture: upload hardening, evidence storage, on-device inference, mobile camera & Cloudinary integration."""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import time

import numpy as np
from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from PIL import Image, ImageOps, UnidentifiedImageError

from ...config import MAX_BYTES, MAX_IMAGE_EDGE, MAX_PIXELS
from ...core import db, security
from ...services import cloudinary, detector, inference
from ...services import review as service
from ..deps import (
    Denied,
    assert_csrf,
    can_write_lot,
    ensure_write,
    image_required,
    lot_required,
    require_role,
    require_user,
    service_lot_in_org,
)
from ..pages import page

router = APIRouter(tags=["capture"])


@router.get("/lots/{lot_id}/capture", response_class=HTMLResponse)
def capture_page(request: Request, lot_id: int):
    s = require_user(request)
    L = lot_required(s, lot_id)
    if s["user"]["role"] == "admin":
        raise Denied(403, "not_allowed")
    can_write = can_write_lot(s, L) and L["status"] != "decided"
    units = service.units_with_views(lot_id)
    progress = service.progress(lot_id)

    # Auto-initialize first sample garment (G-01) if lot has no sample units yet
    if not units and can_write:
        code = "G-01"
        uid = db.x("INSERT INTO sample_unit(lot_id,garment_code,created_at) VALUES (?,?,?)", (lot_id, code, db.now()))
        for side in ("front", "back"):
            db.x("INSERT INTO unit_view(sample_unit_id,side,required) VALUES (?,?,1)", (uid, side))
        db.audit(s["user"]["id"], s["user"]["display_name"], "unit.created", "lot", lot_id, after={"garment": code})
        units = service.units_with_views(lot_id)
        progress = service.progress(lot_id)

    raw_token = request.cookies.get(security.COOKIE) or request.query_params.get("session_token") or ""
    return page(request, "capture.html", active="lots", lot=L, units=units,
                progress=progress,
                session_token=raw_token,
                cloudinary_configured=cloudinary.is_configured(),
                can_write=can_write)


@router.post("/lots/{lot_id}/units")
def add_unit(request: Request, lot_id: int, csrf: str = Form(""), garment_code: str = Form("")):
    s = require_role(request, "inspector", "supervisor")
    assert_csrf(request, s, csrf)
    L = lot_required(s, lot_id)
    ensure_write(request, s, L)
    plan = service.active_plan(lot_id)
    required = min(plan["n"], L["lot_size"]) if plan else L["lot_size"]
    have = db.one("SELECT COUNT(*) AS n FROM sample_unit WHERE lot_id=?", (lot_id,))["n"]
    if have >= required:
        return RedirectResponse(f"/lots/{lot_id}/capture?err=units_full", status_code=303)
    code = garment_code.strip() or f"G-{have + 1:02d}"
    if db.one("SELECT id FROM sample_unit WHERE lot_id=? AND garment_code=?", (lot_id, code)):
        return RedirectResponse(f"/lots/{lot_id}/capture?err=exists", status_code=303)
    uid = db.x("INSERT INTO sample_unit(lot_id,garment_code,created_at) VALUES (?,?,?)", (lot_id, code, db.now()))
    for side in ("front", "back"):
        db.x("INSERT INTO unit_view(sample_unit_id,side,required) VALUES (?,?,1)", (uid, side))
    db.audit(s["user"]["id"], s["user"]["display_name"], "unit.created", "lot", lot_id, after={"garment": code})
    return RedirectResponse(f"/lots/{lot_id}/capture?ok=saved", status_code=303)


@router.post("/lots/{lot_id}/views/{view_id}/upload")
async def upload(request: Request, lot_id: int, view_id: int, csrf: str = Form(""),
                 file: UploadFile = File(...)):
    s = require_role(request, "inspector", "supervisor")
    assert_csrf(request, s, csrf)
    L = lot_required(s, lot_id)
    ensure_write(request, s, L)
    view = db.one("SELECT v.* FROM unit_view v JOIN sample_unit u ON u.id=v.sample_unit_id"
                  " WHERE v.id=? AND u.lot_id=?", (view_id, lot_id))
    if not view:
        raise Denied(404, "not_found")
    raw = b""
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        raw += chunk
        if len(raw) > MAX_BYTES:
            return RedirectResponse(f"/lots/{lot_id}/capture?err=too_big", status_code=303)
    if not raw:
        return RedirectResponse(f"/lots/{lot_id}/capture?err=bad_type", status_code=303)
    if not (raw.startswith(b"\xff\xd8\xff") or raw.startswith(b"\x89PNG\r\n\x1a\n")):
        return RedirectResponse(f"/lots/{lot_id}/capture?err=bad_type", status_code=303)
    sha_orig = hashlib.sha256(raw).hexdigest()
    dup = db.one("SELECT id FROM image WHERE lot_id=? AND sha256_original=? AND purged=0", (lot_id, sha_orig))
    if dup:
        return RedirectResponse(f"/lots/{lot_id}/capture?err=duplicate", status_code=303)
    try:
        im = Image.open(io.BytesIO(raw))
        if im.width * im.height > MAX_PIXELS:
            return RedirectResponse(f"/lots/{lot_id}/capture?err=too_big", status_code=303)
        im = ImageOps.exif_transpose(im).convert("RGB")
        im.thumbnail((MAX_IMAGE_EDGE, MAX_IMAGE_EDGE), Image.LANCZOS)
    except (UnidentifiedImageError, OSError, ValueError):
        return RedirectResponse(f"/lots/{lot_id}/capture?err=bad_type", status_code=303)
    work = io.BytesIO()
    im.save(work, "JPEG", quality=88, optimize=True)
    data = work.getvalue()
    sha_work = hashlib.sha256(data).hexdigest()
    os.makedirs(service.STORE, exist_ok=True)
    name = f"{os.urandom(16).hex()}.jpg"
    path = os.path.join(service.STORE, name)
    with open(path, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    db.x("UPDATE image SET is_current=0 WHERE view_id=? AND is_current=1", (view_id,))
    img_id = db.x("INSERT INTO image(lot_id,view_id,stored_name,original_name,sha256_original,sha256_working,"
                  "width,height,bytes,is_current,purged,uploaded_by,created_at)"
                  " VALUES (?,?,?,?,?,?,?,?,?,1,0,?,?)",
                  (lot_id, view_id, name, (file.filename or "upload.jpg")[:120], sha_orig, sha_work,
                   im.width, im.height, len(data), s["user"]["id"], db.now()))
    db.audit(s["user"]["id"], s["user"]["display_name"], "image.uploaded", "lot", lot_id,
             after={"image_id": img_id, "view_id": view_id, "bytes": len(data), "sha256": sha_work[:16]})
    inference.enqueue(img_id, s["user"]["id"])
    return RedirectResponse(f"/review/{img_id}?ok=saved", status_code=303)


@router.post("/images/{img_id}/infer")
def infer_again(request: Request, img_id: int, csrf: str = Form("")):
    s = require_role(request, "inspector", "supervisor")
    assert_csrf(request, s, csrf)
    img = image_required(s, img_id)
    ensure_write(request, s, service_lot_in_org(s, img["lot_id"]))
    inference.enqueue(img_id, s["user"]["id"])
    return RedirectResponse(f"/review/{img_id}?ok=saved", status_code=303)


@router.get("/images/{img_id}")
def image_bytes(request: Request, img_id: int):
    s = require_user(request)
    if s["user"]["role"] == "admin":
        raise Denied(403, "not_allowed")
    img = image_required(s, img_id)
    path = os.path.join(service.STORE, img["stored_name"])
    if not os.path.exists(path):
        raise Denied(404, "not_found")
    with open(path, "rb") as f:
        data = f.read()
    return Response(data, media_type="image/jpeg",
                    headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


@router.get("/images/{img_id}/heat")
def image_heat(request: Request, img_id: int):
    s = require_user(request)
    if s["user"]["role"] == "admin":
        raise Denied(403, "not_allowed")
    img = image_required(s, img_id)
    with Image.open(os.path.join(service.STORE, img["stored_name"])) as im:
        res = detector.detect(np.array(im.convert("RGB")))
    return Response(res["heat_png"], media_type="image/jpeg",
                    headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


# --------------------------------------------------------------------------
# Automated Mobile Camera & Cloudinary Integration
# --------------------------------------------------------------------------

def _find_next_pending_view(lot_id: int) -> dict | None:
    """Find the next sample unit view awaiting an inspection image."""
    for u in service.units_with_views(lot_id):
        for v in u["views"]:
            if not v["image"]:
                return {
                    "unit_id": u["id"],
                    "garment_code": u["garment_code"],
                    "view_id": v["id"],
                    "side": v["side"],
                }
    return None


@router.get("/lots/{lot_id}/mobile-cam", response_class=HTMLResponse)
def mobile_cam_page(request: Request, lot_id: int):
    """Mobile-optimized viewfinder interface for zero-click camera capture."""
    s = require_user(request)
    L = lot_required(s, lot_id)
    if s["user"]["role"] == "admin":
        raise Denied(403, "not_allowed")

    units = service.units_with_views(lot_id)
    progress = service.progress(lot_id)
    can_write = can_write_lot(s, L) and L["status"] != "decided"

    # Auto-initialize first sample garment (G-01) if lot has no sample units yet
    if not units and can_write:
        code = "G-01"
        unit_id = db.x("INSERT INTO sample_unit(lot_id,garment_code,created_at) VALUES (?,?,?)",
                       (lot_id, code, db.now()))
        for side in ("front", "back"):
            db.x("INSERT INTO unit_view(sample_unit_id,side,required) VALUES (?,?,1)", (unit_id, side))
        db.audit(s["user"]["id"], s["user"]["display_name"], "unit.created", "lot", lot_id,
                 after={"garment": code})
        units = service.units_with_views(lot_id)
        progress = service.progress(lot_id)

    next_view = _find_next_pending_view(lot_id)

    resp = page(
        request,
        "mobile_capture.html",
        active="lots",
        lot=L,
        units=units,
        progress=progress,
        can_write=can_write,
        next_view=next_view,
        cloudinary_configured=cloudinary.is_configured(),
    )
    # Persist session cookie on the mobile device if passed via QR code parameter
    token = request.query_params.get("session_token")
    if token:
        resp.set_cookie(
            security.COOKIE,
            token,
            path="/",
            samesite="lax",
            httponly=True,
            secure=security.COOKIE_SECURE,
        )
    return resp


@router.get("/lots/{lot_id}/views/{view_id}/cloudinary-sign")
def cloudinary_sign(request: Request, lot_id: int, view_id: int):
    """Generate backend-mediated signature for direct client-to-Cloudinary upload."""
    s = require_role(request, "inspector", "supervisor")
    L = lot_required(s, lot_id)
    ensure_write(request, s, L)
    view = db.one(
        "SELECT v.*, u.garment_code FROM unit_view v JOIN sample_unit u ON u.id=v.sample_unit_id"
        " WHERE v.id=? AND u.lot_id=?",
        (view_id, lot_id),
    )
    if not view:
        raise Denied(404, "not_found")
    sig_data = cloudinary.sign_upload_params(lot_id, view_id, garment_code=view["garment_code"])
    return JSONResponse(sig_data)


@router.post("/lots/{lot_id}/views/{view_id}/register-cloudinary")
async def register_cloudinary(request: Request, lot_id: int, view_id: int):
    """Receive uploaded Cloudinary receipt, cache local working copy, associate with lot and run inference."""
    s = require_role(request, "inspector", "supervisor")
    L = lot_required(s, lot_id)
    ensure_write(request, s, L)
    view = db.one(
        "SELECT v.*, u.garment_code FROM unit_view v JOIN sample_unit u ON u.id=v.sample_unit_id"
        " WHERE v.id=? AND u.lot_id=?",
        (view_id, lot_id),
    )
    if not view:
        raise Denied(404, "not_found")

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "invalid_json"}, status_code=400)

    public_id = str(body.get("public_id") or "").strip()
    secure_url = str(body.get("secure_url") or "").strip()
    captured_at = str(body.get("captured_at") or db.now()).strip()
    client_b64 = body.get("image_base64")

    if not public_id or not secure_url:
        return JSONResponse({"ok": False, "error": "missing_cloudinary_ref"}, status_code=400)

    # Prevent duplicate registration
    dup = db.one(
        "SELECT id FROM image WHERE lot_id=? AND cloudinary_public_id=? AND purged=0",
        (lot_id, public_id),
    )
    if dup:
        return JSONResponse({"ok": False, "error": "duplicate_image", "image_id": dup["id"]}, status_code=409)

    raw = None
    if client_b64:
        if "," in client_b64:
            client_b64 = client_b64.split(",", 1)[1]
        try:
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
        return JSONResponse({"ok": False, "error": "failed_to_fetch_image"}, status_code=400)

    sha_orig = hashlib.sha256(raw).hexdigest()
    dup_sha = db.one(
        "SELECT id FROM image WHERE lot_id=? AND sha256_original=? AND purged=0",
        (lot_id, sha_orig),
    )
    if dup_sha:
        return JSONResponse({"ok": False, "error": "duplicate_image_sha", "image_id": dup_sha["id"]}, status_code=409)

    try:
        im = Image.open(io.BytesIO(raw))
        im = ImageOps.exif_transpose(im).convert("RGB")
        im.thumbnail((MAX_IMAGE_EDGE, MAX_IMAGE_EDGE), Image.LANCZOS)
    except Exception:
        return JSONResponse({"ok": False, "error": "bad_image_format"}, status_code=400)

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
            s["user"]["id"],
            secure_url,
            public_id,
            captured_at,
            view_id,
            s["user"]["id"],
            db.now(),
        ),
    )

    db.audit(
        s["user"]["id"],
        s["user"]["display_name"],
        "image.cloudinary_registered",
        "lot",
        lot_id,
        after={"image_id": img_id, "view_id": view_id, "public_id": public_id, "bytes": len(data)},
    )

    inference.enqueue(img_id, s["user"]["id"])
    next_view = _find_next_pending_view(lot_id)

    return JSONResponse({
        "ok": True,
        "image_id": img_id,
        "view_id": view_id,
        "public_id": public_id,
        "secure_url": secure_url,
        "next_view": next_view,
        "lot_complete": next_view is None,
    })


@router.post("/lots/{lot_id}/views/{view_id}/mobile-upload")
async def mobile_upload(
    request: Request,
    lot_id: int,
    view_id: int,
    file: UploadFile = File(...),
    captured_at: str = Form(""),
    csrf: str = Form(""),
):
    """Direct mobile camera stream upload (with automatic server-side Cloudinary archiving)."""
    s = require_role(request, "inspector", "supervisor")
    if csrf:
        assert_csrf(request, s, csrf)
    L = lot_required(s, lot_id)
    ensure_write(request, s, L)
    view = db.one(
        "SELECT v.*, u.garment_code FROM unit_view v JOIN sample_unit u ON u.id=v.sample_unit_id"
        " WHERE v.id=? AND u.lot_id=?",
        (view_id, lot_id),
    )
    if not view:
        raise Denied(404, "not_found")

    if hasattr(file, "file") and hasattr(file.file, "read"):
        raw = file.file.read()
    else:
        raw = await file.read()
    if len(raw) > MAX_BYTES:
        return JSONResponse({"ok": False, "error": "too_big"}, status_code=400)
    if not (raw.startswith(b"\xff\xd8\xff") or raw.startswith(b"\x89PNG\r\n\x1a\n")):
        return JSONResponse({"ok": False, "error": "bad_type"}, status_code=400)

    sha_orig = hashlib.sha256(raw).hexdigest()
    dup = db.one(
        "SELECT id FROM image WHERE lot_id=? AND sha256_original=? AND purged=0",
        (lot_id, sha_orig),
    )
    if dup:
        return JSONResponse({"ok": False, "error": "duplicate", "image_id": dup["id"]}, status_code=409)

    try:
        im = Image.open(io.BytesIO(raw))
        im = ImageOps.exif_transpose(im).convert("RGB")
        im.thumbnail((MAX_IMAGE_EDGE, MAX_IMAGE_EDGE), Image.LANCZOS)
    except Exception:
        return JSONResponse({"ok": False, "error": "bad_image"}, status_code=400)

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

    # Background upload to Cloudinary if configured
    cld_res = {}
    try:
        cld_res = await cloudinary.upload_to_cloudinary(
            data,
            lot_id,
            view_id,
            filename=file.filename or "mobile_cam.jpg",
            garment_code=view["garment_code"],
        )
    except Exception as exc:
        cld_res = {
            "public_id": f"cld_local_{sha_orig[:16]}",
            "secure_url": f"/images/{stored_name}",
            "status": f"upload_error_{type(exc).__name__}",
        }

    cld_url = cld_res.get("secure_url") or f"/images/{stored_name}"
    cld_pid = cld_res.get("public_id") or f"cld_local_{sha_orig[:16]}"
    cap_time = captured_at.strip() or db.now()

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
            (file.filename or "mobile_cam.jpg")[:120],
            sha_orig,
            sha_work,
            im.width,
            im.height,
            len(data),
            s["user"]["id"],
            cld_url,
            cld_pid,
            cap_time,
            view_id,
            s["user"]["id"],
            db.now(),
        ),
    )

    db.audit(
        s["user"]["id"],
        s["user"]["display_name"],
        "image.mobile_uploaded",
        "lot",
        lot_id,
        after={"image_id": img_id, "view_id": view_id, "bytes": len(data), "cld_pid": cld_pid},
    )

    inference.enqueue(img_id, s["user"]["id"])
    next_view = _find_next_pending_view(lot_id)

    return JSONResponse({
        "ok": True,
        "image_id": img_id,
        "view_id": view_id,
        "cloudinary_url": cld_url,
        "public_id": cld_pid,
        "next_view": next_view,
        "lot_complete": next_view is None,
    })


@router.get("/lots/{lot_id}/views-status")
def views_status(request: Request, lot_id: int):
    """Real-time poll endpoint for live inspection gallery syncing."""
    s = require_user(request)
    L = lot_required(s, lot_id)
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
                "thumbnail_url": f"/images/{img['id']}" if img else None,
                "review_state": v["review_state"],
                "inference_status": v["inference_status"],
                "open_proposals": v["open_proposals"],
            })
        out_units.append({
            "unit_id": u["id"],
            "garment_code": u["garment_code"],
            "views": views,
        })
    from ..pages import get_public_base_url

    public_base_url, is_tunnel = get_public_base_url(request)
    return JSONResponse({
        "lot_id": lot_id,
        "lot_code": L["lot_code"],
        "status": L["status"],
        "progress": progress,
        "units": out_units,
        "public_base_url": public_base_url,
        "is_tunnel": is_tunnel,
    })


@router.get("/qr")
def qr_code_image(text: str = ""):
    """Generate local, offline QR code PNG directly from server memory with zero external dependencies."""
    try:
        import qrcode
        img = qrcode.make(text or "http://localhost:8077")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return Response(
            content=buf.getvalue(),
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=86400"},
        )
    except Exception:
        return Response(content=b"", status_code=500)
