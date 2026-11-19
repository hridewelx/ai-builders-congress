"""Dashboard, the lot list, and registering a new lot."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ...core import db
from ...core.permissions import organization_id
from ...services import review as service
from ...services.stats import demo_stats
from ..deps import check_csrf, current_user, role_required
from ..serializers import catalogs, clean, lot_cards, model_info

router = APIRouter(tags=["lots"])

@router.get("/dashboard")
def dashboard(request: Request):
    session = current_user(request)
    cards = lot_cards(organization_id(session))
    return {
        "cards": cards[:4],
        "counters": service.counters(),
        "stats": demo_stats(),
        "model": model_info(),
        "user": clean(session["user"]),
    }


@router.get("/lots")
def lots(request: Request, state: str = "", outcome: str = "", q: str = ""):
    session = current_user(request)
    return {
        "cards": lot_cards(organization_id(session), state, outcome, q),
        "state": state, "outcome": outcome, "q": q,
        "counters": service.counters(),
    }


@router.get("/lots/new")
def new_lot_form(request: Request):
    session = current_user(request)
    role_required(session, "inspector", "supervisor")
    return catalogs(organization_id(session))


@router.post("/lots")
async def create_lot(request: Request):
    session = role_required(current_user(request), "inspector", "supervisor")
    check_csrf(request, session)
    data = await request.json()
    code = str(data.get("lot_code", "")).strip().upper()
    buyer_id = int(data.get("buyer_id") or 0)
    product_id = int(data.get("product_id") or 0)
    lot_size = int(data.get("lot_size") or 0)
    color = str(data.get("color", "")).strip()
    selection = str(data.get("selection_method", "self-declared random")).strip()
    if not code or lot_size < 1 or not buyer_id or not product_id:
        raise HTTPException(status_code=422, detail="invalid")
    org = organization_id(session)
    if not db.one("SELECT id FROM buyer WHERE id=? AND organization_id=?", (buyer_id, org)):
        raise HTTPException(status_code=422, detail="invalid")
    if not db.one("SELECT id FROM product WHERE id=? AND organization_id=?", (product_id, org)):
        raise HTTPException(status_code=422, detail="invalid")
    if db.one("SELECT id FROM lot WHERE organization_id=? AND lot_code=?", (org, code)):
        raise HTTPException(status_code=409, detail="exists")
    lot_id = db.x(
        "INSERT INTO lot(organization_id,lot_code,product_id,buyer_id,color,lot_size,status,"
        "critical_nonvisual_status,selection_method,created_by,created_at)"
        " VALUES (?,?,?,?,?,?, 'open','pending',?,?,?)",
        (org, code, product_id, buyer_id, color, lot_size, selection,
         session["user"]["id"], db.now()))
    db.audit(session["user"]["id"], session["user"]["display_name"], "lot.created", "lot", lot_id,
             after={"lot_code": code, "lot_size": lot_size})
    return {"ok": True, "id": lot_id}
