"""Authentication, demo access, language and the app bootstrap payload."""
from __future__ import annotations

import logging
import time

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from .. import i18n
from ..config import DEMO_LOGIN
from ..core import db, security
from ..services import google_oauth, oauth
from .deps import check_csrf, clear_session_cookies, current_user, session_of, set_session_cookies
from .serializers import bootstrap, catalogs, clean, model_info

router = APIRouter(tags=["auth"])
log = logging.getLogger("lotline.oauth")


def lang_of(request: Request) -> str:
    value = request.cookies.get("ll_lang", "bn")
    return value if value in i18n.LANGS else "bn"


def bootstrap_payload(request: Request) -> dict:
    session = session_of(request)
    payload = bootstrap()
    from ..core import permissions
    payload.update({
        "authenticated": bool(session),
        "is_guest": permissions.is_guest(session),
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


def _oauth_failure(request: Request | None = None, message: str = "oauth") -> RedirectResponse:
    # A duplicate/preloaded callback can arrive after the first one already
    # issued a session. Never turn a valid login into an error page.
    if request is not None and session_of(request):
        return RedirectResponse("/", status_code=303, headers={"Cache-Control": "no-store"})
    response = RedirectResponse(f"/login?err={message}", status_code=303,
                                headers={"Cache-Control": "no-store"})
    response.delete_cookie(oauth.STATE_COOKIE, path="/")
    response.delete_cookie(google_oauth.STATE_COOKIE, path="/")
    return response


def _oauth_start(request: Request, provider, label: str) -> RedirectResponse:
    """Send the browser to an OAuth provider with a signed state cookie."""
    if not provider.enabled():
        raise HTTPException(status_code=404, detail="not_configured")
    state = provider.new_state()
    response = RedirectResponse(provider.authorize_url(state, request), status_code=303,
                                headers={"Cache-Control": "no-store"})
    response.set_cookie(
        provider.STATE_COOKIE, state, httponly=True, samesite="lax", path="/",
        secure=security.COOKIE_SECURE, max_age=provider.STATE_TTL)
    log.info("Starting %s OAuth login", label)
    return response


def _oauth_callback(request: Request, provider, label: str,
                    code: str, state: str, error: str) -> RedirectResponse:
    """Finish an OAuth dance and issue the same session a password login would."""
    if not provider.enabled():
        raise HTTPException(status_code=404, detail="not_configured")
    if session_of(request):
        return RedirectResponse("/", status_code=303, headers={"Cache-Control": "no-store"})
    if error or not code:
        log.warning("%s OAuth callback rejected: %s", label, error or "no code")
        return _oauth_failure(request)
    if not provider.verify_state(request.cookies.get(provider.STATE_COOKIE), state):
        log.warning("%s OAuth callback rejected: state mismatch", label)
        return _oauth_failure(request)
    try:
        token = provider.exchange_code(code, request)
        email, display_name, login = provider.fetch_identity(token)
        ip = request.client.host if request.client else ""
        user = provider.login_or_create(email, display_name, login, ip=ip)
        provider.remember_code(code)
    except provider.OAuthError as exc:
        if provider.completed_code(code):
            log.info("%s OAuth callback replayed after a successful login", label)
            return RedirectResponse("/", status_code=303, headers={"Cache-Control": "no-store"})
        log.warning("%s OAuth callback rejected: %s", label, exc)
        return _oauth_failure(request)
    cookie, csrf = security.create_session(user["id"], ip)
    response = RedirectResponse("/", status_code=303, headers={"Cache-Control": "no-store"})
    set_session_cookies(response, cookie, csrf, samesite="lax")
    response.delete_cookie(provider.STATE_COOKIE, path="/")
    return response


@router.get("/auth/github")
def github_login(request: Request):
    """Start the GitHub OAuth dance for either UI (link/redirect)."""
    return _oauth_start(request, oauth, "GitHub")


@router.get("/auth/github/callback", name="github_callback")
def github_callback(request: Request, code: str = "", state: str = "", error: str = ""):
    """Finish the GitHub dance and issue the same session a password login would."""
    return _oauth_callback(request, oauth, "GitHub", code, state, error)


@router.get("/auth/google")
def google_login(request: Request):
    """Start the Google OAuth dance for either UI (link/redirect)."""
    return _oauth_start(request, google_oauth, "Google")


@router.get("/auth/google/callback", name="google_callback")
def google_callback(request: Request, code: str = "", state: str = "", error: str = ""):
    """Finish the Google dance and issue the same session a password login would."""
    return _oauth_callback(request, google_oauth, "Google", code, state, error)


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
              "admin": "admin@lotline.demo",
              "guest": "guest@lotline.demo"}
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
