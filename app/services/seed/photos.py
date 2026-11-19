"""Staged garment photos, their stored bytes, and human review moves."""
from __future__ import annotations

import hashlib
import io
import os
import time
import uuid

import numpy as np
from PIL import Image, ImageOps

from ...core import db
from .. import review as service
from .. import vision
from .fixtures import _name, provisional_critical

BASE_COLORS = {
    "navy": (58, 78, 120),
    "ecru": (206, 196, 172),
    "black": (72, 74, 80),
    "sage": (140, 162, 138),
    "plum": (128, 96, 118),
    "maroon": (150, 74, 78),
}

def _canonical(pil: Image.Image) -> tuple[bytes, bytes, Image.Image]:
    raw = io.BytesIO()
    pil.convert("RGB").save(raw, "JPEG", quality=90)
    original = raw.getvalue()
    im = Image.open(io.BytesIO(original))
    im = ImageOps.exif_transpose(im).convert("RGB")
    im.thumbnail((1200, 1200), Image.LANCZOS)
    work = io.BytesIO()
    im.save(work, "JPEG", quality=88, optimize=True)
    return original, work.getvalue(), im


def store_bytes(work: bytes) -> tuple[str, str]:
    os.makedirs(service.STORE, exist_ok=True)
    name = f"{uuid.uuid4().hex}.jpg"
    with open(os.path.join(service.STORE, name), "wb") as f:
        f.write(work)
    return name, hashlib.sha256(work).hexdigest()


def _file_sha(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()



def upload_photo(lot_id, view_id, user_id, seed, defects, color, size=(560, 720)):
    pil, truth = vision.staged_photo(seed=seed, base=color, defects=defects, size=size)
    original, work, im = _canonical(pil)
    name, sha = store_bytes(work)
    img_id = db.x("INSERT INTO image(lot_id,view_id,stored_name,original_name,sha256_original,sha256_working,"
                  "width,height,bytes,is_current,purged,uploaded_by,created_at)"
                  " VALUES (?,?,?,?,?,?,?,?,?,1,0,?,?)",
                  (lot_id, view_id, name, f"staged_{seed}.jpg", hashlib.sha256(original).hexdigest(), sha,
                   im.width, im.height, len(work), user_id, db.now()))
    job_id = db.x("INSERT INTO inference_job(image_id,status,model_version,created_at) VALUES (?,?,?,?)",
                  (img_id, "running", vision.MODEL_NAME, db.now()))
    t0 = time.time()
    try:
        res = vision.detect(np.array(im))
        for p in res["proposals"]:
            db.x("INSERT INTO prediction(job_id,image_id,defect_type,score,x1,y1,x2,y2,review_state,"
                 "provisional_critical,created_at) VALUES (?,?,?,?,?,?,?,?,'proposed',?,?)",
                 (job_id, img_id, p["type"], p["score"], p["box"][0], p["box"][1], p["box"][2], p["box"][3],
                  provisional_critical(service.lot(lot_id)["buyer_id"], p["type"]), db.now()))
        db.x("UPDATE inference_job SET status='succeeded', finished_at=?, latency_ms=? WHERE id=?",
             (db.now(), int((time.time() - t0) * 1000), job_id))
    except Exception as exc:  # never a clean pass
        db.x("UPDATE inference_job SET status='failed', error=?, finished_at=? WHERE id=?",
             (str(exc)[:300], db.now(), job_id))
    db.audit(user_id, _name(user_id), "image.uploaded", "image", img_id,
             after={"view_id": view_id, "bytes": len(work), "sha256": sha[:16]})
    return img_id



def confirm(img_id, index, zone, reviewer, band=None, as_type=None):
    preds = db.q("SELECT * FROM prediction WHERE image_id=? ORDER BY id", (img_id,))
    if index >= len(preds):
        return None
    p = preds[index]
    L = db.one("SELECT l.*, b.name AS buyer_name FROM lot l JOIN image i ON i.lot_id=l.id"
               " JOIN buyer b ON b.id=l.buyer_id WHERE i.id=?", (img_id,))
    dtype = as_type or p["defect_type"]
    c = service.map_clause(L["buyer_id"], dtype, zone, band)
    db.x("UPDATE prediction SET review_state='confirmed', confirmed_type=?, zone_code=?, size_band=?,"
         " severity=?, clause_ref=?, reviewed_by=?, reviewed_at=? WHERE id=?",
         (dtype, zone, band, c["severity"] if c else None, c["clause_ref"] if c else None,
          reviewer, db.now(), p["id"]))
    db.audit(reviewer, _name(reviewer), "defect.confirmed", "prediction", p["id"],
             after={"type": dtype, "zone": zone, "severity": c["severity"] if c else None,
                    "clause": c["clause_ref"] if c else None})
    return p["id"]


def reject(img_id, index, reviewer, second_pending="confirmed"):
    """Seeded history: a Supervisor has already second-reviewed seeded rejections."""
    preds = db.q("SELECT * FROM prediction WHERE image_id=? ORDER BY id", (img_id,))
    if index >= len(preds):
        return
    p = preds[index]
    sr = second_pending
    if sr is None and p["provisional_critical"]:
        sr = "pending"
    db.x("UPDATE prediction SET review_state='rejected', second_review=?, reviewed_by=?, reviewed_at=? WHERE id=?",
         (sr, reviewer, db.now(), p["id"]))
    db.audit(reviewer, _name(reviewer), "defect.rejected", "prediction", p["id"],
             after={"provisional_critical": bool(p["provisional_critical"]), "second_review": sr})


def settle_view(img_id, reviewer, confirm_index=None, zone="I", as_type=None):
    """Confirm one proposal (if any), reject the rest, and mark the view reviewed."""
    preds = db.q("SELECT * FROM prediction WHERE image_id=? ORDER BY id", (img_id,))
    for k in range(len(preds)):
        if confirm_index is not None and k == confirm_index:
            confirm(img_id, k, zone, reviewer, as_type=as_type)
        else:
            reject(img_id, k, reviewer)
    state = "confirmed_defects" if confirm_index is not None else "reviewed_clean"
    review_view(img_id, state, reviewer)
    db.audit(reviewer, _name(reviewer), "view." + state, "image", img_id)


def review_view(img_id, state, reviewer, note=None):
    db.x("INSERT OR REPLACE INTO view_review(image_id,state,note,reviewed_by,reviewed_at) VALUES (?,?,?,?,?)",
         (img_id, state, note, reviewer, db.now()))
