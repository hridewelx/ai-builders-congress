"""Exception handlers shared by the whole application."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse

from .deps import Denied
from .pages import ctx, templates


def register(app: FastAPI) -> None:
    """Attach the HTML error handlers to an application instance."""

    @app.exception_handler(Denied)
    async def denied_handler(request: Request, exc: Denied):
        if exc.status == 401:
            return RedirectResponse("/login", status_code=303,
                                    headers={"Cache-Control": "no-store"})
        response = templates.TemplateResponse(
            request, "error.html", ctx(request, code=exc.status, message=exc.message),
            status_code=exc.status,
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(404)
    async def notfound(request: Request, exc):
        response = templates.TemplateResponse(
            request, "error.html", ctx(request, code=404, message="not_found"), status_code=404,
        )
        response.headers["Cache-Control"] = "no-store"
        return response
