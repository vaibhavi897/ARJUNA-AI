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
    from google.genai import types

    # Structured JSON responses used throughout the Learning Hub are served
    # by v1beta. Pin the API version so newer SDK defaults do not route these
    # requests to v1, where JSON mode is rejected.
    return genai.Client(
        api_key=settings.GEMINI_API_KEY,
        http_options=types.HttpOptions(api_version="v1beta"),
    )


def _shape(schema: Any, data: Any) -> Any:
    """Models sometimes return a bare list instead of {"field": [...]}. Wrap it when the schema has one obvious list field."""
    if isinstance(data, list):
        list_fields = [n for n, f in schema.model_fields.items() if "list" in str(f.annotation)]
        required = [n for n in list_fields if schema.model_fields[n].is_required()]
        target = required[0] if len(required) == 1 else (list_fields[0] if len(list_fields) == 1 else None)
        if target:
            return {target: data}
    return data


def _model_chain() -> list[str]:
    chain = [settings.GEMINI_MODEL] + [m.strip() for m in (settings.GEMINI_FALLBACK_MODELS or "").split(",") if m.strip()]
    seen: list[str] = []
    for m in chain:
        if m not in seen:
            seen.append(m)
    return seen


def generate_json(
    prompt: str,
    *,
    retries: int = 2,
    temperature: float = 0.4,
    max_tokens: int | None = None,
    schema: Any = None,
) -> Any:
    """Call Gemini for JSON. Falls through the model chain on 429/500/503 and
    retries with backoff. With ``schema`` (a pydantic model class) the response is
    validated and returned as a plain dict; invalid output triggers a retry."""
    if not settings.gemini_enabled:
        raise GeminiUnavailable("GEMINI_API_KEY is not configured.")
    try:
        from google.genai import errors, types
    except ImportError as exc:
        logger.exception("Google Gen AI SDK is missing from the backend environment")
        raise GeminiUnavailable(
            "Gemini support is not installed on the server. Install backend/requirements.txt and restart the backend."
        ) from exc

    client = _client()
    cfg: dict[str, Any] = {"response_mime_type": "application/json", "temperature": temperature}
    if max_tokens:
        cfg["max_output_tokens"] = max_tokens
    config = types.GenerateContentConfig(**cfg)
    last: Exception | None = None
    delay = 2.0
    for attempt in range(1, retries + 1):
        for model in _model_chain():
            try:
                response = client.models.generate_content(model=model, contents=prompt, config=config)
                text = (response.text or "").strip()
                if text.startswith("```"):
                    text = text.strip("`").removeprefix("json").strip()
                data = json.loads(text)
                if schema is not None:
                    data = schema.model_validate(_shape(schema, data)).model_dump()
                return data
            except errors.APIError as exc:
                last = exc
                code = getattr(exc, "code", None)
                logger.warning("Gemini %s on %s (attempt %d)", code, model, attempt)
                if code in (429, 500, 503, 404):
                    continue  # try the next model in the chain
                raise GeminiUnavailable(f"Gemini request failed: {exc}") from exc
            except (json.JSONDecodeError, ValueError) as exc:  # includes pydantic ValidationError
                last = exc
                logger.warning("Gemini output invalid on %s (attempt %d): %s", model, attempt, str(exc)[:120])
                break  # retry from the primary model with a fresh sample
        if attempt < retries:
            time.sleep(delay)
            delay *= 2
    raise GeminiUnavailable(f"Gemini request failed: {last}")


def cached_json(db: Session, kind: str, key_parts: tuple, prompt: str, **kw: Any) -> dict[str, Any] | None:
    """Return cached output, else call Gemini once and store it. None if unavailable."""
    key = make_key(kind, *key_parts)
    hit = get_cached(db, key)
    if hit is not None:
        return hit
    if not settings.gemini_enabled:
        return None
    try:
        data = generate_json(prompt, **kw)
    except GeminiUnavailable as exc:
        logger.warning("%s", exc)
        return None
    if not isinstance(data, dict):
        data = {"result": data}
    put_cached(db, key, kind, data)
    return data
