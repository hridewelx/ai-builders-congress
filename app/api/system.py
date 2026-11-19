"""Health, optimizer state and security-gated image bytes."""
from __future__ import annotations

import os

import numpy as np
from fastapi import APIRouter, HTTPException, Request, Response
from PIL import Image

from ..core import db, metrics
from ..core.permissions import image_for
from ..services import detector, inference
from .deps import current_user

router = APIRouter(tags=["system"])


@router.get("/metrics")
def metrics_endpoint():
    """Latency, status and error counters for the running process."""
    payload = metrics.snapshot()
    payload["inference"] = {
        "mode": inference.mode(),
        "queued": db.one("SELECT COUNT(*) AS n FROM inference_job WHERE status='queued'")["n"],
        "running": db.one("SELECT COUNT(*) AS n FROM inference_job WHERE status='running'")["n"],
        "failed": db.one("SELECT COUNT(*) AS n FROM inference_job WHERE status='failed'")["n"],
    }
    return payload


@router.get("/health")
def health():
    db.one("SELECT 1")
    backend = detector.active_backend()
    trained = backend == "onnx"
    return {
        "ready": True,
        "detector": backend,
        "model": detector.MODEL_NAME if trained else None,
        "weights_loaded": trained,
        "threshold": detector.DEFAULT_THRESHOLD,
        "note": ("trained detector is serving" if trained
                 else "numpy baseline is serving; no trained weights in this build"),
    }


@router.get("/images/{image_id}")
def image_bytes(request: Request, image_id: int):
    session = current_user(request)
    if session["user"]["role"] == "admin":
        raise HTTPException(status_code=403, detail="not_allowed")
    image = image_for(session, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="not_found")
    from ..services import review as service
    path = os.path.join(service.STORE, image["stored_name"])
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="not_found")
    with open(path, "rb") as handle:
        data = handle.read()
    return Response(data, media_type="image/jpeg",
                    headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


@router.get("/images/{image_id}/heat")
def image_heat(request: Request, image_id: int):
    session = current_user(request)
    if session["user"]["role"] == "admin":
        raise HTTPException(status_code=403, detail="not_allowed")
    image = image_for(session, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="not_found")
    from ..services import review as service
    with Image.open(os.path.join(service.STORE, image["stored_name"])) as handle:
        result = detector.detect(np.array(handle.convert("RGB")))
    return Response(result["heat_png"], media_type="image/jpeg",
                    headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})
