"""Role and ownership rules shared by the API."""
from __future__ import annotations


def can_write_lot(session: dict, lot) -> bool:
    """Supervisors write every lot; an inspector writes only lots they created."""
    role = session["user"]["role"]
    return role == "supervisor" or (role == "inspector" and lot["created_by"] == session["user"]["id"])
