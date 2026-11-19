"""JSON API consumed by the React single-page application.

The browser only talks to FastAPI. Pages are rendered in the client; every
decision, severity lookup and permission check still happens on the server.
"""
from __future__ import annotations

from fastapi import APIRouter

from . import admin, auth, decisions, lots, review, system

router = APIRouter(prefix="/api")
router.include_router(auth.router)
router.include_router(system.router)
router.include_router(lots.router)
router.include_router(review.router)
router.include_router(decisions.router)
router.include_router(admin.router)
