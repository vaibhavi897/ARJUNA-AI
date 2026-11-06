"""Computer Modern fonts for the resume (the template is a LaTeX document).

Matplotlib ships the BaKoMa Computer Modern TrueType files. They use TeX's text
encoding, so en/em dashes and curly quotes exist as glyphs but are not reachable
by Unicode. We derive a copy at runtime (never committed or redistributed) with
the missing Unicode entries added, and register it with ReportLab.
"""

from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path

from app.core.config import settings

_REGISTERED = False
# BaKoMa glyph names are swapped: its "emdash" is 0.5em wide (a true en dash) and "endash" is 1em wide.
EXTRA = {0x2013: "emdash", 0x2014: "endash", 0x2018: "quoteleft", 0x2019: "quoteright", 0x201C: "quotedblleft", 0x201D: "quotedblright"}


def _source_dir() -> Path:
    import matplotlib

    return Path(matplotlib.__file__).parent / "mpl-data" / "fonts" / "ttf"


def _derive(src: Path, dst: Path) -> None:
    from fontTools.ttLib import TTFont

    font = TTFont(str(src))
    order = set(font.getGlyphOrder())
    for table in font["cmap"].tables:
        if table.isUnicode():
            for cp, name in EXTRA.items():
                if name in order:
                    table.cmap[cp] = name
    font.save(str(dst))


def register() -> None:
    """Register CMR (regular) and CMB (bold) with ReportLab. Safe to call repeatedly."""
    global _REGISTERED
    if _REGISTERED:
        return
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    cache = Path(settings.UPLOAD_DIR) / "_fonts"
    cache.mkdir(parents=True, exist_ok=True)
    for face, fname in (("CMR", "cmr10.ttf"), ("CMB", "cmb10.ttf")):
        dst = cache / f"{face.lower()}_resume_v2.ttf"
        if not dst.exists():
            _derive(_source_dir() / fname, dst)
        pdfmetrics.registerFont(TTFont(face, str(dst)))
    _REGISTERED = True


_ASCII = {"\u20b9": "Rs ", "\u2022": "-", "\u00a0": " ", "\u2026": "...", "\u00d7": "x", "\u2192": "->", "\u2212": "-", "\u2011": "-", "\u200b": ""}


def clean(text: str) -> str:
    """Make text safe for the font: map common symbols, strip accents, drop anything else unsupported."""
    out = []
    for ch in text:
        if ch in _ASCII:
            out.append(_ASCII[ch])
        elif ord(ch) < 128 or ord(ch) in EXTRA:
            out.append(ch)
        else:
            base = unicodedata.normalize("NFKD", ch)
            out.append("".join(c for c in base if ord(c) < 128))
    s = "".join(out)
    # straight quotes -> curly (TeX maps the straight double quote to a closing quote)
    s = re.sub(r'(^|[\s(\[])"', "\\1\u201c", s)
    s = s.replace('"', "\u201d")
    s = re.sub(r"(^|[\s(\[])'", "\\1\u2018", s)
    s = s.replace("'", "\u2019")
    return s


def font_dir_exists() -> bool:
    return os.path.isdir(_source_dir())
