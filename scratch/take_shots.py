import subprocess
import time
from pathlib import Path

chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
html_dir = Path("docs/qa_screenshots/html").resolve()
out_dir = Path("docs/qa_screenshots").resolve()
prof_dir = Path("C:/Users/Jitu/AppData/Local/Temp/chrome_qa_prof").resolve()
prof_dir.mkdir(parents=True, exist_ok=True)

html_files = sorted(html_dir.glob("*.html"))
print(f"Found {len(html_files)} HTML files to screenshot.")

# Key screens for multi-viewport capture (desktop, tablet, mobile)
responsive_keys = [
    "01_login_en", "01_login_bn",
    "02_dashboard_inspector_en", "02_dashboard_inspector_bn",
    "03_lots_list_en", "03_lots_list_bn",
    "04_create_lot_en", "04_create_lot_bn",
    "05_lot_cockpit_en", "05_lot_cockpit_bn",
    "06_sampling_plan_supervisor_en", "07_photo_capture_en",
    "08_review_queue_en", "09_image_review_en",
    "10_decision_center_en", "11_inspection_report_en",
    "12_audit_log_en", "13_admin_users_en", "13_admin_health_en"
]

def capture_screen(html_path, out_png, width, height):
    cmd = [
        chrome,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        f"--user-data-dir={prof_dir.as_posix()}",
        f"--window-size={width},{height}",
        f"--screenshot={out_png.as_posix()}",
        f"file:///{html_path.as_posix()}"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if out_png.exists():
        size = out_png.stat().st_size
        return size
    else:
        print(f"Failed {out_png.name}: {res.stderr}")
        return 0

total_captured = 0
for hf in html_files:
    base = hf.stem
    # Standard desktop 1440x900
    out_desktop = out_dir / f"{base}_desktop_1440.png"
    s1 = capture_screen(hf, out_desktop, 1440, 900)
    if s1 > 0:
        total_captured += 1
        print(f"Captured: {out_desktop.name} ({s1 // 1024} KB)")

    # If it's one of the core screens, also capture tablet (768) and mobile (390)
    if any(base.startswith(k) for k in responsive_keys):
        out_tab = out_dir / f"{base}_tablet_768.png"
        s2 = capture_screen(hf, out_tab, 768, 1024)
        if s2 > 0:
            total_captured += 1
            print(f"Captured: {out_tab.name} ({s2 // 1024} KB)")

        out_mob = out_dir / f"{base}_mobile_390.png"
        s3 = capture_screen(hf, out_mob, 390, 844)
        if s3 > 0:
            total_captured += 1
            print(f"Captured: {out_mob.name} ({s3 // 1024} KB)")

print(f"\nSuccessfully captured {total_captured} screenshots across viewports!")
