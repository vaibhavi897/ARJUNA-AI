"""Single source of truth for the resume's geometry.

The PDF renderer draws exactly the operations produced here, and the
"fits on one page?" check measures exactly the same operations, so what the
learner sees is what the check validated. Constants are measured from the
template resume (A4, LaTeX Computer Modern, 10pt, blue headings with rules).

Resume content model (JSON):
  {"header": {"name": str, "contacts": [str]},
   "sections": [{"key", "title", "type": "entries" | "bullets" | "lines",
                 "entries": [{"title","right","subtitle","subright","bullets":[str],"source":{...}}],
                 "bullets": [str],                 # type "bullets"
                 "lines": [{"label","text"}]}]}    # type "lines"
Text fields accept **bold** and *italic* markup.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from reportlab.pdfbase.pdfmetrics import stringWidth

from app.modules.resume_builder import fonts

PAGE_W, PAGE_H = 595.276, 841.89
ML = MR = 21.6
TEXT_W = PAGE_W - ML - MR
RIGHT = PAGE_W - MR
BLUE = (0.1216, 0.3059, 0.4745)
BLACK = (0, 0, 0)

NAME_SIZE, HEAD_SIZE, BODY = 14.3, 12.0, 10.0
LEADING = 11.95
NAME_BASE = 24.29
CONTACT_DY = 11.96
FIRST_HEADING_DY = 31.95        # contact baseline -> first heading baseline
HEADING_DY = 19.95              # last body baseline -> next heading baseline
RULE_DY = 4.45                  # heading baseline -> rule
FIRST_ROW_DY = 11.1             # rule -> first body baseline
ENTRY_GAP = 2.95                # default extra space before every entry after the first
ENTRY_GAP_BY_SECTION = {"education": 1.95, "experience": 2.95, "projects": 1.45, "leadership": 1.45}  # measured from the template
HEADER_TO_BULLET = 12.7         # entry title / subtitle -> first bullet baseline
BULLET_INDENT = 10.0
CONTACT_GAP = 13.3
BOTTOM_LIMIT = 820.2            # last baseline must not pass this (template ends at ~817)
LINE_GROUP_GAP = {"achievements": 2.0}
MIN_SCALE = 0.94
BOLD_X = 1.148                  # template uses Computer Modern Bold EXTENDED; cmb10 is ~15% narrower
SPACE_SHRINK = 1.11             # TeX interword shrink (pt at 10pt)
MAX_STRETCH = 2.4               # a justified space may grow to this many natural spaces

Seg = tuple[str, bool, bool]  # text, bold, italic


@dataclass
class Op:
    kind: str                   # text | rule | dot
    x: float
    y: float                    # distance from the TOP of the page (baseline for text)
    segs: list[Seg] = field(default_factory=list)
    size: float = BODY
    color: tuple[float, float, float] = BLACK
    x1: float = 0.0
    link: str | None = None
    space_extra: float = 0.0    # extra width added to every space (justified lines)


def parse_markup(s: str) -> list[Seg]:
    segs: list[Seg] = []
    buf, bold, ital, i = "", False, False, 0
    s = fonts.clean(s or "")
    while i < len(s):
        if s.startswith("**", i):
            if buf:
                segs.append((buf, bold, ital)); buf = ""
            bold = not bold; i += 2
        elif s[i] == "*" and (i + 1 < len(s) and s[i + 1] != " ") or (s[i] == "*" and ital):
            if buf:
                segs.append((buf, bold, ital)); buf = ""
            ital = not ital; i += 1
        else:
            buf += s[i]; i += 1
    if buf:
        segs.append((buf, bold, ital))
    return segs


def strip_markup(s: str) -> str:
    return "".join(t for t, _, _ in parse_markup(s))


def _w(text: str, bold: bool, size: float) -> float:
    return stringWidth(text, "CMB" if bold else "CMR", size) * (BOLD_X if bold else 1.0)


def seg_width(segs: list[Seg], size: float) -> float:
    return sum(_w(t, b, size) for t, b, _ in segs)


def _words(segs: list[Seg]) -> list[list[Seg]]:
    words: list[list[Seg]] = []
    cur: list[Seg] = []
    for text, b, i in segs:
        for part in re.split(r"( )", text):
            if part == " ":
                if cur:
                    words.append(cur); cur = []
            elif part:
                cur.append((part, b, i))
    if cur:
        words.append(cur)
    return words


def wrap(segs: list[Seg], width: float, size: float, first_width: float | None = None) -> list[list[Seg]]:
    """Greedy word wrap with TeX-like space shrink. Returns lines as flat segment lists (spaces included)."""
    space = _w(" ", False, size)
    shrink = SPACE_SHRINK * size / 10.0
    lines: list[list[Seg]] = []
    cur: list[Seg] = []
    cur_w, n_words = 0.0, 0
    limit = first_width if first_width is not None else width
    for word in _words(segs):
        ww = seg_width(word, size)
        add = ww if not cur else space + ww
        # a line may be squeezed by shrinking its spaces, as TeX does
        if cur and cur_w + add > limit + shrink * n_words + 0.01:
            lines.append(cur); cur, cur_w, n_words, limit = [], 0.0, 0, width
            add = ww
        if cur:
            cur.append((" ", False, False)); cur_w += space
        cur.extend(word); cur_w += ww; n_words += 1
    if cur:
        lines.append(cur)
    return lines or [[]]


def justify_extra(line: list[Seg], width: float, size: float) -> float:
    """Extra width per space so a (non-final) line fills ``width`` exactly; 0 when it cannot be justified sensibly."""
    spaces = sum(t.count(" ") for t, _, _ in line)
    if not spaces:
        return 0.0
    extra = (width - seg_width(line, size)) / spaces
    space = _w(" ", False, size)
    lo, hi = -SPACE_SHRINK * size / 10.0, space * (MAX_STRETCH - 1)
    return extra if lo - 0.01 <= extra <= hi else 0.0


def _link_for(item: str) -> str | None:
    t = item.strip()
    if "@" in t and " " not in t:
        return "mailto:" + t
    if re.match(r"^(www\.)?(linkedin|github)\.com", t, re.I) or re.match(r"^https?://", t):
        return t if t.startswith("http") else "https://" + t
    return None


def layout(resume: dict[str, Any], scale: float = 1.0) -> tuple[list[Op], float]:
    """Return (draw operations, last baseline distance from top). ``scale`` shrinks type and leading together."""
    fonts.register()
    body, head, nsize = BODY * scale, HEAD_SIZE * scale, NAME_SIZE * scale
    lead = LEADING * scale
    ops: list[Op] = []

    h = resume.get("header", {})
    name_segs = [(fonts.clean(h.get("name", "")), True, False)]
    ops.append(Op("text", (PAGE_W - seg_width(name_segs, nsize)) / 2, NAME_BASE, name_segs, nsize, BLUE))
    y = NAME_BASE + CONTACT_DY * scale
    contacts = [c for c in h.get("contacts", []) if c and c.strip()]
    if contacts:
        widths = [seg_width(parse_markup(c), body) for c in contacts]
        total = sum(widths) + CONTACT_GAP * (len(contacts) - 1)
        x = (PAGE_W - total) / 2
        for c, w in zip(contacts, widths):
            ops.append(Op("text", x, y, parse_markup(c), body, BLACK, link=_link_for(c)))
            x += w + CONTACT_GAP
    y += FIRST_HEADING_DY * scale

    first_section = True
    for sec in resume.get("sections", []):
        if not _has_content(sec):
            continue
        if not first_section:
            y += HEADING_DY * scale
        first_section = False
        ops.append(Op("text", ML, y, [(fonts.clean(sec.get("title", "")), True, False)], head, BLUE))
        rule_y = y + RULE_DY * scale
        ops.append(Op("rule", ML, rule_y, x1=RIGHT, color=BLUE))
        y = rule_y + FIRST_ROW_DY * scale
        stype = sec.get("type", "entries")
        if stype == "entries":
            first_entry = True
            for e in sec.get("entries", []):
                if not first_entry:
                    y += ENTRY_GAP_BY_SECTION.get(sec.get("key", ""), ENTRY_GAP) * scale
                first_entry = False
                y = _entry(ops, e, y, body, lead, scale)
            y -= lead
        elif stype == "bullets":
            for k, b in enumerate(sec.get("bullets", [])):
                y = _bullet(ops, b, y, body, lead)
            y -= lead
        else:
            gap = LINE_GROUP_GAP.get(sec.get("key", ""), 0.0) * scale
            for k, ln in enumerate(sec.get("lines", [])):
                if k:
                    y += gap
                segs = ([(fonts.clean(ln.get("label", "")) + ":", True, False), (" ", False, False)] if ln.get("label") else []) + parse_markup(ln.get("text", ""))
                para = wrap(segs, TEXT_W, body)
                for j, line in enumerate(para):
                    ex = justify_extra(line, TEXT_W, body) if j < len(para) - 1 else 0.0
                    ops.append(Op("text", ML, y, line, body, space_extra=ex))
                    y += lead
            y -= lead
    return ops, y


def _has_content(sec: dict[str, Any]) -> bool:
    return bool(sec.get("entries") or sec.get("bullets") or sec.get("lines"))


def _entry(ops: list[Op], e: dict[str, Any], y: float, body: float, lead: float, scale: float) -> float:
    right = parse_markup(e.get("right", ""))
    rw = seg_width(right, body)
    title = parse_markup(e.get("title", ""))
    tlines = wrap(title, TEXT_W, body, first_width=TEXT_W - rw - 12 if right else None)
    for i, line in enumerate(tlines):
        ops.append(Op("text", ML, y, line, body))
        if i == 0 and right:
            ops.append(Op("text", RIGHT - rw, y, right, body))
        if i < len(tlines) - 1:
            y += lead
    last_header = y
    sub = parse_markup(e.get("subtitle", ""))
    subright = parse_markup(e.get("subright", ""))
    if sub or subright:
        y += lead
        if sub:
            ops.append(Op("text", ML, y, sub, body))
        if subright:
            ops.append(Op("text", RIGHT - seg_width(subright, body), y, subright, body))
        last_header = y
    bullets = [b for b in e.get("bullets", []) if b and b.strip()]
    y = last_header
    if bullets:
        y = last_header + HEADER_TO_BULLET * scale          # first bullet baseline
        for b in bullets:
            y = _bullet(ops, b, y, body, lead)               # returns the NEXT baseline
        return y
    return last_header + lead


def _bullet(ops: list[Op], text: str, y: float, body: float, lead: float) -> float:
    """Draw one bullet whose first baseline is ``y``. Returns the baseline where the next element would start."""
    lines = wrap(parse_markup(text), TEXT_W - BULLET_INDENT, body)
    ops.append(Op("dot", ML + 2.6, y - 0.34 * body, size=1.6))
    for i, line in enumerate(lines):
        ex = justify_extra(line, TEXT_W - BULLET_INDENT, body) if i < len(lines) - 1 else 0.0
        ops.append(Op("text", ML + BULLET_INDENT, y, line, body, space_extra=ex))
        if i < len(lines) - 1:
            y += lead
    return y + lead


def measure(resume: dict[str, Any]) -> dict[str, Any]:
    """Fit the resume on ONE page. Tries scale 1.0 down to MIN_SCALE; reports overflow in lines."""
    scale = 1.0
    while True:
        ops, last = layout(resume, scale)
        if last <= BOTTOM_LIMIT:
            return {"fits": True, "scale": round(scale, 3), "last_baseline": round(last, 1), "overflow_lines": 0, "ops": ops}
        if scale <= MIN_SCALE + 1e-6:
            over = int((last - BOTTOM_LIMIT) / (LEADING * scale)) + 1
            return {"fits": False, "scale": round(scale, 3), "last_baseline": round(last, 1), "overflow_lines": over, "ops": ops}
        scale = max(MIN_SCALE, round(scale - 0.01, 3))


def measure_at(resume: dict[str, Any], scale: float = 1.0) -> dict[str, Any]:
    """Single-scale fit check (no shrinking)."""
    _, last = layout(resume, scale)
    return {"fits": last <= BOTTOM_LIMIT, "last_baseline": round(last, 1)}


def line_count(text: str, width: float | None = None, size: float = BODY, indent: float = 0.0) -> int:
    fonts.register()
    return len(wrap(parse_markup(text), (width or TEXT_W) - indent, size))
