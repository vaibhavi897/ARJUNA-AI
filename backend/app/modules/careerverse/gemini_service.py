"""Gemini access. Server-side only; every result is cached in PostgreSQL.

Gemini explains and narrates *sourced* data. It is never asked to produce
salary, growth or hiring figures, and prompts say so explicitly.
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging_config import get_logger
from app.models import CareerAiOutput

logger = get_logger(__name__)

NO_INVENTION_RULES = (
    "Rules: use ONLY the facts provided in the input. Do NOT invent or estimate salaries, "
    "compensation, employment numbers, growth rates, or claims about which companies are hiring. "
    "If a figure is missing from the input, do not mention one. Plain, student-friendly English."
)


class GeminiUnavailable(RuntimeError):
    """Raised when Gemini is not configured or the call ultimately failed."""


def is_enabled() -> bool:
    return settings.gemini_enabled


def make_key(kind: str, *parts: Any) -> str:
    digest = hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()[:40]
    return f"{kind}:{digest}"


def get_cached(db: Session, key: str) -> dict[str, Any] | None:
    row = db.scalar(select(CareerAiOutput).where(CareerAiOutput.cache_key == key))
    return row.payload if row else None


def put_cached(db: Session, key: str, kind: str, payload: dict[str, Any]) -> None:
    row = db.scalar(select(CareerAiOutput).where(CareerAiOutput.cache_key == key))
    if row is None:
        db.add(CareerAiOutput(cache_key=key, kind=kind, payload=payload, model=settings.GEMINI_MODEL))
    else:
        row.payload, row.model = payload, settings.GEMINI_MODEL
    db.flush()


def _client():  # noqa: ANN202
    from google import genai  # imported lazily so the app boots without the SDK

    return genai.Client(api_key=settings.GEMINI_API_KEY)


def generate_json(prompt: str, *, retries: int = 3, temperature: float = 0.4) -> Any:
    """Call Gemini for a JSON response, with backoff on rate limits (429/503)."""
    if not settings.gemini_enabled:
        raise GeminiUnavailable("GEMINI_API_KEY is not configured.")
    from google.genai import errors, types

    client = _client()
    config = types.GenerateContentConfig(response_mime_type="application/json", temperature=temperature)
    delay = 2.0
    last: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            response = client.models.generate_content(model=settings.GEMINI_MODEL, contents=prompt, config=config)
            text = (response.text or "").strip()
            if text.startswith("```"):
                text = text.strip("`").removeprefix("json").strip()
            return json.loads(text)
        except errors.APIError as exc:
            last = exc
            code = getattr(exc, "code", None)
            if code in (429, 500, 503) and attempt < retries:
                logger.warning("Gemini %s on attempt %d; retrying in %.0fs", code, attempt, delay)
                time.sleep(delay)
                delay *= 2
                continue
            break
        except (json.JSONDecodeError, ValueError) as exc:
            last = exc
            logger.warning("Gemini returned non-JSON on attempt %d", attempt)
    raise GeminiUnavailable(f"Gemini request failed: {last}")


def cached_json(db: Session, kind: str, key_parts: tuple, prompt: str) -> dict[str, Any] | None:
    """Return cached output, else call Gemini once and store it. None if unavailable."""
    key = make_key(kind, *key_parts)
    hit = get_cached(db, key)
    if hit is not None:
        return hit
    if not settings.gemini_enabled:
        return None
    try:
        data = generate_json(prompt)
    except GeminiUnavailable as exc:
        logger.warning("%s", exc)
        return None
    if not isinstance(data, dict):
        data = {"result": data}
    put_cached(db, key, kind, data)
    return data
