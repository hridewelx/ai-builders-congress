"""Backwards-compatible import path. Canonical module: app.core.security."""
from app.core.security import *  # noqa: F401,F403
from app.core.security import (  # noqa: F401
    COOKIE,
    COOKIE_SECURE,
    SESSION_ABSOLUTE,
    SESSION_IDLE,
    check_csrf,
    clear_attempts,
    create_session,
    current_session,
    destroy_session,
    hash_password,
    last_failure_at,
    login_delay,
    policy_errors,
    record_attempt,
    revoke_user_sessions,
    verify_password,
)
