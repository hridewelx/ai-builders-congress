"""Every button and form control must have an accessible name.

The UI uses icon-only buttons and a few grouped checkbox rows. An icon is a
picture, not a label, so a screen reader announces "button" and nothing else.
This test is deliberately dumb and template-level: it catches the regression a
CSS review cannot see.
"""
from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from app.main import app

BUTTON = re.compile(r"<button\b([^>]*)>(.*?)</button>", re.DOTALL | re.IGNORECASE)
CONTROL = re.compile(r"<(input|select|textarea)\b([^>]*)>", re.IGNORECASE)
ARIA_LABEL = re.compile(r'aria-label\s*=\s*"([^"]*)"')
TITLE = re.compile(r'title\s*=\s*"([^"]*)"')
TYPE = re.compile(r'type\s*=\s*"([^"]*)"')
ID = re.compile(r'\bid\s*=\s*"([^"]*)"')
FOR = re.compile(r'<label\b[^>]*\bfor\s*=\s*"([^"]*)"', re.IGNORECASE)
TAG = re.compile(r"<[^>]+>")
SKIP_TYPES = {"hidden", "submit", "button", "reset", "image"}

PAGES = {
    "inspector": ["/", "/lots/6", "/review/55", "/lots/6/decision", "/how"],
    "supervisor": ["/", "/lots/1/report", "/how", "/audit"],
    "admin": ["/admin", "/audit"],
}


def _client(role: str) -> TestClient:
    client = TestClient(app)
    assert client.get(f"/demo/{role}").status_code == 200
    return client


def _name(attrs: str, inner: str) -> str:
    for pattern in (ARIA_LABEL, TITLE):
        match = pattern.search(attrs)
        if match and match.group(1).strip():
            return match.group(1).strip()
    return TAG.sub(" ", inner).replace("&nbsp;", " ").strip()


def _inside_label(html: str, position: int) -> bool:
    """True when the control sits between <label> and </label>, i.e. labelled implicitly."""
    before = html[:position]
    return before.rfind("<label") > before.rfind("</label>")


@pytest.mark.parametrize("role,pages", PAGES.items())
def test_buttons_have_accessible_names(role, pages):
    client = _client(role)
    unnamed: list[str] = []
    for path in pages:
        response = client.get(path)
        assert response.status_code == 200, f"{path} returned {response.status_code}"
        for attrs, inner in BUTTON.findall(response.text):
            if not _name(attrs, inner):
                unnamed.append(f"{path}: <button{attrs[:80]}>")
    assert not unnamed, "buttons without an accessible name:\n" + "\n".join(unnamed)


def test_form_controls_are_labelled(role="inspector"):
    """A placeholder is not a label, and a visual asterisk is not one either."""
    client = _client(role)
    problems: list[str] = []
    for path in PAGES[role]:
        html = client.get(path).text
        labelled = set(FOR.findall(html))
        for match in CONTROL.finditer(html):
            tag, attrs = match.group(1), match.group(2)
            type_match = TYPE.search(attrs)
            if type_match and type_match.group(1).lower() in SKIP_TYPES:
                continue
            if ARIA_LABEL.search(attrs):
                continue
            control_id = ID.search(attrs)
            if control_id and control_id.group(1) in labelled:
                continue
            if _inside_label(html, match.start()):
                continue
            problems.append(f"{path}: <{tag}{attrs[:90]}>")
    assert not problems, "form controls without a label:\n" + "\n".join(problems)
