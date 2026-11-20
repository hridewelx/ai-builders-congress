"""Request dependencies: sessions, roles, CSRF and write permissions."""
from __future__ import annotations

from fastapi import Request

from ..core import db, security


class Denied(Exception):
    """Raised when a request is not allowed; mapped to a redirect or error page."""

    def __init__(self, status: int = 403, message: str = "not_allowed"):
        self.status = status
        self.message = message
        super().__init__(message)


def sess_of(request: Request):
    """Return the server-side session for this request, or None."""
    return security.current_session(request.cookies.get(security.COOKIE))


def require_user(request: Request):
    s = sess_of(request)
    if not s:
        raise Denied(401, "login_required")
    return s


def organization_id(s: dict) -> int:
    return int(s["user"]["organization_id"])


def lot_required(s: dict, lot_id: int):
    """A lot owned by the caller's organisation, or a 404 that reveals nothing."""
    from ..services import review as service
    lot = service.lot(lot_id, organization_id(s))
    if not lot:
        raise Denied(404, "not_found")
    return lot


def image_required(s: dict, image_id: int):
    image = db.one("SELECT * FROM image WHERE id=?", (image_id,))
    if not image or not service_lot_in_org(s, image["lot_id"]):
        raise Denied(404, "not_found")
    return image


def service_lot_in_org(s: dict, lot_id: int):
    from ..services import review as service
    return service.lot(lot_id, organization_id(s))


def require_role(request: Request, *roles: str):
    s = require_user(request)
    if s["user"]["role"] not in roles:
        db.audit(
            s["user"]["id"],
            s["user"]["display_name"],
            "request.denied",
            "route",
            request.url.path,
            after={"role": s["user"]["role"]},
            ip=request.client.host if request.client else None,
        )
        raise Denied(403, "not_allowed")
    return s


def assert_csrf(request: Request, s: dict, token: str | None) -> None:
    """Double-submit CSRF check plus an Origin/Host comparison."""
    if not security.check_csrf(s, token):
        raise Denied(403, "csrf")
    origin = request.headers.get("origin")
    if origin:
        host = request.headers.get("host", "")
        if origin.split("://")[-1] != host:
            raise Denied(403, "csrf")


def can_write_lot(s: dict, lot) -> bool:
    """Supervisors write every lot; an inspector writes only lots they created."""
    role = s["user"]["role"]
    return role == "supervisor" or (role == "inspector" and lot["created_by"] == s["user"]["id"])


def ensure_write(request: Request, s: dict, lot_row) -> None:
    """Reject writes to lots the caller may not change, or that are locked."""
    if not can_write_lot(s, lot_row):
        raise Denied(403, "not_allowed")
    if lot_row["status"] in ("decided", "archived"):
        raise Denied(403, "locked")
