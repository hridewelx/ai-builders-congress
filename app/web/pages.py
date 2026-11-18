"""Template environment and the per-request template context."""
from __future__ import annotations

import json

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from .. import i18n
from ..config import TEMPLATES_DIR, ZONES
from ..core import security

templates = Jinja2Templates(directory=TEMPLATES_DIR)
templates.env.filters["fromjson"] = json.loads


def lang_of(request: Request) -> str:
    """Resolve the UI language from the cookie, defaulting to English."""
    value = request.cookies.get("ll_lang", "en")
    return value if value in i18n.LANGS else "en"


def ctx(request: Request, **kw) -> dict:
    """Build the base template context every screen receives."""
    session = security.current_session(request.cookies.get(security.COOKIE))
    lang = lang_of(request)
    context = {
        "request": request,
        "user": session["user"] if session else None,
        "csrf": session["session"]["csrf"] if session else "",
        "lang": lang,
        "tr": lambda key: i18n.t(key, lang),
        "reason": lambda code: i18n.reason_text(code, lang),
        "active": "",
        "ok": request.query_params.get("ok"),
        "err": request.query_params.get("err"),
        "roles": {"admin": True, "inspector": True, "supervisor": True},
        "zones": ZONES,
    }
    context.update(kw)
    return context


def page(request: Request, name: str, status_code: int = 200, **kw) -> HTMLResponse:
    """Render a Jinja template with the shared context."""
    return templates.TemplateResponse(request, name, ctx(request, **kw), status_code=status_code)
