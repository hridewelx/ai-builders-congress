"""Phase 3 tests: Dashboard, Lots list, Create Lot, Audit log, and Report view."""
from __future__ import annotations

from starlette.requests import Request
from starlette.templating import Jinja2Templates

from app.core import db
from app.i18n import format_num, t
from app.services import review as service
from app.services import vision
from app.web.pages import ctx, dt_local_filter, num_filter, num_grouped_filter
from app.web.routes.dashboard import lot_cards
from app.web.routes.reports import _report_ctx
from app.web.stats import demo_stats, load_model_card

templates = Jinja2Templates(directory="templates")
templates.env.globals["tr"] = t
templates.env.globals["num"] = format_num
templates.env.filters["num"] = num_filter
templates.env.filters["num_grouped"] = num_grouped_filter
templates.env.filters["dt_local"] = dt_local_filter


def test_dashboard_page():
    """Verify Dashboard page rendering across Inspector, Supervisor, and Admin."""
    user_insp = {"id": 4, "role": "inspector", "display_name": "Rakib Hasan", "email": "rakib@lotline.demo"}
    user_sup = {"id": 2, "role": "supervisor", "display_name": "Farhan Chowdhury", "email": "farhan@lotline.demo"}
    user_admin = {"id": 1, "role": "admin", "display_name": "Nusrat Jahan", "email": "nusrat@lotline.demo"}

    counters = service.counters()
    card = load_model_card()
    # The explainer page must always know which model serves live uploads,
    # even when the seeder wrote an older model_card.json.
    assert "live_model" in card
    stats = demo_stats()

    for lang in ["en", "bn"]:
        scope = {"type": "http", "method": "GET", "path": "/", "headers": [(b"cookie", f"ll_lang={lang}".encode())], "query_string": b""}
        req = Request(scope)
        cards = lot_cards(req)

        # 1. Inspector Dashboard
        c_insp = ctx(req, active="dashboard", user=user_insp, cards=cards[:4], counters=counters,
                     model=vision.MODEL_NAME, model_ok=True, stats=stats)
        html_insp = templates.TemplateResponse(req, "dashboard.html", c_insp).body.decode("utf-8")
        assert "kpi" in html_insp
        assert any(k in html_insp for k in ("System Recommendation", "সিস্টেম সুপারিশ", "Decision", "সিদ্ধান্ত"))
        assert any(k in html_insp for k in ("Final Disposition", "Decision:", "চূড়ান্ত সিদ্ধান্ত", "Current decision", "বর্তমান সিদ্ধান্ত", "সিদ্ধান্ত:"))
        assert "autoencoder" in html_insp.lower() or "অটোএনকোডার" in html_insp

        # 2. Supervisor Dashboard (sees pending overrides if present)
        c_sup = ctx(req, active="dashboard", user=user_sup, cards=cards[:4], counters=counters,
                    model=vision.MODEL_NAME, model_ok=True, stats=stats)
        html_sup = templates.TemplateResponse(req, "dashboard.html", c_sup).body.decode("utf-8")
        assert "kpi" in html_sup
        assert "pipeline" in html_sup

        # 3. Admin Dashboard (sees System Alerts)
        c_admin = ctx(req, active="dashboard", user=user_admin, cards=cards[:4], counters=counters,
                      model=vision.MODEL_NAME, model_ok=True, stats=stats)
        html_admin = templates.TemplateResponse(req, "dashboard.html", c_admin).body.decode("utf-8")
        assert any(k in html_admin for k in ("System Status", "সিস্টেম অবস্থা", "System Operational Integrity", "সিস্টেম অপারেশনাল ইন্টিগ্রিটি"))
        assert "Admin QC Blocked" in html_admin or "অ্যাডমিন QC নিষিদ্ধ" in html_admin


def test_lots_list_page():
    """Verify Lots list page with filter form, two-line disposition, and role gating."""
    user_insp = {"id": 4, "role": "inspector", "display_name": "Rakib Hasan"}
    user_admin = {"id": 1, "role": "admin", "display_name": "Nusrat Jahan"}

    for lang in ["en", "bn"]:
        scope = {"type": "http", "method": "GET", "path": "/lots", "headers": [(b"cookie", f"ll_lang={lang}".encode())], "query_string": b""}
        req = Request(scope)
        cards = lot_cards(req)

        # Inspector sees + New Lot button
        c_insp = ctx(req, active="lots", user=user_insp, cards=cards, state="", outcome="", q="")
        html_insp = templates.TemplateResponse(req, "lots.html", c_insp).body.decode("utf-8")
        assert "/lots/new" in html_insp
        assert "LT-2026-014" in html_insp
        assert "Two-Line Disposition" in html_insp or "টু-লাইন ডিসপোজিশন" in html_insp

        # Admin does NOT see + New Lot button
        c_admin = ctx(req, active="lots", user=user_admin, cards=cards, state="", outcome="", q="")
        html_admin = templates.TemplateResponse(req, "lots.html", c_admin).body.decode("utf-8")
        assert "/lots/new" not in html_admin

        # Empty state when cards list is empty
        c_empty = ctx(req, active="lots", user=user_insp, cards=[], state="archived", outcome="", q="nonexistent")
        html_empty = templates.TemplateResponse(req, "lots.html", c_empty).body.decode("utf-8")
        assert "empty-state" in html_empty
        assert "No lots match" in html_empty or "কোনো লট নেই" in html_empty


def test_lot_new_page():
    """Verify Create Lot page with form fields, disclaimer, and query error handling."""
    user_insp = {"id": 4, "role": "inspector", "display_name": "Rakib Hasan"}
    buyers = db.q("SELECT * FROM buyer ORDER BY name")
    products = db.q("SELECT * FROM product ORDER BY name")

    for lang in ["en", "bn"]:
        # Standard form view
        scope = {"type": "http", "method": "GET", "path": "/lots/new", "headers": [(b"cookie", f"ll_lang={lang}".encode())], "query_string": b""}
        req = Request(scope)
        c = ctx(req, active="lots", user=user_insp, buyers=buyers, products=products)
        html = templates.TemplateResponse(req, "lot_new.html", c).body.decode("utf-8")
        assert "newLotForm" in html
        assert 'name="lot_code"' in html
        assert 'name="lot_size"' in html
        assert "self-declared random" in html or "স্ব-ঘোষিত" in html
        assert "What happens next" in html or "এরপরের ধাপ" in html

        # Error state: code already exists
        scope_err = {"type": "http", "method": "GET", "path": "/lots/new", "headers": [(b"cookie", f"ll_lang={lang}".encode())], "query_string": b"err=exists"}
        req_err = Request(scope_err)
        c_err = ctx(req_err, active="lots", user=user_insp, buyers=buyers, products=products)
        html_err = templates.TemplateResponse(req_err, "lot_new.html", c_err).body.decode("utf-8")
        assert "Lot code already exists" in html_err or "ইতিমধ্যে ব্যবহৃত" in html_err


def test_audit_page():
    """Verify Audit page with event rows, before/after diffs, and admin-only CSV export."""
    user_sup = {"id": 2, "role": "supervisor", "display_name": "Farhan Chowdhury"}
    user_admin = {"id": 1, "role": "admin", "display_name": "Nusrat Jahan"}

    rows = [
        {
            "id": 101,
            "at": "2026-11-18 10:15:00",
            "actor_user_id": 2,
            "actor_label": "Farhan Chowdhury",
            "action": "override.created",
            "entity": "lot",
            "entity_id": 1,
            "before": {"status": "REJECT"},
            "after": {"status": "OVERRIDE_ACCEPT", "reason": "Tested sample passed reinspection."},
        },
        {
            "id": 102,
            "at": "2026-11-18 10:16:00",
            "actor_user_id": 4,
            "actor_label": "Rakib Hasan",
            "action": "auth.denied",
            "entity": "system",
            "entity_id": None,
            "before": None,
            "after": {"reason": "403 forbidden on admin route"},
        }
    ]

    for lang in ["en", "bn"]:
        scope = {"type": "http", "method": "GET", "path": "/audit", "headers": [(b"cookie", f"ll_lang={lang}".encode())], "query_string": b""}
        req = Request(scope)

        # 1. Admin sees CSV export
        c_admin = ctx(req, active="audit", user=user_admin, rows=rows, q="", can_export=True)
        html_admin = templates.TemplateResponse(req, "audit.html", c_admin).body.decode("utf-8")
        assert "/audit.csv" in html_admin
        assert "override.created" in html_admin
        assert "auth.denied" in html_admin
        assert "View state diff" in html_admin or "পরিবর্তন দেখুন" in html_admin

        # 2. Supervisor does NOT see CSV export
        c_sup = ctx(req, active="audit", user=user_sup, rows=rows, q="", can_export=False)
        html_sup = templates.TemplateResponse(req, "audit.html", c_sup).body.decode("utf-8")
        assert "/audit.csv" not in html_sup


def test_report_page():
    """Verify One-page Inspection Report with 2-line disposition and PDF download."""
    user_insp = {"id": 4, "role": "inspector", "display_name": "Rakib Hasan"}

    for lot_id in [1, 2]:
        rc = _report_ctx(lot_id)
        for lang in ["en", "bn"]:
            scope = {"type": "http", "method": "GET", "path": f"/lots/{lot_id}/report", "headers": [(b"cookie", f"ll_lang={lang}".encode())], "query_string": b""}
            req = Request(scope)
            c = ctx(req, active="lots", user=user_insp, rc=rc, lot=rc["lot"])
            html = templates.TemplateResponse(req, "report.html", c).body.decode("utf-8")
            assert f"/lots/{lot_id}/report.pdf" in html
            assert "data-print" in html
            assert "reportSheet" in html
            assert "System Recommendation" in html or "সিস্টেম সুপারিশ" in html
            assert "Final Disposition" in html or "চূড়ান্ত সিদ্ধান্ত" in html
            assert "ISO 2859-1" in html
            assert "Snapshot SHA-256" in html or "SHA-256" in html
