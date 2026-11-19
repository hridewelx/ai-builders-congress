import os
import sys
from pathlib import Path
from starlette.requests import Request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core import db
from app.services import review as service, vision
from app.web.pages import ctx, templates
from app.web.routes.dashboard import lot_cards
from app.web.stats import demo_stats, load_model_card

db.init()

out_dir = Path("docs/qa_screenshots/html")
out_dir.mkdir(parents=True, exist_ok=True)

user_insp = {"id": 4, "role": "inspector", "display_name": "Rakib Hasan", "email": "rakib@lotline.demo"}
user_sup = {"id": 2, "role": "supervisor", "display_name": "Farhan Chowdhury", "email": "farhan@lotline.demo"}
user_admin = {"id": 1, "role": "admin", "display_name": "Nusrat Jahan", "email": "nusrat@lotline.demo"}

def prepare_html(html_str):
    # Fix paths so local browser can resolve static assets
    abs_static = Path("static").resolve().as_uri()
    html_str = html_str.replace('href="/static/', f'href="{abs_static}/')
    html_str = html_str.replace('src="/static/', f'src="{abs_static}/')
    return html_str

def save_screen(name, template_name, context):
    req = context["request"]
    html = templates.TemplateResponse(req, template_name, context).body.decode("utf-8")
    fixed_html = prepare_html(html)
    p = out_dir / f"{name}.html"
    p.write_text(fixed_html, encoding="utf-8")
    print(f"Generated: {name}.html ({len(fixed_html)} bytes)")

# 1. Login Screen (English & Bengali)
for lang in ["en", "bn"]:
    req = Request({"type": "http", "method": "GET", "path": "/login", "headers": [(b"cookie", f"ll_lang={lang}".encode())], "query_string": b""})
    c = ctx(req, active="login", user=None, err=None)
    save_screen(f"01_login_{lang}", "login.html", c)

# 2. Dashboard Screen (Inspector, Supervisor, Admin in EN & BN)
counters = service.counters()
stats = demo_stats()
for lang in ["en", "bn"]:
    req = Request({"type": "http", "method": "GET", "path": "/", "headers": [(b"cookie", f"ll_lang={lang}".encode())], "query_string": b""})
    cards = lot_cards(req)
    c_insp = ctx(req, active="dashboard", user=user_insp, cards=cards[:6], counters=counters, model=vision.MODEL_NAME, model_ok=True, stats=stats)
    save_screen(f"02_dashboard_inspector_{lang}", "dashboard.html", c_insp)
    
    c_sup = ctx(req, active="dashboard", user=user_sup, cards=cards[:6], counters=counters, model=vision.MODEL_NAME, model_ok=True, stats=stats)
    save_screen(f"02_dashboard_supervisor_{lang}", "dashboard.html", c_sup)

    c_admin = ctx(req, active="dashboard", user=user_admin, cards=cards[:6], counters=counters, model=vision.MODEL_NAME, model_ok=True, stats=stats)
    save_screen(f"02_dashboard_admin_{lang}", "dashboard.html", c_admin)

# 3. Lots List Screen (EN & BN)
for lang in ["en", "bn"]:
    req = Request({"type": "http", "method": "GET", "path": "/lots", "headers": [(b"cookie", f"ll_lang={lang}".encode())], "query_string": b""})
    cards = lot_cards(req)
    c = ctx(req, active="lots", user=user_insp, cards=cards, state="", outcome="", q="")
    save_screen(f"03_lots_list_{lang}", "lots.html", c)

# 4. Create Lot Screen (EN & BN)
buyers = db.q("SELECT * FROM buyer ORDER BY name")
products = db.q("SELECT * FROM product ORDER BY name")
for lang in ["en", "bn"]:
    req = Request({"type": "http", "method": "GET", "path": "/lots/new", "headers": [(b"cookie", f"ll_lang={lang}".encode())], "query_string": b""})
    c = ctx(req, active="lots", user=user_insp, buyers=buyers, products=products)
    save_screen(f"04_create_lot_{lang}", "lot_new.html", c)

# 5. Lot Cockpit (Overview) Screen (EN & BN)
lot_id = 1
L = service.lot(lot_id)
plan = service.active_plan(lot_id)
plan_d = service.plan_dict(plan)
progress = service.progress(lot_id)
units = service.units_with_views(lot_id)
d = service.latest_decision(lot_id)
ov = service.override_for(d["id"]) if d else None
hist = db.q("SELECT * FROM decision WHERE lot_id=? ORDER BY sequence DESC", (lot_id,))
audit = service.timeline(lot_id)
final = service.final_disposition(d, ov) if d else None
for lang in ["en", "bn"]:
    req = Request({"type": "http", "method": "GET", "path": f"/lots/{lot_id}", "headers": [(b"cookie", f"ll_lang={lang}".encode())], "query_string": b""})
    c = ctx(req, active="lots", user=user_insp, lot=L, plan=plan, plan_d=plan_d, progress=progress, units=units, decision=d, override=ov, final=final, history=hist, audit=audit, is_admin=False, can_write=True)
    save_screen(f"05_lot_cockpit_{lang}", "lot.html", c)

# 6. Sampling Plan Screen (Supervisor edit & Inspector read-only)
for lang in ["en", "bn"]:
    req = Request({"type": "http", "method": "GET", "path": f"/lots/{lot_id}/plan", "headers": [(b"cookie", f"ll_lang={lang}".encode())], "query_string": b""})
    c_sup = ctx(req, active="lots", user=user_sup, lot=L, plan=plan, plan_d=plan_d, is_supervisor=True, locked=False)
    save_screen(f"06_sampling_plan_supervisor_{lang}", "plan.html", c_sup)
    c_insp = ctx(req, active="lots", user=user_insp, lot=L, plan=plan, plan_d=plan_d, is_supervisor=False, locked=False)
    save_screen(f"06_sampling_plan_inspector_{lang}", "plan.html", c_insp)

# 7. Photo Capture Screen (EN & BN)
for lang in ["en", "bn"]:
    req = Request({"type": "http", "method": "GET", "path": f"/lots/{lot_id}/capture", "headers": [(b"cookie", f"ll_lang={lang}".encode())], "query_string": b""})
    c = ctx(req, active="lots", user=user_insp, lot=L, units=units, progress=progress, can_write=True)
    save_screen(f"07_photo_capture_{lang}", "capture.html", c)

# 8. Review Queue Screen (EN & BN)
queue = service.review_queue(lot_id)
for lang in ["en", "bn"]:
    req = Request({"type": "http", "method": "GET", "path": f"/lots/{lot_id}/review", "headers": [(b"cookie", f"ll_lang={lang}".encode())], "query_string": b""})
    c = ctx(req, active="lots", user=user_insp, lot=L, queue=queue)
    save_screen(f"08_review_queue_{lang}", "review_queue.html", c)

# 9. Image Review Screen (EN & BN)
img = db.one("SELECT * FROM image WHERE lot_id=1 LIMIT 1")
img_id = img["id"]
view = db.one("SELECT v.*, u.garment_code, u.id AS unit_id FROM unit_view v JOIN sample_unit u ON u.id=v.sample_unit_id WHERE v.id=?", (img["view_id"],))
review = db.one("SELECT rr.*, a.display_name AS reviewer FROM view_review rr LEFT JOIN app_user a ON a.id=rr.reviewed_by WHERE rr.image_id=?", (img_id,))
job = db.one("SELECT * FROM inference_job WHERE image_id=? ORDER BY id DESC LIMIT 1", (img_id,))
preds = db.q("SELECT p.*, a.display_name AS reviewer FROM prediction p LEFT JOIN app_user a ON a.id=p.reviewed_by WHERE p.image_id=? ORDER BY p.id", (img_id,))
clause_rows = db.q("SELECT * FROM clause_mapping WHERE buyer_id=? ORDER BY defect_type, zone_code", (L["buyer_id"],))
for lang in ["en", "bn"]:
    req = Request({"type": "http", "method": "GET", "path": f"/review/{img_id}", "headers": [(b"cookie", f"ll_lang={lang}".encode())], "query_string": b""})
    c = ctx(req, active="lots", user=user_sup, lot=L, image=img, view=view, review=review, job=job, preds=[dict(p) for p in preds], clauses=[dict(cl) for cl in clause_rows], status=service.derive_status(job), next_item=None, can_write=True, is_supervisor=True)
    save_screen(f"09_image_review_{lang}", "review.html", c)

# 10. Decision Center Screen (EN & BN)
import json
from app.domain import engine
hist_full = db.q("SELECT d.*, u.display_name AS decided_by FROM decision d JOIN app_user u ON u.id=d.created_by WHERE d.lot_id=? ORDER BY d.sequence DESC", (lot_id,))
decision_data = dict(d) if d else None
if decision_data:
    decision_data["reasons"] = json.loads(decision_data["reasons"])
    decision_data["counts"] = json.loads(decision_data["counts"])
    decision_data["class_limits"] = json.loads(decision_data["class_limits"] or "{}")
    decision_data["completeness"] = json.loads(decision_data["completeness"] or "{}")
    decision_data["plan_snapshot"] = json.loads(decision_data["plan_snapshot"]) if decision_data["plan_snapshot"] else None
history_data = [dict(h) | {"counts": json.loads(h["counts"]), "reasons": json.loads(h["reasons"])} for h in hist_full]

for lang in ["en", "bn"]:
    req = Request({"type": "http", "method": "GET", "path": f"/lots/{lot_id}/decision", "headers": [(b"cookie", f"ll_lang={lang}".encode())], "query_string": b""})
    c = ctx(req, active="lots", user=user_sup, lot=L, plan=plan_d, decision=decision_data, override=ov, final=final, history=history_data, progress=progress, is_supervisor=True, can_write=True, reason_text=engine.REASONS)
    save_screen(f"10_decision_center_{lang}", "decision.html", c)

# 11. Reports Screen (EN & BN)
from app.web.routes.reports import _report_ctx
rc = _report_ctx(lot_id)
for lang in ["en", "bn"]:
    req = Request({"type": "http", "method": "GET", "path": f"/lots/{lot_id}/report", "headers": [(b"cookie", f"ll_lang={lang}".encode())], "query_string": b""})
    c = ctx(req, active="lots", user=user_insp, lot=L, rc=rc)
    save_screen(f"11_inspection_report_{lang}", "report.html", c)

# 12. Audit Log Screen (EN & BN)
audit_rows = db.q("SELECT * FROM audit_event ORDER BY id DESC LIMIT 50")
audit_list = []
for a in audit_rows:
    row = dict(a)
    row["before"] = json.loads(row["before_json"]) if row.get("before_json") else None
    row["after"] = json.loads(row["after_json"]) if row.get("after_json") else None
    audit_list.append(row)

for lang in ["en", "bn"]:
    req = Request({"type": "http", "method": "GET", "path": "/audit", "headers": [(b"cookie", f"ll_lang={lang}".encode())], "query_string": b""})
    c = ctx(req, active="audit", user=user_admin, rows=audit_list, q="", can_export=True)
    save_screen(f"12_audit_log_{lang}", "audit.html", c)

# 13. Admin Console Screen (Users, Health, Clauses in EN & BN)
users = db.q("SELECT * FROM app_user ORDER BY id")
models = db.q("SELECT * FROM model_version ORDER BY id DESC")
tests = db.q("SELECT * FROM model_selftest ORDER BY id DESC LIMIT 8")
acts = db.q("SELECT * FROM model_activation ORDER BY id DESC LIMIT 10")
clauses = db.q("SELECT c.*, b.name AS buyer_name FROM clause_mapping c JOIN buyer b ON b.id=c.buyer_id ORDER BY b.name, c.defect_type")
health = {
    "db_bytes": 1048576, "disk_free": 50000000000, "disk_total": 100000000000,
    "images": 12, "jobs_ok": 10, "jobs_failed": 2, "audit_rows": 45, "sessions": 3,
    "model": vision.MODEL_NAME, "model_loaded": True,
    "model_sha": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
}

for lang in ["en", "bn"]:
    req = Request({"type": "http", "method": "GET", "path": "/admin", "headers": [(b"cookie", f"ll_lang={lang}".encode())], "query_string": b"tab=users"})
    c = ctx(req, active="admin", tab_name="users", user=user_admin, tab="users", users=users, models=models, tests=tests, activations=acts, clauses=clauses, health=health, card=load_model_card())
    save_screen(f"13_admin_users_{lang}", "admin.html", c)

    c_health = ctx(req, active="admin", tab_name="health", user=user_admin, tab="health", users=users, models=models, tests=tests, activations=acts, clauses=clauses, health=health, card=load_model_card())
    save_screen(f"13_admin_health_{lang}", "admin.html", c_health)

print("\n--- All 13 Screens Successfully Rendered! ---")
