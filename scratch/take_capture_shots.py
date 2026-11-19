import subprocess
import os
from pathlib import Path

chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
cwd = os.path.abspath(".")
prof_dir = Path("C:/Users/Jitu/AppData/Local/Temp/chrome_qa_prof2").resolve()
prof_dir.mkdir(parents=True, exist_ok=True)

files = [
    ("scratch/cap_lot7_bn.html", "scratch/cap_lot7_1366.png", 1366, 768),
    ("scratch/cap_lot7_bn.html", "scratch/cap_lot7_390.png", 390, 844),
    ("scratch/cap_zero_bn.html", "scratch/cap_zero_1366.png", 1366, 768),
    ("scratch/admin_dash_bn.html", "scratch/admin_dash_1366.png", 1366, 768),
    ("scratch/admin_dash_bn.html", "scratch/admin_dash_390.png", 390, 844),
]

for src, out, w, h in files:
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
    print(f"Captured {full_out} size: {os.path.getsize(full_out)}")
