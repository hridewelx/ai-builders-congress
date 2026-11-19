"""The admin endpoint answers "which model, and how is it behaving" as JSON."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def _admin():
    client = TestClient(app)
    assert client.get("/demo/admin").status_code == 200
    return client


def test_registry_endpoint_reports_registry_and_live_metrics():
    payload = _admin().get("/admin/model/registry").json()
    assert set(payload) == {"registry", "live_30_days"}
    assert "entries" in payload["registry"]
    live = payload["live_30_days"]
    assert "confirmation_rate" in live
    assert "not recall or precision" in live["note"]
    if payload["registry"]["latest"]:
        assert payload["registry"]["latest"]["model"] == "frcnn-mnv3-v2"


def test_registry_endpoint_requires_admin():
    client = TestClient(app)
    assert client.get("/demo/inspector").status_code == 200
    assert client.get("/admin/model/registry").status_code == 403
