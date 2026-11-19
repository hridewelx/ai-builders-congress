"""Request dependencies for the JSON API: sessions, roles and CSRF."""
from __future__ import annotations

from fastapi import HTTPException, Request, Response

from ..core import db, security


def session_of(request: Request):
    return security.current_session(request.cookies.get(security.COOKIE))


def current_user(request: Request) -> dict:
    s = session_of(request)
    if not s:
        raise HTTPException(status_code=401, detail="login_required")
    return s


def role_required(s: dict, *roles: str) -> dict:
    if s["user"]["role"] not in roles:
        raise HTTPException(status_code=403, detail="not_allowed")
    return s


def check_csrf(request: Request, s: dict) -> None:
    """Accept the token from the double-submit cookie or the API header."""
    token = request.headers.get("x-csrf-token") or request.cookies.get("ll_csrf") or ""
    if not security.check_csrf(s, token):
        raise HTTPException(status_code=403, detail="csrf")
    origin = request.headers.get("origin")
    if origin:
        host = request.headers.get("host", "")
        if origin.split("://")[-1] != host:
            raise HTTPException(status_code=403, detail="csrf")


def auth_response_payload(s: dict) -> dict:
    return {"user": s["user"], "csrf": s["session"]["csrf"]}


def set_session_cookies(response: Response, cookie: str, csrf: str) -> None:
    response.set_cookie(security.COOKIE, cookie, httponly=True, samesite="strict",
                        secure=security.COOKIE_SECURE, max_age=security.SESSION_ABSOLUTE,
                        path="/")
    response.set_cookie("ll_csrf", csrf, httponly=False, samesite="strict",
                        secure=security.COOKIE_SECURE, max_age=security.SESSION_ABSOLUTE,
                        path="/")


def clear_session_cookies(response: Response) -> None:
    response.delete_cookie(security.COOKIE, path="/")
    response.delete_cookie("ll_csrf", path="/")


def audit_denied(request: Request, s: dict) -> None:
    db.audit(
        s["user"]["id"],
        s["user"]["display_name"],
        "request.denied",
        "route",
        request.url.path,
        after={"role": s["user"]["role"]},
        ip=request.client.host if request.client else None,
    )
