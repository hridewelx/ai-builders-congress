"""Write both card formats from the same metrics."""
from __future__ import annotations

import json
from pathlib import Path

from .card_json import json_card
from .markdown import markdown


def write(out_md: Path, out_json: Path, metrics: dict, checkpoint: dict,
          calibration: dict | None = None, parity: dict | None = None,
          operating_point: dict | None = None, source: str | None = None,
          integrity: dict | None = None, leakage: dict | None = None,
          reliability: dict | None = None) -> dict:
    """Write both artefacts from one set of measurements."""
    text = markdown(metrics, checkpoint, calibration, parity,
                    source=source, integrity=integrity, leakage=leakage,
                    operating_point=operating_point, reliability=reliability)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(text, encoding="utf-8")
    card = json_card(metrics, checkpoint, calibration, parity, operating_point, reliability)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(card, indent=2, ensure_ascii=False), encoding="utf-8")
    return card
