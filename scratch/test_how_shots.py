from __future__ import annotations
import os
import subprocess
from pathlib import Path
from starlette.requests import Request
from app.web.pages import ctx, templates
from app.web.stats import demo_stats, load_model_card

card = load_model_card()
stats = demo_stats()

roles = [
    ("admin", {"id": 1, "role": "admin", "display_name": "Nusrat Jahan", "email": "nusrat@lotline.demo"}),
    ("supervisor", {"id": 2, "role": "supervisor", "display_name": "Farhan Chowdhury", "email": "farhan@lotline.demo"}),
    ("inspector", {"id": 4, "role": "inspector", "display_name": "Rakib Hasan", "email": "rakib@lotline.demo"}),
]

os.makedirs("scratch/how_screens", exist_ok=True)
html_files = []

for rname, user in roles:
    for lang in ["bn", "en"]:
        req = Request({"type": "http", "method": "GET", "path": "/how", "headers": [(b"cookie", f"ll_lang={lang}".encode())], "query_string": b""})
        c = ctx(req, active="how", user=user, card=card, stats=stats)
        html = templates.TemplateResponse(req, "how.html", c).body.decode("utf-8")
        out_html = f"scratch/how_screens/how_{rname}_{lang}.html"
        with open(out_html, "w", encoding="utf-8") as f:
            f.write(html)
        html_files.append((out_html, rname, lang))

chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
prof_dir = Path("C:/Users/Jitu/AppData/Local/Temp/chrome_qa_prof_how").resolve()
prof_dir.mkdir(parents=True, exist_ok=True)

shots = [
    ("scratch/how_screens/how_admin_bn.html", "scratch/how_admin_bn_1366.png", 1366, 768),
    ("scratch/how_screens/how_admin_bn.html", "scratch/how_admin_bn_390.png", 390, 844),
    ("scratch/how_screens/how_supervisor_bn.html", "scratch/how_sup_bn_1366.png", 1366, 768),
    ("scratch/how_screens/how_inspector_bn.html", "scratch/how_insp_bn_1366.png", 1366, 768),
    ("scratch/how_screens/how_inspector_bn.html", "scratch/how_insp_bn_390.png", 390, 844),
    ("scratch/how_screens/how_admin_en.html", "scratch/how_admin_en_1366.png", 1366, 768),
]

for src, out, w, h in shots:
    full_src = "file:///" + os.path.abspath(src).replace("\\", "/")
    full_out = os.path.abspath(out).replace("\\", "/")
    cmd = [
        chrome,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        f"--user-data-dir={prof_dir.as_posix()}",
        f"--window-size={w},{h}",
        f"--screenshot={full_out}",
        full_src
    ]
    subprocess.run(cmd, check=True)
    print(f"Captured {full_out} (size: {os.path.getsize(full_out)} bytes)")

print("All screenshots captured successfully.")

