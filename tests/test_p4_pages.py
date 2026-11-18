"""Phase 4 tests: Configuration & Admin User Management (P2 screens)."""
from __future__ import annotations

from starlette.requests import Request
from starlette.templating import Jinja2Templates

from app.core import db
from app.domain import engine
from app.i18n import t
from app.services import vision
from app.web.pages import ctx
from app.web.stats import load_model_card

templates = Jinja2Templates(directory="templates")
templates.env.globals["tr"] = t


def test_admin_user_management_screen():
    """Verify Admin user table, role protection, last-admin protection, and query alerts."""
    user_admin = {"id": 1, "role": "admin", "display_name": "Nusrat Jahan", "email": "nusrat@lotline.demo"}

    users = db.q("SELECT * FROM app_user ORDER BY id")
    models = db.q("SELECT * FROM model_version ORDER BY id DESC")
    tests = db.q("SELECT * FROM model_selftest ORDER BY id DESC LIMIT 8")
    acts = db.q("SELECT * FROM model_activation ORDER BY id DESC LIMIT 10")
    clauses = db.q("SELECT c.*, b.name AS buyer_name FROM clause_mapping c JOIN buyer b ON b.id=c.buyer_id ORDER BY b.name, c.defect_type")
    health = {
        "db_bytes": 1048576,
        "disk_free": 50000000000,
        "disk_total": 100000000000,
        "images": 12,
        "jobs_ok": 10,
        "jobs_failed": 2,
        "audit_rows": 45,
        "sessions": 3,
        "model": vision.MODEL_NAME,
        "model_loaded": True,
        "model_sha": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    }

    for lang in ["en", "bn"]:
        # 1. Standard users tab
        scope = {"type": "http", "method": "GET", "path": "/admin", "headers": [(b"cookie", f"ll_lang={lang}".encode())], "query_string": b"tab=users"}
        req = Request(scope)
        c = ctx(req, active="admin", tab_name="users", user=user_admin, tab="users", users=users,
                models=models, tests=tests, activations=acts, clauses=clauses, health=health, card=load_model_card())
        html = templates.TemplateResponse(req, "admin.html", c).body.decode("utf-8")
        assert "createUserForm" in html
        assert "nusrat@lotline.demo" in html
        assert ("Self (locked)" in html) or ("নিজের অ্যাকাউন্ট" in html)

        # 2. Last admin protection alert
        scope_la = {"type": "http", "method": "GET", "path": "/admin", "headers": [(b"cookie", f"ll_lang={lang}".encode())], "query_string": b"err=last_admin"}
        req_la = Request(scope_la)
        c_la = ctx(req_la, active="admin", user=user_admin, tab="users", users=users,
                  models=models, tests=tests, activations=acts, clauses=clauses, health=health, card=load_model_card())
        html_la = templates.TemplateResponse(req_la, "admin.html", c_la).body.decode("utf-8")
        assert ("Cannot disable last active administrator" in html_la) or ("একমাত্র সক্রিয় অ্যাডমিন" in html_la)

        # 3. Self-role change protection alert
        scope_sr = {"type": "http", "method": "GET", "path": "/admin", "headers": [(b"cookie", f"ll_lang={lang}".encode())], "query_string": b"err=self_role"}
        req_sr = Request(scope_sr)
        c_sr = ctx(req_sr, active="admin", user=user_admin, tab="users", users=users,
                  models=models, tests=tests, activations=acts, clauses=clauses, health=health, card=load_model_card())
        html_sr = templates.TemplateResponse(req_sr, "admin.html", c_sr).body.decode("utf-8")
        assert ("Cannot modify your own administrative role" in html_sr) or ("নিজের অ্যাডমিন ভূমিকা" in html_sr)

        # 4. Temporary password alert
        scope_tp = {"type": "http", "method": "GET", "path": "/admin", "headers": [(b"cookie", f"ll_lang={lang}".encode())], "query_string": b"temp=TempSecretPass123!Aa"}
        req_tp = Request(scope_tp)
        c_tp = ctx(req_tp, active="admin", user=user_admin, tab="users", users=users,
                  models=models, tests=tests, activations=acts, clauses=clauses, health=health, card=load_model_card())
        html_tp = templates.TemplateResponse(req_tp, "admin.html", c_tp).body.decode("utf-8")
        assert "TempSecretPass123!Aa" in html_tp
        assert ("Temporary Password Generated" in html_tp) or ("অস্থায়ী পাসওয়ার্ড" in html_tp)


def test_admin_models_and_health_tabs():
    """Verify Models and Health tabs with self-test history and system resource metrics."""
    user_admin = {"id": 1, "role": "admin", "display_name": "Nusrat Jahan"}
    models = db.q("SELECT * FROM model_version ORDER BY id DESC")
    tests = db.q("SELECT * FROM model_selftest ORDER BY id DESC LIMIT 8")
    acts = db.q("SELECT * FROM model_activation ORDER BY id DESC LIMIT 10")
    clauses = db.q("SELECT c.*, b.name AS buyer_name FROM clause_mapping c JOIN buyer b ON b.id=c.buyer_id ORDER BY b.name")
    health = {
        "db_bytes": 204800,
        "disk_free": 45000000000,
        "disk_total": 100000000000,
        "images": 12,
        "jobs_ok": 8,
        "jobs_failed": 1,
        "audit_rows": 50,
        "sessions": 2,
        "model": vision.MODEL_NAME,
        "model_loaded": True,
        "model_sha": "d41d8cd98f00b204e9800998ecf8427e",
    }

    scope_m = {"type": "http", "method": "GET", "path": "/admin", "headers": [], "query_string": b"tab=models"}
    req_m = Request(scope_m)
    c_m = ctx(req_m, active="admin", user=user_admin, tab="models", users=[], models=models,
              tests=tests, activations=acts, clauses=clauses, health=health, card=load_model_card())
    html_m = templates.TemplateResponse(req_m, "admin.html", c_m).body.decode("utf-8")
    assert "/admin/models/selftest" in html_m
    assert "/admin/models/activate" in html_m
    assert 'minlength="20"' in html_m

    scope_h = {"type": "http", "method": "GET", "path": "/admin", "headers": [], "query_string": b"tab=health"}
    req_h = Request(scope_h)
    c_h = ctx(req_h, active="admin", user=user_admin, tab="health", users=[], models=models,
              tests=tests, activations=acts, clauses=clauses, health=health, card=load_model_card())
    html_h = templates.TemplateResponse(req_h, "admin.html", c_h).body.decode("utf-8")
    assert "online" in html_h
    assert "Audit chain" in html_h or "অডিট চেইন" in html_h
    assert "Evidence integrity" in html_h or "প্রমাণ অখণ্ডতা" in html_h


def test_admin_clauses_tab():
    """Verify buyer clauses matrix displays defect types, zones, severity, and read-only notice."""
    user_admin = {"id": 1, "role": "admin", "display_name": "Nusrat Jahan"}
    clauses = db.q("SELECT c.*, b.name AS buyer_name FROM clause_mapping c JOIN buyer b ON b.id=c.buyer_id ORDER BY b.name")
    scope = {"type": "http", "method": "GET", "path": "/admin", "headers": [], "query_string": b"tab=clauses"}
    req = Request(scope)
    c = ctx(req, active="admin", user=user_admin, tab="clauses", users=[], models=[], tests=[], activations=[], clauses=clauses, health={}, card={})
    html = templates.TemplateResponse(req, "admin.html", c).body.decode("utf-8")
    assert "Buyer Quality Specifications" in html
    assert "clause_readonly" in html or "read-only" in html.lower() or "পড়া যায়" in html
    assert "Nordic Wear" in html or "EuroKnit" in html or "Pacific Apparel" in html


def test_configuration_dialog_in_shell():
    """Verify Configuration dialog presence for Supervisor/Admin and absence for Inspector."""
    user_sup = {"id": 2, "role": "supervisor", "display_name": "Farhan Chowdhury"}
    user_admin = {"id": 1, "role": "admin", "display_name": "Nusrat Jahan"}
    user_insp = {"id": 4, "role": "inspector", "display_name": "Rakib Hasan"}

    scope = {"type": "http", "method": "GET", "path": "/", "headers": [], "query_string": b""}
    req = Request(scope)

    # Supervisor shell has config dialog
    c_sup = ctx(req, active="dashboard", user=user_sup, cards=[], counters={}, model="", model_ok=True, stats={})
    html_sup = templates.TemplateResponse(req, "dashboard.html", c_sup).body.decode("utf-8")
    assert 'id="configDialog"' in html_sup
    assert 'data-dialog-open="configDialog"' in html_sup
    assert "Enterprise Synchronization" in html_sup or "এন্টারপ্রাইজ সিঙ্ক" in html_sup

    # Admin shell has config dialog
    c_admin = ctx(req, active="dashboard", user=user_admin, cards=[], counters={}, model="", model_ok=True, stats={})
    html_admin = templates.TemplateResponse(req, "dashboard.html", c_admin).body.decode("utf-8")
    assert 'id="configDialog"' in html_admin

    # Inspector does NOT have config dialog
    c_insp = ctx(req, active="dashboard", user=user_insp, cards=[], counters={}, model="", model_ok=True, stats={})
    html_insp = templates.TemplateResponse(req, "dashboard.html", c_insp).body.decode("utf-8")
    assert 'id="configDialog"' not in html_insp

