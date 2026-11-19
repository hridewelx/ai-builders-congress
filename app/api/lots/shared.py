"""Small guards and lookups shared by the lot routes."""
from __future__ import annotations

from fastapi import HTTPException, Request

from ..deps import audit_denied


def _lang(request: Request) -> str:
    value = request.cookies.get("ll_lang", "bn")
    return value if value in ("en", "bn") else "bn"



def _ensure_write(request: Request, session: dict, lot) -> None:
    from ...core.permissions import can_write_lot
    if not lot or not can_write_lot(session, lot):
        audit_denied(request, session)
        raise HTTPException(status_code=403, detail="not_allowed")
    if lot["status"] in ("decided", "archived"):
        raise HTTPException(status_code=403, detail="locked")


def _lot_or_404(lot_id: int, session: dict):
    from ...core.permissions import lot_for
    lot = lot_for(session, lot_id)
    if not lot:
        raise HTTPException(status_code=404, detail="not_found")
    return lot



def _float(value):
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None
