"""Template environment and the per-request template context."""
from __future__ import annotations

import json

import jinja2
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from .. import i18n
from ..config import TEMPLATES_DIR, ZONES
from ..core import security
from ..services import oauth

templates = Jinja2Templates(directory=TEMPLATES_DIR)
templates.env.filters["fromjson"] = json.loads


@jinja2.pass_context
def num_filter(context: dict, value: object) -> str:
    lang = context.get("lang", "en")
    return i18n.format_num(value, lang)


@jinja2.pass_context
def num_grouped_filter(context: dict, value: object) -> str:
    lang = context.get("lang", "en")
    return i18n.format_grouped_num(value, lang)


@jinja2.pass_context
def dt_local_filter(context: dict, value: object) -> str:
    lang = context.get("lang", "en")
    return i18n.format_datetime(value, lang)


templates.env.filters["num"] = num_filter
templates.env.filters["num_grouped"] = num_grouped_filter
templates.env.filters["dt_local"] = dt_local_filter


def lang_of(request: Request) -> str:
    """Resolve the UI language from the cookie, defaulting to Bangla."""
    value = request.cookies.get("ll_lang", "bn")
    return value if value in i18n.LANGS else "bn"


def ctx(request: Request, **kw) -> dict:
    """Build the base template context every screen receives."""
    session = security.current_session(request.cookies.get(security.COOKIE))
    lang = lang_of(request)
    user = session["user"] if session else None
    catalog_buyers = []
    catalog_products = []
    last_selftest = None
    try:
        from ..core import db
        catalog_buyers = [dict(r) for r in db.q("SELECT * FROM buyer ORDER BY id")]
        catalog_products = [dict(r) for r in db.q("SELECT * FROM product ORDER BY id")]
        selftest_row = db.one("SELECT * FROM model_selftest ORDER BY id DESC LIMIT 1")
        last_selftest = dict(selftest_row) if selftest_row else None
    except Exception:
        pass

    context = {
        "request": request,
        "user": user,
        "csrf": session["session"]["csrf"] if session else "",
        "lang": lang,
        "tr": lambda key, **kw: i18n.t(key, lang, **kw),
        "num": lambda val: i18n.format_num(val, lang),
        "num_grouped": lambda val: i18n.format_grouped_num(val, lang),
        "event_label": lambda action: i18n.event_label(action, lang),
        "reason": lambda code: i18n.reason_text(code, lang),
        "active": "",
        "ok": request.query_params.get("ok"),
        "err": request.query_params.get("err"),
        "roles": {"admin": True, "inspector": True, "supervisor": True},
        "zones": ZONES,
        "catalog_buyers": catalog_buyers,
        "catalog_products": catalog_products,
        "last_selftest": last_selftest,
        "github_oauth": oauth.enabled(),
    }
    context.update(kw)
    return context


def page(request: Request, name: str, status_code: int = 200, **kw) -> HTMLResponse:
    """Render a Jinja template with the shared context.

    HTML is never cached: a cached login page or a cached "redirect to login"
    makes an OAuth callback appear to have done nothing until a refresh.
    """
    response = templates.TemplateResponse(request, name, ctx(request, **kw),
                                          status_code=status_code)
    response.headers["Cache-Control"] = "no-store"
    return response
