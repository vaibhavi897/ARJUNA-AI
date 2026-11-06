"""CareerVerse endpoints: career catalogue, insights, stories, fit and comparison.

All routes require the existing JWT session. ``{career_ref}`` accepts either the
numeric id or the slug.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.models import Career
from app.modules.auth.dependencies import CurrentUser, DbSession
from app.modules.careerverse import (
    career_comparison_service,
    career_fit_service,
    career_research_service,
    career_salary_service,
    career_service,
    career_story_service,
)

router = APIRouter(tags=["careerverse"])

# --- tiny per-user rate limiter for the endpoints that can reach Gemini -------
_WINDOWS: dict[tuple[int, str], deque[float]] = defaultdict(deque)


def _rate_limit(user_id: int, bucket: str, limit: int = 12, per_seconds: int = 60) -> None:
    now = time.monotonic()
    q = _WINDOWS[(user_id, bucket)]
    while q and now - q[0] > per_seconds:
        q.popleft()
    if len(q) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="You are doing that too quickly. Please wait a minute and try again.",
            headers={"Retry-After": str(per_seconds)},
        )
    q.append(now)


def _career_or_404(db: DbSession, ref: str) -> Career:
    career = career_service.resolve_career(db, ref)
    if career is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Career not found.")
    return career


class SavedBody(BaseModel):
    saved: bool


class ComparisonBody(BaseModel):
    career_ids: list[int] = Field(min_length=2, max_length=3)


# ------------------------------------------------------------------ catalogue
@router.get("/careers")
def list_careers(user: CurrentUser, db: DbSession, q: str | None = Query(default=None, max_length=80), industry: str | None = Query(default=None, max_length=80)) -> dict[str, Any]:
    items = career_service.list_careers(db, user, q, industry)
    return {"items": items, "total": len(items), "industries": career_service.list_industries(db)}


@router.get("/careers/{career_ref}")
def career_detail(career_ref: str, user: CurrentUser, db: DbSession, track: bool = False) -> dict[str, Any]:
    career = _career_or_404(db, career_ref)
    if track:
        career_service.record_view(db, user, career, "insights")
    return career_service.career_detail(db, career)


@router.get("/careers/{career_ref}/salary")
def career_salary(career_ref: str, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    return career_salary_service.salary_view(db, _career_or_404(db, career_ref))


@router.get("/careers/{career_ref}/companies")
def career_companies(career_ref: str, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    return career_service.companies_view(_career_or_404(db, career_ref))


@router.get("/careers/{career_ref}/skills")
def career_skills(career_ref: str, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    return career_service.skills_view(_career_or_404(db, career_ref))


@router.get("/careers/{career_ref}/trajectory")
def career_trajectory(career_ref: str, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    return career_service.trajectory_view(_career_or_404(db, career_ref))


@router.get("/careers/{career_ref}/exit-options")
def career_exit_options(career_ref: str, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    return career_service.exits_view(_career_or_404(db, career_ref))


@router.post("/careers/{career_ref}/ai-summary")
def career_ai_summary(career_ref: str, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    """Plain-language summary written by Gemini from stored data; generated once, then cached."""
    career = _career_or_404(db, career_ref)
    cached = career_service.gemini_service.get_cached(db, career_service.gemini_service.make_key("overview", career.id, str(career.last_updated)))
    if cached is None:
        _rate_limit(user.id, "ai")
    summary = cached or career_service.ai_summary(db, career)
    db.commit()
    return {"ai_summary": summary, "ai_available": career_service.gemini_service.is_enabled()}


@router.get("/careers/{career_ref}/job-market")
def career_job_market(career_ref: str, user: CurrentUser, db: DbSession, country: str = Query(default="in", pattern="^[a-z]{2}$")) -> dict[str, Any]:
    """Optional live listings (Adzuna). Never required for the rest of CareerVerse."""
    career = _career_or_404(db, career_ref)
    if not career_research_service.adzuna_enabled():
        return {"available": False, "reason": "Live job listings are not configured."}
    data = career_research_service.fetch_adzuna_jobs(career.title, country)
    if data is None:
        return {"available": False, "reason": "Live job listings are temporarily unavailable."}
    return {"available": True, **data}


@router.put("/careers/{career_ref}/saved")
def save_career(career_ref: str, body: SavedBody, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    career = _career_or_404(db, career_ref)
    p = career_service.set_saved(db, user, career, body.saved)
    return {"career_id": career.id, "is_saved": p.is_saved}


# ------------------------------------------------------------------ stories
@router.get("/career-stories/{career_ref}")
def story(career_ref: str, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    result = career_story_service.story_overview(db, _career_or_404(db, career_ref), user)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No story is available for this career yet.")
    return result


@router.get("/career-stories/{career_ref}/scenes/{scene_number}")
def story_scene(career_ref: str, scene_number: int, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    result = career_story_service.get_scene(db, _career_or_404(db, career_ref), user, scene_number)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scene not found.")
    return result


# ------------------------------------------------------------------ fit + comparison
@router.get("/career-fit")
def career_recommendations(user: CurrentUser, db: DbSession, limit: int = Query(default=8, ge=1, le=20)) -> dict[str, Any]:
    return career_fit_service.recommend(db, user, limit)


@router.post("/career-fit/{career_ref}")
def career_fit(career_ref: str, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    career = _career_or_404(db, career_ref)
    _rate_limit(user.id, "fit", limit=10)
    return career_fit_service.analyse(db, user, career)


@router.post("/career-comparison")
def career_comparison(body: ComparisonBody, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    ids = list(dict.fromkeys(body.career_ids))
    if len(ids) < 2:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Choose at least two different careers.")
    _rate_limit(user.id, "compare")
    result = career_comparison_service.compare(db, ids)
    if len(result["careers"]) != len(ids):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or more careers were not found.")
    return result


# ------------------------------------------------------------------ student state
@router.get("/user/career-history")
def career_history(user: CurrentUser, db: DbSession) -> dict[str, Any]:
    return {"items": career_service.career_history(db, user)}


@router.get("/user/career-progress")
def career_progress(user: CurrentUser, db: DbSession) -> dict[str, Any]:
    return {"items": career_service.career_progress_list(db, user)}


@router.get("/user/saved-careers")
def saved_careers(user: CurrentUser, db: DbSession) -> dict[str, Any]:
    return {"items": career_service.saved_careers(db, user)}
