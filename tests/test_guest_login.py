"""The guest account: it may read the whole demo and may change nothing.

The guest is a real authenticated user (so every read path works exactly as for
an inspector), and it is refused at every write boundary: the lot-scoped write
check in `app/core/permissions.py` and the role guards of both the API and the
web routes.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core import db, permissions, security
from app.core.permissions import GUEST_EMAIL, can_write_lot, is_guest
from app.main import app
from app.services.seed.fixtures import add_guest


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    db.init()
    add_guest()  # the running app does this at startup; TestClient does not


def _guest_session() -> dict:
    user = db.one("SELECT * FROM app_user WHERE email=?", (GUEST_EMAIL,))
    assert user, "the guest account is seeded"
    return {"user": user, "session": {"id": 0, "csrf": ""}}


def _lot(owner_role: str) -> db.Row:
    return db.one(
        "SELECT l.* FROM lot l JOIN app_user u ON u.id = l.created_by WHERE u.role=? ORDER BY l.id LIMIT 1",
        (owner_role,),
    )


def _signed_in_guest(monkeypatch) -> TestClient:
    monkeypatch.setattr("app.web.routes.auth.DEMO_LOGIN", True)
    client = TestClient(app)
    assert client.get("/guest", follow_redirects=False).status_code == 303
    return client


def test_the_guest_is_seeded_and_has_no_usable_password():
    user = db.one("SELECT * FROM app_user WHERE email=?", (GUEST_EMAIL,))
    assert user is not None
    assert user["status"] == "active"
    # A read-only visitor must not be signable-in as a known account.
    assert not security.verify_password(user["password_hash"], "QualityFloor2026!")


def test_the_guest_never_writes_a_lot_it_does_not_own():
    session = _guest_session()
    assert is_guest(session) is True
    assert can_write_lot(session, _lot("inspector")) is False


def test_the_guest_never_writes_even_a_lot_it_appears_to_own():
    """Ownership is the inspector rule; the guest is refused whatever the owner."""
    user = dict(_guest_session()["user"])
    lot = dict(_lot("inspector"))
    lot["created_by"] = user["id"]
    assert can_write_lot({"user": user, "session": {}}, lot) is False


def test_an_inspector_still_writes_its_own_lot():
    """The guest rule must not leak into the role rule."""
    inspector = db.one("SELECT * FROM app_user WHERE email=?", ("inspector@lotline.demo",))
    lot = db.one("SELECT * FROM lot WHERE created_by=? ORDER BY id LIMIT 1", (inspector["id"],))
    assert lot is not None
    assert can_write_lot({"user": inspector, "session": {}}, lot) is True


def test_guest_login_sets_a_session_and_lands_on_the_dashboard(monkeypatch):
    monkeypatch.setattr("app.web.routes.auth.DEMO_LOGIN", True)
    response = TestClient(app).get("/guest", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/"
    assert any(name.startswith("ll_") for name in response.cookies)
    assert 0 < len(response.cookies.get("ll_csrf") or "") < 200


def test_guest_login_is_off_when_the_demo_is_off(monkeypatch):
    monkeypatch.setattr("app.web.routes.auth.DEMO_LOGIN", False)
    assert TestClient(app).get("/guest", follow_redirects=False).status_code == 404


def test_guest_reads_the_working_pages(monkeypatch):
    client = _signed_in_guest(monkeypatch)
    for path in ("/lots", "/lots/6", "/lots/6/review", "/lots/6/plan", "/lots/6/capture",
                 "/lots/1/decision", "/how"):
        assert client.get(path).status_code == 200, path


def test_guest_is_refused_the_supervisor_and_admin_pages(monkeypatch):
    client = _signed_in_guest(monkeypatch)
    for path in ("/admin", "/audit"):
        assert client.get(path, follow_redirects=False).status_code == 403, path
    # an admin-only API too, not just a page
    assert client.get("/admin/model/registry", follow_redirects=False).status_code == 403


def test_guest_is_refused_a_write_form(monkeypatch):
    """The plan page is readable; its save button is not a guest action."""
    client = _signed_in_guest(monkeypatch)
    token = client.cookies.get("ll_csrf") or ""
    response = client.post("/lots/6/plan", data={"csrf": token, "n": 200, "counting_mode": "single",
                                                 "critical_ac": 0, "critical_re": 0, "major_ac": 2,
                                                 "major_re": 3, "minor_ac": 5, "minor_re": 6,
                                                 "source_edition": "x", "source_reference": "y",
                                                 "confirmed": "1"},
                           follow_redirects=False)
    assert response.status_code == 403
    assert db.one("SELECT id FROM plan WHERE lot_id=6 LIMIT 1") is not None  # nothing new, nothing lost
    unit = client.post("/lots/6/units", data={"csrf": token, "garment_code": "GUEST-UNIT"},
                       follow_redirects=False)
    assert unit.status_code == 403
    assert not db.one("SELECT id FROM sample_unit WHERE garment_code='GUEST-UNIT'")


def test_guest_is_refused_the_write_api(monkeypatch):
    monkeypatch.setattr("app.api.auth.DEMO_LOGIN", True)
    client = TestClient(app)
    assert client.post("/api/auth/demo/guest").status_code == 200
    headers = {"x-csrf-token": client.cookies.get("ll_csrf") or ""}
    lot = _lot("inspector")
    created = client.post("/api/lots", json={"lot_code": "GUEST-1", "buyer_id": 1, "product_id": 1,
                                             "lot_size": 100, "color": "Black"}, headers=headers)
    assert created.status_code == 403
    assert client.post(f"/api/lots/{lot['id']}/plan", json={}, headers=headers).status_code == 403
    assert client.post(f"/api/lots/{lot['id']}/decisions", json={}, headers=headers).status_code == 403


def test_the_login_page_offers_a_guest_way_in(monkeypatch):
    monkeypatch.setattr("app.web.pages.DEMO_LOGIN", True)
    body = TestClient(app).get("/login").text
    assert 'href="/guest"' in body
    assert "অতিথি হিসেবে দেখুন" in body or "Continue as guest" in body


def test_the_login_page_hides_the_guest_button_when_the_demo_is_off(monkeypatch):
    monkeypatch.setattr("app.web.pages.DEMO_LOGIN", False)
    body = TestClient(app).get("/login").text
    assert 'href="/guest"' not in body


def test_the_sidebar_calls_the_guest_a_guest(monkeypatch):
    client = _signed_in_guest(monkeypatch)
    body = client.get("/lots").text
    assert "guest-tag" in body
    assert permissions.is_guest({"user": db.one("SELECT * FROM app_user WHERE email=?", (GUEST_EMAIL,))})
