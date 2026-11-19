"""Seed the demo: one factory, three roles, two buyers, eleven lots, staged photos.

All garment photos are procedurally staged for this demo and are labelled as
staged everywhere. No personal data, no real buyer data.
"""
from __future__ import annotations

from .fixtures import (  # noqa: F401
    DEMO_PASSWORD,  # noqa: F401
    _name,
    add_buyer,
    add_clause,
    add_lot,
    add_user,
    provisional_critical,
)
from .models import register_live_model  # noqa: F401
from .photos import (  # noqa: F401
    BASE_COLORS,  # noqa: F401
    _canonical,
    _file_sha,
    confirm,
    reject,
    review_view,
    settle_view,
    store_bytes,
    upload_photo,
)
from .scenario import run  # noqa: F401

__all__ = ["run", "DEMO_PASSWORD", "BASE_COLORS", "register_live_model"]
