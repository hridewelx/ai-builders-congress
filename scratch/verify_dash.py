import subprocess
from pathlib import Path
from starlette.requests import Request
from app.services import review as service
from app.services import vision
from app.web.pages import ctx, templates
from app.web.routes.dashboard import lot_cards
from app.web.stats import demo_stats, load_model_card

chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
prof_dir = Path("C:/Users/Jitu/AppData/Local/Temp/chrome_dash_prof").resolve()
prof_dir.mkdir(parents=True, exist_ok=True)
scratch_dir = Path("scratch").resolve()

user_insp = {"id": 4, "role": "inspector", "display_name": "Rakib Hasan", "email": "rakib@lotline.demo"}
counters = service.counters()
card = load_model_card()
stats = demo_stats()

for lang in ["bn", "en"]:
    scope = {"type": "http", "method": "GET", "path": "/", "headers": [(b"cookie", f"ll_lang={lang}".encode())], "query_string": b""}
    req = Request(scope)
    cards = lot_cards(req)
    c_insp = ctx(req, active="dashboard", user=user_insp, cards=cards[:6], counters=counters,
                 model=vision.MODEL_NAME, model_ok=True, stats=stats)
    
    html = templates.TemplateResponse(req, "dashboard.html", c_insp).body.decode("utf-8")
    # Replace relative /static/ references with file path or keep relative to workspace root
    html = html.replace('href="/static/', 'href="../static/').replace('src="/static/', 'src="../static/')
    
    html_file = scratch_dir / f"dash_{lang}.html"
    html_file.write_text(html, encoding="utf-8")
    print(f"Wrote {html_file}")

    for w, h, name in [(1440, 900, "1440"), (1366, 768, "1366"), (390, 844, "390")]:
        out_png = scratch_dir / f"dash_{lang}_{name}.png"
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
            print(f"Captured {out_png.name} ({out_png.stat().st_size} bytes)")
        else:
            print(f"Failed {out_png.name}: {res.stderr}")

