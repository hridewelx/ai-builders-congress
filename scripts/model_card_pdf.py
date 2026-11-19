"""Render the model card to PDF for submission attachments.

The card is the single source; this script is a view of it, not a second copy.
It understands the small markdown subset the generator emits: `##` headings,
`-` bullets, pipe tables, and plain paragraphs. Anything else is printed as text
rather than silently dropped.

    python scripts/model_card_pdf.py --md docs/MODEL_CARD.md --out docs/LOTLINE_MODEL_CARD.pdf
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from fpdf import FPDF

ASCII_MAP = {"\u2014": "-", "\u2013": "-", "\u2022": "*", "\u2026": "...", "\u2192": "->",
             "\u2265": ">=", "\u2264": "<=", "\u00b7": "-", "\u2018": "'", "\u2019": "'",
             "\u201c": '"', "\u201d": '"'}
TABLE_ROW = re.compile(r"^\|(.+)\|$")
SEPARATOR = re.compile(r"^\|[\s:|-]+\|$")


def soft_break(text: str, every: int = 60) -> str:
    """Long hashes and paths have no spaces; fpdf cannot break them."""
    out = []
    for word in text.split(" "):
        while len(word) > every:
            out.append(word[:every])
            word = word[every:]
        out.append(word)
    return " ".join(out)


def ascii_safe(text: str) -> str:
    for source, target in ASCII_MAP.items():
        text = text.replace(source, target)
    return text.encode("latin-1", "replace").decode("latin-1")


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def render(md_path: Path, out_path: Path) -> Path:
    if not md_path.exists():
        raise SystemExit(f"no model card at {md_path}")
    text = md_path.read_text(encoding="utf-8")
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.multi_cell(0, 8, ascii_safe("Lotline - model card"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 8)
    pdf.multi_cell(0, 4, ascii_safe(f"Rendered from {md_path.as_posix()}; that file is the source of truth."), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    for raw in text.splitlines():
        line = raw.rstrip()
        if pdf.get_y() > 258:  # start a page before the auto-break lands mid-cell
            pdf.add_page()
        if not line or set(line) == {"-"}:
            pdf.ln(1.5)
            continue
        if line.startswith("# "):
            continue  # the title is drawn above
        if line.startswith("## "):
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 11)
            pdf.multi_cell(0, 5.5, ascii_safe(line[3:]), new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 8.5)
            continue
        if SEPARATOR.match(line):
            continue
        if TABLE_ROW.match(line):
            cells = _cells(line)
            pdf.set_font("Helvetica", "", 7.5)
            pdf.multi_cell(0, 4, ascii_safe(soft_break("  |  ".join(cells))[:220]), new_x="LMARGIN", new_y="NEXT")
            continue
        if line.startswith("- "):
            pdf.set_font("Helvetica", "", 8.5)
            pdf.multi_cell(0, 4.4, ascii_safe(soft_break("- " + line[2:])), new_x="LMARGIN", new_y="NEXT")
            continue
        pdf.set_font("Helvetica", "", 8.5)
        pdf.multi_cell(0, 4.4, ascii_safe(soft_break(line)), new_x="LMARGIN", new_y="NEXT")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(out_path))
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render the model card to PDF.")
    parser.add_argument("--md", type=Path, default=Path("docs/MODEL_CARD.md"))
    parser.add_argument("--out", type=Path, default=Path("docs/LOTLINE_MODEL_CARD.pdf"))
    args = parser.parse_args(argv)
    path = render(args.md, args.out)
    print(f"wrote {path} ({path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
