"""Backwards-compatible import path. Canonical module: app.domain.engine.

The engine is a pure function: it imports only hashlib and json, so it can never
call a model, a database or the network. This shim keeps older imports working.
"""
from app.domain.engine import *  # noqa: F401,F403
from app.domain.engine import (  # noqa: F401
    CLASSES,
    ENGINE_VERSION,
    REASONS,
    SEVERITY_RANK,
    PlanInvalid,
    count_units,
    decide,
    snapshot_hash,
    validate_plan,
)
