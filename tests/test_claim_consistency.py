"""Every number the pitch quotes must exist in the model card.

The rule for this project is that nothing in the pitch may exceed
`docs/MODEL_CARD.md`. A rule with no check is a wish, so this test extracts the
model numbers from the pitch and the README and requires each one to appear in
the card. It cannot judge whether a sentence is fair; it can judge whether the
number was invented.
"""
from __future__ import annotations

import re
from pathlib import Path

CARD = Path("docs/MODEL_CARD.md")
SOURCES = [Path("README.md"), Path("PITCH.md")]
NUMBER = re.compile(r"\b0\.\d{2,4}\b|\b\d{2,3}\.\d{1,2}\s?%")


def _numbers(text: str) -> set[str]:
    return {match.group(0).replace("*", "").replace(" ", "") for match in NUMBER.finditer(text)}


def _in_card(number: str, card_numbers: set[str]) -> bool:
    """A rounded quote is fine: 0.106 and 0.118 are the card's 0.1061 and 0.1179."""
    if number in card_numbers:
        return True
    try:
        value = float(number.replace("%", ""))
    except ValueError:
        return False
    for other in card_numbers:
        try:
            # Two-decimal prose ("0.95") rounds a four-decimal metric ("0.9474"),
            # so allow half a unit of the quoted precision.
            tolerance = 0.005 if len(number.replace("%", "").split(".")[-1]) <= 2 else 0.0006
            if abs(value - float(other.replace("%", ""))) <= tolerance:
                return True
        except ValueError:
            continue
    return False


def test_pitch_numbers_come_from_the_card():
    card_text = CARD.read_text(encoding="utf-8")
    card_numbers = _numbers(card_text)
    missing: dict[str, list[str]] = {}
    for source in SOURCES:
        if not source.exists():
            continue
        quoted = _numbers(source.read_text(encoding="utf-8"))
        absent = sorted(number for number in quoted if not _in_card(number, card_numbers))
        if absent:
            missing[source.name] = absent
    assert not missing, (
        "numbers quoted outside the card that the card does not contain: "
        + ", ".join(f"{name}: {values}" for name, values in missing.items()))


def test_card_states_the_caveats_the_pitch_relies_on():
    card = CARD.read_text(encoding="utf-8").lower()
    for phrase in ("same four", "clean image", "calibration", "approximate mapping"):
        assert phrase in card, f"the card must state {phrase!r}"
