"""Google OAuth: configuration, state handling, and identity mapping."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.core import db
from app.main import app
from app.services import google_oauth, oauth


def _configure(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "google-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "google-client-secret")
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "https://example.test/api/auth/google/callback")
    monkeypatch.delenv("LOTLINE_STATE_SECRET", raising=False)


def test_google_button_is_hidden_without_credentials(monkeypatch):
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)
    client = TestClient(app)
    assert client.get("/api/auth/google", follow_redirects=False).status_code == 404
    payload = client.get("/api/bootstrap").json()
    assert payload["google_oauth"] is False


def test_google_start_redirects_with_state_cookie(monkeypatch):
    _configure(monkeypatch)
    client = TestClient(app)
    payload = client.get("/api/bootstrap").json()
    assert payload["google_oauth"] is True
    page = client.get("/login")
    assert 'href="/api/auth/google"' in page.text
    response = client.get("/api/auth/google", follow_redirects=False)
    assert response.status_code == 303
    location = response.headers["location"]
    assert location.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert "client_id=google-client-id" in location
    assert "scope=openid" in location
    assert "state=" in location
    assert google_oauth.STATE_COOKIE in response.cookies


def test_google_callback_rejects_a_bad_state(monkeypatch):
    _configure(monkeypatch)
    client = TestClient(app)
    response = client.get("/api/auth/google/callback?code=abc&state=wrong", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login?err=oauth"


def test_google_state_is_signed_and_provider_specific(monkeypatch):
    _configure(monkeypatch)
    monkeypatch.setenv("GITHUB_CLIENT_ID", "github-client-id")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "github-client-secret")
    state = google_oauth.new_state()
    assert google_oauth.verify_state(None, state)
    assert not google_oauth.verify_state(None, state + "tampered")
    assert not google_oauth.verify_state(None, oauth.new_state())


def test_google_callback_works_without_the_state_cookie(monkeypatch):
    _configure(monkeypatch)
    user = db.one("SELECT * FROM app_user WHERE role='inspector' LIMIT 1")
    monkeypatch.setattr(google_oauth, "exchange_code", lambda code, request=None: "token")
    monkeypatch.setattr(google_oauth, "fetch_identity",
                        lambda token: (user["email"], user["display_name"], "google-subject"))
    monkeypatch.setattr(google_oauth, "login_or_create", lambda *args, **kwargs: user)

    client = TestClient(app)
    response = client.get(
        f"/api/auth/google/callback?code=abc&state={google_oauth.new_state()}",
        follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/"
    cookies = response.headers.get_list("set-cookie")
    session_cookie = next(item for item in cookies if item.startswith("ll_session="))
    assert "SameSite=lax" in session_cookie


def test_identity_accepts_only_a_verified_email(monkeypatch):
    def fake_request(url, *, data=None, token=None):
        assert url.endswith("/userinfo")
        return {"sub": "12345", "email": "Primary@Example.Test", "email_verified": True,
                "name": "The Inspector"}

    monkeypatch.setattr(oauth, "_json_request", fake_request)
    email, name, subject = google_oauth.fetch_identity("token")
    assert email == "primary@example.test"
    assert name == "The Inspector"
    assert subject == "12345"


def test_identity_refuses_an_unverified_email(monkeypatch):
    def fake_request(url, *, data=None, token=None):
        return {"sub": "12345", "email": "unverified@example.test", "email_verified": False}

    monkeypatch.setattr(oauth, "_json_request", fake_request)
    try:
        google_oauth.fetch_identity("token")
    except google_oauth.OAuthError:
        pass
    else:  # pragma: no cover - a regression would reach this branch
        raise AssertionError("an unverified email must not become a session")
