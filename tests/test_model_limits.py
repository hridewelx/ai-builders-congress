"""The product's handling of what the model cannot do.

Three claims are easy to make in a pitch and easy to break in code:

1. Scores are a ranking, never a probability.
2. Two classes have no public labels and stay human-entered.
3. A defect the model has never seen can still be recorded by a human.

These tests check the code and the copy, not the slides.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core import db
from app.main import app

TEMPLATES = Path("templates")
CATALOGS = Path("app/i18n/catalogs")


def _client(role: str, lang: str = "en") -> TestClient:
    client = TestClient(app)
    assert client.get(f"/demo/{role}").status_code == 200
    client.get(f"/lang/{lang}")
    return client


def test_scores_are_never_described_as_a_probability():
    """Any mention of probability must be a denial, in either language."""
    offenders: list[str] = []
    for path in list(TEMPLATES.rglob("*.html")) + list(CATALOGS.glob("*.py")):
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in re.finditer(r"(?i)(confidence|probabilit\w*|likely|সম্ভাবনা)", text):
            # Negation sits before the word in English and after it in Bangla,
            # so look at both sides of the match.
            window = (text[max(0, match.start() - 40):match.start()]
                      + " " + text[match.end():match.end() + 40]).lower()
            if not any(neg in window for neg in ("not ", "never", "no ", "n't", "নয়", "নেই")):
                line = text[:match.start()].count("\n") + 1
                offenders.append(f"{path}:{line}: {text.splitlines()[line - 1].strip()[:120]}")
    assert not offenders, "scores must not be presented as probabilities:\n" + "\n".join(offenders)


def test_manual_only_classes_are_named_in_the_review_ui():
    html = _client("inspector").get("/review/55").text
    assert "skipped stitch and shade band" in html, "the page must say which classes are human-entered"
    assert "human enters them" in html
    for value in ("skipped_stitch", "shade_band", "other"):
        assert f'value="{value}"' in html, f"{value} must stay selectable for a human"


def test_a_defect_the_model_cannot_name_can_still_be_recorded():
    """The open-set answer is a human path, so it has to work — and clean up after itself."""
    client = _client("inspector")
    page = client.get("/review/55")
    csrf = client.cookies.get("ll_csrf")
    match = re.search(r'action="/review/(\d+)/add"', page.text)
    if match is None:
        pytest.skip("this view has no manual-add form in the seeded state")
    image_id = match.group(1)
    watermark = db.one("SELECT COALESCE(MAX(id), 0) AS m FROM prediction")["m"]
    before = db.one("SELECT COUNT(*) AS n FROM prediction WHERE image_id=? AND reviewed_by IS NOT NULL",
                    (image_id,))["n"]
    try:
        response = client.post(f"/review/{image_id}/add", data={
            "csrf": csrf, "defect_type": "other", "zone": "II", "cx": "0.5", "cy": "0.5",
            "w": "0.1", "h": "0.1", "severity": "major", "note": "unknown surface mark",
        }, follow_redirects=False)
        assert response.status_code in (302, 303), response.text[:200]
        after = db.one("SELECT COUNT(*) AS n FROM prediction WHERE image_id=? AND reviewed_by IS NOT NULL",
                       (image_id,))["n"]
        assert after == before + 1, "a manually added 'other' defect must be stored"
    finally:
        # The demo database is the demo. A test may not leave a confirmed defect
        # behind, because that changes what the lot decision shows.
        for row in db.q("SELECT id FROM prediction WHERE id > ?", (watermark,)):
            db.x("DELETE FROM audit_event WHERE entity='prediction' AND entity_id=?", (str(row["id"]),))
            db.x("DELETE FROM prediction WHERE id=?", (row["id"],))


def test_the_approximate_mapping_does_not_over_claim_its_name():
    """`needle_line` learns from Vertical LineMark, so the label must not promise a cause."""
    html = _client("inspector").get("/review/55").text
    assert "line mark (approx.)" in html
    assert "approximate mapping" in html
    assert "Vertical LineMark" in html
