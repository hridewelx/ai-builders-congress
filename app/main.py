"""Lotline — knitwear lot acceptance you can defend.

Application factory. The rule of the product is enforced in `app/domain/engine.py`:
AI proposes defects, a human confirms them, and the deterministic engine decides.
This module only wires configuration, error handling and HTTP routes together.
"""
from __future__ import annotations

import logging
import re
import time

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from .api import router as api_router
from .config import APP_TITLE, STATIC_DIR
from .core import db, metrics
from .services import detector, inference, seed, vision
from .web import errors
from .web.routes import admin, auth, capture, dashboard, decisions, lots, reports, review, system

log = logging.getLogger("lotline")


class SensitiveParamFilter(logging.Filter):
    """Mask sensitive query string credentials like session_token from server logs."""

    _pattern = re.compile(r"(session_token=)[^&\s'\"]+", re.IGNORECASE)

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self._pattern.sub(r"\1[REDACTED]", record.msg)
        if record.args:
            cleaned_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    cleaned_args.append(self._pattern.sub(r"\1[REDACTED]", arg))
                else:
                    cleaned_args.append(arg)
            record.args = tuple(cleaned_args)
        return True


def create_app() -> FastAPI:
    """Build the ASGI application."""
    # Install sensitive credential filter on access loggers
    param_filter = SensitiveParamFilter()
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error", "lotline"):
        l = logging.getLogger(name)
        if not any(isinstance(f, SensitiveParamFilter) for f in l.filters):
            l.addFilter(param_filter)

    app = FastAPI(title=APP_TITLE, docs_url=None, redoc_url=None)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    errors.register(app)

    app.include_router(api_router)

    for module in (auth, dashboard, lots, capture, review, decisions, reports, admin, system):
        app.include_router(module.router)

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        started = time.perf_counter()
        metrics.begin()
        try:
            response = await call_next(request)
        except Exception:
            metrics.observe(request.method, 500, time.perf_counter() - started)
            raise
        finally:
            metrics.end()
        elapsed_ms = (time.perf_counter() - started) * 1000
        metrics.observe(request.method, response.status_code, elapsed_ms / 1000)
        log.info("%s %s -> %s (%.0f ms)", request.method, request.url.path,
                 response.status_code, elapsed_ms)
        return response

    @app.on_event("startup")
    def _startup() -> None:
        detector.require_available()
        db.init()
        seed.run()
        inference.start()
        try:
            vision._train_or_load()
        except Exception:  # a missing model must never stop the app from serving
            log.exception("vision model could not be loaded; manual review stays available")

    return app


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
app = create_app()
