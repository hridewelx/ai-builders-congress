"""Runtime configuration for the Lotline demo.

Every path and limit the application uses is defined once here. Values can be
overridden with environment variables so the same image runs locally, in CI and
on a hosted demo.
"""
from __future__ import annotations

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    from dotenv import load_dotenv

    load_dotenv()
    load_dotenv(os.path.join(BASE_DIR, ".env"))
except Exception:
    pass

# Built-in lightweight parser so .env is always loaded even without python-dotenv
_env_file = os.path.join(BASE_DIR, ".env")
if os.path.isfile(_env_file):
    try:
        with open(_env_file, "r", encoding="utf-8") as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith("#") and "=" in _line:
                    _k, _v = _line.split("=", 1)
                    _k = _k.strip()
                    _v = _v.strip().strip('"').strip("'")
                    if _k and _k not in os.environ:
                        os.environ[_k] = _v
    except Exception:
        pass

# --- filesystem -------------------------------------------------------------
DATA_DIR = os.environ.get("LOTLINE_DATA", os.path.join(BASE_DIR, "data"))
STORE_DIR = os.path.join(DATA_DIR, "store")
MODEL_DIR = os.path.join(DATA_DIR, "models")
DATASET_DIR = os.path.join(DATA_DIR, "dataset")
DB_PATH = os.environ.get("LOTLINE_DB", os.path.join(DATA_DIR, "lotline.db"))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# --- uploads ----------------------------------------------------------------
MAX_BYTES = 15 * 1024 * 1024
MAX_PIXELS = 50_000_000
MAX_IMAGE_EDGE = 1600

# --- domain constants -------------------------------------------------------
ZONES = ["I", "II", "III"]

# --- demo behaviour ---------------------------------------------------------
# One-click demo logins are only enabled when this is on. Never enable it for a
# deployment that holds real inspection data.
DEMO_LOGIN = os.environ.get("LOTLINE_DEMO", "1") == "1"
APP_NAME = "Lotline"
APP_TITLE = "Lotline — knitwear lot acceptance"

# --- inference --------------------------------------------------------------
# background: upload returns at once and a worker thread scores the image.
# sync: run in the request (tests and single-shot scripts).
INFERENCE_MODE = os.environ.get("LOTLINE_INFERENCE_MODE", "background").strip().lower()
if INFERENCE_MODE not in {"background", "sync"}:
    INFERENCE_MODE = "background"

# --- Cloudinary configuration -----------------------------------------------
CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "")
CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY", "")
CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET", "")
CLOUDINARY_FOLDER = os.environ.get("CLOUDINARY_FOLDER", "lotline_inspections")
CLOUDINARY_UPLOAD_PRESET = os.environ.get("CLOUDINARY_UPLOAD_PRESET", "")

# --- HTTPS Tunnel Configuration (Cloudflare Tunnel / Local Dev) -------------
PUBLIC_TUNNEL_URL = os.environ.get("PUBLIC_TUNNEL_URL", "").strip().rstrip("/")
TUNNEL_FILE = os.path.join(DATA_DIR, "tunnel_url.txt")


def is_valid_tunnel_url(url: str) -> bool:
    """Validate that url is a secure https URL with a well-formed domain."""
    if not isinstance(url, str) or not url.startswith("https://"):
        return False
    host = url[8:].split("/")[0].split(":")[0].strip().lower()
    if host in ("api.trycloudflare.com", "developers.cloudflare.com"):
        return False
    import re
    return bool(re.match(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+$", host))


def get_active_tunnel_url() -> str | None:
    """Return validated active public HTTPS tunnel URL, or None if inactive."""
    # 1. Dynamic environment variable check
    env_url = os.environ.get("PUBLIC_TUNNEL_URL", "").strip().rstrip("/")
    if env_url and is_valid_tunnel_url(env_url):
        return env_url

    # 2. Check runtime status file from scripts/tunnel.py
    if os.path.exists(TUNNEL_FILE):
        try:
            import time

            # Discard stale status files older than 24 hours
            if time.time() - os.path.getmtime(TUNNEL_FILE) < 86400:
                with open(TUNNEL_FILE, "r", encoding="utf-8") as f:
                    url = f.read().strip().rstrip("/")
                if is_valid_tunnel_url(url):
                    return url
        except Exception:
            pass
    return None


def get_active_tunnel_host() -> str | None:
    """Return hostname of the active tunnel URL, or None."""
    url = get_active_tunnel_url()
    if url:
        return url[8:].split("/")[0].split(":")[0].strip().lower()
    return None
