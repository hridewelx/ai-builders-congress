"""Audit log and administration."""
from __future__ import annotations

import io
import json
import os
import shutil

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from ...core import db, security
from ...services import detector, vision
from ...services import review as service
from ..deps import Denied, assert_csrf, require_role
from ..pages import page
from ..stats import load_model_card

router = APIRouter(tags=["admin"])


@router.get("/audit", response_class=HTMLResponse)
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


@router.get("/audit.csv")
def audit_csv(request: Request):
    s = require_role(request, "admin")
    rows = db.q("SELECT * FROM audit_event ORDER BY id DESC")
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


@router.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request):
    require_role(request, "admin")
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


@router.post("/admin/users")
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


@router.post("/admin/users/{user_id}")
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


@router.post("/admin/models/selftest")
def admin_selftest(request: Request, csrf: str = Form("")):
    s = require_role(request, "admin")
    assert_csrf(request, s, csrf)
    if detector.available():
        model_name = detector.MODEL_NAME
        ok, detail = detector.selftest()
    else:
        model_name = vision.MODEL_NAME
        ok, detail = vision.selftest()
    db.x("INSERT INTO model_selftest(model_name,passed,detail,created_at) VALUES (?,?,?,?)",
         (model_name, 1 if ok else 0, detail, db.now()))
    db.audit(s["user"]["id"], s["user"]["display_name"], "model.selftest", "model_version", model_name,
             after={"passed": ok, "detail": detail})
    return RedirectResponse("/admin?tab=models&ok=saved", status_code=303)


@router.post("/admin/models/activate")
def admin_activate(request: Request, csrf: str = Form(""), reason: str = Form("")):
    s = require_role(request, "admin")
    assert_csrf(request, s, csrf)
    if len(reason.strip()) < 20:
        return RedirectResponse("/admin?tab=models&err=reason_short", status_code=303)
    model_name = detector.MODEL_NAME if detector.available() else vision.MODEL_NAME
    last = db.one("SELECT * FROM model_selftest WHERE model_name=? ORDER BY id DESC LIMIT 1", (model_name,))
    if not last or not last["passed"]:
        return RedirectResponse("/admin?tab=models&err=selftest_required", status_code=303)
    db.x("INSERT INTO model_activation(model_name,action,actor,reason,created_at) VALUES (?,?,?,?,?)",
         (model_name, "activate", s["user"]["display_name"], reason.strip(), db.now()))
    db.audit(s["user"]["id"], s["user"]["display_name"], "model.activated", "model_version", model_name,
             after={"reason": reason.strip()})
    return RedirectResponse("/admin?tab=models&ok=saved", status_code=303)
