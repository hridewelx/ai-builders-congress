"""One-page inspection report (PDF). Renders the stored decision row only."""
from __future__ import annotations

import os

from fpdf import FPDF

_FONT_CANDIDATES = [
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
     "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
]


def para(pdf: FPDF, h: float, text: str, **kw) -> None:
    """Full-width paragraph from the left margin (never from a stray x)."""
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, h, text, **kw)


def _font_family(pdf: FPDF) -> str:
    for regular, bold in _FONT_CANDIDATES:
        if os.path.exists(regular) and os.path.exists(bold):
            pdf.add_font("App", "", regular)
            pdf.add_font("App", "B", bold)
            return "App"
    return "Helvetica"

OUTCOME_TEXT = {
    "ACCEPT": "The sample met the plan. This is a statistical inference, not proof that the lot is defect-free.",
    "REJECT": "At least one class reached its rejection number. The sample failed the plan.",
    "HOLD": "The sampling rule cannot be applied yet. The blocking reasons are listed above.",
    "ESCALATE": "A person must decide. This case is outside the system's competence.",
}
OUTCOME_RGB = {"ACCEPT": (22, 120, 80), "REJECT": (170, 40, 40),
               "HOLD": (150, 100, 10), "ESCALATE": (110, 60, 150)}


class Report(FPDF):
    def header(self):
        self.set_font(self.family if hasattr(self, "family") else "Helvetica", "B", 15)
        self.set_text_color(15, 23, 42)
        self.cell(0, 7, "LOTLINE", new_x="LMARGIN", new_y="NEXT")
        self.set_font(self.family if hasattr(self, "family") else "Helvetica", "", 8)
        self.set_text_color(110, 120, 135)
        self.cell(0, 4, "AI proposes. Humans confirm. The deterministic sampling engine decides.", new_x="LMARGIN", new_y="NEXT")
        self.ln(1)
        self.set_draw_color(220, 225, 232)
        self.line(14, self.get_y(), 196, self.get_y())
        self.ln(3)


def build(ctx: dict) -> bytes:
    pdf = Report(format="A4")
    family = _font_family(pdf)
    pdf.family = family
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.set_margins(14, 12, 14)
    pdf.add_page()
    pdf.set_text_color(30, 41, 59)

    # Title block
    pdf.set_font(pdf.family if hasattr(pdf, "family") else "Helvetica", "B", 13)
    pdf.cell(120, 7, "Lot inspection report", new_x="LEFT", new_y="NEXT")
    pdf.set_font(pdf.family if hasattr(pdf, "family") else "Helvetica", "", 9)
    pdf.set_text_color(90, 100, 115)
    pdf.cell(120, 5, f"Lot {ctx['lot_code']} · {ctx['product']} · {ctx['buyer']}", new_x="LEFT", new_y="NEXT")
    pdf.cell(120, 5, f"Decision #{ctx['sequence']} · {ctx['created_at']} · engine {ctx['engine_version']}",
             new_x="LEFT", new_y="NEXT")
    pdf.ln(3)

    # Outcome band
    rgb = OUTCOME_RGB.get(ctx["outcome"], (30, 41, 59))
    pdf.set_fill_color(*rgb)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font(pdf.family if hasattr(pdf, "family") else "Helvetica", "B", 11)
    label = f"SYSTEM RECOMMENDATION: {ctx['outcome']}"
    pdf.cell(0, 9, "  " + label, new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.set_fill_color(245, 247, 250)
    pdf.set_text_color(30, 41, 59)
    pdf.set_font(pdf.family if hasattr(pdf, "family") else "Helvetica", "", 9)
    para(pdf, 5, "  " + OUTCOME_TEXT.get(ctx["outcome"], ""), fill=True)
    if ctx.get("override"):
        o = ctx["override"]
        pdf.set_fill_color(255, 244, 214)
        pdf.set_font(pdf.family if hasattr(pdf, "family") else "Helvetica", "B", 9)
        para(pdf, 5, f"  OVERRIDDEN — system: {ctx['outcome']}, supervisor: {o['final_disposition'].replace('OVERRIDE_', '')}. "
                             f"Reason: {o['reason']}" + (" (approved by a second Supervisor)" if o.get("approved") else
                                                         " (PENDING second-Supervisor approval; system outcome remains in force)"),
                       fill=True)
    pdf.ln(3)

    # Plan + counts side by side
    y0 = pdf.get_y()
    pdf.set_font(pdf.family if hasattr(pdf, "family") else "Helvetica", "B", 9)
    pdf.cell(90, 5, "Sampling plan (entered)", new_x="LEFT", new_y="NEXT")
    pdf.set_font(pdf.family if hasattr(pdf, "family") else "Helvetica", "", 8)
    if ctx.get("plan"):
        p = ctx["plan"]
        lines = [
            f"n entered: {p['n']}    n effective: {ctx['n_effective']}",
            f"Counting mode: {p['counting_mode']}",
            "Critical: AQL " + str(p.get("critical_aql") if p.get("critical_aql") is not None else "-")
            + f"  Ac {p['critical']['ac']} / Re {p['critical']['re']}",
            "Major: AQL " + str(p.get("major_aql") if p.get("major_aql") is not None else "-")
            + f"  Ac {p['major']['ac']} / Re {p['major']['re']}",
            "Minor: AQL " + str(p.get("minor_aql") if p.get("minor_aql") is not None else "-")
            + f"  Ac {p['minor']['ac']} / Re {p['minor']['re']}",
            (f"Source: {p.get('source_edition') or '-'} / {p.get('source_reference') or '-'}"),
            "Default values are an assumption, not a standard.",
        ]
    else:
        lines = ["No sampling plan is configured."]
    for ln in lines:
        pdf.cell(90, 4.4, ln, new_x="LEFT", new_y="NEXT")

    y1 = pdf.get_y()
    pdf.set_xy(108, y0)
    pdf.set_font(pdf.family if hasattr(pdf, "family") else "Helvetica", "B", 9)
    pdf.cell(88, 5, "Confirmed defective garments", new_x="LEFT", new_y="NEXT")
    pdf.set_font(pdf.family if hasattr(pdf, "family") else "Helvetica", "", 8)
    pdf.set_xy(108, pdf.get_y())
    pdf.cell(24, 5, "Class", border="B")
    pdf.cell(18, 5, "Count", border="B", align="R")
    pdf.cell(18, 5, "Ac", border="B", align="R")
    pdf.cell(18, 5, "Re", border="B", align="R")
    pdf.cell(14, 5, "Result", border="B", align="R", new_x="LEFT", new_y="NEXT")
    for cls in ("critical", "major", "minor"):
        st = (ctx.get("class_status") or {}).get(cls)
        pdf.set_x(108)
        pdf.cell(24, 5, cls.capitalize())
        if st:
            pdf.cell(18, 5, str(st["count"]), align="R")
            pdf.cell(18, 5, str(st["ac"]), align="R")
            pdf.cell(18, 5, str(st["re"]), align="R")
            pdf.cell(14, 5, st["status"], align="R")
        else:
            pdf.cell(18, 5, "-", align="R")
            pdf.cell(18, 5, "-", align="R")
            pdf.cell(18, 5, "-", align="R")
            pdf.cell(14, 5, "-", align="R")
        pdf.ln(5)
    pdf.set_x(108)
    pdf.set_font(pdf.family if hasattr(pdf, "family") else "Helvetica", "", 7.5)
    pdf.multi_cell(88, 3.6, f"Garments present {ctx['units_present']} / required {ctx['required_units']}. "
                            f"Views pending: {ctx['views_pending']}. Evidence problems: {ctx['evidence_bad']}.")
    pdf.set_y(max(y1, pdf.get_y()) + 3)

    # Reasons
    pdf.set_font(pdf.family if hasattr(pdf, "family") else "Helvetica", "B", 9)
    pdf.cell(0, 5, "Reasons recorded (canonical codes)", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(pdf.family if hasattr(pdf, "family") else "Helvetica", "", 8)
    for r in ctx["reasons"]:
        pdf.cell(6, 4.4, "•")
        para(pdf, 4.4, f"{r['code']} — {r['text']}")
    pdf.ln(1)

    # Evidence and gates
    pdf.set_font(pdf.family if hasattr(pdf, "family") else "Helvetica", "B", 9)
    pdf.cell(0, 5, "Evidence and gates", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(pdf.family if hasattr(pdf, "family") else "Helvetica", "", 8)
    ev = [
        f"Critical non-visual check: {ctx['nonvisual']}",
        f"Images in evidence: {ctx['images']} · units: {ctx['units']} · detector: {ctx['model']} ({ctx['model_domains']})",
        f"Manual inspection: {'yes' if ctx['manual'] else 'no'} · selection method: {ctx['selection']}",
        f"Snapshot SHA-256: {ctx['snapshot_hash'][:32]}…",
        "Scope: the critical class covers visible defects only. Photo evidence cannot prove needle or metal absence.",
    ]
    for line in ev:
        para(pdf, 4.2, "• " + line)
    pdf.ln(2)

    # Signature
    pdf.ln(3)
    pdf.set_font(pdf.family if hasattr(pdf, "family") else "Helvetica", "", 8)
    pdf.cell(90, 4, "Inspector: ______________________________")
    pdf.cell(88, 4, "Supervisor: _____________________________", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font(pdf.family if hasattr(pdf, "family") else "Helvetica", "", 6.8)
    pdf.set_text_color(120, 130, 145)
    para(pdf, 3.4, "This report renders one stored decision row. It contains no reconstructed sampling table, no percentage "
                          "allowance, and no claim of calibration or ISO certification. AQL schemes were designed for a continuing "
                          "series of lots; for an isolated lot this report states only which entered plan was applied. "
                          "Generated by Lotline demo build for the International AI Builders Congress 2026.")
    out = pdf.output()
    return bytes(out)
