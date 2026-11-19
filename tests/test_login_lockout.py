"""The login delay must be enforced, not just logged."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.core import db, security
from app.main import app

EMAIL = "lockout-probe@example.invalid"


def _clear() -> None:
    db.x("DELETE FROM login_attempt WHERE account_key=?", (EMAIL,))


def test_delay_grows_then_caps():
    _clear()
    try:
        delays = []
        for _ in range(8):
            delays.append(security.login_delay(EMAIL))
            security.record_attempt(EMAIL, False)
        assert delays[:4] == [0, 0, 0, 0], "the first four failures must not delay a real user"
        assert delays[4] == 30, "the fifth failure starts a 30 s delay"
        assert delays[5] == 60 and delays[6] == 120, "the delay doubles"
        assert max(delays) <= 15 * 60, "the delay is capped at 15 minutes"
    finally:
        _clear()


def test_blocked_attempt_issues_no_session():
    _clear()
    try:
        for _ in range(5):
            security.record_attempt(EMAIL, False)
        client = TestClient(app)
        response = client.post("/login", data={"email": EMAIL, "password": "not-the-password"},
                               follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/login?err=rl"
        assert security.COOKIE not in response.cookies
    finally:
        _clear()
