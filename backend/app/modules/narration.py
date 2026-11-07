"""Narration (text to speech) with Sarvam AI.

Design mirrors ``app.modules.translate``:

  * the provider key lives in the backend environment only — the browser never sees it;
  * finished audio is cached on disk by (text, language, voice, model), so a scene
    narrated once is never paid for again;
  * long text is split at sentence boundaries to stay under the per-call limit and
    the returned pieces are concatenated into a single WAV;
  * when the provider is not configured or fails, the caller gets a clear message
    and the feature simply stays hidden in the UI.

Narration is optional everywhere. Nothing else in the app depends on it.
"""

from __future__ import annotations

import base64
import hashlib
import io
import wave
from pathlib import Path

import httpx

from app.core.config import settings
from app.core.logging_config import get_logger
from app.modules.translate import LANGUAGES, split_text

logger = get_logger(__name__)

# bulbul:v2 accepts 1500 characters per call, v3 and v4-flash accept 2500. Stay
# under the smallest so the chunker is correct for every configured model.
MAX_CHARS = 1400
MAX_TEXT = 6000                     # refuse anything longer than a few paragraphs
CACHE_DIR = Path(__file__).resolve().parents[2] / "uploads" / "narration"


class NarrationUnavailable(RuntimeError):
    """Provider missing or failing. The message is safe to show to the user."""


def is_configured() -> bool:
    return bool(settings.SARVAM_API_KEY)


def _cache_key(text: str, lang: str) -> str:
    raw = "\x1f".join([text, lang, settings.SARVAM_TTS_MODEL, settings.SARVAM_TTS_SPEAKER, f"{settings.SARVAM_TTS_PACE:.2f}"])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _cache_path(key: str) -> Path:
    return CACHE_DIR / f"{key}.wav"


def _join_wav(chunks: list[bytes]) -> bytes:
    """Concatenate WAV chunks into one file. Falls back to the first chunk on mismatch."""
    if len(chunks) == 1:
        return chunks[0]
    out = io.BytesIO()
    writer: wave.Wave_write | None = None
    try:
        for chunk in chunks:
            with wave.open(io.BytesIO(chunk), "rb") as r:
                if writer is None:
                    writer = wave.open(out, "wb")
                    writer.setnchannels(r.getnchannels())
                    writer.setsampwidth(r.getsampwidth())
                    writer.setframerate(r.getframerate())
                writer.writeframes(r.readframes(r.getnframes()))
        if writer is not None:
            writer.close()
    except wave.Error as exc:
        logger.warning("Could not join narration chunks (%s); returning the first piece", exc)
        return chunks[0]
    return out.getvalue()


async def _sarvam_tts(client: httpx.AsyncClient, text: str, lang: str) -> bytes:
    body: dict[str, object] = {
        "text": text,
        "language_code": lang,
        "speaker": settings.SARVAM_TTS_SPEAKER,
        "model": settings.SARVAM_TTS_MODEL,
        "pace": settings.SARVAM_TTS_PACE,
    }
    # Normalises numbers and English words ("2.6 points", "31 hours"), which
    # this narration is full of. Verified accepted on bulbul:v3.
    body["enable_preprocessing"] = True
    try:
        r = await client.post(
            f"{settings.SARVAM_BASE_URL}/text-to-speech",
            json=body,
            headers={"api-subscription-key": settings.SARVAM_API_KEY or ""},
        )
    except httpx.HTTPError as exc:
        logger.warning("Sarvam TTS request failed: %s", type(exc).__name__)
        raise NarrationUnavailable("Could not reach the narration service. Please try again.") from exc

    if r.status_code in (401, 403):
        raise NarrationUnavailable("The narration service rejected the API key.")
    if r.status_code == 429:
        raise NarrationUnavailable("The narration service is busy. Please try again shortly.")
    if r.status_code >= 400:
        logger.warning("Sarvam TTS returned HTTP %s: %s", r.status_code, r.text[:300])
        raise NarrationUnavailable("The narration service returned an error. Please try again.")

    try:
        audios = r.json().get("audios")
    except ValueError:
        audios = None
    if not isinstance(audios, list) or not audios or not isinstance(audios[0], str):
        raise NarrationUnavailable("The narration service returned no audio.")
    try:
        return base64.b64decode(audios[0])
    except (ValueError, TypeError) as exc:
        raise NarrationUnavailable("The narration service returned audio that could not be read.") from exc


async def synthesize(text: str, lang: str) -> bytes:
    """Return WAV bytes for ``text`` in ``lang``. Cached on disk across users."""
    if not is_configured():
        raise NarrationUnavailable("Narration is not configured on this server.")
    if lang not in LANGUAGES:
        raise NarrationUnavailable("Unsupported narration language.")
    text = " ".join(text.split())
    if not text:
        raise NarrationUnavailable("There is nothing to read out.")
    if len(text) > MAX_TEXT:
        raise NarrationUnavailable("That is too much text to read out at once.")

    key = _cache_key(text, lang)
    path = _cache_path(key)
    try:
        if path.is_file():
            return path.read_bytes()
    except OSError:
        pass  # unreadable cache is not an error; just synthesise again

    pieces = split_text(text, MAX_CHARS)
    async with httpx.AsyncClient(timeout=60) as client:
        chunks = [await _sarvam_tts(client, p, lang) for p in pieces]
    audio = _join_wav(chunks)

    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".part")
        tmp.write_bytes(audio)
        tmp.replace(path)
    except OSError as exc:
        logger.warning("Could not cache narration audio: %s", exc)
    return audio
