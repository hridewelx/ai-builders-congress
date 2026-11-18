"""Lotline demo web application (FastAPI + Jinja2 + SQLite).

Same governing principle as the specification:
AI proposes defects, humans confirm defects, a deterministic engine decides,
and no failure path can turn into an acceptance.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import time

import numpy as np
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image, ImageOps, UnidentifiedImageError

from . import db, engine, i18n, report, security, seed, service, vision

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES = Jinja2Templates(directory=os.path.join(BASE, "templates"))
TEMPLATES.env.filters["fromjson"] = json.loads
STATIC = os.path.join(BASE, "static")
MAX_BYTES = 15 * 1024 * 1024
MAX_PIXELS = 50_000_000
ZONES = ["I", "II", "III"]

app = FastAPI(title="Lotline", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.on_event("startup")
def _startup() -> None:
    db.init()
    seed.run()
    try:
        vision._train_or_load()
    except Exception:
        pass


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

class Denied(Exception):
    def __init__(self, status: int = 403, message: str = "not_allowed"):
        self.status = status
        self.message = message


def sess_of(request: Request):
    return security.current_session(request.cookies.get(security.COOKIE))


def lang_of(request: Request) -> str:
    v = request.cookies.get("ll_lang", "en")
    return v if v in i18n.LANGS else "en"


def ctx(request: Request, **kw) -> dict:
    s = sess_of(request)
    lang = lang_of(request)
    c = {
        "request": request,
        "user": s["user"] if s else None,
        "csrf": s["session"]["csrf"] if s else "",
        "lang": lang,
        "tr": lambda k: i18n.t(k, lang),
        "reason": lambda code: i18n.reason_text(code, lang),
        "active": "",
        "ok": request.query_params.get("ok"),
        "err": request.query_params.get("err"),
        "roles": {"admin": True, "inspector": True, "supervisor": True},
        "zones": ZONES,
    }
    c.update(kw)
    return c


def page(request: Request, name: str, status_code: int = 200, **kw) -> HTMLResponse:
    return TEMPLATES.TemplateResponse(request, name, ctx(request, **kw), status_code=status_code)


def require_user(request: Request):
    s = sess_of(request)
    if not s:
        raise Denied(401, "login_required")
    return s


def require_role(request: Request, *roles):
    s = require_user(request)
    if s["user"]["role"] not in roles:
        db.audit(s["user"]["id"], s["user"]["display_name"], "request.denied", "route",
                 request.url.path, after={"role": s["user"]["role"]}, ip=request.client.host if request.client else None)
        raise Denied(403, "not_allowed")
    return s


def assert_csrf(request: Request, s: dict, token: str | None) -> None:
    if not security.check_csrf(s, token):
        raise Denied(403, "csrf")
    origin = request.headers.get("origin")
    if origin:
        host = request.headers.get("host", "")
        if origin.split("://")[-1] != host:
            raise Denied(403, "csrf")


def can_write_lot(s: dict, lot) -> bool:
    role = s["user"]["role"]
    return role == "supervisor" or (role == "inspector" and lot["created_by"] == s["user"]["id"])


def ensure_write(request: Request, s: dict, lot_row) -> None:
    if not can_write_lot(s, lot_row):
        raise Denied(403, "not_allowed")
    if lot_row["status"] == "decided":
        raise Denied(403, "locked")
    for r in ("archived",):
        if lot_row["status"] == r:
            raise Denied(403, "locked")


@app.exception_handler(Denied)
async def denied_handler(request: Request, exc: Denied):
    if exc.status == 401:
        return RedirectResponse("/login", status_code=303)
    name = "error.html"
    return TEMPLATES.TemplateResponse(request, name, ctx(request, code=exc.status, message=exc.message),
                                      status_code=exc.status)


@app.exception_handler(404)
async def notfound(request: Request, exc):
    return TEMPLATES.TemplateResponse(request, "error.html",
                                      ctx(request, code=404, message="not_found"), status_code=404)


# --------------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------------

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if sess_of(request):
        return RedirectResponse("/", status_code=303)
    return page(request, "login.html", active="login")


@app.post("/login")
def login(request: Request, email: str = Form(""), password: str = Form("")):
    email = email.strip().lower()
    if security.login_delay(email) and time.time() - security.last_failure_at(email) < security.login_delay(email):
        security.record_attempt(email, False, request.client.host if request.client else "")
        return RedirectResponse("/login?err=rl", status_code=303)
    user = db.one("SELECT * FROM app_user WHERE email=?", (email,))
    ok = bool(user and user["status"] == "active" and security.verify_password(user["password_hash"], password))
    if not ok:
        # constant-work path: verify a dummy hash when the account does not exist
        if not user:
            security.verify_password(security.hash_password("dummy-password-value"), password)
        security.record_attempt(email, False, request.client.host if request.client else "")
        return RedirectResponse("/login?err=failed", status_code=303)
    security.record_attempt(email, True)
    security.clear_attempts(email)
    cookie, csrf = security.create_session(user["id"], request.client.host if request.client else "")
    resp = RedirectResponse("/", status_code=303)
    resp.set_cookie(security.COOKIE, cookie, httponly=True, samesite="strict",
                    secure=security.COOKIE_SECURE, max_age=security.SESSION_ABSOLUTE)
    resp.set_cookie("ll_csrf", csrf, httponly=False, samesite="strict", secure=security.COOKIE_SECURE,
                    max_age=security.SESSION_ABSOLUTE)
    return resp


@app.get("/demo/{role}")
def demo_login(request: Request, role: str):
    if os.environ.get("LOTLINE_DEMO", "1") != "1":
        raise Denied(404, "not_found")
    emails = {"inspector": "inspector@lotline.demo", "supervisor": "supervisor@lotline.demo",
              "admin": "admin@lotline.demo"}
    if role not in emails:
        raise Denied(404, "not_found")
    user = db.one("SELECT * FROM app_user WHERE email=?", (emails[role],))
    if not user:
        raise Denied(404, "not_found")
    cookie, csrf = security.create_session(user["id"], request.client.host if request.client else "")
    resp = RedirectResponse("/", status_code=303)
    resp.set_cookie(security.COOKIE, cookie, httponly=True, samesite="strict",
                    secure=security.COOKIE_SECURE, max_age=security.SESSION_ABSOLUTE)
    resp.set_cookie("ll_csrf", csrf, httponly=False, samesite="strict", secure=security.COOKIE_SECURE,
                    max_age=security.SESSION_ABSOLUTE)
    return resp


@app.post("/logout")
def logout(request: Request, csrf: str = Form("")):
    s = require_user(request)
    assert_csrf(request, s, csrf)
    security.destroy_session(s["session"]["id"], s["user"]["id"])
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie(security.COOKIE)
    resp.delete_cookie("ll_csrf")
    return resp


@app.get("/lang/{code}")
def set_lang(request: Request, code: str, next: str = "/"):
    resp = RedirectResponse(next or "/", status_code=303)
    if code in i18n.LANGS:
        resp.set_cookie("ll_lang", code, max_age=60 * 60 * 24 * 365, samesite="lax")
    return resp


# --------------------------------------------------------------------------
# Dashboard, lots
# --------------------------------------------------------------------------

def lot_cards(request: Request, state: str = "", outcome: str = "", q: str = ""):
    rows = db.q("SELECT l.*, b.name AS buyer_name, p.name AS product_name"
                " FROM lot l JOIN buyer b ON b.id=l.buyer_id JOIN product p ON p.id=l.product_id"
                " ORDER BY l.id DESC")
    out = []
    for r in rows:
        d = service.latest_decision(r["id"])
        ov = service.override_for(d["id"]) if d else None
        final = service.final_disposition(d, ov) if d else None
        p = service.progress(r["id"])
        card = {**dict(r), "decision": dict(d) if d else None, "override": ov, "final": final,
                "progress": p}
        if state and card["status"] != state:
            continue
        if outcome and final != outcome:
            continue
        if q:
            hay = f"{card['lot_code']} {card['buyer_name']} {card['product_name']} {card['color']}".lower()
            if q.lower() not in hay:
                continue
        out.append(card)
    return out


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    s = require_user(request)
    cards = lot_cards(request)
    c = service.counters()
    card = load_model_card()
    return page(request, "dashboard.html", active="dashboard", cards=cards[:6], counters=c,
                model=vision.MODEL_NAME, model_ok=card.get("self_test", {}).get("passed", False),
                stats=demo_stats())


@app.get("/lots", response_class=HTMLResponse)
def lots_page(request: Request):
    require_user(request)
    state = request.query_params.get("state", "")
    outcome = request.query_params.get("outcome", "")
    q = request.query_params.get("q", "")
    cards = lot_cards(request, state, outcome, q)
    return page(request, "lots.html", active="lots", cards=cards, state=state, outcome=outcome, q=q)


@app.get("/lots/new", response_class=HTMLResponse)
def new_lot_page(request: Request):
    s = require_role(request, "inspector", "supervisor")
    buyers = db.q("SELECT * FROM buyer ORDER BY name")
    products = db.q("SELECT * FROM product ORDER BY name")
    return page(request, "lot_new.html", active="lots", buyers=buyers, products=products)


@app.post("/lots/new")
def new_lot(request: Request, csrf: str = Form(""), lot_code: str = Form(""), buyer_id: int = Form(0),
            product_id: int = Form(0), color: str = Form(""), lot_size: int = Form(0),
            selection_method: str = Form("self-declared random")):
    s = require_role(request, "inspector", "supervisor")
    assert_csrf(request, s, csrf)
    code = lot_code.strip().upper()
    if not code or lot_size < 1 or not buyer_id or not product_id:
        return RedirectResponse("/lots/new?err=invalid", status_code=303)
    if db.one("SELECT id FROM lot WHERE lot_code=?", (code,)):
        return RedirectResponse("/lots/new?err=exists", status_code=303)
    lot_id = db.x("INSERT INTO lot(organization_id,lot_code,product_id,buyer_id,color,lot_size,status,"
                  "critical_nonvisual_status,selection_method,created_by,created_at)"
                  " VALUES (1,?,?,?,?,?, 'open','pending',?,?,?)",
                  (code, product_id, buyer_id, color.strip(), lot_size, selection_method.strip(),
                   s["user"]["id"], db.now()))
    db.audit(s["user"]["id"], s["user"]["display_name"], "lot.created", "lot", lot_id,
             after={"lot_code": code, "lot_size": lot_size})
    return RedirectResponse(f"/lots/{lot_id}?ok=saved", status_code=303)


@app.get("/lots/{lot_id}", response_class=HTMLResponse)
def lot_page(request: Request, lot_id: int):
    s = require_user(request)
    L = service.lot(lot_id)
    if not L:
        raise Denied(404, "not_found")
    plan = service.active_plan(lot_id)
    p = service.progress(lot_id)
    units = service.units_with_views(lot_id)
    d = service.latest_decision(lot_id)
    ov = service.override_for(d["id"]) if d else None
    hist = db.q("SELECT * FROM decision WHERE lot_id=? ORDER BY sequence DESC", (lot_id,))
    audit = service.timeline(lot_id)
    is_admin = s["user"]["role"] == "admin"
    return page(request, "lot.html", active="lots", lot=L, plan=plan, plan_d=service.plan_dict(plan),
                progress=p, units=units, decision=d, override=ov,
                final=service.final_disposition(d, ov) if d else None, history=hist, audit=audit,
                is_admin=is_admin, can_write=(not is_admin and can_write_lot(s, L) and L["status"] != "decided"))


@app.get("/lots/{lot_id}/plan", response_class=HTMLResponse)
def plan_page(request: Request, lot_id: int):
    s = require_user(request)
    L = service.lot(lot_id)
    if not L:
        raise Denied(404, "not_found")
    plan = service.active_plan(lot_id)
    return page(request, "plan.html", active="lots", lot=L, plan=plan, plan_d=service.plan_dict(plan),
                is_supervisor=s["user"]["role"] == "supervisor",
                locked=L["status"] == "decided")


@app.post("/lots/{lot_id}/plan")
def plan_save(request: Request, lot_id: int, csrf: str = Form(""), n: int = Form(0),
              counting_mode: str = Form(""), critical_ac: int = Form(-1), critical_re: int = Form(-1),
              major_ac: int = Form(-1), major_re: int = Form(-1), minor_ac: int = Form(-1),
              minor_re: int = Form(-1), critical_aql: str = Form(""), major_aql: str = Form(""),
              minor_aql: str = Form(""), source_edition: str = Form(""), source_reference: str = Form("")):
    s = require_role(request, "supervisor")
    assert_csrf(request, s, csrf)
    L = service.lot(lot_id)
    if not L:
        raise Denied(404, "not_found")
    if L["status"] == "decided":
        raise Denied(403, "locked")
    plan = {"n": n, "counting_mode": counting_mode,
            "critical": {"ac": critical_ac, "re": critical_re},
            "major": {"ac": major_ac, "re": major_re},
            "minor": {"ac": minor_ac, "re": minor_re}}
    errs = engine.validate_plan(plan)
    if errs:
        return RedirectResponse(f"/lots/{lot_id}/plan?err=invalid", status_code=303)
    prev = service.active_plan(lot_id)
    ver = (prev["version"] + 1) if prev else 1
    db.x("INSERT INTO plan(lot_id,version,n,counting_mode,critical_aql,critical_ac,critical_re,"
         "major_aql,major_ac,major_re,minor_aql,minor_ac,minor_re,inspection_level,sampling_type,"
         "source_edition,source_reference,is_demo,entered_by,created_at)"
         " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'II','single',?,?,0,?,?)",
         (lot_id, ver, n, counting_mode, _f(critical_aql), critical_ac, critical_re,
          _f(major_aql), major_ac, major_re, _f(minor_aql), minor_ac, minor_re,
          source_edition.strip(), source_reference.strip(), s["user"]["id"], db.now()))
    db.audit(s["user"]["id"], s["user"]["display_name"], "plan.created", "lot", lot_id,
             after={"version": ver, "n": n, "mode": counting_mode})
    # a plan defines the sample: create the garment slots once, so capture has somewhere to go
    have = db.one("SELECT COUNT(*) c FROM sample_unit WHERE lot_id=?", (lot_id,))["c"]
    if have == 0:
        for i in range(1, n + 1):
            uid = db.x("INSERT INTO sample_unit(lot_id, garment_code, created_at) VALUES (?,?,?)",
                       (lot_id, f"G-{i:02d}", db.now()))
            for side in ("front", "back"):
                db.x("INSERT INTO unit_view(sample_unit_id, side, required) VALUES (?,?,1)", (uid, side))
        db.audit(s["user"]["id"], s["user"]["display_name"], "units.generated", "lot", lot_id,
                 after={"count": n, "views": n * 2})
    return RedirectResponse(f"/lots/{lot_id}?ok=saved", status_code=303)


def _f(v: str):
    try:
        return float(v) if v not in (None, "") else None
    except ValueError:
        return None


@app.post("/lots/{lot_id}/nonvisual")
def nonvisual(request: Request, lot_id: int, csrf: str = Form(""), status: str = Form(""),
              note: str = Form("")):
    s = require_role(request, "supervisor")
    assert_csrf(request, s, csrf)
    L = service.lot(lot_id)
    if not L:
        raise Denied(404, "not_found")
    if status not in ("pending", "done", "not_required", "failed"):
        raise Denied(422, "invalid")
    if status == "failed" and len(note.strip()) < 3:
        raise Denied(422, "note_required")
    if L["status"] == "decided" and status != L["critical_nonvisual_status"]:
        raise Denied(403, "locked")
    db.x("UPDATE lot SET critical_nonvisual_status=?, nonvisual_note=? WHERE id=?",
         (status, note.strip() or None, lot_id))
    db.audit(s["user"]["id"], s["user"]["display_name"], "lot.nonvisual_changed", "lot", lot_id,
             before={"status": L["critical_nonvisual_status"]}, after={"status": status, "note": note.strip()})
    return RedirectResponse(f"/lots/{lot_id}?ok=saved", status_code=303)


# --------------------------------------------------------------------------
# Capture
# --------------------------------------------------------------------------

@app.get("/lots/{lot_id}/capture", response_class=HTMLResponse)
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


@app.post("/lots/{lot_id}/units")
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


@app.post("/lots/{lot_id}/views/{view_id}/upload")
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
        im.thumbnail((1600, 1600), Image.LANCZOS)
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


@app.post("/images/{img_id}/infer")
def infer_again(request: Request, img_id: int, csrf: str = Form("")):
    s = require_role(request, "inspector", "supervisor")
    assert_csrf(request, s, csrf)
    img = db.one("SELECT * FROM image WHERE id=?", (img_id,))
    if not img:
        raise Denied(404, "not_found")
    ensure_write(request, s, service.lot(img["lot_id"]))
    run_inference(img_id, s["user"]["id"], request)
    return RedirectResponse(f"/review/{img_id}?ok=saved", status_code=303)


@app.get("/images/{img_id}")
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


@app.get("/images/{img_id}/heat")
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


# --------------------------------------------------------------------------
# Review
# --------------------------------------------------------------------------

@app.get("/lots/{lot_id}/review", response_class=HTMLResponse)
def review_queue_page(request: Request, lot_id: int):
    s = require_user(request)
    L = service.lot(lot_id)
    if not L:
        raise Denied(404, "not_found")
    if s["user"]["role"] == "admin":
        raise Denied(403, "not_allowed")
    return page(request, "review_queue.html", active="lots", lot=L, queue=service.review_queue(lot_id))


@app.get("/review/{img_id}", response_class=HTMLResponse)
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


@app.post("/review/{img_id}/confirm")
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


@app.post("/review/{img_id}/reject")
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


@app.post("/review/{img_id}/second-review")
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


@app.post("/review/{img_id}/add")
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


@app.post("/review/{img_id}/state")
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


# --------------------------------------------------------------------------
# Decision, override, report
# --------------------------------------------------------------------------

@app.post("/lots/{lot_id}/decisions")
def compute_decision(request: Request, lot_id: int, csrf: str = Form(""), note: str = Form("")):
    s = require_role(request, "inspector", "supervisor")
    assert_csrf(request, s, csrf)
    L = service.lot(lot_id)
    if not L:
        raise Denied(404, "not_found")
    if not can_write_lot(s, L):
        raise Denied(403, "not_allowed")
    if L["status"] == "decided":
        return RedirectResponse(f"/lots/{lot_id}/decision?err=locked", status_code=303)
    service.compute_decision(lot_id, s["user"]["id"], note.strip())
    return RedirectResponse(f"/lots/{lot_id}/decision?ok=saved", status_code=303)


@app.get("/lots/{lot_id}/decision", response_class=HTMLResponse)
def decision_page(request: Request, lot_id: int):
    s = require_user(request)
    L = service.lot(lot_id)
    if not L:
        raise Denied(404, "not_found")
    plan = service.plan_dict(service.active_plan(lot_id))
    d = service.latest_decision(lot_id)
    ov = service.override_for(d["id"]) if d else None
    hist = db.q("SELECT d.*, u.display_name AS decided_by FROM decision d JOIN app_user u ON u.id=d.created_by"
                " WHERE d.lot_id=? ORDER BY d.sequence DESC", (lot_id,))
    d = dict(d) if d else None
    if d:
        d["reasons"] = json.loads(d["reasons"])
        d["counts"] = json.loads(d["counts"])
        d["class_limits"] = json.loads(d["class_limits"] or "{}")
        d["completeness"] = json.loads(d["completeness"] or "{}")
        d["plan_snapshot"] = json.loads(d["plan_snapshot"]) if d["plan_snapshot"] else None
    prog = service.progress(lot_id)
    return page(request, "decision.html", active="lots", lot=L, plan=plan, decision=d, override=ov,
                final=service.final_disposition(db.one("SELECT * FROM decision WHERE id=?", (d["id"],)), ov) if d else None,
                history=[dict(h) | {"counts": json.loads(h["counts"]), "reasons": json.loads(h["reasons"])} for h in hist],
                progress=prog, is_supervisor=s["user"]["role"] == "supervisor",
                can_write=(can_write_lot(s, L) and L["status"] != "decided"),
                reason_text=engine.REASONS)


@app.post("/decisions/{decision_id}/override")
def make_override(request: Request, decision_id: int, csrf: str = Form(""), disposition: str = Form(""),
                  reason: str = Form("")):
    s = require_role(request, "supervisor")
    assert_csrf(request, s, csrf)
    d = db.one("SELECT * FROM decision WHERE id=?", (decision_id,))
    if not d:
        raise Denied(404, "not_found")
    if d["outcome"] not in ("ACCEPT", "REJECT"):
        return RedirectResponse(f"/lots/{d['lot_id']}/decision?err=override_not_allowed", status_code=303)
    if d["primary_reason"] == "REJECT_CRITICAL_NONVISUAL_FAILED":
        return RedirectResponse(f"/lots/{d['lot_id']}/decision?err=override_not_allowed", status_code=303)
    if disposition not in ("OVERRIDE_ACCEPT", "OVERRIDE_REJECT"):
        raise Denied(422, "invalid")
    if disposition == "OVERRIDE_ACCEPT" and d["outcome"] == "ACCEPT":
        return RedirectResponse(f"/lots/{d['lot_id']}/decision?err=override_not_allowed", status_code=303)
    if len(reason.strip()) < 20:
        return RedirectResponse(f"/lots/{d['lot_id']}/decision?err=reason_short", status_code=303)
    if db.one("SELECT id FROM override WHERE decision_id=?", (decision_id,)):
        return RedirectResponse(f"/lots/{d['lot_id']}/decision?err=already_overridden", status_code=303)
    high_risk = disposition == "OVERRIDE_ACCEPT" and d["outcome"] == "REJECT"
    status = "pending_approval" if high_risk else "effective"
    oid = db.x("INSERT INTO override(decision_id,supervisor_id,final_disposition,reason,status,created_at)"
               " VALUES (?,?,?,?,?,?)",
               (decision_id, s["user"]["id"], disposition, reason.strip(), status, db.now()))
    if not high_risk:
        db.x("UPDATE lot SET status='decided', version=version+1 WHERE id=?", (d["lot_id"],))
    db.audit(s["user"]["id"], s["user"]["display_name"], "decision.overridden", "override", oid,
             after={"disposition": disposition, "system": d["outcome"], "status": status})
    return RedirectResponse(f"/lots/{d['lot_id']}/decision?ok=saved", status_code=303)


@app.post("/overrides/{override_id}/approval")
def approve_override(request: Request, override_id: int, csrf: str = Form(""), decision: str = Form("approved")):
    s = require_role(request, "supervisor")
    assert_csrf(request, s, csrf)
    o = db.one("SELECT * FROM override WHERE id=?", (override_id,))
    if not o:
        raise Denied(404, "not_found")
    if o["supervisor_id"] == s["user"]["id"]:
        return RedirectResponse(f"/lots/{db.one('SELECT lot_id FROM decision WHERE id=?', (o['decision_id'],))['lot_id']}/decision?err=self_approval",
                               status_code=303)
    if db.one("SELECT id FROM override_approval WHERE override_id=?", (override_id,)):
        raise Denied(422, "already_approved")
    db.x("INSERT INTO override_approval(override_id,approver_id,decision,created_at) VALUES (?,?,?,?)",
         (override_id, s["user"]["id"], "approved" if decision == "approved" else "refused", db.now()))
    d = db.one("SELECT * FROM decision WHERE id=?", (o["decision_id"],))
    if decision == "approved":
        db.x("UPDATE override SET status='effective' WHERE id=?", (override_id,))
        db.x("UPDATE lot SET status='decided', version=version+1 WHERE id=?", (d["lot_id"],))
    db.audit(s["user"]["id"], s["user"]["display_name"], "decision.override_approved", "override", override_id,
             after={"decision": decision})
    return RedirectResponse(f"/lots/{d['lot_id']}/decision?ok=saved", status_code=303)


def _report_ctx(lot_id: int) -> dict:
    L = service.lot(lot_id)
    d = service.latest_decision(lot_id)
    if not d:
        raise Denied(404, "not_found")
    ov = service.override_for(d["id"])
    plan = json.loads(d["plan_snapshot"]) if d["plan_snapshot"] else None
    reasons = json.loads(d["reasons"])
    comp = json.loads(d["completeness"])
    counts = json.loads(d["counts"])
    limits = json.loads(d["class_limits"] or "{}")
    class_status = {c: {"count": counts.get(c, 0), "ac": limits.get(c, {}).get("ac"),
                        "re": limits.get(c, {}).get("re"),
                        "status": "FAIL" if limits.get(c) and counts.get(c, 0) >= limits[c]["re"] else "PASS"}
                    for c in engine.CLASSES} if limits else {}
    images = db.one("SELECT COUNT(*) AS n FROM image WHERE lot_id=? AND purged=0", (lot_id,))["n"]
    units = db.one("SELECT COUNT(*) AS n FROM sample_unit WHERE lot_id=?", (lot_id,))["n"]
    return {
        "lot_code": L["lot_code"], "product": L["product_name"], "buyer": L["buyer_name"],
        "sequence": d["sequence"], "created_at": d["created_at"], "engine_version": d["engine_version"],
        "outcome": d["outcome"], "override": ov
        and {"final_disposition": ov["final_disposition"], "reason": ov["reason"], "approved": ov["effective"]},
        "plan": plan, "n_effective": (plan or {}).get("n"), "counts": counts, "class_status": class_status,
        "reasons": [{"code": r, "text": engine.REASONS.get(r, ("", r))[1]} for r in reasons],
        "units_present": comp.get("units_present"), "required_units": comp.get("required_units"),
        "views_pending": comp.get("views_pending"), "evidence_bad": comp.get("evidence_bad"),
        "nonvisual": L["critical_nonvisual_status"], "images": images, "units": units,
        "model": vision.MODEL_NAME, "model_domains": "staged knit panels (synthetic), no factory images",
        "manual": bool(d["manual_inspection"]), "selection": L["selection_method"],
        "snapshot_hash": d["snapshot_hash"], "lot": L, "decision": d, "progress": service.progress(lot_id),
        "reasons_raw": reasons,
    }


@app.get("/lots/{lot_id}/report", response_class=HTMLResponse)
def report_page(request: Request, lot_id: int):
    s = require_user(request)
    if s["user"]["role"] == "admin":
        raise Denied(403, "not_allowed")
    rc = _report_ctx(lot_id)
    return page(request, "report.html", active="lots", rc=rc, lot=rc["lot"])


@app.get("/lots/{lot_id}/report.pdf")
def report_pdf(request: Request, lot_id: int):
    s = require_user(request)
    if s["user"]["role"] == "admin":
        raise Denied(403, "not_allowed")
    rc = _report_ctx(lot_id)
    data = report.build(rc)
    return Response(data, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="lotline-{rc["lot_code"]}-decision-{rc["sequence"]}.pdf"',
                             "Cache-Control": "no-store"})


# --------------------------------------------------------------------------
# Audit, admin, help
# --------------------------------------------------------------------------

@app.get("/audit", response_class=HTMLResponse)
def audit_page(request: Request):
    s = require_role(request, "supervisor", "admin")
    q = request.query_params.get("q", "")
    rows = db.q("SELECT * FROM audit_event ORDER BY id DESC LIMIT 300")
    out = []
    for r in rows:
        d = dict(r)
        if q and q.lower() not in f"{d['action']} {d['entity']} {d['actor_label']}".lower():
            continue
        d["before"] = json.loads(d["before_json"]) if d["before_json"] else None
        d["after"] = json.loads(d["after_json"]) if d["after_json"] else None
        out.append(d)
    return page(request, "audit.html", active="audit", rows=out[:200], q=q,
                can_export=s["user"]["role"] == "admin")


@app.get("/audit.csv")
def audit_csv(request: Request):
    s = require_role(request, "admin")
    rows = db.q("SELECT * FROM audit_event ORDER BY id DESC")
    lines = ["id,at,actor,action,entity,entity_id,before,after"]
    import csv as _csv
    buf = io.StringIO()
    w = _csv.writer(buf)
    w.writerow(["id", "at", "actor", "action", "entity", "entity_id", "before", "after"])
    for r in rows:
        w.writerow([r["id"], r["at"], r["actor_label"], r["action"], r["entity"], r["entity_id"],
                    r["before_json"] or "", r["after_json"] or ""])
    db.audit(s["user"]["id"], s["user"]["display_name"], "audit.exported", "audit_event", "all")
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="lotline-audit.csv"'})


@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request):
    s = require_role(request, "admin")
    tab = request.query_params.get("tab", "users")
    users = db.q("SELECT * FROM app_user ORDER BY id")
    models = db.q("SELECT * FROM model_version ORDER BY id DESC")
    tests = db.q("SELECT * FROM model_selftest ORDER BY id DESC LIMIT 8")
    acts = db.q("SELECT * FROM model_activation ORDER BY id DESC LIMIT 10")
    clauses = db.q("SELECT c.*, b.name AS buyer_name FROM clause_mapping c JOIN buyer b ON b.id=c.buyer_id"
                   " ORDER BY b.name, c.defect_type, c.zone_code")
    free = shutil.disk_usage(service.STORE)
    health = {
        "db_bytes": os.path.getsize(db.DB_PATH) if os.path.exists(db.DB_PATH) else 0,
        "disk_free": free.free, "disk_total": free.total,
        "images": db.one("SELECT COUNT(*) AS n FROM image WHERE purged=0")["n"],
        "jobs_ok": db.one("SELECT COUNT(*) AS n FROM inference_job WHERE status='succeeded'")["n"],
        "jobs_failed": db.one("SELECT COUNT(*) AS n FROM inference_job WHERE status='failed'")["n"],
        "audit_rows": db.one("SELECT COUNT(*) AS n FROM audit_event")["n"],
        "sessions": db.one("SELECT COUNT(*) AS n FROM user_session")["n"],
        "model": vision.MODEL_NAME, "model_loaded": bool(vision._state.get("model")),
        "model_sha": (db.one("SELECT artifact_sha FROM model_version ORDER BY id DESC LIMIT 1") or {"artifact_sha": "-"})["artifact_sha"],
    }
    return page(request, "admin.html", active="admin", tab=tab, users=users, models=models, tests=tests,
                activations=acts, clauses=clauses, health=health, card=load_model_card())


@app.post("/admin/users")
def admin_create_user(request: Request, csrf: str = Form(""), email: str = Form(""), display_name: str = Form(""),
                      role: str = Form("inspector"), password: str = Form("")):
    s = require_role(request, "admin")
    assert_csrf(request, s, csrf)
    email = email.strip().lower()
    if role not in ("admin", "inspector", "supervisor") or not email or db.one("SELECT id FROM app_user WHERE email=?", (email,)):
        return RedirectResponse("/admin?err=invalid", status_code=303)
    errs = security.policy_errors(password, email, display_name)
    if errs:
        return RedirectResponse("/admin?err=policy", status_code=303)
    uid = db.x("INSERT INTO app_user(organization_id,email,display_name,role,password_hash,status,must_change,created_at)"
               " VALUES (1,?,?,?,?,'active',1,?)",
               (email, display_name.strip() or email.split("@")[0], role, security.hash_password(password), db.now()))
    db.audit(s["user"]["id"], s["user"]["display_name"], "user.created", "app_user", uid,
             after={"email": email, "role": role})
    return RedirectResponse("/admin?ok=saved", status_code=303)


@app.post("/admin/users/{user_id}")
def admin_user_action(request: Request, user_id: int, csrf: str = Form(""), action: str = Form(""),
                      role: str = Form("")):
    s = require_role(request, "admin")
    assert_csrf(request, s, csrf)
    u = db.one("SELECT * FROM app_user WHERE id=?", (user_id,))
    if not u:
        raise Denied(404, "not_found")
    if action == "disable":
        if u["role"] == "admin" and db.one("SELECT COUNT(*) AS n FROM app_user WHERE role='admin' AND status='active'")["n"] <= 1:
            return RedirectResponse("/admin?err=last_admin", status_code=303)
        db.x("UPDATE app_user SET status='disabled' WHERE id=?", (user_id,))
        security.revoke_user_sessions(user_id)
    elif action == "enable":
        db.x("UPDATE app_user SET status='active' WHERE id=?", (user_id,))
    elif action == "role" and role in ("admin", "inspector", "supervisor"):
        if user_id == s["user"]["id"]:
            return RedirectResponse("/admin?err=self_role", status_code=303)
        db.x("UPDATE app_user SET role=? WHERE id=?", (role, user_id))
        security.revoke_user_sessions(user_id)
    elif action == "reset":
        pw = "Temp" + os.urandom(6).hex() + "!Aa"
        db.x("UPDATE app_user SET password_hash=?, must_change=1 WHERE id=?",
             (security.hash_password(pw), user_id))
        security.revoke_user_sessions(user_id)
        db.audit(s["user"]["id"], s["user"]["display_name"], "user.password_reset", "app_user", user_id)
        return RedirectResponse(f"/admin?ok=temp&temp={pw}", status_code=303)
    db.audit(s["user"]["id"], s["user"]["display_name"], f"user.{action}", "app_user", user_id,
             before={"role": u["role"], "status": u["status"]})
    return RedirectResponse("/admin?ok=saved", status_code=303)


@app.post("/admin/models/selftest")
def admin_selftest(request: Request, csrf: str = Form("")):
    s = require_role(request, "admin")
    assert_csrf(request, s, csrf)
    ok, detail = vision.selftest()
    db.x("INSERT INTO model_selftest(model_name,passed,detail,created_at) VALUES (?,?,?,?)",
         (vision.MODEL_NAME, 1 if ok else 0, detail, db.now()))
    db.audit(s["user"]["id"], s["user"]["display_name"], "model.selftest", "model_version", vision.MODEL_NAME,
             after={"passed": ok, "detail": detail})
    return RedirectResponse("/admin?tab=models&ok=saved", status_code=303)


@app.post("/admin/models/activate")
def admin_activate(request: Request, csrf: str = Form(""), reason: str = Form("")):
    s = require_role(request, "admin")
    assert_csrf(request, s, csrf)
    if len(reason.strip()) < 20:
        return RedirectResponse("/admin?tab=models&err=reason_short", status_code=303)
    last = db.one("SELECT * FROM model_selftest ORDER BY id DESC LIMIT 1")
    if not last or not last["passed"]:
        return RedirectResponse("/admin?tab=models&err=selftest_required", status_code=303)
    db.x("INSERT INTO model_activation(model_name,action,actor,reason,created_at) VALUES (?,?,?,?,?)",
         (vision.MODEL_NAME, "activate", s["user"]["display_name"], reason.strip(), db.now()))
    db.audit(s["user"]["id"], s["user"]["display_name"], "model.activated", "model_version", vision.MODEL_NAME,
             after={"reason": reason.strip()})
    return RedirectResponse("/admin?tab=models&ok=saved", status_code=303)


@app.get("/how", response_class=HTMLResponse)
def how_page(request: Request):
    require_user(request)
    card = load_model_card()
    return page(request, "how.html", active="how", card=card, stats=demo_stats())


@app.get("/healthz")
def healthz():
    return JSONResponse({"ok": True})


@app.get("/readyz")
def readyz():
    db.one("SELECT 1")
    return JSONResponse({"ready": True})


def load_model_card() -> dict:
    p = os.path.join(os.path.dirname(service.STORE), "models", "model_card.json")
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except OSError:
        return {}


def demo_stats() -> dict:
    img = db.one("SELECT COUNT(*) AS n FROM image WHERE purged=0")["n"]
    preds = db.one("SELECT COUNT(*) AS n FROM prediction")["n"]
    confirmed = db.one("SELECT COUNT(*) AS n FROM prediction WHERE review_state='confirmed'")["n"]
    rejected = db.one("SELECT COUNT(*) AS n FROM prediction WHERE review_state='rejected'")["n"]
    dec = db.q("SELECT outcome, COUNT(*) AS n FROM decision GROUP BY outcome")
    return {"images": img, "proposals": preds, "confirmed": confirmed, "rejected": rejected,
            "decisions": {r["outcome"]: r["n"] for r in dec},
            "lots": db.one("SELECT COUNT(*) AS n FROM lot")["n"],
            "audit": db.one("SELECT COUNT(*) AS n FROM audit_event")["n"]}
