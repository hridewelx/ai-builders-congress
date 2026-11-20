"""GitHub OAuth: configuration, state handling, and identity mapping."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.core import db
from app.main import app
from app.services import oauth


def test_github_button_is_hidden_without_credentials(monkeypatch):
    monkeypatch.delenv("GITHUB_CLIENT_ID", raising=False)
    monkeypatch.delenv("GITHUB_CLIENT_SECRET", raising=False)
    client = TestClient(app)
    assert client.get("/api/auth/github", follow_redirects=False).status_code == 404
    payload = client.get("/api/bootstrap").json()
    assert payload["github_oauth"] is False


def test_github_start_redirects_with_state_cookie(monkeypatch):
    monkeypatch.setenv("GITHUB_CLIENT_ID", "client-id")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("GITHUB_REDIRECT_URI", "https://example.test/api/auth/github/callback")
    client = TestClient(app)
    response = client.get("/api/auth/github", follow_redirects=False)
    assert response.status_code == 303
    location = response.headers["location"]
    assert location.startswith("https://github.com/login/oauth/authorize?")
    assert "client_id=client-id" in location
    assert "state=" in location
    assert oauth.STATE_COOKIE in response.cookies


def test_github_callback_rejects_a_bad_state(monkeypatch):
    monkeypatch.setenv("GITHUB_CLIENT_ID", "client-id")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("GITHUB_REDIRECT_URI", "https://example.test/api/auth/github/callback")
    client = TestClient(app)
    response = client.get("/api/auth/github/callback?code=abc&state=wrong", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login?err=oauth"


def test_signed_state_survives_a_missing_cookie(monkeypatch):
    monkeypatch.setenv("GITHUB_CLIENT_ID", "client-id")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "client-secret")
    state = oauth.new_state()
    assert oauth.verify_state(None, state)
    assert not oauth.verify_state(None, state + "tampered")


def test_callback_works_without_the_state_cookie(monkeypatch):
    monkeypatch.setenv("GITHUB_CLIENT_ID", "client-id")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("GITHUB_REDIRECT_URI", "https://example.test/api/auth/github/callback")
    user = db.one("SELECT * FROM app_user WHERE role='inspector' LIMIT 1")
    monkeypatch.setattr(oauth, "exchange_code", lambda code, request=None: "token")
    monkeypatch.setattr(oauth, "fetch_identity",
                        lambda token: (user["email"], user["display_name"], "octocat"))
    monkeypatch.setattr(oauth, "login_or_create", lambda *args, **kwargs: user)

    client = TestClient(app)
    state = oauth.new_state()
    response = client.get(f"/api/auth/github/callback?code=abc&state={state}",
                          follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/"


def test_callback_sets_lax_session_cookies_and_no_store(monkeypatch):
    monkeypatch.setenv("GITHUB_CLIENT_ID", "client-id")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("GITHUB_REDIRECT_URI", "https://example.test/api/auth/github/callback")
    user = db.one("SELECT * FROM app_user WHERE role='inspector' LIMIT 1")
    monkeypatch.setattr(oauth, "exchange_code", lambda code, request=None: "token")
    monkeypatch.setattr(oauth, "fetch_identity",
                        lambda token: (user["email"], user["display_name"], "octocat"))
    monkeypatch.setattr(oauth, "login_or_create", lambda *args, **kwargs: user)

    client = TestClient(app)
    start = client.get("/api/auth/github", follow_redirects=False)
    assert start.headers["cache-control"] == "no-store"
    state = start.cookies.get(oauth.STATE_COOKIE)
    response = client.get(f"/api/auth/github/callback?code=abc&state={state}",
                          follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/"
    assert response.headers["cache-control"] == "no-store"
    cookies = response.headers.get_list("set-cookie")
    session_cookie = next(item for item in cookies if item.startswith("ll_session="))
    assert "SameSite=lax" in session_cookie


def test_unauthenticated_page_redirect_is_not_cacheable():
    client = TestClient(app)
    response = client.get("/lots", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"
    assert response.headers["cache-control"] == "no-store"


def test_identity_prefers_the_primary_verified_email(monkeypatch):
    def fake_request(url, *, data=None, token=None):
        if url.endswith("/user"):
            return {"login": "octocat", "name": "The Octocat"}
        return [
            {"email": "old@example.test", "primary": False, "verified": True},
            {"email": "Primary@Example.Test", "primary": True, "verified": True},
            {"email": "unverified@example.test", "primary": False, "verified": False},
        ]

    monkeypatch.setattr(oauth, "_json_request", fake_request)
    email, name, login = oauth.fetch_identity("token")
    assert email == "primary@example.test"
    assert name == "The Octocat"
    assert login == "octocat"


def test_identity_refuses_an_account_without_a_verified_email(monkeypatch):
    def fake_request(url, *, data=None, token=None):
        if url.endswith("/user"):
            return {"login": "octocat", "name": "The Octocat"}
        return [{"email": "unverified@example.test", "primary": True, "verified": False}]

    monkeypatch.setattr(oauth, "_json_request", fake_request)
    try:
        oauth.fetch_identity("token")
    except oauth.OAuthError:
        pass
    else:  # pragma: no cover - a regression would reach this branch
        raise AssertionError("an unverified email must not become a session")
