"""Audit log, administration, explainer page and downloadable artefacts."""
from __future__ import annotations

import csv
import io
import json
import os
import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response

from ..config import DB_PATH
from ..core import db, security
from ..core.permissions import organization_id
from ..services import detector, vision
from ..services import report as report_service
from ..services import review as service
from ..services.stats import demo_stats, load_model_card
from .deps import check_csrf, current_user, role_required
from .serializers import clean, report_context

router = APIRouter(tags=["admin"])


@router.get("/audit")
def audit_log(request: Request, q: str = ""):
    session = role_required(current_user(request), "supervisor", "admin")
    rows = db.q("SELECT a.* FROM audit_event a LEFT JOIN app_user u ON u.id=a.actor_id"
                " WHERE a.actor_id IS NULL OR u.organization_id=? ORDER BY a.id DESC LIMIT 300",
                (organization_id(session),))
    out = []
    for row in rows:
        data = dict(row)
        if q and q.lower() not in f"{data['action']} {data['entity']} {data['actor_label']}".lower():
            continue
        data["before"] = json.loads(data["before_json"]) if data["before_json"] else None
        data["after"] = json.loads(data["after_json"]) if data["after_json"] else None
        out.append(clean(data))
    return {"rows": out[:200], "q": q, "can_export": session["user"]["role"] == "admin"}


@router.get("/audit.csv")
def audit_csv(request: Request):
    session = role_required(current_user(request), "admin")
    rows = db.q("SELECT a.* FROM audit_event a LEFT JOIN app_user u ON u.id=a.actor_id"
                " WHERE a.actor_id IS NULL OR u.organization_id=? ORDER BY a.id DESC",
                (organization_id(session),))
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "at", "actor", "action", "entity", "entity_id", "before", "after"])
    for row in rows:
        writer.writerow([row["id"], row["at"], row["actor_label"], row["action"], row["entity"],
                         row["entity_id"], row["before_json"] or "", row["after_json"] or ""])
    db.audit(session["user"]["id"], session["user"]["display_name"], "audit.exported",
             "audit_event", "all")
    return Response(buffer.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="lotline-audit.csv"'})


@router.get("/admin")
def admin_page(request: Request, tab: str = "users"):
    session = role_required(current_user(request), "admin")
    org = organization_id(session)
    users = db.q("SELECT * FROM app_user WHERE organization_id=? ORDER BY id", (org,))
    models = db.q("SELECT * FROM model_version ORDER BY id DESC")
    tests = db.q("SELECT * FROM model_selftest ORDER BY id DESC LIMIT 8")
    activations = db.q("SELECT * FROM model_activation ORDER BY id DESC LIMIT 10")
    clauses = db.q("SELECT c.*, b.name AS buyer_name FROM clause_mapping c"
                   " JOIN buyer b ON b.id=c.buyer_id WHERE b.organization_id=?"
                   " ORDER BY b.name, c.defect_type, c.zone_code", (org,))
    free = shutil.disk_usage(service.STORE)
    health = {
        "db_bytes": os.path.getsize(db.DB_PATH) if os.path.exists(db.DB_PATH) else 0,
        "disk_free": free.free,
        "disk_total": free.total,
        "images": db.one("SELECT COUNT(*) AS n FROM image WHERE purged=0")["n"],
        "jobs_ok": db.one("SELECT COUNT(*) AS n FROM inference_job WHERE status='succeeded'")["n"],
        "jobs_failed": db.one("SELECT COUNT(*) AS n FROM inference_job WHERE status='failed'")["n"],
        "audit_rows": db.one("SELECT COUNT(*) AS n FROM audit_event")["n"],
        "sessions": db.one("SELECT COUNT(*) AS n FROM user_session")["n"],
        "model": detector.MODEL_NAME if detector.available() else vision.MODEL_NAME,
        "model_loaded": bool(detector.available() or vision._state.get("model")),
        "model_sha": (db.one("SELECT artifact_sha FROM model_version ORDER BY id DESC LIMIT 1")
                      or {"artifact_sha": "-"})["artifact_sha"],
    }
    return {
        "tab": tab,
        "user": clean(session["user"]),
        "users": [clean(row) for row in users],
        "models": clean(models),
        "tests": clean(tests),
        "activations": clean(activations),
        "clauses": clean(clauses),
        "health": health,
        "card": load_model_card(),
    }


@router.get("/admin/model/registry")
def model_registry(request: Request):
    role_required(current_user(request), "admin")
    from ml import live_metrics, registry
    try:
        latest = registry.latest()
        entries = len(registry.history())
    except (OSError, ValueError):
        latest, entries = None, 0
    try:
        rows = [dict(row) for row in live_metrics._query(Path(DB_PATH), 30)]
        live = live_metrics.summarise(rows, live_metrics.operating_threshold())
    except (SystemExit, OSError):
        live = {"proposals": 0, "note": "no database readable from this process"}
    from fastapi.responses import JSONResponse
    return JSONResponse({"registry": {"entries": entries, "latest": latest},
                         "live_30_days": live})


@router.post("/admin/users")
async def create_user(request: Request):
    session = role_required(current_user(request), "admin")
    check_csrf(request, session)
    data = await request.json()
    email = str(data.get("email") or "").strip().lower()
    display_name = str(data.get("display_name") or "").strip()
    role = str(data.get("role") or "inspector")
    password = str(data.get("password") or "")
    if role not in ("admin", "inspector", "supervisor") or not email or \
            db.one("SELECT id FROM app_user WHERE email=?", (email,)):
        raise HTTPException(status_code=422, detail="invalid")
    if security.policy_errors(password, email, display_name):
        raise HTTPException(status_code=422, detail="policy")
    user_id = db.x("INSERT INTO app_user(organization_id,email,display_name,role,password_hash,"
                   "status,must_change,created_at) VALUES (?,?,?,?,?,'active',1,?)",
                   (organization_id(session), email, display_name or email.split("@")[0], role,
                    security.hash_password(password), db.now()))
    db.audit(session["user"]["id"], session["user"]["display_name"], "user.created", "app_user",
             user_id, after={"email": email, "role": role})
    return {"ok": True, "id": user_id}


@router.post("/admin/users/{user_id}")
async def user_action(request: Request, user_id: int):
    session = role_required(current_user(request), "admin")
    check_csrf(request, session)
    user = db.one("SELECT * FROM app_user WHERE id=? AND organization_id=?",
                  (user_id, organization_id(session)))
    if not user:
        raise HTTPException(status_code=404, detail="not_found")
    data = await request.json()
    action = str(data.get("action") or "")
    role = str(data.get("role") or "")
    temp_password = None
    if action == "disable":
        if user["role"] == "admin" and db.one(
                "SELECT COUNT(*) AS n FROM app_user WHERE role='admin' AND status='active'"
                " AND organization_id=?", (organization_id(session),))["n"] <= 1:
            raise HTTPException(status_code=409, detail="last_admin")
        db.x("UPDATE app_user SET status='disabled' WHERE id=?", (user_id,))
        security.revoke_user_sessions(user_id)
    elif action == "enable":
        db.x("UPDATE app_user SET status='active' WHERE id=?", (user_id,))
    elif action == "role" and role in ("admin", "inspector", "supervisor"):
        if user_id == session["user"]["id"]:
            raise HTTPException(status_code=409, detail="self_role")
        db.x("UPDATE app_user SET role=? WHERE id=?", (role, user_id))
        security.revoke_user_sessions(user_id)
    elif action == "reset":
        temp_password = "Temp" + os.urandom(6).hex() + "!Aa"
        db.x("UPDATE app_user SET password_hash=?, must_change=1 WHERE id=?",
             (security.hash_password(temp_password), user_id))
        security.revoke_user_sessions(user_id)
        db.audit(session["user"]["id"], session["user"]["display_name"], "user.password_reset",
                 "app_user", user_id)
        return {"ok": True, "temp_password": temp_password}
    else:
        raise HTTPException(status_code=422, detail="invalid")
    db.audit(session["user"]["id"], session["user"]["display_name"], f"user.{action}", "app_user",
             user_id, before={"role": user["role"], "status": user["status"]})
    return {"ok": True}


@router.post("/admin/models/selftest")
def selftest(request: Request):
    session = role_required(current_user(request), "admin")
    check_csrf(request, session)
    if detector.available():
        model_name = detector.MODEL_NAME
        ok, detail = detector.selftest()
    else:
        model_name = vision.MODEL_NAME
        ok, detail = vision.selftest()
    db.x("INSERT INTO model_selftest(model_name,passed,detail,created_at) VALUES (?,?,?,?)",
         (model_name, 1 if ok else 0, detail, db.now()))
    db.audit(session["user"]["id"], session["user"]["display_name"], "model.selftest",
             "model_version", model_name, after={"passed": ok, "detail": detail})
    return {"ok": True, "passed": ok, "detail": detail}


@router.post("/admin/models/activate")
async def activate(request: Request):
    session = role_required(current_user(request), "admin")
    check_csrf(request, session)
    data = await request.json()
    reason = str(data.get("reason") or "")
    if len(reason.strip()) < 20:
        raise HTTPException(status_code=422, detail="reason_short")
    model_name = detector.MODEL_NAME if detector.available() else vision.MODEL_NAME
    last = db.one("SELECT * FROM model_selftest WHERE model_name=? ORDER BY id DESC LIMIT 1",
                  (model_name,))
    if not last or not last["passed"]:
        raise HTTPException(status_code=409, detail="selftest_required")
    db.x("INSERT INTO model_activation(model_name,action,actor,reason,created_at) VALUES (?,?,?,?,?)",
         (model_name, "activate", session["user"]["display_name"], reason.strip(), db.now()))
    db.audit(session["user"]["id"], session["user"]["display_name"], "model.activated",
             "model_version", model_name, after={"reason": reason.strip()})
    return {"ok": True}


@router.get("/how")
def how(request: Request):
    current_user(request)
    return {"card": load_model_card(), "stats": demo_stats(), "model": detector.MODEL_NAME
            if detector.available() else vision.MODEL_NAME}


@router.get("/lots/{lot_id}/report.pdf")
def report_pdf(request: Request, lot_id: int):
    session = current_user(request)
    if session["user"]["role"] == "admin":
        raise HTTPException(status_code=403, detail="not_allowed")
    context = report_context(lot_id)
    if not context:
        raise HTTPException(status_code=404, detail="not_found")
    data = report_service.build(context)
    return Response(data, media_type="application/pdf",
                    headers={"Content-Disposition":
                             f'inline; filename="lotline-{context["lot_code"]}-decision-'
                             f'{context["sequence"]}.pdf"',
                             "Cache-Control": "no-store"})
