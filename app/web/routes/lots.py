"""Single-lot cockpit: overview, sampling plan, non-visual check."""
from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ...core import db
from ...domain import engine
from ...services import review as service
from ..deps import Denied, assert_csrf, can_write_lot, require_role, require_user
from ..pages import page

router = APIRouter(tags=["lots"])


@router.get("/lots/{lot_id}", response_class=HTMLResponse)
def lot_page(request: Request, lot_id: int):
    s = require_user(request)
    L = service.lot(lot_id)
    if not L:
        raise Denied(404, "not_found")
    plan = service.active_plan(lot_id)
    p = service.progress(lot_id)
    units = service.units_with_views(lot_id)
    d = service.latest_decision(lot_id)
    ov = service.override_for(d["id"]) if d else None
    hist = db.q("SELECT * FROM decision WHERE lot_id=? ORDER BY sequence DESC", (lot_id,))
    audit = service.timeline(lot_id)
    is_admin = s["user"]["role"] == "admin"
    return page(request, "lot.html", active="lots", lot=L, plan=plan, plan_d=service.plan_dict(plan),
                progress=p, units=units, decision=d, override=ov,
                final=service.final_disposition(d, ov) if d else None, history=hist, audit=audit,
                is_admin=is_admin, can_write=(not is_admin and can_write_lot(s, L) and L["status"] != "decided"))


@router.get("/lots/{lot_id}/plan", response_class=HTMLResponse)
def plan_page(request: Request, lot_id: int):
    s = require_user(request)
    L = service.lot(lot_id)
    if not L:
        raise Denied(404, "not_found")
    plan = service.active_plan(lot_id)
    return page(request, "plan.html", active="lots", lot=L, plan=plan, plan_d=service.plan_dict(plan),
                is_supervisor=s["user"]["role"] == "supervisor",
                locked=L["status"] == "decided")


@router.post("/lots/{lot_id}/plan")
def plan_save(request: Request, lot_id: int, csrf: str = Form(""), n: int = Form(0),
              counting_mode: str = Form(""), critical_ac: int = Form(-1), critical_re: int = Form(-1),
              major_ac: int = Form(-1), major_re: int = Form(-1), minor_ac: int = Form(-1),
              minor_re: int = Form(-1), critical_aql: str = Form(""), major_aql: str = Form(""),
              minor_aql: str = Form(""), source_edition: str = Form(""), source_reference: str = Form("")):
    s = require_role(request, "supervisor")
    assert_csrf(request, s, csrf)
    L = service.lot(lot_id)
    if not L:
        raise Denied(404, "not_found")
    if L["status"] == "decided":
        raise Denied(403, "locked")
    plan = {"n": n, "counting_mode": counting_mode,
            "critical": {"ac": critical_ac, "re": critical_re},
            "major": {"ac": major_ac, "re": major_re},
            "minor": {"ac": minor_ac, "re": minor_re}}
    errs = engine.validate_plan(plan)
    if errs:
        return RedirectResponse(f"/lots/{lot_id}/plan?err=invalid", status_code=303)
    prev = service.active_plan(lot_id)
    ver = (prev["version"] + 1) if prev else 1
    db.x("INSERT INTO plan(lot_id,version,n,counting_mode,critical_aql,critical_ac,critical_re,"
         "major_aql,major_ac,major_re,minor_aql,minor_ac,minor_re,inspection_level,sampling_type,"
         "source_edition,source_reference,is_demo,entered_by,created_at)"
         " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'II','single',?,?,0,?,?)",
         (lot_id, ver, n, counting_mode, _f(critical_aql), critical_ac, critical_re,
          _f(major_aql), major_ac, major_re, _f(minor_aql), minor_ac, minor_re,
          source_edition.strip(), source_reference.strip(), s["user"]["id"], db.now()))
    db.audit(s["user"]["id"], s["user"]["display_name"], "plan.created", "lot", lot_id,
             after={"version": ver, "n": n, "mode": counting_mode})
    # a plan defines the sample: create the garment slots once, so capture has somewhere to go
    have = db.one("SELECT COUNT(*) c FROM sample_unit WHERE lot_id=?", (lot_id,))["c"]
    if have == 0:
        for i in range(1, n + 1):
            uid = db.x("INSERT INTO sample_unit(lot_id, garment_code, created_at) VALUES (?,?,?)",
                       (lot_id, f"G-{i:02d}", db.now()))
            for side in ("front", "back"):
                db.x("INSERT INTO unit_view(sample_unit_id, side, required) VALUES (?,?,1)", (uid, side))
        db.audit(s["user"]["id"], s["user"]["display_name"], "units.generated", "lot", lot_id,
                 after={"count": n, "views": n * 2})
    return RedirectResponse(f"/lots/{lot_id}?ok=saved", status_code=303)


def _f(v: str):
    try:
        return float(v) if v not in (None, "") else None
    except ValueError:
        return None


@router.post("/lots/{lot_id}/nonvisual")
def nonvisual(request: Request, lot_id: int, csrf: str = Form(""), status: str = Form(""),
              note: str = Form("")):
    s = require_role(request, "supervisor")
    assert_csrf(request, s, csrf)
    L = service.lot(lot_id)
    if not L:
        raise Denied(404, "not_found")
    if status not in ("pending", "done", "not_required", "failed"):
        raise Denied(422, "invalid")
    if status == "failed" and len(note.strip()) < 3:
        raise Denied(422, "note_required")
    if L["status"] == "decided" and status != L["critical_nonvisual_status"]:
        raise Denied(403, "locked")
    db.x("UPDATE lot SET critical_nonvisual_status=?, nonvisual_note=? WHERE id=?",
         (status, note.strip() or None, lot_id))
    db.audit(s["user"]["id"], s["user"]["display_name"], "lot.nonvisual_changed", "lot", lot_id,
             before={"status": L["critical_nonvisual_status"]}, after={"status": status, "note": note.strip()})
    return RedirectResponse(f"/lots/{lot_id}?ok=saved", status_code=303)
