"""Request dependencies for the JSON API: sessions, roles and CSRF."""
from __future__ import annotations

from fastapi import HTTPException, Request, Response

from ..core import db, security


def session_of(request: Request):
    token = request.cookies.get(security.COOKIE) or request.query_params.get("session_token")
    if not token:
        auth = request.headers.get("authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:].strip()
    return security.current_session(token)


def current_user(request: Request) -> dict:
    s = session_of(request)
    if not s:
        raise HTTPException(status_code=401, detail="login_required")
    return s


def role_required(s: dict, *roles: str) -> dict:
    from ..core.permissions import is_guest
    if is_guest(s) or s["user"]["role"] not in roles:
        raise HTTPException(status_code=403, detail="not_allowed")
    return s


def check_csrf(request: Request, s: dict) -> None:
    """Accept the token from the double-submit cookie or the API header."""
    token = request.headers.get("x-csrf-token") or request.cookies.get("ll_csrf") or ""
    if not security.check_csrf(s, token):
        raise HTTPException(status_code=403, detail="csrf")
    origin = request.headers.get("origin")
    if not origin:
        return

    origin_host = origin.split("://")[-1].split(":")[0].strip().lower()
    host = request.headers.get("host", "").split(":")[0].strip().lower()

    if origin_host == host:
        return

    client_ip = request.client.host if request.client else ""
    if client_ip in ("127.0.0.1", "::1", "localhost", "testclient"):
        from ..config import get_active_tunnel_host

        expected_tunnel_host = get_active_tunnel_host()
        fwd_host = request.headers.get("x-forwarded-host", "").split(":")[0].strip().lower()
        fwd_proto = request.headers.get("x-forwarded-proto", "").strip().lower()

        if (
            expected_tunnel_host
            and fwd_host == expected_tunnel_host
            and origin_host == expected_tunnel_host
            and fwd_proto == "https"
        ):
            return

    raise HTTPException(status_code=403, detail="csrf")


def auth_response_payload(s: dict) -> dict:
    return {"user": s["user"], "csrf": s["session"]["csrf"]}


def set_session_cookies(response: Response, cookie: str, csrf: str,
                        samesite: str = "strict") -> None:
    """Issue the session pair. OAuth callbacks must use ``lax``.

    A session cookie set in a response to GitHub's cross-site redirect is not
    reliably sent on the immediately following navigation when it is marked
    Strict, which looks like "login again until you refresh".
    """
    response.set_cookie(security.COOKIE, cookie, httponly=True, samesite=samesite,
                        secure=security.COOKIE_SECURE, max_age=security.SESSION_ABSOLUTE,
                        path="/")
    response.set_cookie("ll_csrf", csrf, httponly=False, samesite=samesite,
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
