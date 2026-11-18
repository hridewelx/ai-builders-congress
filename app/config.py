"""Runtime configuration for the Lotline demo.

Every path and limit the application uses is defined once here. Values can be
overridden with environment variables so the same image runs locally, in CI and
on a hosted demo.
"""
from __future__ import annotations

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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
