"""Saved items and Gemini message drafts for curated Career Connect data."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.models import CareerConnectSavedItem
from app.modules.auth.dependencies import CurrentUser, DbSession
from app.modules.careerverse.gemini_service import GeminiUnavailable, generate_json
from app.models import StudentProfile

router = APIRouter(prefix="/career-connect", tags=["career-connect"])


class SavedItemIn(BaseModel):
    item_type: Literal["job", "professional"]
    item_id: str = Field(min_length=1, max_length=100)


class MessageDraftIn(BaseModel):
    purpose: Literal["career guidance", "informational interview", "referral request", "general networking"]
    professional_name: str = Field(min_length=1, max_length=120)
    designation: str = Field(min_length=1, max_length=160)
    company: str = Field(min_length=1, max_length=160)
    domain: str = Field(min_length=1, max_length=100)


@router.get("/saved")
def list_saved(user: CurrentUser, db: DbSession) -> list[dict]:
    rows = db.scalars(select(CareerConnectSavedItem).where(CareerConnectSavedItem.user_id == user.id).order_by(CareerConnectSavedItem.created_at.desc()))
    return [{"item_type": r.item_type, "item_id": r.item_id} for r in rows]


@router.post("/saved", status_code=status.HTTP_201_CREATED)
def save_item(body: SavedItemIn, user: CurrentUser, db: DbSession) -> dict:
    row = db.scalar(select(CareerConnectSavedItem).where(CareerConnectSavedItem.user_id == user.id, CareerConnectSavedItem.item_type == body.item_type, CareerConnectSavedItem.item_id == body.item_id))
    if row is None:
        db.add(CareerConnectSavedItem(user_id=user.id, item_type=body.item_type, item_id=body.item_id))
        db.commit()
    return {"saved": True, "item_type": body.item_type, "item_id": body.item_id}


@router.delete("/saved/{item_type}/{item_id}")
def remove_saved(item_type: Literal["job", "professional"], item_id: str, user: CurrentUser, db: DbSession) -> dict:
    row = db.scalar(select(CareerConnectSavedItem).where(CareerConnectSavedItem.user_id == user.id, CareerConnectSavedItem.item_type == item_type, CareerConnectSavedItem.item_id == item_id))
    if row is not None:
        db.delete(row)
        db.commit()
    return {"saved": False, "item_type": item_type, "item_id": item_id}


@router.post("/message-draft")
def draft_message(body: MessageDraftIn, user: CurrentUser, db: DbSession) -> dict:
    profile = db.scalar(select(StudentProfile).where(StudentProfile.user_id == user.id))
    profile_name = user.full_name
    background = ""
    if profile:
        background = ", ".join(filter(None, [profile.headline, profile.bio]))[:700]
    prompt = f"""Write one concise, warm, professional LinkedIn connection message (80-120 words maximum). It is a draft only; never claim it was sent. Purpose: {body.purpose}. Recipient: {body.professional_name}, {body.designation} at {body.company}. Career domain: {body.domain}. Student name: {profile_name}. Student profile summary (may be empty): {background}. Use only these facts. Do not invent shared connections, experience, achievements, or facts about the recipient. Be respectful and specific to the purpose. Return JSON with one string property named message."""
    try:
        result = generate_json(prompt, retries=2, temperature=0.5, max_tokens=300)
    except GeminiUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    message = result.get("message") if isinstance(result, dict) else None
    if not isinstance(message, str) or not message.strip():
        raise HTTPException(status_code=502, detail="Gemini returned an empty draft. Please try again.")
    return {"message": message.strip()}
