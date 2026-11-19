"""In-process cache of the trained autoencoder.

Kept in its own module so the cache survives a reload of the code that uses it,
and so app.api.admin can report whether a model is loaded.
"""
from __future__ import annotations

_state: dict = {}
