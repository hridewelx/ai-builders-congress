"""Role, ownership and organisation rules shared by the API and web routes."""
from __future__ import annotations

GUEST_EMAIL = "guest@lotline.demo"


def organization_id(session: dict) -> int:
    return int(session["user"]["organization_id"])


def is_guest(session: dict | None) -> bool:
    """The guest account reads the staged demo and changes nothing.

    The session holds a sqlite3.Row, which supports [] but not .get().
    """
    try:
        user = session["user"] if session else None
        email = user["email"] if user else ""
    except (KeyError, IndexError, TypeError):
        return False
    return (email or "").strip().lower() == GUEST_EMAIL


def can_write_lot(session: dict, lot) -> bool:
    """Supervisors write every lot; an inspector writes only lots they created.

    The guest never writes, whatever the lot or the owner.
    """
    if is_guest(session):
        return False
    role = session["user"]["role"]
    return role == "supervisor" or (role == "inspector" and lot["created_by"] == session["user"]["id"])


def lot_for(session: dict, lot_id: int):
    """A lot the caller's organisation owns, or None. Never leaks another tenant's lot."""
    from ..services import review as service
    return service.lot(lot_id, organization_id(session))


def image_for(session: dict, image_id: int):
    """An image whose lot belongs to the caller's organisation, or None."""
    from ..core import db
    image = db.one("SELECT * FROM image WHERE id=?", (image_id,))
    if not image:
        return None
    return image if lot_for(session, image["lot_id"]) else None


def decision_for(session: dict, decision_id: int):
    from ..core import db
    decision = db.one("SELECT * FROM decision WHERE id=?", (decision_id,))
    if not decision or not lot_for(session, decision["lot_id"]):
        return None
    return decision


def override_for(session: dict, override_id: int):
    from ..core import db
    override = db.one("SELECT * FROM override WHERE id=?", (override_id,))
    if not override or not decision_for(session, override["decision_id"]):
        return None
    return override
