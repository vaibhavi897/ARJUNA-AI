"""Text extraction from uploaded resumes.

Uploads are untrusted input: the file is only ever read by a parser library,
never executed, and extraction failures are captured rather than raised.
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


def _extract_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception as exc:  # pragma: no cover - depends on file
            raise ExtractionError("The PDF is password protected.") from exc

    chunks: list[str] = []
    # Cap pages: a resume is short, and this bounds work on hostile input.
    for page in reader.pages[:15]:
        try:
            chunks.append(page.extract_text() or "")
        except Exception as exc:  # pragma: no cover
            logger.warning("PDF page extraction failed: %s", exc)
    return "\n".join(chunks)


def _extract_docx(path: Path) -> str:
    import docx

    document = docx.Document(str(path))
    chunks = [para.text for para in document.paragraphs]
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
