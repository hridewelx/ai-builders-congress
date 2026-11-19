import subprocess
from pathlib import Path
from starlette.requests import Request
from app.core import db
from app.services import review as service
from app.web.pages import ctx, templates
from app.web.routes.lots import lot_page

chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
prof_dir = Path("C:/Users/Jitu/AppData/Local/Temp/chrome_lot_prof").resolve()
prof_dir.mkdir(parents=True, exist_ok=True)
scratch_dir = Path("scratch").resolve()

user_insp = {"id": 4, "role": "inspector", "display_name": "Rakib Hasan", "email": "rakib@lotline.demo"}
user_sup = {"id": 2, "role": "supervisor", "display_name": "Farhan Chowdhury", "email": "farhan@lotline.demo"}

test_cases = [
    # lot_id, user, lang, name
    (1, user_insp, "bn", "lot1_insp_bn"),
    (1, user_insp, "en", "lot1_insp_en"),
    (5, user_insp, "bn", "lot5_insp_bn_noplan"),
    (5, user_sup, "bn", "lot5_sup_bn_noplan"),
]

for lot_id, user, lang, tag in test_cases:
    scope = {"type": "http", "method": "GET", "path": f"/lots/{lot_id}", "headers": [(b"cookie", f"ll_lang={lang}".encode())], "query_string": b""}
    req = Request(scope)
    
    L = service.lot(lot_id)
    plan = service.active_plan(lot_id)
    p = service.progress(lot_id)
    units = service.units_with_views(lot_id)
    d = service.latest_decision(lot_id)
    ov = service.override_for(d["id"]) if d else None
    hist = db.q("SELECT * FROM decision WHERE lot_id=? ORDER BY sequence DESC", (lot_id,))
    audit = service.timeline(lot_id)
    is_admin = user["role"] == "admin"
    
    c = ctx(req, active="lots", user=user, lot=L, plan=plan, plan_d=service.plan_dict(plan),
            progress=p, units=units, decision=d, override=ov,
            final=service.final_disposition(d, ov) if d else None, history=hist, audit=audit,
            is_admin=is_admin, can_write=(not is_admin and L["status"] != "decided"))
            
    html = templates.TemplateResponse(req, "lot.html", c).body.decode("utf-8")
    html = html.replace('href="/static/', 'href="../static/').replace('src="/static/', 'src="../static/')
    
    html_file = scratch_dir / f"{tag}.html"
    html_file.write_text(html, encoding="utf-8")
    print(f"Wrote {html_file.name}")
    
    for w, h, vp in [(1440, 900, "1440"), (1366, 768, "1366"), (390, 844, "390")]:
        out_png = scratch_dir / f"{tag}_{vp}.png"
        cmd = [
            chrome,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            f"--user-data-dir={prof_dir.as_posix()}",
            f"--window-size={w},{h}",
            f"--screenshot={out_png.as_posix()}",
            f"file:///{html_file.as_posix()}"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if out_png.exists():
            print(f"  Captured {out_png.name} ({out_png.stat().st_size} bytes)")
        else:
            print(f"  Failed {out_png.name}: {res.stderr}")

