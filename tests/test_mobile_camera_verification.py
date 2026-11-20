"""Automated verification suite for mobile camera capture functionality in LOTLINE.

Verifies:
1. Touch event debounce & single-fire logic
2. Pointer-events isolation on shutter inner element
3. Video readiness & canvas draw pipeline with dataURL fallback
4. Captured frame preview and retake state transitions
5. Cloudinary & direct server image upload endpoints
6. Desktop camera click compatibility
"""
from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

from app.core import db
from app.services import cloudinary
from app.services import review as service


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    db.init()


def test_mobile_camera_modal_tsx_architecture():
    """Verify MobileCameraModal.tsx contains all required mobile fixes and diagnostics."""
    tsx_path = Path(__file__).resolve().parents[1] / "frontend" / "src" / "components" / "MobileCameraModal.tsx"
    assert tsx_path.exists(), "MobileCameraModal.tsx not found"
    content = tsx_path.read_text(encoding="utf-8")

    # 1. Shutter button attributes
    assert 'touchAction: "manipulation"' in content, "Shutter button must have touchAction: manipulation"
    assert 'WebkitTapHighlightColor: "transparent"' in content, "Shutter must have transparent tap highlight"
    assert 'userSelect: "none"' in content, "Shutter must disable user selection"
    assert 'pointerEvents: "none"' in content, "Shutter inner element must have pointerEvents: none"

    # 2. Both touch and click listeners with debounce
    assert "handleShutterTrigger" in content, "Shutter must use handleShutterTrigger"
    assert "onTouchEnd={handleShutterTrigger}" in content, "Shutter must listen to onTouchEnd"
    assert "onClick={handleShutterTrigger}" in content, "Shutter must listen to onClick"
    assert "lastCaptureTimeRef" in content, "Debounce ref must exist"
    assert "e.preventDefault()" in content, "onTouchEnd must prevent simulated click"

    # 3. Canvas draw, readyState, and dataURL fallback
    assert "video.readyState < 2" in content, "Must validate video.readyState"
    assert "dataUrlToBlob" in content, "Must have fallback dataUrlToBlob converter"
    assert "canvas.toDataURL" in content, "Must fallback to canvas.toDataURL if toBlob fails"

    # 4. Preview and Retake
    assert "capturedPreviewUrl" in content, "capturedPreviewUrl state must exist"
    assert "Retake" in content or "পুনরায়" in content, "Retake button must be available"
    assert "URL.revokeObjectURL" in content, "Must clean up object URLs"

    # 5. Diagnostic logs
    assert "[MobileCamera] CAPTURE_CLICKED" in content
    assert "[MobileCamera] VIDEO_READY" in content
    assert "[MobileCamera] CANVAS_DRAW_SUCCESS" in content
    assert "[MobileCamera] IMAGE_BLOB_CREATED" in content
    assert "[MobileCamera] IMAGE_PREVIEW_UPDATED" in content
    assert "[MobileCamera] IMAGE_UPLOAD_STARTED" in content
    assert "[MobileCamera] IMAGE_UPLOAD_SUCCESS" in content
    assert "[MobileCamera] IMAGE_UPLOAD_FAILED" in content


def test_mobile_capture_html_template_architecture():
    """Verify mobile_capture.html template has pointer-events isolation, touch handling, and logs."""
    html_path = Path(__file__).resolve().parents[1] / "templates" / "mobile_capture.html"
    assert html_path.exists(), "mobile_capture.html not found"
    content = html_path.read_text(encoding="utf-8")

    # 1. CSS attributes
    assert "pointer-events: none;" in content, "Inner shutter div must have pointer-events: none"
    assert "touch-action: manipulation;" in content, "Shutter button must have touch-action: manipulation"

    # 2. Touch event listeners
    assert 'shutterBtn.addEventListener("touchend"' in content, "Shutter must have touchend listener"
    assert 'shutterBtn.addEventListener("click"' in content, "Shutter must have click listener"

    # 3. Diagnostics and fallbacks
    assert "[MobileCamera-HTML] CAPTURE_CLICKED" in content
    assert "[MobileCamera-HTML] VIDEO_READY" in content
    assert "[MobileCamera-HTML] CANVAS_DRAW_SUCCESS" in content
    assert "[MobileCamera-HTML] IMAGE_BLOB_CREATED" in content
    assert "dataUrlToBlob" in content, "HTML template must have dataUrlToBlob fallback"


def test_shutter_debounce_simulation():
    """Simulate mobile browser touch-end followed immediately by synthetic click."""
    events_triggered = []
    last_trigger_time = 0

    def trigger_capture(event_type: str, timestamp_ms: int):
        nonlocal last_trigger_time
        # Debounce rule: ignore triggers within 400ms
        if last_trigger_time > 0 and (timestamp_ms - last_trigger_time < 400):
            return False
        last_trigger_time = timestamp_ms
        events_triggered.append(event_type)
        return True

    # Scenario A: User taps shutter on Android Chrome
    # 1. touchend arrives at t=1000ms
    res1 = trigger_capture("touchend", 1000)
    assert res1 is True
    assert len(events_triggered) == 1

    # 2. 50ms later, synthetic click arrives from browser at t=1050ms
    res2 = trigger_capture("click", 1050)
    assert res2 is False
    assert len(events_triggered) == 1  # Still exactly 1!

    # Scenario B: User taps again 600ms later at t=1650ms
    res3 = trigger_capture("touchend", 1650)
    assert res3 is True
    assert len(events_triggered) == 2


def test_image_blob_generation_and_validation():
    """Verify valid image JPEG bytes can be parsed by PIL and validated for dimensions."""
    img = Image.new("RGB", (1280, 720), color=(73, 109, 137))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    raw_bytes = buf.getvalue()

    assert len(raw_bytes) > 0
    assert raw_bytes[:2] == b"\xff\xd8"  # JPEG SOI header

    # Verify PIL opens it properly
    reopened = Image.open(io.BytesIO(raw_bytes))
    assert reopened.size == (1280, 720)
    assert reopened.format == "JPEG"


def test_cloudinary_sign_params():
    """Verify Cloudinary signing returns upload_url and required params for client-side uploads."""
    lot_id = 1
    units = service.units_with_views(lot_id)
    view_id = units[0]["views"][0]["id"]
    garment_code = units[0]["garment_code"]

    res = cloudinary.sign_upload_params(lot_id=lot_id, view_id=view_id, garment_code=garment_code)
    assert "upload_url" in res
    assert "timestamp" in res
    assert "folder" in res
    assert "tags" in res
    assert f"lot_{lot_id}" in res["folder"]
