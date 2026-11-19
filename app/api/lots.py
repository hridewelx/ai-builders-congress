"""Dashboard, lot cockpit, sampling plan, capture and review queues."""
from __future__ import annotations

import hashlib
import io
import os

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError

from ..config import MAX_BYTES, MAX_IMAGE_EDGE, MAX_PIXELS, ZONES
from ..core import db
from ..services import detector, vision
from ..services import review as service
from ..services.stats import demo_stats
from .deps import audit_denied, check_csrf, current_user, role_required
from .serializers import catalogs, clean, decision_payload, lot_cards, model_info, timeline

router = APIRouter(tags=["lots"])


def _lang(request: Request) -> str:
    value = request.cookies.get("ll_lang", "bn")
    return value if value in ("en", "bn") else "bn"


def _ensure_write(request: Request, session: dict, lot) -> None:
    from ..core.permissions import can_write_lot
    if not can_write_lot(session, lot):
        audit_denied(request, session)
        raise HTTPException(status_code=403, detail="not_allowed")
    if lot["status"] in ("decided", "archived"):
        raise HTTPException(status_code=403, detail="locked")


def _lot_or_404(lot_id: int):
    lot = service.lot(lot_id)
    if not lot:
        raise HTTPException(status_code=404, detail="not_found")
    return lot


@router.get("/dashboard")
def dashboard(request: Request):
    session = current_user(request)
    cards = lot_cards()
    return {
        "cards": cards[:4],
        "counters": service.counters(),
        "stats": demo_stats(),
        "model": model_info(),
        "user": clean(session["user"]),
    }


@router.get("/lots")
def lots(request: Request, state: str = "", outcome: str = "", q: str = ""):
    current_user(request)
    return {
        "cards": lot_cards(state, outcome, q),
        "state": state, "outcome": outcome, "q": q,
        "counters": service.counters(),
    }


@router.get("/lots/new")
def new_lot_form(request: Request):
    session = current_user(request)
    role_required(session, "inspector", "supervisor")
    return catalogs()


@router.post("/lots")
async def create_lot(request: Request):
    session = role_required(current_user(request), "inspector", "supervisor")
    check_csrf(request, session)
    data = await request.json()
    code = str(data.get("lot_code", "")).strip().upper()
    buyer_id = int(data.get("buyer_id") or 0)
    product_id = int(data.get("product_id") or 0)
    lot_size = int(data.get("lot_size") or 0)
    color = str(data.get("color", "")).strip()
    selection = str(data.get("selection_method", "self-declared random")).strip()
    if not code or lot_size < 1 or not buyer_id or not product_id:
        raise HTTPException(status_code=422, detail="invalid")
    if db.one("SELECT id FROM lot WHERE lot_code=?", (code,)):
        raise HTTPException(status_code=409, detail="exists")
    lot_id = db.x(
        "INSERT INTO lot(organization_id,lot_code,product_id,buyer_id,color,lot_size,status,"
        "critical_nonvisual_status,selection_method,created_by,created_at)"
        " VALUES (1,?,?,?,?,?, 'open','pending',?,?,?)",
        (code, product_id, buyer_id, color, lot_size, selection,
         session["user"]["id"], db.now()))
    db.audit(session["user"]["id"], session["user"]["display_name"], "lot.created", "lot", lot_id,
             after={"lot_code": code, "lot_size": lot_size})
    return {"ok": True, "id": lot_id}


@router.get("/lots/{lot_id}")
def lot_detail(request: Request, lot_id: int):
    session = current_user(request)
    lot = _lot_or_404(lot_id)
    plan = service.active_plan(lot_id)
    progress = service.progress(lot_id)
    units = service.units_with_views(lot_id)
    row = service.latest_decision(lot_id)
    decision = decision_payload(row)
    override = service.override_for(row["id"]) if row else None
    history = [decision_payload(item) for item in
               db.q("SELECT d.*, u.display_name AS decided_by FROM decision d"
                    " JOIN app_user u ON u.id=d.created_by WHERE d.lot_id=?"
                    " ORDER BY d.sequence DESC", (lot_id,))]
    from ..core.permissions import can_write_lot
    is_admin = session["user"]["role"] == "admin"
    return {
        "lot": clean(lot),
        "plan": service.plan_dict(plan),
        "plan_row": clean(plan),
        "progress": progress,
        "units": clean(units),
        "decision": decision,
        "override": clean(override),
        "final": service.final_disposition(row, override) if row else None,
        "history": history,
        "audit": timeline(lot_id),
        "is_admin": is_admin,
        "is_supervisor": session["user"]["role"] == "supervisor",
        "can_write": (not is_admin and can_write_lot(session, lot)
                      and lot["status"] != "decided"),
        "user": clean(session["user"]),
    }


def evidence_summary(lot_id: int) -> dict:
    ev = service.build_evidence(lot_id)
    counts = {"critical": 0, "major": 0, "minor": 0}
    for defect in ev["defects"]:
        severity = defect.get("severity")
        if severity in counts:
            counts[severity] += 1
    return {
        "units_present": ev["units_present"],
        "required_units": ev["required_units"],
        "counts": counts,
        "has_defects": len(ev["defects"]) > 0,
        "nonvisual_status": ev["lot"].get("critical_nonvisual_status", "pending"),
    }


@router.get("/lots/{lot_id}/plan")
def plan_detail(request: Request, lot_id: int):
    session = current_user(request)
    lot = _lot_or_404(lot_id)
    plan = service.active_plan(lot_id)
    row = service.latest_decision(lot_id)
    return {
        "lot": clean(lot),
        "plan": service.plan_dict(plan),
        "plan_row": clean(plan),
        "progress": service.progress(lot_id),
        "units": clean(service.units_with_views(lot_id)),
        "decision": decision_payload(row),
        "evidence_summary": evidence_summary(lot_id),
        "is_supervisor": session["user"]["role"] == "supervisor",
        "locked": lot["status"] == "decided",
        "user": clean(session["user"]),
    }


def _float(value):
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


@router.post("/lots/{lot_id}/plan")
async def save_plan(request: Request, lot_id: int):
    session = role_required(current_user(request), "supervisor")
    check_csrf(request, session)
    lot = _lot_or_404(lot_id)
    if lot["status"] == "decided":
        raise HTTPException(status_code=403, detail="locked")
    data = await request.json()
    lang = _lang(request)

    n = int(data.get("n") or 0)
    counting_mode = str(data.get("counting_mode") or "")
    critical_ac = int(data.get("critical_ac", -1))
    critical_re = int(data.get("critical_re", -1))
    major_ac = int(data.get("major_ac", -1))
    major_re = int(data.get("major_re", -1))
    minor_ac = int(data.get("minor_ac", -1))
    minor_re = int(data.get("minor_re", -1))
    confirmed = str(data.get("confirmed") or "").strip()
    is_demo = 1 if str(data.get("is_demo")) in ("1", "true", "True") else 0
    source_edition = str(data.get("source_edition") or "").strip()
    source_reference = str(data.get("source_reference") or "").strip()

    errors: dict[str, str] = {}
    if not confirmed:
        errors["confirmed"] = ("উৎস থেকে মান মিলিয়ে যাচাইয়ের স্বীকৃতি আবশ্যক।" if lang == "bn"
                               else "Confirmation that values were verified against the source "
                                    "standard / specification is required.")
    if n < 1:
        errors["n"] = ("নমুনার আকার (n) অন্তত ১ হতে হবে।" if lang == "bn"
                       else "Sample size n must be an integer >= 1.")
    elif n > lot["lot_size"]:
        errors["n"] = (f"নমুনার আকার (n) লট সাইজ ({lot['lot_size']})-এর চেয়ে বড় হতে পারে না।"
                       if lang == "bn" else
                       f"Sample size n cannot exceed lot size ({lot['lot_size']}).")
    if counting_mode not in ("highest_class_only", "every_class"):
        errors["counting_mode"] = ("গণনার পদ্ধতি নির্বাচন করুন।" if lang == "bn"
                                   else "Counting mode is required.")
    for key, name_bn, name_en, ac, re_ in (
        ("critical", "ক্রিটিক্যাল", "Critical", critical_ac, critical_re),
        ("major", "মেজর", "Major", major_ac, major_re),
        ("minor", "মাইনর", "Minor", minor_ac, minor_re),
    ):
        if ac < 0:
            errors[f"{key}_ac"] = (f"{name_bn} গ্রহণ সংখ্যা (Ac) ০ বা তার বেশি হতে হবে।" if lang == "bn"
                                   else f"{name_en} acceptance number (Ac) must be >= 0.")
        if re_ < 1:
            errors[f"{key}_re"] = (f"{name_bn} প্রত্যাখ্যান সংখ্যা (Re) অন্তত ১ হতে হবে।" if lang == "bn"
                                   else f"{name_en} rejection number (Re) must be >= 1.")
        elif ac >= 0 and re_ != ac + 1:
            errors[f"{key}_re"] = (
                f"সিঙ্গেল স্যাম্পলিংয়ে Re অবশ্যই Ac + 1 হতে হবে (প্রত্যাশিত Re={ac + 1})।"
                if lang == "bn" else
                f"Single sampling requires Re = Ac + 1 (expected Re={ac + 1}).")
    if errors:
        raise HTTPException(status_code=422, detail={"errors": errors})

    final_source_edition = source_edition
    final_source_ref = source_reference
    if is_demo:
        final_source_edition = ("অননুমোদিত ডেমো অনুমান" if lang == "bn"
                                else "Unauthorized demo assumption")
    elif not final_source_edition and not final_source_ref:
        final_source_edition = ("অননুমোদিত অনুমান" if lang == "bn"
                                else "Unauthorized assumption")

    previous = service.active_plan(lot_id)
    version = (previous["version"] + 1) if previous else 1
    db.x("INSERT INTO plan(lot_id,version,n,counting_mode,critical_aql,critical_ac,critical_re,"
         "major_aql,major_ac,major_re,minor_aql,minor_ac,minor_re,inspection_level,sampling_type,"
         "source_edition,source_reference,is_demo,entered_by,created_at)"
         " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'II','single',?,?,?,?,?)",
         (lot_id, version, n, counting_mode, _float(data.get("critical_aql")), critical_ac, critical_re,
          _float(data.get("major_aql")), major_ac, major_re,
          _float(data.get("minor_aql")), minor_ac, minor_re,
          final_source_edition, final_source_ref, is_demo, session["user"]["id"], db.now()))
    db.audit(session["user"]["id"], session["user"]["display_name"], "plan.confirmed", "lot", lot_id,
             after={"version": version, "n": n, "mode": counting_mode,
                    "confirmed_by": session["user"]["display_name"], "confirmed_at": db.now(),
                    "source": final_source_edition, "is_demo": is_demo})
    db.audit(session["user"]["id"], session["user"]["display_name"], "plan.created", "lot", lot_id,
             after={"version": version, "n": n, "mode": counting_mode, "source": final_source_edition})

    have = db.one("SELECT COUNT(*) c FROM sample_unit WHERE lot_id=?", (lot_id,))["c"]
    if have == 0:
        for index in range(1, n + 1):
            unit_id = db.x("INSERT INTO sample_unit(lot_id, garment_code, created_at) VALUES (?,?,?)",
                           (lot_id, f"G-{index:02d}", db.now()))
            for side in ("front", "back"):
                db.x("INSERT INTO unit_view(sample_unit_id, side, required) VALUES (?,?,1)",
                     (unit_id, side))
        db.audit(session["user"]["id"], session["user"]["display_name"], "units.generated", "lot",
                 lot_id, after={"count": n, "views": n * 2})
    return {"ok": True, "plan": service.plan_dict(service.active_plan(lot_id))}


@router.post("/lots/{lot_id}/nonvisual")
async def set_nonvisual(request: Request, lot_id: int):
    session = role_required(current_user(request), "supervisor")
    check_csrf(request, session)
    lot = _lot_or_404(lot_id)
    data = await request.json()
    status = str(data.get("status") or "")
    note = str(data.get("note") or "")
    if status not in ("pending", "done", "not_required", "failed"):
        raise HTTPException(status_code=422, detail="invalid")
    if status == "failed" and len(note.strip()) < 3:
        raise HTTPException(status_code=422, detail="note_required")
    if lot["status"] == "decided" and status != lot["critical_nonvisual_status"]:
        raise HTTPException(status_code=403, detail="locked")
    db.x("UPDATE lot SET critical_nonvisual_status=?, nonvisual_note=? WHERE id=?",
         (status, note.strip() or None, lot_id))
    db.audit(session["user"]["id"], session["user"]["display_name"], "lot.nonvisual_changed", "lot",
             lot_id, before={"status": lot["critical_nonvisual_status"]},
             after={"status": status, "note": note.strip()})
    return {"ok": True}


@router.get("/lots/{lot_id}/capture")
def capture(request: Request, lot_id: int):
    session = current_user(request)
    lot = _lot_or_404(lot_id)
    if session["user"]["role"] == "admin":
        raise HTTPException(status_code=403, detail="not_allowed")
    from ..core.permissions import can_write_lot
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
    lot = _lot_or_404(lot_id)
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
    lot = _lot_or_404(lot_id)
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
    run_inference(image_id, session["user"]["id"])
    return {"ok": True, "image_id": image_id}


def run_inference(image_id: int, user_id: int) -> str:
    image = db.one("SELECT * FROM image WHERE id=?", (image_id,))
    if not image:
        return "failed"
    lot = service.lot(image["lot_id"])
    model_name = detector.MODEL_NAME if detector.available() else vision.MODEL_NAME
    job_id = db.x("INSERT INTO inference_job(image_id,status,model_version,created_at) VALUES (?,?,?,?)",
                  (image_id, "running", model_name, db.now()))
    import time
    started = time.time()
    try:
        with Image.open(os.path.join(service.STORE, image["stored_name"])) as handle:
            result = detector.detect(__import__("numpy").array(handle.convert("RGB")))
        for proposal in result["proposals"]:
            critical = 0
            for zone in ZONES:
                clause = service.map_clause(lot["buyer_id"], proposal["type"], zone, None)
                if clause and clause["severity"] == "critical":
                    critical = 1
            db.x("INSERT INTO prediction(job_id,image_id,defect_type,score,x1,y1,x2,y2,review_state,"
                 "provisional_critical,created_at) VALUES (?,?,?,?,?,?,?,?,'proposed',?,?)",
                 (job_id, image_id, proposal["type"], proposal["score"], proposal["box"][0],
                  proposal["box"][1], proposal["box"][2], proposal["box"][3], critical, db.now()))
        actual_model = result.get("model", model_name)
        db.x("UPDATE inference_job SET status='succeeded', model_version=?, finished_at=?, latency_ms=?"
             " WHERE id=?", (actual_model, db.now(), int((time.time() - started) * 1000), job_id))
        db.audit(user_id, str(user_id), "inference.succeeded", "image", image_id,
                 after={"proposals": len(result["proposals"]), "model": actual_model})
        return "ok"
    except Exception as exc:  # a detector failure must never block manual review
        db.x("UPDATE inference_job SET status='failed', error=?, finished_at=? WHERE id=?",
             (str(exc)[:300], db.now(), job_id))
        db.audit(user_id, str(user_id), "inference.failed", "image", image_id,
                 after={"error": str(exc)[:200]})
        return "failed"


@router.post("/images/{image_id}/infer")
def infer_again(request: Request, image_id: int):
    session = role_required(current_user(request), "inspector", "supervisor")
    check_csrf(request, session)
    image = db.one("SELECT * FROM image WHERE id=?", (image_id,))
    if not image:
        raise HTTPException(status_code=404, detail="not_found")
    _ensure_write(request, session, service.lot(image["lot_id"]))
    status = run_inference(image_id, session["user"]["id"])
    return {"ok": status == "ok", "status": status}


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
    from ..core.permissions import can_write_lot
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
