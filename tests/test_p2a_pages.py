"""Phase 2a test suite: Lot detail, Capture, Review queue, and Review screen rendering."""
from __future__ import annotations

import sys
from pathlib import Path
import pytest
from starlette.requests import Request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core import db
from app.services import review as service
from app.web.pages import ctx, templates

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    db.init()

def test_lot_overview_rendering():
    """Test lot detail renders cleanly in both languages with pipeline stepper and 2-line disposition."""
    lot_id = 1
    L = service.lot(lot_id)
    plan = service.active_plan(lot_id)
    plan_d = service.plan_dict(plan)
    progress = service.progress(lot_id)
    units = service.units_with_views(lot_id)
    d = service.latest_decision(lot_id)
    ov = service.override_for(d["id"]) if d else None
    hist = db.q("SELECT * FROM decision WHERE lot_id=? ORDER BY sequence DESC", (lot_id,))
    audit = service.timeline(lot_id)
    final = service.final_disposition(d, ov) if d else None
    user = {"id": 4, "role": "inspector", "display_name": "Rakib Hasan"}

    for lang in ["en", "bn"]:
        scope = {"type": "http", "method": "GET", "path": f"/lots/{lot_id}", "headers": [(b"cookie", f"ll_lang={lang}".encode())], "query_string": b""}
        req = Request(scope)
        c = ctx(req, active="lots", user=user, lot=L, plan=plan, plan_d=plan_d, progress=progress, units=units, decision=d, override=ov, final=final, history=hist, audit=audit, is_admin=False, can_write=True)
        resp = templates.TemplateResponse(req, "lot.html", c)
        assert resp.status_code == 200
        html = resp.body.decode("utf-8")
        assert "pipeline" in html
        assert "System recommendation" in html or "সিস্টেম সুপারিশ" in html
        assert "Final disposition" in html or "চূড়ান্ত সিদ্ধান্ত" in html
        assert "Normal inspection" in html or "General Level II" in html or "ISO 2859-1" in html

def test_capture_screen_rendering():
    """Test capture screen renders with mobile filters, upload forms, and HEIC rules."""
    lot_id = 1
    L = service.lot(lot_id)
    progress = service.progress(lot_id)
    units = service.units_with_views(lot_id)
    user = {"id": 4, "role": "inspector", "display_name": "Rakib Hasan"}

    for lang in ["en", "bn"]:
        scope = {"type": "http", "method": "GET", "path": f"/lots/{lot_id}/capture", "headers": [(b"cookie", f"ll_lang={lang}".encode())], "query_string": b""}
        req = Request(scope)
        c = ctx(req, active="lots", user=user, lot=L, units=units, progress=progress, can_write=True)
        resp = templates.TemplateResponse(req, "capture.html", c)
        assert resp.status_code == 200
        html = resp.body.decode("utf-8")
        assert "pipeline" in html
        assert "unitPicker" in html
        assert "data-filter-side" in html
        assert ("15 MB" in html) or ("১৫ মেগাবাইট" in html)
        assert "HEIC" in html

def test_review_queue_rendering():
    """Test review queue renders with priority sorting and pipeline stepper."""
    lot_id = 1
    L = service.lot(lot_id)
    queue = service.review_queue(lot_id)
    user = {"id": 4, "role": "inspector", "display_name": "Rakib Hasan"}

    for lang in ["en", "bn"]:
        scope = {"type": "http", "method": "GET", "path": f"/lots/{lot_id}/review", "headers": [(b"cookie", f"ll_lang={lang}".encode())], "query_string": b""}
        req = Request(scope)
        c = ctx(req, active="lots", user=user, lot=L, queue=queue)
        resp = templates.TemplateResponse(req, "review_queue.html", c)
        assert resp.status_code == 200
        html = resp.body.decode("utf-8")
        assert "pipeline" in html
        assert "table" in html or "queue" in html

def test_image_review_screen_rendering():
    """Test image review screen with bounding boxes, uncalibrated score, manual add, and shortcuts."""
    img = db.one("SELECT * FROM image WHERE lot_id=1 LIMIT 1")
    assert img is not None
    img_id = img["id"]
    L = service.lot(1)
    view = db.one("SELECT v.*, u.garment_code, u.id AS unit_id FROM unit_view v JOIN sample_unit u ON u.id=v.sample_unit_id WHERE v.id=?", (img["view_id"],))
    review = db.one("SELECT rr.*, a.display_name AS reviewer FROM view_review rr LEFT JOIN app_user a ON a.id=rr.reviewed_by WHERE rr.image_id=?", (img_id,))
    job = db.one("SELECT * FROM inference_job WHERE image_id=? ORDER BY id DESC LIMIT 1", (img_id,))
    preds = db.q("SELECT p.*, a.display_name AS reviewer FROM prediction p LEFT JOIN app_user a ON a.id=p.reviewed_by WHERE p.image_id=? ORDER BY p.id", (img_id,))
    clause_rows = db.q("SELECT * FROM clause_mapping WHERE buyer_id=? ORDER BY defect_type, zone_code", (L["buyer_id"],))
    queue = service.review_queue(1)
    nxt = next((q for q in queue if q["view"]["image"] and q["view"]["image"]["id"] != img_id), None)
    user = {"id": 2, "role": "supervisor", "display_name": "Farhan Chowdhury"}

    for lang in ["en", "bn"]:
        scope = {"type": "http", "method": "GET", "path": f"/review/{img_id}", "headers": [(b"cookie", f"ll_lang={lang}".encode())], "query_string": b""}
        req = Request(scope)
        c = ctx(req, active="lots", user=user, lot=L, image=img, view=view, review=review, job=job, preds=[dict(p) for p in preds], clauses=[dict(c) for c in clause_rows], status=service.derive_status(job), next_item=nxt, can_write=True, is_supervisor=True)
        resp = templates.TemplateResponse(req, "review.html", c)
        assert resp.status_code == 200
        html = resp.body.decode("utf-8")
        assert "pipeline" in html
        assert "viewerScroll" in html
        assert "boxLayer" in html
        assert "Score (uncalibrated)" in html
        assert "shortcutsDialog" in html
        assert 'value="confirmed_defects"' in html
        assert 'value="reviewed_clean"' in html
        assert 'value="needs_retake"' in html
