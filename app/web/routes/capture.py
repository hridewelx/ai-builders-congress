"""Photo capture: upload hardening, evidence storage, on-device inference."""
from __future__ import annotations

import hashlib
import io
import os
import time

import numpy as np
from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from PIL import Image, ImageOps, UnidentifiedImageError

from ...config import MAX_BYTES, MAX_IMAGE_EDGE, MAX_PIXELS, ZONES
from ...core import db
from ...services import review as service
from ...services import vision
from ..deps import Denied, assert_csrf, can_write_lot, ensure_write, require_role, require_user
from ..pages import page

router = APIRouter(tags=["capture"])


@router.get("/lots/{lot_id}/capture", response_class=HTMLResponse)
def capture_page(request: Request, lot_id: int):
    s = require_user(request)
    L = service.lot(lot_id)
    if not L:
        raise Denied(404, "not_found")
    if s["user"]["role"] == "admin":
        raise Denied(403, "not_allowed")
    return page(request, "capture.html", active="lots", lot=L, units=service.units_with_views(lot_id),
                progress=service.progress(lot_id),
                can_write=(can_write_lot(s, L) and L["status"] != "decided"))


@router.post("/lots/{lot_id}/units")
def add_unit(request: Request, lot_id: int, csrf: str = Form(""), garment_code: str = Form("")):
    s = require_role(request, "inspector", "supervisor")
    assert_csrf(request, s, csrf)
    L = service.lot(lot_id)
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
    L = service.lot(lot_id)
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
    run_inference(img_id, s["user"]["id"], request)
    return RedirectResponse(f"/review/{img_id}?ok=saved", status_code=303)


def run_inference(img_id: int, user_id: int, request: Request | None = None) -> str:
    img = db.one("SELECT * FROM image WHERE id=?", (img_id,))
    if not img:
        return "failed"
    L = service.lot(img["lot_id"])
    job_id = db.x("INSERT INTO inference_job(image_id,status,model_version,created_at) VALUES (?,?,?,?)",
                  (img_id, "running", vision.MODEL_NAME, db.now()))
    t0 = time.time()
    try:
        with Image.open(os.path.join(service.STORE, img["stored_name"])) as im:
            res = vision.detect(np.array(im.convert("RGB")))
        for p in res["proposals"]:
            crit = 0
            for z in ZONES:
                c = service.map_clause(L["buyer_id"], p["type"], z, None)
                if c and c["severity"] == "critical":
                    crit = 1
            db.x("INSERT INTO prediction(job_id,image_id,defect_type,score,x1,y1,x2,y2,review_state,"
                 "provisional_critical,created_at) VALUES (?,?,?,?,?,?,?,?,'proposed',?,?)",
                 (job_id, img_id, p["type"], p["score"], p["box"][0], p["box"][1], p["box"][2], p["box"][3],
                  crit, db.now()))
        db.x("UPDATE inference_job SET status='succeeded', finished_at=?, latency_ms=? WHERE id=?",
             (db.now(), int((time.time() - t0) * 1000), job_id))
        db.audit(user_id, str(user_id), "inference.succeeded", "image", img_id,
                 after={"proposals": len(res["proposals"]), "model": vision.MODEL_NAME})
        return "ok"
    except Exception as exc:
        db.x("UPDATE inference_job SET status='failed', error=?, finished_at=? WHERE id=?",
             (str(exc)[:300], db.now(), job_id))
        db.audit(user_id, str(user_id), "inference.failed", "image", img_id, after={"error": str(exc)[:200]})
        return "failed"


@router.post("/images/{img_id}/infer")
def infer_again(request: Request, img_id: int, csrf: str = Form("")):
    s = require_role(request, "inspector", "supervisor")
    assert_csrf(request, s, csrf)
    img = db.one("SELECT * FROM image WHERE id=?", (img_id,))
    if not img:
        raise Denied(404, "not_found")
    ensure_write(request, s, service.lot(img["lot_id"]))
    run_inference(img_id, s["user"]["id"], request)
    return RedirectResponse(f"/review/{img_id}?ok=saved", status_code=303)


@router.get("/images/{img_id}")
def image_bytes(request: Request, img_id: int):
    s = require_user(request)
    if s["user"]["role"] == "admin":
        raise Denied(403, "not_allowed")
    img = db.one("SELECT * FROM image WHERE id=?", (img_id,))
    if not img:
        raise Denied(404, "not_found")
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
    img = db.one("SELECT * FROM image WHERE id=?", (img_id,))
    if not img:
        raise Denied(404, "not_found")
    with Image.open(os.path.join(service.STORE, img["stored_name"])) as im:
        res = vision.detect(np.array(im.convert("RGB")))
    return Response(res["heat_png"], media_type="image/jpeg",
                    headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})
