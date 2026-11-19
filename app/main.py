"""Lotline — knitwear lot acceptance you can defend.

Application factory. The rule of the product is enforced in `app/domain/engine.py`:
AI proposes defects, a human confirms them, and the deterministic engine decides.
This module only wires configuration, error handling and HTTP routes together.
"""
from __future__ import annotations

import logging
import time

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from .config import APP_TITLE, STATIC_DIR
from .core import db
from .services import detector, seed, vision
from .web import errors
from .web.routes import admin, auth, capture, dashboard, decisions, lots, reports, review, system

log = logging.getLogger("lotline")


def create_app() -> FastAPI:
    """Build the ASGI application."""
    app = FastAPI(title=APP_TITLE, docs_url=None, redoc_url=None)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    errors.register(app)

    for module in (auth, dashboard, lots, capture, review, decisions, reports, admin, system):
        app.include_router(module.router)

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        started = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started) * 1000
        log.info("%s %s -> %s (%.0f ms)", request.method, request.url.path,
                 response.status_code, elapsed_ms)
        return response

    @app.on_event("startup")
    def _startup() -> None:
        detector.require_available()
        db.init()
        seed.run()
        try:
            vision._train_or_load()
        except Exception:  # a missing model must never stop the app from serving
            log.exception("vision model could not be loaded; manual review stays available")

    return app


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
app = create_app()
