"""Authentication, demo access, language and the app bootstrap payload."""
from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException, Request

from .. import i18n
from ..config import DEMO_LOGIN
from ..core import db, security
from .deps import check_csrf, clear_session_cookies, current_user, session_of, set_session_cookies
from .serializers import bootstrap, catalogs, clean, model_info

router = APIRouter(tags=["auth"])


def lang_of(request: Request) -> str:
    value = request.cookies.get("ll_lang", "bn")
    return value if value in i18n.LANGS else "bn"


def bootstrap_payload(request: Request) -> dict:
    session = session_of(request)
    payload = bootstrap()
    payload.update({
        "authenticated": bool(session),
        "lang": lang_of(request),
        "user": clean(session["user"]) if session else None,
        "csrf": session["session"]["csrf"] if session else "",
        "catalogs": catalogs(),
        "last_selftest": None,
        "model": model_info(),
    })
    row = db.one("SELECT * FROM model_selftest ORDER BY id DESC LIMIT 1")
    payload["last_selftest"] = clean(row) if row else None
    return payload


@router.get("/bootstrap")
def get_bootstrap(request: Request):
    return bootstrap_payload(request)


@router.post("/auth/login")
async def login(request: Request):
    data = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    if security.login_delay(email) and time.time() - security.last_failure_at(email) < security.login_delay(email):
        security.record_attempt(email, False, request.client.host if request.client else "")
        raise HTTPException(status_code=429, detail="rl")
    user = db.one("SELECT * FROM app_user WHERE email=?", (email,))
    ok = bool(user and user["status"] == "active" and security.verify_password(user["password_hash"], password))
    if not ok:
        if not user:
            # Constant-work path: verify a dummy hash when the account is absent.
            security.verify_password(security.hash_password("dummy-password-value"), password)
        security.record_attempt(email, False, request.client.host if request.client else "")
        raise HTTPException(status_code=401, detail="failed")
    security.record_attempt(email, True)
    security.clear_attempts(email)
    cookie, csrf = security.create_session(user["id"], request.client.host if request.client else "")
    from fastapi.responses import JSONResponse
    payload = bootstrap_payload(request)
    payload["user"] = clean(user)
    payload["csrf"] = csrf
    payload["authenticated"] = True
    response = JSONResponse(payload)
    set_session_cookies(response, cookie, csrf)
    return response


@router.post("/auth/demo/{role}")
def demo_login(request: Request, role: str):
    if not DEMO_LOGIN:
        raise HTTPException(status_code=404, detail="not_found")
    emails = {"inspector": "inspector@lotline.demo",
              "supervisor": "supervisor@lotline.demo",
              "admin": "admin@lotline.demo"}
    if role not in emails:
        raise HTTPException(status_code=404, detail="not_found")
    user = db.one("SELECT * FROM app_user WHERE email=?", (emails[role],))
    if not user:
        raise HTTPException(status_code=404, detail="not_found")
    cookie, csrf = security.create_session(user["id"], request.client.host if request.client else "")
    from fastapi.responses import JSONResponse
    payload = bootstrap_payload(request)
    payload["user"] = clean(user)
    payload["csrf"] = csrf
    payload["authenticated"] = True
    response = JSONResponse(payload)
    set_session_cookies(response, cookie, csrf)
    return response


@router.post("/auth/logout")
def logout(request: Request):
    session = current_user(request)
    check_csrf(request, session)
    security.destroy_session(session["session"]["id"], session["user"]["id"])
    from fastapi.responses import JSONResponse
    response = JSONResponse({"ok": True})
    clear_session_cookies(response)
    return response


@router.post("/lang/{code}")
def set_lang(request: Request, code: str):
    from fastapi.responses import JSONResponse
    response = JSONResponse({"ok": True, "lang": code if code in i18n.LANGS else lang_of(request)})
    if code in i18n.LANGS:
        response.set_cookie("ll_lang", code, max_age=60 * 60 * 24 * 365, samesite="lax", path="/")
    return response
