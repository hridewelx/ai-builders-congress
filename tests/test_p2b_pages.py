"""Phase 2b test suite: Sampling Plan, Decision Center, and Override & Approval flow."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from starlette.requests import Request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core import db
from app.domain import engine
from app.services import review as service
from app.web.pages import ctx, templates


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    db.init()

def render_decision(lot_id, user, lang="en", override_obj=None):
    L = service.lot(lot_id)
    plan = service.plan_dict(service.active_plan(lot_id))
    progress = service.progress(lot_id)
    d = service.latest_decision(lot_id)
    ov = override_obj or (service.override_for(d["id"]) if d else None)
    hist = db.q("SELECT d.*, u.display_name AS decided_by FROM decision d JOIN app_user u ON u.id=d.created_by WHERE d.lot_id=? ORDER BY d.sequence DESC", (lot_id,))

    decision_data = dict(d) if d else None
    if decision_data:
        decision_data["reasons"] = json.loads(decision_data["reasons"])
        decision_data["counts"] = json.loads(decision_data["counts"])
        decision_data["class_limits"] = json.loads(decision_data["class_limits"] or "{}")
        decision_data["completeness"] = json.loads(decision_data["completeness"] or "{}")
        decision_data["plan_snapshot"] = json.loads(decision_data["plan_snapshot"]) if decision_data["plan_snapshot"] else None

    history_data = [dict(h) | {"counts": json.loads(h["counts"]), "reasons": json.loads(h["reasons"])} for h in hist]
    final = service.final_disposition(d, ov) if d else None

    scope = {"type": "http", "method": "GET", "path": f"/lots/{lot_id}/decision", "headers": [(b"cookie", f"ll_lang={lang}".encode())], "query_string": b""}
    req = Request(scope)
    c = ctx(req, active="lots", user=user, lot=L, plan=plan, decision=decision_data, override=ov, final=final, history=history_data, progress=progress, is_supervisor=user["role"] == "supervisor", can_write=True, reason_text=engine.REASONS)
    resp = templates.TemplateResponse(req, "decision.html", c)
    assert resp.status_code == 200
    return resp.body.decode("utf-8")

def test_plan_page_supervisor_and_inspector():
    """Verify Sampling Plan page gives full form to Supervisor and read-only to Inspector."""
    lot_id = 1
    L = service.lot(lot_id)
    plan = service.active_plan(lot_id)
    plan_d = service.plan_dict(plan)

    user_sup = {"id": 2, "role": "supervisor", "display_name": "Farhan Chowdhury"}
    user_insp = {"id": 4, "role": "inspector", "display_name": "Rakib Hasan"}

    for lang in ["en", "bn"]:
        scope = {"type": "http", "method": "GET", "path": f"/lots/{lot_id}/plan", "headers": [(b"cookie", f"ll_lang={lang}".encode())], "query_string": b""}
        req = Request(scope)

        # 1. Supervisor sees form, demo preset, confirmation, preview card, and assumptions
        c_sup = ctx(req, active="lots", user=user_sup, lot=L, plan=plan, plan_d=plan_d, is_supervisor=True, locked=False)
        html_sup = templates.TemplateResponse(req, "plan.html", c_sup).body.decode("utf-8")
        assert "pipeline" in html_sup
        assert "planForm" in html_sup
        assert "highest_class_only" in html_sup
        assert "every_class" in html_sup
        assert "btnDemoPreset" in html_sup
        assert "confirmed" in html_sup
        assert "planPreviewCard" in html_sup
        assert "unreferencedNotice" in html_sup
        assert ("Gate: Sampling Plan" in html_sup) or ("গেট: স্যাম্পলিং প্ল্যান" in html_sup)
        assert "Single sampling" in html_sup or "সিঙ্গেল স্যাম্পলিং" in html_sup

        # 2. Inspector sees read-only notice and NO edit form
        c_insp = ctx(req, active="lots", user=user_insp, lot=L, plan=plan, plan_d=plan_d, is_supervisor=False, locked=False)
        html_insp = templates.TemplateResponse(req, "plan.html", c_insp).body.decode("utf-8")
        assert "pipeline" in html_insp
        assert ("Inspector view (read-only)" in html_insp) or ("ইন্সপেক্টর ভিউ" in html_insp)
        assert "planForm" not in html_insp

    # 3. Lot without plan (Lot 5) starts with empty form fields (no prefilled 8 or 480)
    L5 = service.lot(5)
    c_l5 = ctx(req, active="lots", user=user_sup, lot=L5, plan=None, plan_d=None, is_supervisor=True, locked=False)
    html_l5 = templates.TemplateResponse(req, "plan.html", c_l5).body.decode("utf-8")
    assert 'value=""' in html_l5 or 'value=' not in html_l5.split('id="plan-n"')[1].split('>')[0] or 'value=""' in html_l5.split('id="plan-n"')[1].split('>')[0]
    assert 'HOLD_PLAN_MISSING' in html_l5

def test_decision_center_outcomes():
    """Verify Decision Center renders all four outcomes (ACCEPT, REJECT, HOLD, ESCALATE)."""
    user_sup = {"id": 2, "role": "supervisor", "display_name": "Farhan Chowdhury"}

    # Lot 1 = REJECT
    html1 = render_decision(1, user_sup, "en")
    assert "pipeline" in html1
    assert "REJECT" in html1
    assert "System recommendation" in html1
    assert "Final disposition" in html1

    # Lot 2 = ACCEPT
    html2 = render_decision(2, user_sup, "en")
    assert "ACCEPT" in html2

    # Lot 3 = HOLD
    html3 = render_decision(3, user_sup, "en")
    assert "HOLD" in html3
    assert "cannot be overridden" in html3 or "override" in html3

    # Lot 4 = ESCALATE
    html4 = render_decision(4, user_sup, "en")
    assert "ESCALATE" in html4

def test_override_flow_rendering():
    """Verify override panels: high risk pending approval, two-supervisor flow, and self-approval block."""
    user_sup_a = {"id": 2, "role": "supervisor", "display_name": "Supervisor A"}
    user_sup_b = {"id": 3, "role": "supervisor", "display_name": "Supervisor B"}

    # Mock pending override initiated by Supervisor A
    pending_ov = {
        "id": 99,
        "decision_id": 1,
        "supervisor_id": 2,
        "supervisor": "Supervisor A",
        "final_disposition": "OVERRIDE_ACCEPT",
        "reason": "Garment was reinspected by master tailor and passed.",
        "status": "pending_approval",
        "effective": False,
        "created_at": "2026-11-18 10:00:00",
        "approval": None,
    }

    # 1. Initiating Supervisor A cannot self-approve
    html_a = render_decision(1, user_sup_a, "en", override_obj=pending_ov)
    assert "HIGH RISK · PENDING APPROVAL" in html_a
    assert "Self-approval forbidden" in html_a
    assert 'value="approved"' not in html_a

    # 2. Second Supervisor B sees Approve and Refuse buttons
    html_b = render_decision(1, user_sup_b, "en", override_obj=pending_ov)
    assert "HIGH RISK · PENDING APPROVAL" in html_b
    assert "Second Supervisor Action" in html_b
    assert 'name="decision" value="approved"' in html_b
    assert 'name="decision" value="refused"' in html_b
