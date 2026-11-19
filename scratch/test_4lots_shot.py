from __future__ import annotations
import os
import subprocess
from pathlib import Path
from starlette.requests import Request
from app.services import review, vision
from app.web.pages import ctx, templates
from app.web.routes.dashboard import lot_cards
from app.web.stats import demo_stats

user_insp = {"id": 4, "role": "inspector", "display_name": "Rakib Hasan", "email": "rakib@lotline.demo"}
req = Request({"type": "http", "method": "GET", "path": "/", "headers": [(b"cookie", b"ll_lang=bn")], "query_string": b""})
cards = lot_cards(req)
c = ctx(req, active="dashboard", user=user_insp, cards=cards[:4], counters=review.counters(),
        model=vision.MODEL_NAME, model_ok=True, stats=demo_stats())
html = templates.TemplateResponse(req, "dashboard.html", c).body.decode("utf-8")

os.makedirs("scratch", exist_ok=True)
with open("scratch/dash_4lots.html", "w", encoding="utf-8") as f:
    f.write(html)

chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
prof_dir = Path("C:/Users/Jitu/AppData/Local/Temp/chrome_qa_prof4").resolve()
prof_dir.mkdir(parents=True, exist_ok=True)
out_png = os.path.abspath("scratch/dash_4lots_1366.png").replace("\\", "/")
full_src = "file:///" + os.path.abspath("scratch/dash_4lots.html").replace("\\", "/")

cmd = [
    chrome,
    "--headless=new",
    "--disable-gpu",
    "--no-sandbox",
    f"--user-data-dir={prof_dir.as_posix()}",
    "--window-size=1366,768",
    f"--screenshot={out_png}",
    full_src
]
subprocess.run(cmd, check=True)
print("Captured", out_png, "size:", os.path.getsize(out_png))

