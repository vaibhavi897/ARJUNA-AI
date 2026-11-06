"""Text extraction from uploaded resumes.

Uploads are untrusted input: the file is only ever read by a parser library,
never executed, and extraction failures are captured rather than raised.

Two things matter for the parser downstream:

1. **Bullet markers survive.** A PDF carries the glyph in the text stream, but
   a DOCX list paragraph does not - the bullet lives in the numbering
   definition. Without a marker the parser cannot tell a bullet from a new
   entry heading, so list paragraphs are re-prefixed here.
2. **Hyperlinks survive.** Resume headings usually read "Github" with the URL
   attached as a link annotation. The anchor text alone is useless, so link
   targets are appended to the line they belong to.
"""

from __future__ import annotations

import re
from pathlib import Path

from app.core.logging_config import get_logger

logger = get_logger(__name__)

ALLOWED_EXTENSIONS = {".pdf", ".docx"}
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/x-pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    # Some browsers send a generic type; the extension check is authoritative.
    "application/octet-stream",
}

PDF_MAGIC = b"%PDF-"
ZIP_MAGIC = b"PK\x03\x04"  # .docx is a zip container

_WHITESPACE = re.compile(r"[ \t ]+")
_BLANK_LINES = re.compile(r"\n{3,}")

# pypdf splits a word when the font kerns its first glyph away from the rest
# ("V yapariOne", "T echnology"). The pieces are rejoined only when a wider
# space threshold proves the two belong to the same word.
_SPLIT_LETTER_RE = re.compile(r"(?<![A-Za-z0-9])([A-Z])\s([a-z][A-Za-z0-9’'-]*)")
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9’'+#.&/-]*")

# A wide space threshold suppresses the spurious intra-word space but also
# welds genuinely adjacent words together, so it is only ever used as a
# reference vocabulary, never as the extracted text.
_REFERENCE_SPACE_WIDTH = 400.0

_DOCX_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_DOCX_REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_DOCX_BULLET_PREFIX_RE = re.compile(r"^[-*•●▪‣⁃>]")

MAX_PDF_PAGES = 15


class ExtractionError(RuntimeError):
    """Raised when no text could be read from the file."""


def sniff_matches_extension(head: bytes, extension: str) -> bool:
    """Cheap magic-byte check so a renamed file is rejected early."""
    if extension == ".pdf":
        return head.startswith(PDF_MAGIC)
    if extension == ".docx":
        return head.startswith(ZIP_MAGIC)
    return False


def _normalise(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _WHITESPACE.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    return _BLANK_LINES.sub("\n\n", text).strip()


def _line_key(value: str) -> str:
    """Comparison key that ignores spacing, case and punctuation differences."""
    return re.sub(r"[^a-z0-9]", "", value.lower())[:40]


def repair_split_words(text: str, reference: str) -> str:
    """Rejoin ``V yapariOne`` -> ``VyapariOne`` when ``reference`` agrees.

    ``reference`` is the same document extracted with a wider space threshold.
    A candidate is only merged when the merged form actually occurs there, so
    a real single-letter word ("A modular architecture") is left alone.
    """
    vocabulary = set(_WORD_RE.findall(reference))
    if not vocabulary:
        return text

    def merge(match: re.Match[str]) -> str:
        joined = match.group(1) + match.group(2)
        return joined if joined in vocabulary else match.group(0)

    return _SPLIT_LETTER_RE.sub(merge, text)


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------
def _pdf_link_targets(page) -> list[tuple[float, float, str]]:
    """``(y_bottom, y_top, url)`` for every link annotation on the page."""
    out: list[tuple[float, float, str]] = []
    try:
        annotations = page.get("/Annots") or []
    except Exception:  # pragma: no cover - malformed PDF
        return out
    for annotation in annotations:
        try:
            obj = annotation.get_object()
            uri = (obj.get("/A") or {}).get("/URI")
            rect = obj.get("/Rect")
            if not uri or not rect or len(rect) < 4:
                continue
            y_bottom = float(min(rect[1], rect[3]))
            y_top = float(max(rect[1], rect[3]))
            out.append((y_bottom, y_top, str(uri)))
        except Exception:  # pragma: no cover - malformed annotation
            continue
    return out


def _pdf_text_bands(page) -> list[tuple[float, str]]:
    """``(baseline_y, text)`` per visual line, used to place link annotations."""
    fragments: dict[float, list[str]] = {}

    def visitor(text, _cm, tm, _font_dict, _font_size) -> None:
        if not text or not text.strip():
            return
        fragments.setdefault(round(float(tm[5]), 1), []).append(text)

    try:
        page.extract_text(visitor_text=visitor)
    except Exception:  # pragma: no cover - depends on file
        return []
    return [(y, "".join(parts)) for y, parts in fragments.items()]


def _attach_pdf_links(page, text: str) -> str:
    """Append each link annotation's URL to the text line it sits on."""
    links = _pdf_link_targets(page)
    if not links:
        return text

    bands = _pdf_text_bands(page)
    per_line: dict[str, list[str]] = {}
    unplaced: list[str] = []
    for y_bottom, y_top, url in links:
        band = next(
            (
                band_text
                for band_y, band_text in bands
                if y_bottom - 2.0 <= band_y <= y_top + 2.0
            ),
            None,
        )
        key = _line_key(band) if band else ""
        if key:
            per_line.setdefault(key, []).append(url)
        else:
            unplaced.append(url)

    out: list[str] = []
    for line in text.split("\n"):
        urls = per_line.pop(_line_key(line), None)
        if urls:
            missing = [url for url in urls if url not in line]
            if missing:
                line = " ".join([line, *missing]).strip()
        out.append(line)

    # Links whose line could not be located still belong to the document.
    leftovers = unplaced + [url for urls in per_line.values() for url in urls]
    if leftovers:
        out.append(" ".join(leftovers))
    return "\n".join(out)


def _extract_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception as exc:  # pragma: no cover - depends on file
            raise ExtractionError("The PDF is password protected.") from exc

    chunks: list[str] = []
    reference_chunks: list[str] = []
    # Cap pages: a resume is short, and this bounds work on hostile input.
    for page in reader.pages[:MAX_PDF_PAGES]:
        try:
            page_text = page.extract_text() or ""
        except Exception as exc:  # pragma: no cover
            logger.warning("PDF page extraction failed: %s", exc)
            continue
        chunks.append(_attach_pdf_links(page, page_text))
        try:
            reference_chunks.append(
                page.extract_text(space_width=_REFERENCE_SPACE_WIDTH) or ""
            )
        except Exception:  # pragma: no cover - reference pass is best effort
            pass

    text = "\n".join(chunks)
    reference = "\n".join(reference_chunks)
    return repair_split_words(text, reference) if reference else text


# ---------------------------------------------------------------------------
# DOCX
# ---------------------------------------------------------------------------
def _docx_is_list_paragraph(paragraph) -> bool:
    style = (getattr(paragraph.style, "name", "") or "").lower()
    if "list bullet" in style or "list number" in style or "list paragraph" in style:
        return True
    properties = paragraph._p.find(f"{_DOCX_NS}pPr")
    return properties is not None and properties.find(f"{_DOCX_NS}numPr") is not None


def _docx_paragraph_links(paragraph) -> list[str]:
    """URLs behind ``w:hyperlink`` runs in this paragraph."""
    urls: list[str] = []
    try:
        rels = paragraph.part.rels
    except Exception:  # pragma: no cover - defensive
        return urls
    for node in paragraph._p.findall(f".//{_DOCX_NS}hyperlink"):
        rel_id = node.get(f"{_DOCX_REL_NS}id")
        if not rel_id:
            continue
        rel = rels.get(rel_id)
        target = getattr(rel, "target_ref", None)
        if target and str(target).lower().startswith(("http://", "https://")):
            urls.append(str(target))
    return urls


def _extract_docx(path: Path) -> str:
    import docx

    document = docx.Document(str(path))
    chunks: list[str] = []
    for paragraph in document.paragraphs:
        body = paragraph.text.strip()
        if not body:
            continue
        extra = [url for url in _docx_paragraph_links(paragraph) if url not in body]
        if extra:
            body = " ".join([body, *extra])
        # Word keeps the bullet glyph in the numbering definition, not the run
        # text; the parser needs a marker to tell a bullet from a heading.
        if _docx_is_list_paragraph(paragraph) and not _DOCX_BULLET_PREFIX_RE.match(body):
            body = f"• {body}"
        chunks.append(body)

    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                chunks.append(" | ".join(cells))
    return "\n".join(chunks)


def extract_text(path: Path, extension: str) -> str:
    """Return normalised plain text. Raises :class:`ExtractionError` when empty."""
    extension = extension.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ExtractionError(f"Unsupported file type: {extension}")

    try:
        raw = _extract_pdf(path) if extension == ".pdf" else _extract_docx(path)
    except ExtractionError:
        raise
    except Exception as exc:
        logger.exception("Resume extraction failed for %s", path.name)
        raise ExtractionError(
            "We could not read this file. Please re-export it and try again."
        ) from exc

    text = _normalise(raw)
    if len(text) < 40:
        raise ExtractionError(
            "Almost no text was found. If this is a scanned resume, upload a "
            "text-based PDF or DOCX instead."
        )
    return text
