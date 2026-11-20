"""Google OAuth (OpenID Connect) for the demo.

Same contract as :mod:`app.services.oauth`: the browser is sent to Google,
comes back with a one-time code, and the server exchanges it for an identity.
Only a verified Google email can become a session. The Google access token is
used once and never stored.

Configuration:

    GOOGLE_CLIENT_ID
    GOOGLE_CLIENT_SECRET
    GOOGLE_REDIRECT_URI   (defaults to the callback URL of the current request)

State is signed with a provider-specific key so a state value minted for the
GitHub callback cannot be replayed against the Google callback.
"""
from __future__ import annotations

import os
import urllib.parse

from . import oauth

OAuthError = oauth.OAuthError
STATE_COOKIE = "ll_google_oauth_state"
STATE_TTL = oauth.STATE_TTL
AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
SCOPES = "openid email profile"


def client_id() -> str:
    return os.environ.get("GOOGLE_CLIENT_ID", "").strip()


def client_secret() -> str:
    return os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()


def enabled() -> bool:
    return bool(client_id() and client_secret())


def new_state() -> str:
    return oauth.new_state(client_secret())


def verify_state(cookie: str | None, state: str | None) -> bool:
    return oauth.verify_state(cookie, state, client_secret())


def redirect_uri(request=None) -> str:
    configured = os.environ.get("GOOGLE_REDIRECT_URI", "").strip()
    if configured:
        return configured
    if request is not None:
        return str(request.url_for("google_callback"))
    raise OAuthError("GOOGLE_REDIRECT_URI is not configured")


def authorize_url(state: str, request=None) -> str:
    params = {
        "client_id": client_id(),
        "redirect_uri": redirect_uri(request),
        "response_type": "code",
        "scope": SCOPES,
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    return f"{AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"


def exchange_code(code: str, request=None) -> str:
    payload = {
        "client_id": client_id(),
        "client_secret": client_secret(),
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri(request),
    }
    data = oauth._json_request(TOKEN_URL, data=payload)
    token = str(data.get("access_token") or "")
    if not token:
        raise OAuthError("Google did not issue an access token")
    return token


def fetch_identity(token: str) -> tuple[str, str, str]:
    """Return ``(email, display_name, subject)`` for a verified Google account."""
    data = oauth._json_request(USERINFO_URL, token=token)
    if not isinstance(data, dict):
        raise OAuthError("Google did not return an identity")
    if data.get("email_verified") is not True:
        raise OAuthError("Google account has no verified email")
    email = str(data.get("email") or "").strip().lower()
    if not email:
        raise OAuthError("Google account has no email")
    subject = str(data.get("sub") or "").strip() or email
    display_name = str(data.get("name") or email.split("@")[0]).strip()[:120]
    return email, display_name or email, subject


def login_or_create(email: str, display_name: str, login: str, ip: str = ""):
    return oauth.login_or_create(email, display_name, login, ip=ip, provider="google")


remember_code = oauth.remember_code
completed_code = oauth.completed_code

