"""Report tests that do not depend on the host having fonts installed."""
from __future__ import annotations

from app.services import report


def _context() -> dict:
    return {
        "lot_code": "LT-TEST-001",
        "product": "Essential Crew Tee",
        "buyer": "Nordika Retail",
        "sequence": 1,
        "created_at": "2026-11-19T10:00:00Z",
        "engine_version": "engine-1.0",
        "outcome": "REJECT",
        "override": None,
        "plan": {
            "n": 8,
            "counting_mode": "highest_class_only",
            "critical_aql": 0.0,
            "major_aql": 1.5,
            "minor_aql": 2.5,
            "critical": {"ac": 0, "re": 1},
            "major": {"ac": 1, "re": 2},
            "minor": {"ac": 2, "re": 3},
            "source_edition": "test",
            "source_reference": "test",
        },
        "n_effective": 8,
        "class_status": {},
        "reasons": [{"code": "CRITICAL_DEFECT", "text": "A critical defect was confirmed."}],
        "units_present": 8,
        "required_units": 8,
        "views_pending": 0,
        "evidence_bad": 0,
        "nonvisual": "done",
        "images": 16,
        "units": 8,
        "model": "frcnn-mnv3-v2",
        "model_domains": "BDFD9 factory fabric close-ups plus staged knit panels",
        "manual": False,
        "selection": "random",
        "snapshot_hash": "a" * 64,
    }


def test_pdf_builds_without_any_system_font(monkeypatch):
    """The container has no fonts; the PDF must still be generated."""
    monkeypatch.setattr(report, "_FONT_CANDIDATES", [])
    data = report.build(_context())
    assert data.startswith(b"%PDF")
    assert len(data) > 1000


def test_report_states_its_language(monkeypatch):
    """The PDF is English while the UI is Bangla; the report must say so."""
    captured: list[str] = []
    original = report.Report.cell

    def spy(self, w=None, h=None, text="", *args, **kwargs):
        captured.append(str(text))
        return original(self, w, h, text, *args, **kwargs)

    monkeypatch.setattr(report.Report, "cell", spy)
    data = report.build(_context())
    assert data.startswith(b"%PDF")
    assert any("Report language: English" in text for text in captured)
