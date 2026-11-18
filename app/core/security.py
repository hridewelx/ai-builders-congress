"""Identity: Argon2id passwords, server-side sessions, CSRF, role checks."""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from . import db

# OWASP-minimum-class parameters; the encoded hash carries them so they can rise.
_ph = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1, hash_len=32, salt_len=16)

SESSION_IDLE = 30 * 60
SESSION_ABSOLUTE = 8 * 60 * 60
COOKIE = "ll_session"
COOKIE_SECURE = os.environ.get("LOTLINE_SECURE_COOKIE", "0") == "1"


def hash_password(pw: str) -> str:
    return _ph.hash(pw)


def verify_password(stored: str, pw: str) -> bool:
    try:
        return _ph.verify(stored, pw)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def policy_errors(pw: str, email: str = "", name: str = "") -> list[str]:
    errs = []
    if len(pw) < 15:
        errs.append("At least 15 characters.")
    if len(pw) > 128:
        errs.append("At most 128 characters.")
    low = pw.lower()
    if "lotline" in low:
        errs.append("Must not contain the product name.")
    if email and email.split("@")[0].lower() and email.split("@")[0].lower() in low:
        errs.append("Must not contain the email local part.")
    if name and name.lower() in low:
        errs.append("Must not contain your display name.")
    for common in ("password", "123456", "qwerty", "letmein", "admin"):
        if common in low:
            errs.append("Too common.")
            break
    return errs


def _token() -> str:
    return secrets.token_urlsafe(32)


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def create_session(user_id: int, ip: str = "") -> tuple[str, str]:
    sid = secrets.token_hex(16)
    verifier = _token()
    csrf = _token()
    t = time.time()
    db.x("INSERT INTO user_session(id,user_id,verifier_hash,csrf,created_at,last_seen,absolute_expiry)"
         " VALUES (?,?,?,?,?,?,?)", (sid, user_id, _sha(verifier), csrf, t, t, t + SESSION_ABSOLUTE))
    db.audit(user_id, str(user_id), "session.created", "user_session", sid, ip=ip)
    return f"{sid}.{verifier}", csrf


def current_session(raw: str | None):
    if not raw or "." not in raw:
        return None
    sid, verifier = raw.split(".", 1)
    row = db.one("SELECT * FROM user_session WHERE id=?", (sid,))
    if not row:
        return None
    now = time.time()
    if now > row["absolute_expiry"] or now - row["last_seen"] > SESSION_IDLE:
        db.x("DELETE FROM user_session WHERE id=?", (sid,))
        return None
    if not hmac.compare_digest(row["verifier_hash"], _sha(verifier)):
        return None
    if now - row["last_seen"] > 60:
        db.x("UPDATE user_session SET last_seen=? WHERE id=?", (now, sid))
    user = db.one("SELECT * FROM app_user WHERE id=?", (row["user_id"],))
    if not user or user["status"] != "active":
        return None
    return {"session": row, "user": user}


def destroy_session(sid: str, user_id: int) -> None:
    db.x("DELETE FROM user_session WHERE id=?", (sid,))
    db.audit(user_id, str(user_id), "session.destroyed", "user_session", sid)


def check_csrf(sess: dict | None, token: str | None) -> bool:
    if not sess or not token:
        return False
    return hmac.compare_digest(sess["session"]["csrf"], token)


def login_delay(email: str) -> int:
    """Progressive delay: 0 for the first four failures, 30 s at five, doubling."""
    row = db.one("SELECT COUNT(*) AS n FROM login_attempt WHERE account_key=? AND ok=0", (email.lower(),))
    n = row["n"] if row else 0
    if n < 4:
        return 0
    return min(15 * 60, 30 * (2 ** (n - 4)))


def last_failure_at(email: str) -> float:
    row = db.one("SELECT MAX(at) AS at FROM login_attempt WHERE account_key=? AND ok=0", (email.lower(),))
    return float(row["at"]) if row and row["at"] else 0.0


def record_attempt(email: str, ok: bool, ip: str = "") -> None:
    db.x("INSERT INTO login_attempt(account_key,at,ok,ip) VALUES (?,?,?,?)",
         (email.lower(), time.time(), 1 if ok else 0, ip))


def clear_attempts(email: str) -> None:
    db.x("DELETE FROM login_attempt WHERE account_key=?", (email.lower(),))


def revoke_user_sessions(user_id: int, keep_sid: str | None = None) -> None:
    if keep_sid:
        db.x("DELETE FROM user_session WHERE user_id=? AND id<>?", (user_id, keep_sid))
    else:
        db.x("DELETE FROM user_session WHERE user_id=?", (user_id,))
