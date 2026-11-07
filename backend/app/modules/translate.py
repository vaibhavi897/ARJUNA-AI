"""Translate interface text and AI-written content with Sarvam AI.

Design:
  * every string is cached in the database by (language, hash), so repeated text is translated once for ALL users;
  * long strings are split at sentence boundaries to stay under the provider's per-call limit;
  * the provider key lives in the backend environment only;
  * when the provider is not configured or fails, the caller gets a clear error and the original English is kept.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
from typing import Awaitable, Callable

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging_config import get_logger
from app.models import TranslationCache

logger = get_logger(__name__)

# Languages offered in the UI (Sarvam language codes). English is the source.
LANGUAGES: dict[str, str] = {
    "en-IN": "English",
    "hi-IN": "हिन्दी (Hindi)",
    "mr-IN": "मराठी (Marathi)",
    "gu-IN": "ગુજરાતી (Gujarati)",
    "bn-IN": "বাংলা (Bengali)",
    "ta-IN": "தமிழ் (Tamil)",
    "te-IN": "తెలుగు (Telugu)",
    "kn-IN": "ಕನ್ನಡ (Kannada)",
    "ml-IN": "മലയാളം (Malayalam)",
    "pa-IN": "ਪੰਜਾਬੀ (Punjabi)",
    "od-IN": "ଓଡ଼ିଆ (Odia)",
}
MAX_CHUNK = 900            # characters per provider call (mayura accepts ~1000)
CONCURRENCY = 10

Sender = Callable[[str, str], Awaitable[str]]


class TranslationUnavailable(RuntimeError):
    """Provider missing or failing. The message is safe to show to the user."""


def is_configured() -> bool:
    return bool(settings.SARVAM_API_KEY)


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def split_text(text: str, limit: int = MAX_CHUNK) -> list[str]:
    """Split on sentence boundaries, never mid-word, so each piece fits one provider call."""
    text = text.strip()
    if len(text) <= limit:
        return [text]
    parts: list[str] = []
    cur = ""
    for sent in re.split(r"(?<=[.!?।])\s+", text):
        while len(sent) > limit:                                  # one enormous sentence: break at spaces
            cut = sent.rfind(" ", 0, limit)
            cut = cut if cut > 0 else limit
            if cur:
                parts.append(cur); cur = ""
            parts.append(sent[:cut]); sent = sent[cut:].lstrip()
        if len(cur) + len(sent) + 1 > limit and cur:
            parts.append(cur); cur = sent
        else:
            cur = f"{cur} {sent}".strip()
    if cur:
        parts.append(cur)
    return parts


async def _sarvam(text: str, lang: str) -> str:
    if not settings.SARVAM_API_KEY:
        raise TranslationUnavailable("Translation is not configured on this server.")
    body = {"input": text, "source_language_code": "en-IN", "target_language_code": lang, "model": settings.SARVAM_TRANSLATE_MODEL,
            "mode": "formal", "enable_preprocessing": True}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(f"{settings.SARVAM_BASE_URL}/translate", json=body, headers={"api-subscription-key": settings.SARVAM_API_KEY})
    except httpx.HTTPError as exc:
        logger.warning("Sarvam request failed: %s", type(exc).__name__)
        raise TranslationUnavailable("Could not reach the translation service. Please try again.") from exc
    if r.status_code in (401, 403):
        raise TranslationUnavailable("The translation service rejected the API key.")
    if r.status_code == 429:
        raise TranslationUnavailable("The translation service is busy. Please try again shortly.")
    if r.status_code >= 400:
        logger.warning("Sarvam returned HTTP %s", r.status_code)
        raise TranslationUnavailable("The translation service returned an error. Please try again.")
    try:
        out = r.json().get("translated_text")
    except ValueError:
        out = None
    if not isinstance(out, str) or not out.strip():
        raise TranslationUnavailable("The translation service returned an empty result.")
    return out


async def translate_many(db: Session, texts: list[str], lang: str, sender: Sender | None = None) -> list[str]:
    """Translate ``texts`` into ``lang``; returns a list of the same length and order."""
    if lang not in LANGUAGES:
        raise ValueError("Unsupported language.")
    if lang == "en-IN":
        return list(texts)
    send = sender or _sarvam
    clean = [t if isinstance(t, str) else "" for t in texts]
    uniq = list(dict.fromkeys(t.strip() for t in clean if t.strip()))
    hashes = {t: _hash(t) for t in uniq}
    found: dict[str, str] = {}
    if uniq:
        rows = db.scalars(select(TranslationCache).where(TranslationCache.lang == lang, TranslationCache.text_hash.in_(list(hashes.values()))))
        by_hash = {r.text_hash: r.translated_text for r in rows}
        found = {t: by_hash[h] for t, h in hashes.items() if h in by_hash}
    todo = [t for t in uniq if t not in found]

    sem = asyncio.Semaphore(CONCURRENCY)

    async def one(t: str) -> tuple[str, str]:
        async with sem:
            pieces = await asyncio.gather(*[send(p, lang) for p in split_text(t)])
        return t, " ".join(x.strip() for x in pieces)

    if todo:
        results = await asyncio.gather(*[one(t) for t in todo])
        new = dict(results)
        found.update(new)
        stmt = pg_insert(TranslationCache).values([{"lang": lang, "text_hash": hashes[t], "source_text": t, "translated_text": v} for t, v in new.items()])
        db.execute(stmt.on_conflict_do_nothing(constraint="uq_translation_lang_hash"))
        db.commit()
    return [found.get(t.strip(), t) if t.strip() else t for t in clean]
