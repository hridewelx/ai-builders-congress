"""Dashboard, lot list and lot creation."""
from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ...core import db
from ...services import review as service
from ...services import vision
from ..deps import assert_csrf, require_role, require_user
from ..pages import page
from ..stats import demo_stats, load_model_card

router = APIRouter(tags=["lots"])


def lot_cards(request: Request, state: str = "", outcome: str = "", q: str = ""):
    rows = db.q("SELECT l.*, b.name AS buyer_name, p.name AS product_name"
                " FROM lot l JOIN buyer b ON b.id=l.buyer_id JOIN product p ON p.id=l.product_id"
                " ORDER BY l.id DESC")
    out = []
    for r in rows:
        d = service.latest_decision(r["id"])
        ov = service.override_for(d["id"]) if d else None
        final = service.final_disposition(d, ov) if d else None
        p = service.progress(r["id"])
        card = {**dict(r), "decision": dict(d) if d else None, "override": ov, "final": final,
                "progress": p}
        if state and card["status"] != state:
            continue
        if outcome and final != outcome:
            continue
        if q:
            hay = f"{card['lot_code']} {card['buyer_name']} {card['product_name']} {card['color']}".lower()
            if q.lower() not in hay:
                continue
        out.append(card)
    return out


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    require_user(request)
    cards = lot_cards(request)
    c = service.counters()
    card = load_model_card()
    return page(request, "dashboard.html", active="dashboard", cards=cards[:6], counters=c,
                model=vision.MODEL_NAME, model_ok=card.get("self_test", {}).get("passed", False),
                stats=demo_stats())


@router.get("/lots", response_class=HTMLResponse)
def lots_page(request: Request):
    require_user(request)
    state = request.query_params.get("state", "")
    outcome = request.query_params.get("outcome", "")
    q = request.query_params.get("q", "")
    cards = lot_cards(request, state, outcome, q)
    return page(request, "lots.html", active="lots", cards=cards, state=state, outcome=outcome, q=q)


@router.get("/lots/new", response_class=HTMLResponse)
def new_lot_page(request: Request):
    require_role(request, "inspector", "supervisor")
    buyers = db.q("SELECT * FROM buyer ORDER BY name")
    products = db.q("SELECT * FROM product ORDER BY name")
    return page(request, "lot_new.html", active="lots", buyers=buyers, products=products)


@router.post("/lots/new")
def new_lot(request: Request, csrf: str = Form(""), lot_code: str = Form(""), buyer_id: int = Form(0),
            product_id: int = Form(0), color: str = Form(""), lot_size: int = Form(0),
            selection_method: str = Form("self-declared random")):
    s = require_role(request, "inspector", "supervisor")
    assert_csrf(request, s, csrf)
    code = lot_code.strip().upper()
    if not code or lot_size < 1 or not buyer_id or not product_id:
        return RedirectResponse("/lots/new?err=invalid", status_code=303)
    if db.one("SELECT id FROM lot WHERE lot_code=?", (code,)):
        return RedirectResponse("/lots/new?err=exists", status_code=303)
    lot_id = db.x("INSERT INTO lot(organization_id,lot_code,product_id,buyer_id,color,lot_size,status,"
                  "critical_nonvisual_status,selection_method,created_by,created_at)"
                  " VALUES (1,?,?,?,?,?, 'open','pending',?,?,?)",
                  (code, product_id, buyer_id, color.strip(), lot_size, selection_method.strip(),
                   s["user"]["id"], db.now()))
    db.audit(s["user"]["id"], s["user"]["display_name"], "lot.created", "lot", lot_id,
             after={"lot_code": code, "lot_size": lot_size})
    return RedirectResponse(f"/lots/{lot_id}?ok=saved", status_code=303)
