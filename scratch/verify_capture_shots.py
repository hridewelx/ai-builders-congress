from __future__ import annotations
import os
import subprocess
from starlette.requests import Request
from app.services import review, vision
from app.web.pages import ctx, templates
from app.web.routes.dashboard import lot_cards
from app.web.stats import demo_stats, load_model_card
from app.core import db

os.makedirs("scratch", exist_ok=True)

# 1. Capture Lot 7 (Inspector, 4 garments, upload boxes ready)
lot7 = review.lot(7)
units7 = review.units_with_views(7)
prog7 = review.progress(7)
user_insp = {"id": 4, "role": "inspector", "display_name": "Rakib Hasan", "email": "rakib@lotline.demo"}

req_cap = Request({"type": "http", "method": "GET", "path": "/lots/7/capture", "headers": [(b"cookie", b"ll_lang=bn")], "query_string": b""})
c_cap = ctx(req_cap, active="lots", user=user_insp, lot=lot7, units=units7, progress=prog7, can_write=True)
html_cap7 = templates.TemplateResponse(req_cap, "capture.html", c_cap).body.decode("utf-8")
with open("scratch/cap_lot7_bn.html", "w", encoding="utf-8") as f:
    f.write(html_cap7)

# 2. Zero-unit lot capture
dummy_lot = {"id": 99, "lot_code": "LT-2026-NEW", "lot_size": 300, "status": "open"}
dummy_prog = {"units": 0, "required_units": 0, "views": 0, "reviewed": 0, "pending": 0, "pct_units": 0, "pct_views": 0}
req_zero = Request({"type": "http", "method": "GET", "path": "/lots/99/capture", "headers": [(b"cookie", b"ll_lang=bn")], "query_string": b""})
c_zero = ctx(req_zero, active="lots", user=user_insp, lot=dummy_lot, units=[], progress=dummy_prog, can_write=True)
html_zero = templates.TemplateResponse(req_zero, "capture.html", c_zero).body.decode("utf-8")
with open("scratch/cap_zero_bn.html", "w", encoding="utf-8") as f:
    f.write(html_zero)

# 3. Admin dashboard with config dialog
user_admin = {"id": 1, "role": "admin", "display_name": "Nusrat Jahan", "email": "nusrat@lotline.demo"}
req_admin = Request({"type": "http", "method": "GET", "path": "/", "headers": [(b"cookie", b"ll_lang=bn")], "query_string": b""})
cards = lot_cards(req_admin)
c_admin = ctx(req_admin, active="dashboard", user=user_admin, cards=cards[:6], counters=review.counters(),
              model=vision.MODEL_NAME, model_ok=True, stats=demo_stats())
html_admin = templates.TemplateResponse(req_admin, "dashboard.html", c_admin).body.decode("utf-8")
with open("scratch/admin_dash_bn.html", "w", encoding="utf-8") as f:
    f.write(html_admin)

print("HTML files written successfully.")

