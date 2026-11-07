"""Translation API: shows the site in Indian languages. Requires a signed-in user; the provider key never leaves the server."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.api.routes.careerverse import _rate_limit
from app.modules.auth.dependencies import CurrentUser, DbSession
from app.modules import translate as tr

router = APIRouter(prefix="/translate", tags=["translate"])


class TranslateIn(BaseModel):
    lang: str = Field(max_length=12)
    texts: list[str] = Field(min_length=1, max_length=80)


@router.get("/languages")
def languages(user: CurrentUser) -> dict[str, Any]:
    return {"configured": tr.is_configured(), "languages": [{"code": c, "name": n} for c, n in tr.LANGUAGES.items()]}


@router.post("")
async def translate(body: TranslateIn, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    if body.lang not in tr.LANGUAGES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unsupported language.")
    if any(len(t) > 4000 for t in body.texts) or sum(len(t) for t in body.texts) > 40000:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "That is too much text to translate at once.")
    if body.lang != "en-IN" and not tr.is_configured():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Translation is not configured on this server yet.")
    _rate_limit(user.id, "translate", limit=60, per_seconds=60)
    try:
        out = await tr.translate_many(db, body.texts, body.lang)
    except tr.TranslationUnavailable as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    return {"lang": body.lang, "texts": out}
