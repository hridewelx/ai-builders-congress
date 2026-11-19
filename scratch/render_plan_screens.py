import os
import sys
import subprocess
import shutil
from pathlib import Path
from starlette.requests import Request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core import db
from app.services import review as service
from app.web.pages import ctx, templates
from app.web.routes.lots import evidence_summary

db.init()

out_dir = Path("scratch/plan_html")
out_dir.mkdir(parents=True, exist_ok=True)

chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
prof_dir = Path("C:/Users/Jitu/AppData/Local/Temp/chrome_qa_plan").resolve()
prof_dir.mkdir(parents=True, exist_ok=True)
brain_dir = Path(r"C:\Users\Jitu\.gemini\antigravity\brain\843fb091-f952-4738-9ffc-9ef5996ee4f0")

user_insp = {"id": 4, "role": "inspector", "display_name": "Rakib Hasan", "email": "rakib@lotline.demo"}
user_sup = {"id": 2, "role": "supervisor", "display_name": "Farhan Chowdhury", "email": "farhan@lotline.demo"}
user_admin = {"id": 1, "role": "admin", "display_name": "Nadia Rahman", "email": "admin@lotline.demo"}

def prepare_html(html_str):
    abs_static = Path("static").resolve().as_uri()
    html_str = html_str.replace('href="/static/', f'href="{abs_static}/')
    html_str = html_str.replace('src="/static/', f'src="{abs_static}/')
    return html_str

def render_page(lot_id, user, lang="bn", ok="", err="", errors=None, form_data=None, is_locked=False):
    L = service.lot(lot_id)
    plan = service.active_plan(lot_id)
    plan_d = service.plan_dict(plan)
    p = service.progress(lot_id)
    units = service.units_with_views(lot_id)
    d = service.latest_decision(lot_id)
    ev_summary = evidence_summary(lot_id)
    is_sup = user["role"] == "supervisor"

    scope = {
        "type": "http",
        "method": "GET",
        "path": f"/lots/{lot_id}/plan",
        "headers": [(b"cookie", f"ll_lang={lang}".encode())],
        "query_string": f"ok={ok}".encode() if ok else b"",
    }
    req = Request(scope)
    c = ctx(
        req, active="lots", user=user, lot=L, plan=plan, plan_d=plan_d,
        progress=p, units=units, decision=d, evidence_summary=ev_summary,
        is_supervisor=is_sup, locked=is_locked or (L["status"] == "decided"),
        ok=ok, err=err, errors=errors, form_data=form_data
    )
    html = templates.TemplateResponse(req, "plan.html", c).body.decode("utf-8")
    return prepare_html(html)

screens = [
    # 1. Lot 5 (No plan yet) as Supervisor (Bengali)
    ("plan_lot5_sup_bn", 5, user_sup, "bn", "", False),
    # 2. Lot 5 (No plan yet) as Inspector (Bengali, read-only empty state)
    ("plan_lot5_insp_bn", 5, user_insp, "bn", "", False),
    # 3. Lot 5 with Success banner after saving
    ("plan_lot5_saved_bn", 5, user_sup, "bn", "saved", False),
    # 4. Lot 1 (Decided / Locked state) as Supervisor (Bengali)
    ("plan_lot1_locked_bn", 1, user_sup, "bn", "", True),
    # 5. Lot 5 (No plan yet) as Supervisor (English)
    ("plan_lot5_sup_en", 5, user_sup, "en", "", False),
]

html_files = []
for name, lot_id, user, lang, ok_val, is_locked in screens:
    content = render_page(lot_id, user, lang=lang, ok=ok_val, is_locked=is_locked)
    filepath = out_dir / f"{name}.html"
    filepath.write_text(content, encoding="utf-8")
    html_files.append((name, filepath))
    print(f"Rendered: {filepath}")

# Take screenshots
shot_targets = [
    ("plan_lot5_sup_bn", 1366, 768),
    ("plan_lot5_sup_bn", 390, 844),
    ("plan_lot5_insp_bn", 1366, 768),
    ("plan_lot5_insp_bn", 390, 844),
    ("plan_lot5_saved_bn", 1366, 768),
    ("plan_lot1_locked_bn", 1366, 768),
    ("plan_lot5_sup_en", 1366, 768),
]

for base_name, w, h in shot_targets:
    src_html = out_dir / f"{base_name}.html"
    out_png = Path(f"scratch/{base_name}_{w}.png").resolve()
    full_src = src_html.resolve().as_uri()

    cmd = [
        chrome,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        f"--user-data-dir={prof_dir.as_posix()}",
        f"--window-size={w},{h}",
        f"--screenshot={out_png.as_posix()}",
        full_src
    ]
    subprocess.run(cmd, check=True)
    print(f"Captured: {out_png} ({os.path.getsize(out_png)} bytes)")

    # Copy to brain artifacts
    target_brain = brain_dir / f"{base_name}_{w}.png"
    shutil.copyfile(out_png, target_brain)
    print(f"Copied to brain: {target_brain}")

