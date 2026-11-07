"""Narration API: reads a piece of page text aloud with Sarvam AI.

Optional feature. When ``SARVAM_API_KEY`` is unset, ``/narration/status`` reports
``configured: false`` and the UI hides the control, so nothing else changes.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, Field

from app.api.routes.careerverse import _rate_limit
from app.modules import narration as nr
from app.modules import translate as tr
from app.modules.auth.dependencies import CurrentUser, DbSession

router = APIRouter(prefix="/narration", tags=["narration"])


class NarrateIn(BaseModel):
    text: str = Field(min_length=1, max_length=nr.MAX_TEXT)
    lang: str = Field(default="en-IN", max_length=12)


@router.get("/status")
def status_(user: CurrentUser) -> dict[str, Any]:
    """Whether narration can be offered, and in which languages."""
    return {
        "configured": nr.is_configured(),
        "languages": [{"code": c, "name": n} for c, n in tr.LANGUAGES.items()],
    }


@router.post("")
async def narrate(body: NarrateIn, user: CurrentUser, db: DbSession) -> Response:
    """Return spoken audio (WAV) for ``text``.

    English text is spoken as given. For any other language the text is first
    translated through the existing cached translation path, so narration matches
    the language the student has chosen for the interface.
    """
    if not nr.is_configured():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Narration is not configured on this server yet.")
    if body.lang not in tr.LANGUAGES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unsupported language.")

    _rate_limit(user.id, "narration", limit=40, per_seconds=60)

    spoken = body.text
    if body.lang != "en-IN":
        try:
            spoken = (await tr.translate_many(db, [body.text], body.lang))[0]
        except tr.TranslationUnavailable:
            # Fall back to reading the English text rather than failing outright.
            spoken = body.text

    try:
        audio = await nr.synthesize(spoken, body.lang)
    except nr.NarrationUnavailable as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc

    return Response(
        content=audio,
        media_type="audio/wav",
        headers={"Cache-Control": "private, max-age=86400", "Content-Length": str(len(audio))},
    )
