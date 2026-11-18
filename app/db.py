"""Backwards-compatible import path. Canonical module: app.core.db."""
from app.core.db import *  # noqa: F401,F403
from app.core.db import (  # noqa: F401
    DATA_DIR,
    DB_PATH,
    SCHEMA,
    STORE_DIR,
    audit,
    connect,
    init,
    new_id,
    now,
    one,
    q,
    x,
)
