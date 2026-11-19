"""Tests for sampling plan validation, confirmation, and live preview UX."""
import pytest
from starlette.requests import Request

from app.core import db, security
from app.services import review as service
from app.web.routes.lots import plan_page, plan_save


@pytest.fixture(scope="module", autouse=True)
def init_data():
    db.init()


def make_req(role: str = "supervisor", lang: str = "bn", query_string: str = ""):
    user = db.one("SELECT * FROM app_user WHERE role=?", (role,))
    assert user is not None
    cookie_val, csrf = security.create_session(user["id"])
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/lots/5/plan",
        "headers": [
            (b"cookie", f"{security.COOKIE}={cookie_val}; ll_lang={lang}".encode()),
            (b"host", b"localhost:8077"),
        ],
        "query_string": query_string.encode(),
    }
    return Request(scope), csrf


def test_plan_missing_confirmation():
    req, csrf = make_req()
    resp = plan_save(
        req, 5, csrf=csrf, n=8,
        counting_mode="highest_class_only",
        critical_ac=0, critical_re=1,
        major_ac=1, major_re=2,
        minor_ac=2, minor_re=3,
        confirmed="",
    )
    assert resp.status_code == 422
    html = resp.body.decode("utf-8")
    assert "errorSummary" in html
    assert "উৎস থেকে মান মিলিয়ে যাচাইয়ের স্বীকৃতি আবশ্যক" in html


def test_plan_invalid_n_exceeds_lotsize():
    req, csrf = make_req()
    resp = plan_save(
        req, 5, csrf=csrf, n=601,
        counting_mode="highest_class_only",
        critical_ac=0, critical_re=1,
        major_ac=1, major_re=2,
        minor_ac=2, minor_re=3,
        confirmed="1",
    )
    assert resp.status_code == 422
    html = resp.body.decode("utf-8")
    assert "errorSummary" in html
    assert "লট সাইজ (600)-এর চেয়ে বড় হতে পারে না" in html


def test_plan_invalid_single_sampling_invariant():
    req, csrf = make_req()
    resp = plan_save(
        req, 5, csrf=csrf, n=8,
        counting_mode="highest_class_only",
        critical_ac=0, critical_re=1,
        major_ac=1, major_re=3,  # Invalid: Re != Ac + 1
        minor_ac=2, minor_re=3,
        confirmed="1",
    )
    assert resp.status_code == 422
    html = resp.body.decode("utf-8")
    assert "errorSummary" in html
    assert "Re অবশ্যই Ac + 1 হতে হবে" in html


def test_plan_save_success_and_audit():
    req, csrf = make_req()
    resp = plan_save(
        req, 5, csrf=csrf, n=8,
        counting_mode="highest_class_only",
        critical_ac=0, critical_re=1,
        major_ac=1, major_re=2,
        minor_ac=2, minor_re=3,
        critical_aql="0.0",
        major_aql="2.5",
        minor_aql="4.0",
        source_edition="",
        source_reference="",
        confirmed="1",
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/lots/5/plan?ok=saved"

    # Verify active plan in DB
    plan = service.active_plan(5)
    assert plan is not None
    assert plan["n"] == 8
    assert plan["critical_ac"] == 0
    assert plan["critical_re"] == 1
    assert plan["source_edition"] == "অননুমোদিত অনুমান"

    # Verify audit events
    audits = db.q("SELECT * FROM audit_event WHERE entity='lot' AND entity_id='5' AND action IN ('plan.confirmed', 'plan.created')")
    actions = [a["action"] for a in audits]
    assert "plan.confirmed" in actions
    assert "plan.created" in actions

    # GET with ok=saved
    req_get, _ = make_req(query_string="ok=saved")
    resp_get = plan_page(req_get, 5)
    assert resp_get.status_code == 200
    html_get = resp_get.body.decode("utf-8")
    assert "plan-success-banner" in html_get
    assert "/lots/5/decision" in html_get
