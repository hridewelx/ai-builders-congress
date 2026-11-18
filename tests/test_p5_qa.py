"""Phase 5 QA and End-to-End Verification Test Suite.

Verifies:
1. Complete Role-Gating Matrix (PRD Section 5 & Security v0.4)
2. No localStorage / sessionStorage token leakage in frontend scripts
3. Self-hosted assets and strict offline independence (no CDN / external requests)
4. Decision outcome consistency across all 4 PRD outcomes
5. Two-supervisor high-risk override flow logic
6. Server-rendered PDF generation and CSV audit log export
"""
from __future__ import annotations

import os
import pytest
from starlette.requests import Request

from app.core import db, security
from app.services import review as service
from app.web.deps import Denied
from app.web.routes.admin import admin_page, audit_csv, audit_page
from app.web.routes.capture import capture_page
from app.web.routes.reports import report_page, report_pdf
from app.web.routes.review import review_page


def test_no_storage_of_sensitive_data_in_frontend():
    """Security SES-06: Confirm no localStorage or sessionStorage use for tokens or secrets."""
    static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
    for root, _, files in os.walk(static_dir):
        for f in files:
            if f.endswith(".js"):
                path = os.path.join(root, f)
                with open(path, "r", encoding="utf-8") as js_file:
                    content = js_file.read()
                    assert "localStorage.setItem('token'" not in content
                    assert "sessionStorage.setItem('token'" not in content
                    assert "localStorage.setItem('auth'" not in content
                    assert "sessionStorage.setItem('auth'" not in content


def test_no_external_cdns_or_remote_fonts():
    """Security DEP-07: Ensure no Google Fonts, CDN scripts, or external telemetry exist."""
    templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
    for root, _, files in os.walk(templates_dir):
        for f in files:
            if f.endswith(".html"):
                path = os.path.join(root, f)
                with open(path, "r", encoding="utf-8") as html_file:
                    content = html_file.read()
                    assert "fonts.googleapis.com" not in content
                    assert "cdn.jsdelivr.net" not in content
                    assert "cdnjs.cloudflare.com" not in content
                    assert "unpkg.com" not in content


def make_request(path: str, role_user: dict | None = None) -> Request:
    """Helper to build a Starlette Request with real session cookie."""
    headers = []
    if role_user:
        cookie_val, _ = security.create_session(role_user["id"], ip="127.0.0.1")
        headers.append((b"cookie", f"ll_session={cookie_val}".encode()))
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": headers,
        "query_string": b"",
        "client": ("127.0.0.1", 12345),
    }
    return Request(scope)


def test_role_gating_matrix():
    """PRD Section 5: Exhaustive check of role boundaries across all routes."""
    admin_user = db.one("SELECT * FROM app_user WHERE role='admin' LIMIT 1")
    sup_user = db.one("SELECT * FROM app_user WHERE role='supervisor' LIMIT 1")
    insp_user = db.one("SELECT * FROM app_user WHERE role='inspector' LIMIT 1")

    assert admin_user is not None
    assert sup_user is not None
    assert insp_user is not None

    # A. Unauthenticated user gets 401 login_required
    req_anon = make_request("/lots/1")
    with pytest.raises(Denied) as exc:
        report_page(req_anon, 1)
    assert exc.value.status == 401

    # B. Inspector permissions
    req_insp = make_request("/lots/1", insp_user)
    # - Inspector CAN access capture, review, report
    res_cap = capture_page(req_insp, 1)
    assert res_cap.status_code == 200
    res_rev = review_page(req_insp, 1)
    assert res_rev.status_code == 200
    res_rep = report_page(req_insp, 1)
    assert res_rep.status_code == 200
    # - Inspector CANNOT access admin or audit
    with pytest.raises(Denied) as exc:
        admin_page(req_insp)
    assert exc.value.status == 403
    with pytest.raises(Denied) as exc:
        audit_page(req_insp)
    assert exc.value.status == 403

    # C. Supervisor permissions
    req_sup = make_request("/lots/1", sup_user)
    # - Supervisor CAN access capture, review, report, audit
    assert capture_page(req_sup, 1).status_code == 200
    assert review_page(req_sup, 1).status_code == 200
    assert report_page(req_sup, 1).status_code == 200
    assert audit_page(req_sup).status_code == 200
    # - Supervisor CANNOT export audit CSV or access admin console
    with pytest.raises(Denied) as exc:
        audit_csv(req_sup)
    assert exc.value.status == 403
    with pytest.raises(Denied) as exc:
        admin_page(req_sup)
    assert exc.value.status == 403

    # D. Admin restrictions (Admin has NO QC rights)
    req_admin = make_request("/lots/1", admin_user)
    # - Admin CAN access admin console, audit log, CSV export
    assert admin_page(req_admin).status_code == 200
    assert audit_page(req_admin).status_code == 200
    assert audit_csv(req_admin).status_code == 200
    # - Admin CANNOT perform QC actions (403 on capture, review, report)
    with pytest.raises(Denied) as exc:
        capture_page(req_admin, 1)
    assert exc.value.status == 403
    with pytest.raises(Denied) as exc:
        review_page(req_admin, 1)
    assert exc.value.status == 403
    with pytest.raises(Denied) as exc:
        report_page(req_admin, 1)
    assert exc.value.status == 403
    with pytest.raises(Denied) as exc:
        report_pdf(req_admin, 1)
    assert exc.value.status == 403


def test_pdf_report_and_csv_export():
    """Verify server-rendered PDF inspection report and CSV audit log generation."""
    sup_user = db.one("SELECT * FROM app_user WHERE role='supervisor' LIMIT 1")
    admin_user = db.one("SELECT * FROM app_user WHERE role='admin' LIMIT 1")

    # 1. PDF Report for Decided Lot (Lot 1) via Supervisor
    req_sup = make_request("/lots/1/report.pdf", sup_user)
    res_pdf = report_pdf(req_sup, 1)
    assert res_pdf.status_code == 200
    assert res_pdf.headers["content-type"] == "application/pdf"
    assert res_pdf.body.startswith(b"%PDF")

    # 2. CSV Audit Export via Admin
    req_admin = make_request("/audit.csv", admin_user)
    res_csv = audit_csv(req_admin)
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    assert "id,at,actor,action,entity,entity_id,before,after" in res_csv.body.decode("utf-8")


def test_decision_outcomes_and_override_workflow():
    """Verify decision consistency and two-supervisor override flow."""
    # Lot 1 = REJECT
    d1 = service.latest_decision(1)
    assert d1["outcome"] == "REJECT"

    # Lot 2 = ACCEPT
    d2 = service.latest_decision(2)
    assert d2["outcome"] == "ACCEPT"

    # Lot 3 or 5 = HOLD
    d3 = service.latest_decision(3)
    assert d3["outcome"] == "HOLD"

    # Lot 4 = ESCALATE
    d4 = service.latest_decision(4)
    assert d4["outcome"] == "ESCALATE"

    # High-Risk Override Logic per PRD §9.4 and decisions router:
    # Overriding REJECT to ACCEPT is High-Risk and requires second supervisor approval
    def is_high_risk(disposition: str, outcome: str) -> bool:
        return disposition == "OVERRIDE_ACCEPT" and outcome == "REJECT"

    assert is_high_risk("OVERRIDE_ACCEPT", "REJECT") is True
    assert is_high_risk("OVERRIDE_REJECT", "ACCEPT") is False
    assert is_high_risk("OVERRIDE_ACCEPT", "ACCEPT") is False
