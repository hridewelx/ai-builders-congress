"""Health checks and the public explainer page."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from ...core import db
from ...services import detector
from ..deps import require_user
from ..pages import page
from ..stats import demo_stats, load_model_card

router = APIRouter(tags=["system"])


@router.get("/how", response_class=HTMLResponse)
def how_page(request: Request):
    require_user(request)
    card = load_model_card()
    return page(request, "how.html", active="how", card=card, stats=demo_stats())


@router.get("/healthz")
def healthz():
    return JSONResponse({"ok": True})


@router.get("/readyz")
def readyz():
    db.one("SELECT 1")
    backend = detector.active_backend()
    return JSONResponse({"ready": True, "detector": backend, "model": detector.MODEL_NAME})
