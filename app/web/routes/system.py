"""Health checks and the public explainer page."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from ...core import db, metrics
from ...services import detector, inference
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


@router.get("/metrics")
def metrics_page():
    """Conventional ops path; the JSON API exposes the same snapshot at /api/metrics."""
    payload = metrics.snapshot()
    payload["inference"] = {
        "mode": inference.mode(),
        "queued": db.one("SELECT COUNT(*) AS n FROM inference_job WHERE status='queued'")["n"],
        "running": db.one("SELECT COUNT(*) AS n FROM inference_job WHERE status='running'")["n"],
        "failed": db.one("SELECT COUNT(*) AS n FROM inference_job WHERE status='failed'")["n"],
    }
    return JSONResponse(payload)


@router.get("/readyz")
def readyz():
    db.one("SELECT 1")
    backend = detector.active_backend()
    trained = backend == "onnx"
    # Report only what is actually scoring. A deployed build without the ONNX
    # package must not look like the trained network is live.
    return JSONResponse({
        "ready": True,
        "detector": backend,
        "model": detector.MODEL_NAME if trained else None,
        "weights_loaded": trained,
        "threshold": detector.review_threshold(),
        "note": "trained detector is serving" if trained else
                "numpy baseline is serving; no trained weights in this build",
    })
