"""Backend hardening: tenant scoping, Postgres SQL translation and metrics."""
from __future__ import annotations

from app.core import db, metrics
from app.services import review as service


def test_lot_lookup_is_scoped_to_an_organisation():
    lot = service.lot(1)
    assert lot is not None
    assert service.lot(1, lot["organization_id"])["id"] == 1
    assert service.lot(1, lot["organization_id"] + 999_999) is None


def test_lot_cards_never_cross_the_tenant_boundary():
    from app.api.serializers import lot_cards

    assert lot_cards(999_999) == []
    assert any(card["id"] == 1 for card in lot_cards())


def test_postgres_translation_keeps_sqlite_untouched(monkeypatch):
    monkeypatch.setattr(db, "DATABASE_URL", "")
    assert db.dialect() == "sqlite"
    assert db.translate_sql("SELECT * FROM lot WHERE id=?") == "SELECT * FROM lot WHERE id=?"

    monkeypatch.setattr(db, "DATABASE_URL", "postgresql://user:pw@example/lotline")
    assert db.dialect() == "postgres"
    assert db.translate_sql("SELECT * FROM lot WHERE id=? AND lot_code=?") == (
        "SELECT * FROM lot WHERE id=%s AND lot_code=%s")
    schema = db.postgres_schema()
    assert "PRAGMA" not in schema
    assert "AUTOINCREMENT" not in schema
    assert "SERIAL PRIMARY KEY" in schema


def test_metrics_expose_latency_and_5xx_counters():
    metrics.reset()
    metrics.observe("GET", 200, 0.025)
    metrics.observe("POST", 503, 0.075)
    snap = metrics.snapshot()
    assert snap["requests_total"] == 2
    assert snap["errors_5xx"] == 1
    assert snap["status_5xx"] == 1
    assert snap["responses"] == {"2xx": 1, "5xx": 1}
    assert snap["latency_ms"]["count"] == 2
    assert snap["latency_ms"]["max"] == 75.0


def test_inference_queue_collapses_a_running_job(monkeypatch):
    from app.services import inference

    monkeypatch.setattr(inference, "mode", lambda: "background")
    monkeypatch.setattr(inference.db, "one", lambda *args, **kwargs: {"id": 7})
    assert inference.enqueue(1, 2) == "queued"


def test_inference_sync_mode_runs_inline(monkeypatch):
    from app.services import inference

    calls = []
    monkeypatch.setattr(inference, "mode", lambda: "sync")
    monkeypatch.setattr(inference, "run", lambda image_id, user_id: calls.append((image_id, user_id)) or "ok")
    assert inference.enqueue(4, 5) == "ok"
    assert calls == [(4, 5)]
