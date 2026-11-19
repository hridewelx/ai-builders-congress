"""The model card, written once and emitted twice.

`docs/MODEL_CARD.md` is what a judge reads; `data/models/model_card_trained.json`
is what the app reads. They used to be produced by different code with different
fields, which is how a card ends up disagreeing with the product. One module now
owns the facts: the markdown is rendered for humans, the JSON for the explainer
page, and both come from the same saved measurements.
"""
from __future__ import annotations

from .card_json import json_card
from .markdown import markdown
from .writer import write

__all__ = ["markdown", "json_card", "write"]
