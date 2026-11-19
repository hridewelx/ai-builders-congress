"""The card PDF is a view of the card, and it must not crash on its own content."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path("scripts").resolve()))
import model_card_pdf  # noqa: E402


def test_renders_the_real_card(tmp_path):
    card = Path("docs/MODEL_CARD.md")
    if not card.exists():
        pytest.skip("no generated card in this checkout")
    out = model_card_pdf.render(card, tmp_path / "card.pdf")
    data = out.read_bytes()
    assert data.startswith(b"%PDF")
    assert len(data) > 3000


def test_missing_card_is_an_error_not_an_empty_pdf(tmp_path):
    with pytest.raises(SystemExit, match="no model card"):
        model_card_pdf.render(tmp_path / "nope.md", tmp_path / "card.pdf")


def test_unicode_dashes_and_hash_like_tokens_do_not_break_the_render(tmp_path):
    md = tmp_path / "card.md"
    md.write_text("# t\n\n## Head\n\n- a " + "f" * 120 + " — dash\n", encoding="utf-8")
    out = model_card_pdf.render(md, tmp_path / "card.pdf")
    assert out.read_bytes().startswith(b"%PDF")
