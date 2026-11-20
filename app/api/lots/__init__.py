"""Lot API routes, split by job and mounted as one router.

Registration order matters: /lots/new must precede /lots/{lot_id}.
"""
from __future__ import annotations

from fastapi import APIRouter

from . import capture, dashboard, plan, review
from .shared import _ensure_write

router = APIRouter()

for module in (dashboard, plan, capture, review):
    router.include_router(module.router)

from .capture import tunnel_status

__all__ = ["router", "_ensure_write", "tunnel_status"]
