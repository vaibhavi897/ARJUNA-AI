"""Word export mirroring the PDF: Times-style 10pt, blue underlined headings, right-aligned dates, exact line spacing."""

from __future__ import annotations

import io
from typing import Any

from docx import Document
from docx.enum.text import WD_LINE_SPACING, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Emu, Pt, RGBColor

from app.modules.resume_builder import fonts, layout

FONT = "Times New Roman"
BLUE = RGBColor(0x00, 0x00, 0x80)
# measured PDF geometry (pt): A4, 21.6pt side margins, text width 552.1pt
PAGE_W_PT, PAGE_H_PT = layout.PAGE_W, layout.PAGE_H


def _runs(par, text: str, size: float = 10.0, color: RGBColor | None = None, force_bold: bool = False) -> None:
    for seg, bold, italic in layout.parse_markup(text):
        if not seg:
            continue
        r = par.add_run(seg)
        r.font.name = FONT
        r._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
        r.font.size = Pt(size)
        r.bold = bold or force_bold
        r.italic = italic
        if color is not None:
            r.font.color.rgb = color


def _fmt(par, after: float = 0.0, before: float = 0.0, line: float = layout.LEADING, left: float = 0.0, hanging: float = 0.0) -> None:
    pf = par.paragraph_format
    pf.space_before, pf.space_after = Pt(before), Pt(after)
    pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    pf.line_spacing = Pt(line)
    pf.left_indent = Pt(left)
    if hanging:
        pf.first_line_indent = Pt(-hanging)
    pf.keep_together = True


def _right_tab(par) -> None:
    par.paragraph_format.tab_stops.add_tab_stop(Pt(layout.TEXT_W), WD_TAB_ALIGNMENT.RIGHT)


def _bottom_border(par, color: str = "000080") -> None:
    ppr = par._p.get_or_add_pPr()
    b = OxmlElement("w:pBdr")
    bt = OxmlElement("w:bottom")
    for k, v in (("w:val", "single"), ("w:sz", "4"), ("w:space", "1"), ("w:color", color)):
        bt.set(qn(k), v)
    b.append(bt)
    ppr.append(b)


def _jc(par, mode: str = "both") -> None:
    ppr = par._p.get_or_add_pPr()
    jc = OxmlElement("w:jc")
    jc.set(qn("w:val"), mode)
    ppr.append(jc)


def _bullet(doc, text: str) -> None:
    p = doc.add_paragraph()
    _fmt(p, left=layout.BULLET_INDENT + 0.0, hanging=layout.BULLET_INDENT)
    _right_tab(p)
    p.paragraph_format.tab_stops.add_tab_stop(Pt(layout.BULLET_INDENT), WD_TAB_ALIGNMENT.LEFT)
    _runs(p, "•\t")
    _runs(p, text)
    _jc(p)


def render_docx(resume: dict[str, Any]) -> bytes:
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Pt(PAGE_W_PT), Pt(PAGE_H_PT)
    sec.left_margin = sec.right_margin = Pt(layout.ML)
    sec.top_margin, sec.bottom_margin = Pt(22), Pt(PAGE_H_PT - layout.BOTTOM_LIMIT - 2)
    sec.header_distance = sec.footer_distance = Pt(0)
    st = doc.styles["Normal"]
    st.font.name, st.font.size = FONT, Pt(10)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    props = doc.core_properties
    props.author = resume.get("header", {}).get("name", "")
    props.title = f"{props.author} - Resume".strip(" -")

    h = resume.get("header", {})
    p = doc.add_paragraph()
    p.alignment = 1
    _fmt(p, after=0, line=17.0)
    _runs(p, f"**{layout.strip_markup(h.get('name', ''))}**", 14.3, BLUE)
    contacts = [c for c in h.get("contacts", []) if c and c.strip()]
    if contacts:
        p = doc.add_paragraph()
        p.alignment = 1
        _fmt(p, after=6, line=layout.LEADING)
        for i, c in enumerate(contacts):
            if i:
                _runs(p, "   |   ")
            _runs(p, c)

    for s in resume.get("sections", []):
        if not layout._has_content(s):
            continue
        p = doc.add_paragraph()
        _fmt(p, before=6, after=3, line=14.5)
        _runs(p, f"**{layout.strip_markup(s.get('title', ''))}**", 12, BLUE)
        _bottom_border(p)
        kind = s.get("type", "entries")
        if kind == "entries":
            for ei, e in enumerate(s.get("entries", [])):
                gap = layout.ENTRY_GAP_BY_SECTION.get(s.get("key", ""), layout.ENTRY_GAP)
                p = doc.add_paragraph()
                _fmt(p, before=gap if ei else 0)
                _right_tab(p)
                _runs(p, e.get("title", ""))
                if e.get("right"):
                    _runs(p, "\t" + e["right"])
                if e.get("subtitle") or e.get("subright"):
                    p = doc.add_paragraph()
                    _fmt(p)
                    _right_tab(p)
                    _runs(p, e.get("subtitle", ""))
                    if e.get("subright"):
                        _runs(p, "\t" + e["subright"])
                for b in e.get("bullets", []):
                    if b and b.strip():
                        _bullet(doc, b)
        elif kind == "bullets":
            for b in s.get("bullets", []):
                _bullet(doc, b)
        else:
            gap = layout.LINE_GROUP_GAP.get(s.get("key", ""), 0.0)
            for li, ln in enumerate(s.get("lines", [])):
                p = doc.add_paragraph()
                _fmt(p, before=gap if li else 0)
                if ln.get("label"):
                    _runs(p, f"**{ln['label']}:** ")
                _runs(p, ln.get("text", ""))
                _jc(p)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
