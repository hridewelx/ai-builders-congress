"""GitHub OAuth for the demo.

The browser is sent to GitHub, comes back with a one-time code, and the server
exchanges it for an identity. The GitHub access token is used once and never
stored; the existing Argon2id-backed server session is issued exactly as for a
password login.

Only the OAuth App credentials are configuration:

    GITHUB_CLIENT_ID
    GITHUB_CLIENT_SECRET
    GITHUB_REDIRECT_URI   (defaults to the callback URL of the current request)
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request

from ..config import APP_NAME
from ..core import db, security

log = logging.getLogger("lotline.oauth")

STATE_COOKIE = "ll_oauth_state"
STATE_TTL = 10 * 60
_CODE_TTL = 2 * 60
_COMPLETED: dict[str, tuple[float, int]] = {}
AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
TOKEN_URL = "https://github.com/login/oauth/access_token"
API_URL = "https://api.github.com"
SCOPES = "read:user user:email"


class OAuthError(Exception):
    """A GitHub login attempt that cannot safely become a session."""


def client_id() -> str:
    return os.environ.get("GITHUB_CLIENT_ID", "").strip()


def client_secret() -> str:
    return os.environ.get("GITHUB_CLIENT_SECRET", "").strip()


def enabled() -> bool:
    return bool(client_id() and client_secret())


def _state_key() -> bytes:
    # Stable across restarts: an OAuth round trip must not fail because the
    # development server reloaded while the user was on GitHub.
    return (os.environ.get("LOTLINE_STATE_SECRET", "").strip() or client_secret()).encode()


def new_state() -> str:
    """A signed, short-lived state value.

    The cookie is still set for browsers that keep it, but verification does
    not depend on that cookie surviving GitHub's cross-site redirect.
    """
    raw = f"{secrets.token_urlsafe(16)}.{int(time.time())}"
    signature = hmac.new(_state_key(), raw.encode(), hashlib.sha256).hexdigest()
    return f"{raw}.{signature}"


def redirect_uri(request=None) -> str:
    configured = os.environ.get("GITHUB_REDIRECT_URI", "").strip()
    if configured:
        return configured
    if request is not None:
        return str(request.url_for("github_callback"))
    raise OAuthError("GITHUB_REDIRECT_URI is not configured")


def authorize_url(state: str, request=None) -> str:
    params = {
        "client_id": client_id(),
        "redirect_uri": redirect_uri(request),
        "scope": SCOPES,
        "state": state,
        "allow_signup": "true",
    }
    return f"{AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"


def verify_state(cookie: str | None, state: str | None) -> bool:
    if not state:
        return False
    if cookie and hmac.compare_digest(str(cookie), str(state)):
        return True
    parts = str(state).split(".")
    if len(parts) != 3:
        return False
    raw = ".".join(parts[:2])
    expected = hmac.new(_state_key(), raw.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, parts[2]):
        return False
    try:
        issued = int(parts[1])
    except ValueError:
        return False
    return 0 <= time.time() - issued <= STATE_TTL


def remember_code(code: str) -> None:
    """Remember that this authorization code already produced a session.

    A duplicated/prefetched callback must not turn a successful login into
    "GitHub sign-in failed" just because GitHub codes are single-use.
    """
    now = time.time()
    for key, (issued, _) in list(_COMPLETED.items()):
        if now - issued > _CODE_TTL:
            _COMPLETED.pop(key, None)
    _COMPLETED[hashlib.sha256(code.encode()).hexdigest()] = (now, 1)


def completed_code(code: str) -> bool:
    key = hashlib.sha256(code.encode()).hexdigest()
    item = _COMPLETED.get(key)
    return bool(item and time.time() - item[0] <= _CODE_TTL)


def _json_request(url: str, *, data: dict | None = None, token: str | None = None):
    headers = {
        "Accept": "application/json",
        "User-Agent": f"{APP_NAME.replace(' ', '-')}-demo",
    }
    body = urllib.parse.urlencode(data).encode() if data is not None else None
    if body is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=body, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise OAuthError(f"GitHub request failed: {type(exc).__name__}") from exc


def exchange_code(code: str, request=None) -> str:
    payload = {
        "client_id": client_id(),
        "client_secret": client_secret(),
        "code": code,
        "redirect_uri": redirect_uri(request),
    }
    data = _json_request(TOKEN_URL, data=payload)
    token = str(data.get("access_token") or "")
    if not token:
        raise OAuthError("GitHub did not issue an access token")
    return token


def fetch_identity(token: str) -> tuple[str, str, str]:
    """Return ``(email, display_name, login)`` using only a verified email."""
    user = _json_request(f"{API_URL}/user", token=token)
    emails = _json_request(f"{API_URL}/user/emails", token=token)
    if not isinstance(emails, list):
        raise OAuthError("GitHub did not return an email list")
    verified = [item for item in emails if item.get("verified") and item.get("email")]
    primary = next((item for item in verified if item.get("primary")), None)
    chosen = primary or (verified[0] if verified else None)
    if not chosen:
        raise OAuthError("GitHub account has no verified email")
    email = str(chosen["email"]).strip().lower()
    login = str(user.get("login") or "github-user")
    display_name = str(user.get("name") or login).strip()[:120]
    return email, display_name or login, login


def login_or_create(email: str, display_name: str, login: str, ip: str = ""):
    """Find the local account or create an inspector account for this demo.

    Existing accounts keep their role. OAuth is a login method, not a role
    grant; the seeded demo buttons remain the way to switch roles.
    """
    user = db.one("SELECT * FROM app_user WHERE email=?", (email,))
    if user:
        if user["status"] != "active":
            raise OAuthError("account is disabled")
        db.audit(user["id"], user["display_name"], "auth.github", "app_user", user["id"],
                 after={"login": login}, ip=ip or None)
        return user

    user_id = db.x(
        "INSERT INTO app_user(organization_id,email,display_name,role,password_hash,status,"
        "must_change,created_at) VALUES (1,?,?,?,?,'active',0,?)",
        (email, display_name, "inspector", security.hash_password(secrets.token_urlsafe(32)), db.now()))
    user = db.one("SELECT * FROM app_user WHERE id=?", (user_id,))
    db.audit(user_id, display_name, "user.github_created", "app_user", user_id,
             after={"email": email, "login": login, "role": "inspector"}, ip=ip or None)
    return user
