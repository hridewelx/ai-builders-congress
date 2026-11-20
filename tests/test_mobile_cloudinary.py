"""Test suite for automated mobile camera and Cloudinary integration."""
from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest
from PIL import Image
from starlette.requests import Request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core import db
from app.services import cloudinary
from app.services import review as service
from app.web.pages import ctx, templates


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    db.init()


def test_cloudinary_signature_generation():
    """Verify Cloudinary signature generation is deterministic and handles parameters correctly."""
    params = {
        "folder": "lotline_test/lot_1",
        "tags": "lot_1,view_2,lotline",
        "timestamp": 1700000000,
    }
    secret = "sample_cloudinary_secret_123"
    sig = cloudinary.generate_signature(params, secret)
    assert isinstance(sig, str)
    assert len(sig) == 40  # SHA-1 hex length

    # Re-computing with identical params yields exact same signature
    sig2 = cloudinary.generate_signature(params, secret)
    assert sig == sig2


def test_cloudinary_sign_upload_params():
    """Verify sign_upload_params returns proper fields and never exposes secret."""
    res = cloudinary.sign_upload_params(lot_id=1, view_id=10, garment_code="G-01")
    assert "upload_url" in res
    assert "timestamp" in res
    assert "folder" in res
    assert "tags" in res
    assert "lot_1" in res["folder"]
    assert "G-01" in res["tags"]
    # Secret must never be in returned dictionary
    assert "api_secret" not in res
    assert "CLOUDINARY_API_SECRET" not in res


def test_mobile_cam_template_rendering():
    """Verify mobile_capture.html template renders cleanly with camera viewfinder and shutter."""
    lot_id = 1
    L = service.lot(lot_id)
    units = service.units_with_views(lot_id)
    progress = service.progress(lot_id)
    user = {"id": 4, "role": "inspector", "display_name": "Rakib Hasan"}

    for lang in ["en", "bn"]:
        scope = {
            "type": "http",
            "method": "GET",
            "path": f"/lots/{lot_id}/mobile-cam",
            "headers": [(b"cookie", f"ll_lang={lang}".encode())],
            "query_string": b"",
        }
        req = Request(scope)
        c = ctx(
            req,
            active="lots",
            user=user,
            lot=L,
            units=units,
            progress=progress,
            can_write=True,
            next_view=None,
            cloudinary_configured=False,
        )
        resp = templates.TemplateResponse(req, "mobile_capture.html", c)
        assert resp.status_code == 200
        html = resp.body.decode("utf-8")
        assert "videoPreview" in html
        assert "shutterBtn" in html
        assert "targetPicker" in html
        assert "captureCanvas" in html
        assert "statusToast" in html


def test_capture_screen_has_mobile_cam_button_and_qr():
    """Verify capture.html now contains mobile camera launch button and QR modal."""
    lot_id = 1
    L = service.lot(lot_id)
    units = service.units_with_views(lot_id)
    progress = service.progress(lot_id)
    user = {"id": 4, "role": "inspector", "display_name": "Rakib Hasan"}

    scope = {
        "type": "http",
        "method": "GET",
        "path": f"/lots/{lot_id}/capture",
        "headers": [(b"cookie", b"ll_lang=en")],
        "query_string": b"",
    }
    req = Request(scope)
    c = ctx(
        req,
        active="lots",
        user=user,
        lot=L,
        units=units,
        progress=progress,
        can_write=True,
        session_token="test_sid.test_verifier",
        cloudinary_configured=True,
    )
    resp = templates.TemplateResponse(req, "capture.html", c)
    assert resp.status_code == 200
    html = resp.body.decode("utf-8")
    assert "/mobile-cam" in html
    assert "qrModal" in html
    assert "Launch Mobile Camera" in html
    assert "Cloudinary Active" in html


def test_image_table_has_cloudinary_columns():
    """Verify the database schema image table has the new metadata columns."""
    conn = db.connect()
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(image)").fetchall()}
    assert "cloudinary_url" in cols
    assert "cloudinary_public_id" in cols
    assert "captured_at" in cols
    assert "inspection_id" in cols
    assert "inspector_id" in cols

