"""Bilingual UI strings. Bangla is a first-class UI language, not a subtitle.

The catalog lives in `catalogs/`, one module per screen area, so a translator
edits a 20-line file instead of a 600-line one. Keys keep their original prefix
(`lot.`, `rev.`, `dec.` …), which is how the screen modules are chosen.

This module composes them, exposes the lookup helpers, and refuses to start if
two catalogs define the same key — a silent overwrite is how "Create plan"
became "Create sampling plan" for one button and not the other.
"""
from __future__ import annotations

from .catalogs import admin, auth, capture, common, decision, how, lots, reports, review
from .formats import BN_DIGITS, BN_MONTHS, DHAKA_TZ, EN_MONTHS, format_datetime, format_grouped_num, format_num
from .reasons import REASON_BN

LANGS = {"en": "English", "bn": "বাংলা"}

_MODULES = (common, auth, lots, capture, review, decision, reports, admin, how)


def _merge() -> dict[str, tuple[str, str]]:
    merged: dict[str, tuple[str, str]] = {}
    origin: dict[str, str] = {}
    for module in _MODULES:
        for key, pair in module.CATALOG.items():
            if key in merged:
                raise RuntimeError(
                    f"duplicate translation key {key!r} in {module.__name__} "
                    f"and {origin[key]}")
            merged[key] = pair
            origin[key] = module.__name__
    return merged


STR: dict[str, tuple[str, str]] = _merge()


def t(key: str, lang: str = "en", **values: object) -> str:
    pair = STR.get(key)
    if not pair:
        return key
    text = pair[1] if lang == "bn" else pair[0]
    return text.format(**values) if values else text


def event_label(action: str, lang: str = "en") -> str:
    """Human label for an audit event key, with a safe fallback for new keys."""
    pair = STR.get("event." + str(action))
    if pair:
        return pair[1] if lang == "bn" else pair[0]
    return str(action).replace(".", " / ").replace("_", " ").strip().title()


def reason_text(code: str, lang: str = "en") -> str:
    """Plain-language explanation of a canonical reason code."""
    from app import engine

    if lang == "bn":
        return REASON_BN.get(code, engine.REASONS.get(code, ("", ""))[1])
    return engine.REASONS.get(code, ("", ""))[1]


__all__ = ["BN_DIGITS", "BN_MONTHS", "DHAKA_TZ", "EN_MONTHS", "LANGS", "REASON_BN",
           "STR", "event_label", "format_datetime", "format_grouped_num", "format_num",
           "reason_text", "t"]
