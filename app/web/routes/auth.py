"""Authentication, demo access and language switching."""
from __future__ import annotations

import time

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ... import i18n
from ...config import DEMO_LOGIN
from ...core import db, security
from ..deps import Denied, assert_csrf, require_user, sess_of
from ..pages import page

router = APIRouter(tags=["auth"])


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if sess_of(request):
        return RedirectResponse("/", status_code=303, headers={"Cache-Control": "no-store"})
    response = page(request, "login.html", active="login")
    response.headers["Cache-Control"] = "no-store"
    return response


@router.post("/login")
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


@router.get("/demo/{role}")
def demo_login(request: Request, role: str):
    if not DEMO_LOGIN:
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


@router.post("/logout")
def logout(request: Request, csrf: str = Form("")):
    s = require_user(request)
    assert_csrf(request, s, csrf)
    security.destroy_session(s["session"]["id"], s["user"]["id"])
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie(security.COOKIE)
    resp.delete_cookie("ll_csrf")
    return resp


@router.get("/lang/{code}")
def set_lang(request: Request, code: str, next: str = "/"):
    resp = RedirectResponse(next or "/", status_code=303)
    if code in i18n.LANGS:
        resp.set_cookie("ll_lang", code, max_age=60 * 60 * 24 * 365, samesite="lax")
    return resp
