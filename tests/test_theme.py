"""The dark theme is a second palette, not a second stylesheet.

Three things are checked, because all three have bitten a real UI:
  1. every colour token the light theme defines is also defined in the dark
     block, so no component silently keeps a white surface;
  2. text keeps WCAG AA contrast against the surface it sits on, measured
     with alpha compositing because the chips are translucent;
  3. the theme is chosen before first paint and the toggle is reachable and
     labelled on every page, including the ones outside the app shell.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

CSS = Path("static/app.css").read_text(encoding="utf-8")
ROOT = Path("templates")


# --------------------------------------------------------------------------
# palette parsing
# --------------------------------------------------------------------------
def _block(selector: str) -> str:
    start = CSS.index(selector)
    depth = 0
    for index in range(start, len(CSS)):
        if CSS[index] == "{":
            depth += 1
        elif CSS[index] == "}":
            depth -= 1
            if depth == 0:
                return CSS[start : index + 1]
    raise AssertionError(f"unclosed block for {selector}")


def _tokens(block: str) -> dict[str, str]:
    return {
        name: value.strip()
        for name, value in re.findall(r"(--[a-z0-9-]+)\s*:\s*([^;]+);", block)
    }


LIGHT = _tokens(_block(":root {"))
DARK = _tokens(_block(':root[data-theme="dark"] {'))


def _is_colour(value: str) -> bool:
    return value.startswith("#") or value.startswith("rgb")


def _hex(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    if len(value) == 3:
        value = "".join(char * 2 for char in value)
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def _over(fg: tuple[int, int, int], alpha: float, bg: tuple[int, int, int]):
    return tuple(round(f * alpha + b * (1 - alpha)) for f, b in zip(fg, bg))


def _luminance(rgb):
    def channel(value: int) -> float:
        value /= 255
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    high, low = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def _theme(name: str) -> dict[str, str]:
    return LIGHT if name == "light" else DARK


# --------------------------------------------------------------------------
# 1. no orphan tokens
# --------------------------------------------------------------------------
def test_dark_block_defines_every_colour_token_the_light_theme_has():
    missing = {
        name
        for name, value in LIGHT.items()
        if _is_colour(value) and name not in DARK
    }
    assert missing == set(), f"dark theme leaves these tokens undefined: {sorted(missing)}"


def test_dark_and_light_are_actually_different():
    for token in ("--bg", "--surface", "--text", "--muted", "--line"):
        assert DARK[token] != LIGHT[token], f"{token} is identical in both themes"


def test_no_component_paints_text_with_the_dark_brand_colour():
    """--navy is a background in both themes; text must use --ink-strong."""
    offenders = [
        line
        for line in CSS.splitlines()
        if "color: var(--navy)" in line.replace("background-color", "")
    ]
    assert offenders == [], f"text painted with --navy: {offenders}"


def test_hardcoded_white_surfaces_are_not_used_outside_the_print_stylesheet():
    print_block = _block("@media print {")
    rest = CSS.replace(print_block, "")
    offenders = re.findall(r"background:\s*#(?:fff|ffffff|f8fafc|f1f5f9)\b", rest)
    assert offenders == [], f"{len(offenders)} hardcoded light surface(s) left: {offenders}"


# --------------------------------------------------------------------------
# 2. contrast
# --------------------------------------------------------------------------
@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize(
    "ink,surface",
    [
        ("--text", "--bg"),
        ("--text", "--surface"),
        ("--muted", "--bg"),
        ("--muted", "--surface"),
        ("--muted", "--surface-subtle"),
        ("--dim", "--surface-subtle"),
        ("--ink-soft", "--surface"),
    ],
)
def test_body_text_meets_wcag_aa(theme, ink, surface):
    tokens = _theme(theme)
    ratio = contrast(_hex(tokens[ink]), _hex(tokens[surface]))
    assert ratio >= 4.5, f"{theme}: {ink} on {surface} is {ratio:.2f}:1"


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize(
    "ink,tint",
    [
        ("--green", "--green-bg"),      # ACCEPT chip
        ("--red-ink", "--red-bg"),      # REJECT chip
        ("--amber-ink", "--amber-bg"),  # HOLD chip
        ("--blue-ink", "--blue-bg"),    # ESCALATE chip
    ],
)
def test_outcome_chips_stay_readable_on_their_own_tint(theme, ink, tint):
    """Chips are translucent, so composite the tint over the page before measuring."""
    tokens = _theme(theme)
    match = re.match(r"rgba\(([\d.]+),\s*([\d.]+),\s*([\d.]+),\s*([\d.]+)\)", tokens[tint])
    if match:
        r, g, b, alpha = match.groups()
        background = _over(_hex(f"#{int(float(r)):02x}{int(float(g)):02x}{int(float(b)):02x}"),
                           float(alpha), _hex(tokens["--surface"]))
    else:
        background = _hex(tokens[tint])
    ratio = contrast(_hex(tokens[ink]), background)
    assert ratio >= 4.5, f"{theme}: {ink} on {tint} is {ratio:.2f}:1"


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_primary_button_label_clears_aa(theme):
    tokens = _theme(theme)
    if theme == "dark":
        # the dark theme moves the primary action onto the accent
        assert contrast(_hex("#0b1220"), _hex(tokens["--lime"])) >= 7
    else:
        assert contrast(_hex("#ffffff"), _hex(tokens["--navy"])) >= 7


def test_focus_ring_is_visible_against_both_canvases():
    """WCAG 2.4.11 wants 3:1 for the indicator itself, not for a faint wash."""
    for theme in ("light", "dark"):
        tokens = _theme(theme)
        line = re.findall(r"#[0-9a-fA-F]{6}", tokens["--focus"])[-1]
        for surface in ("--bg", "--surface"):
            ratio = contrast(_hex(line), _hex(tokens[surface]))
            assert ratio >= 3, f"{theme}: focus ring on {surface} is {ratio:.2f}:1"


# --------------------------------------------------------------------------
# 3. the toggle exists everywhere and runs before paint
# --------------------------------------------------------------------------
def test_theme_is_resolved_before_the_stylesheet_loads():
    base = (ROOT / "base.html").read_text(encoding="utf-8")
    script = base.index('src="/static/theme.js"')
    stylesheet = base.index('href="/static/app.css"')
    assert script < stylesheet, "theme.js must run before app.css paints"


@pytest.mark.parametrize("page", ["base.html", "login.html", "error.html"])
def test_every_page_offers_a_labelled_theme_toggle(page):
    html = (ROOT / page).read_text(encoding="utf-8")
    assert "data-theme-toggle" in html, f"{page} has no toggle"
    toggle = html[html.index("data-theme-toggle") - 400 : html.index("data-theme-toggle") + 400]
    assert "aria-label" in toggle or "aria-label" in html
    assert "aria-pressed" in toggle, f"{page} toggle does not expose its state"


def test_theme_script_respects_the_content_security_policy():
    base = (ROOT / "base.html").read_text(encoding="utf-8")
    script = Path("static/theme.js").read_text(encoding="utf-8")
    assert "<script>" not in base, "inline script is blocked by the CSP"
    assert "javascript:" not in script
    assert "eval(" not in script
    assert "innerHTML" not in script


def test_theme_script_never_stores_anything_but_a_theme():
    script = Path("static/theme.js").read_text(encoding="utf-8")
    stored_keys = set(re.findall(r"localStorage\.setItem\(\s*[A-Z_]+", script))
    assert stored_keys == {"localStorage.setItem(STORAGE_KEY"}
    assert "document.cookie" not in script
