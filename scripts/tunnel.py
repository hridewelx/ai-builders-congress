"""Cloudflare Tunnel Manager for Secure Mobile Camera Testing.

Provides temporary, trusted HTTPS access to the local FastAPI backend (port 8077).
Enables Android Chrome and iOS Safari to satisfy W3C Secure Context requirements
for live camera capture (getUserMedia) without installing root CAs or modifying browser flags.

Lifecycle:
- Checks for an existing, installed `cloudflared` executable (never auto-downloads binaries).
- Exposes ONLY local port 8077 (FastAPI). React port 5173 remains private.
- Safely captures the assigned `https://*.trycloudflare.com` URL.
- Writes active tunnel URL to `data/tunnel_url.txt` for automatic QR code resolution.
- On exit (Ctrl+C), terminates tunnel process and deletes `data/tunnel_url.txt` cleanly.
"""
from __future__ import annotations

import atexit
import os
import re
import shutil
import signal
import subprocess
import sys
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.environ.get("LOTLINE_DATA", os.path.join(BASE_DIR, "data"))
TUNNEL_FILE = os.path.join(DATA_DIR, "tunnel_url.txt")
TARGET_URL = "http://127.0.0.1:8077"

TUNNEL_REGEX = re.compile(r"https://([a-zA-Z0-9-]+)\.trycloudflare\.com")


def extract_tunnel_url(line: str) -> str | None:
    """Extract public tunnel URL while ignoring Cloudflare API endpoints."""
    match = TUNNEL_REGEX.search(line)
    if match:
        subdomain = match.group(1).lower()
        if subdomain not in ("api", "www", "developers"):
            return match.group(0).strip().rstrip("/")
    return None


def find_cloudflared() -> str | None:
    """Locate the cloudflared executable on the system without auto-downloading."""
    # 1. Custom environment variable
    custom_path = os.environ.get("CLOUDFLARED_PATH")
    if custom_path and os.path.isfile(custom_path) and os.access(custom_path, os.X_OK):
        return custom_path

    # 2. In PATH
    which_path = shutil.which("cloudflared")
    if which_path:
        return which_path

    # 3. Known standard Windows installation paths
    candidate_paths = [
        os.path.join(BASE_DIR, "cloudflared.exe"),
        os.path.join(BASE_DIR, ".bin", "cloudflared.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Cloudflare.cloudflared_Microsoft.Winget.Source_8wekyb3d8bbwe\cloudflared.exe"),
        os.path.expandvars(r"%ProgramFiles%\cloudflared\cloudflared.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\cloudflared\cloudflared.exe"),
        os.path.expandvars(r"%USERPROFILE%\scoop\shims\cloudflared.exe"),
        os.path.expandvars(r"%ChocolateyInstall%\bin\cloudflared.exe"),
    ]
    for p in candidate_paths:
        if os.path.isfile(p):
            return p

    return None


def print_missing_instructions() -> None:
    """Display instructions for installing cloudflared."""
    print("=" * 72)
    print(" [ERROR] 'cloudflared' executable was not found on your system.")
    print("=" * 72)
    print("\nTo enable HTTPS mobile camera testing, install Cloudflare Tunnel:")
    print("\nOption 1: Via Windows Package Manager (winget):")
    print("  winget install Cloudflare.cloudflared")
    print("\nOption 2: Direct download from official Cloudflare releases:")
    print("  1. Download 'cloudflared-windows-amd64.exe' from:")
    print("     https://github.com/cloudflare/cloudflared/releases/latest")
    print("  2. Rename it to 'cloudflared.exe' and place it in this project directory:")
    print(f"     {os.path.join(BASE_DIR, 'cloudflared.exe')}")
    print("\nOption 3: Set custom executable path:")
    print('  $env:CLOUDFLARED_PATH = "C:\\path\\to\\cloudflared.exe"')
    print("=" * 72)


def cleanup(proc: subprocess.Popen | None = None) -> None:
    """Terminate tunnel process and remove stale status files."""
    if os.path.exists(TUNNEL_FILE):
        try:
            os.remove(TUNNEL_FILE)
        except Exception:
            pass

    if proc and proc.poll() is None:
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass


def main() -> int:
    cloudflared_bin = find_cloudflared()
    if not cloudflared_bin:
        print_missing_instructions()
        return 1

    # Ensure DATA_DIR exists
    os.makedirs(DATA_DIR, exist_ok=True)

    # Clean any stale file from prior aborted sessions
    if os.path.exists(TUNNEL_FILE):
        try:
            os.remove(TUNNEL_FILE)
        except Exception:
            pass

    cmd = [cloudflared_bin, "tunnel", "--url", TARGET_URL]
    print("=" * 72)
    print(f"[*] Starting Cloudflare Tunnel targeting {TARGET_URL}...")
    print(f"[*] Binary: {cloudflared_bin}")
    print("=" * 72)

    proc = None
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            encoding="utf-8",
            errors="replace",
        )
    except Exception as exc:
        print(f"[!] Failed to launch cloudflared: {exc}")
        return 1

    # Register exit cleanup
    atexit.register(cleanup, proc)

    def signal_handler(sig, frame):
        print("\n[*] Shutting down Cloudflare Tunnel...")
        cleanup(proc)
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    tunnel_url = None
    start_time = time.time()

    try:
        # Read output stream until tunnel URL is announced
        for line in proc.stdout:
            # Check for tunnel URL pattern
            found_url = extract_tunnel_url(line)
            if found_url and not tunnel_url:
                tunnel_url = found_url
                # Write to status file for backend QR generator
                with open(TUNNEL_FILE, "w", encoding="utf-8") as f:
                    f.write(tunnel_url + "\n")
                    f.flush()

                print("\n" + "=" * 72)
                print(" [LOTLINE HTTPS TUNNEL ACTIVE]")
                print(f"  Public Tunnel URL: {tunnel_url}")
                print(f"  Local Target:      {TARGET_URL} (FastAPI)")
                print("  Security:          W3C Secure Context OK (TLS Wildcard)")
                print("  Mobile Ready:      Android Chrome Camera access enabled")
                print("=" * 72)
                print("[*] Both React SPA (5173) and Jinja2 (8077) QR codes are now updated.")
                print("[*] Press Ctrl + C to stop the tunnel and revert to LAN mode.\n")

            # Check if process died prematurely
            if proc.poll() is not None:
                break

            # Timeout after 30 seconds if no URL found
            if not tunnel_url and (time.time() - start_time > 30):
                print("[!] Timeout waiting for Cloudflare Tunnel URL assignment.")
                break

        if not tunnel_url:
            print("[!] Could not establish tunnel. Exit code:", proc.poll())
            cleanup(proc)
            return 1

        # Keep running until user terminates
        proc.wait()

    except KeyboardInterrupt:
        print("\n[*] Interrupted by user.")
    finally:
        cleanup(proc)
        print("[*] Tunnel terminated cleanly. System reverted to LAN mode.")

    return 0


if __name__ == "__main__":
    sys.exit(main())

