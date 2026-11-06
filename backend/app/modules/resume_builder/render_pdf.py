"""Draw the layout operations onto a single A4 page with ReportLab."""

from __future__ import annotations

import io
from typing import Any

from reportlab.pdfgen import canvas

from app.modules.resume_builder import fonts, layout


class DoesNotFit(ValueError):
    def __init__(self, overflow_lines: int):
        super().__init__(f"The resume is about {overflow_lines} line(s) too long for one page. Shorten or remove content.")
        self.overflow_lines = overflow_lines


def render_pdf(resume: dict[str, Any], title: str = "Resume") -> bytes:
    """Return a one-page PDF. Raises DoesNotFit if even the smallest allowed scale overflows."""
    fonts.register()
    fit = layout.measure(resume)
    if not fit["fits"]:
        raise DoesNotFit(fit["overflow_lines"])
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(layout.PAGE_W, layout.PAGE_H))
    c.setTitle(title)
    c.setAuthor(resume.get("header", {}).get("name", ""))
    for op in fit["ops"]:
        if op.kind == "rule":
            c.setStrokeColorRGB(*op.color)
            c.setLineWidth(0.398)
            y = layout.PAGE_H - op.y
            c.line(op.x, y, op.x1, y)
        elif op.kind == "dot":
            c.setFillColorRGB(0, 0, 0)
            c.circle(op.x, layout.PAGE_H - op.y, op.size * fit["scale"], stroke=0, fill=1)
        else:
            x = op.x
            y = layout.PAGE_H - op.y
            for text, bold, ital in op.segs:
                c.setFillColorRGB(*op.color)
                c.setFont("CMB" if bold else "CMR", op.size)
                hs = layout.BOLD_X if bold else 1.0
                if text == " ":
                    x += layout._w(" ", False, op.size) + op.space_extra
                    continue
                if ital or hs != 1.0:
                    c.saveState(); c.translate(x, y); c.transform(hs, 0, 0.2 if ital else 0, 1, 0, 0); c.drawString(0, 0, text); c.restoreState()
                else:
                    c.drawString(x, y, text)
                x += layout._w(text, bold, op.size)
            if op.link:
                c.linkURL(op.link, (op.x, y - 2.5, x, y + op.size * 0.8), relative=0, thickness=0)
    c.showPage()
    c.save()
    return buf.getvalue()
