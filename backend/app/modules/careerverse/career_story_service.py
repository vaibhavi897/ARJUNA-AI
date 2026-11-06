"""Career Stories: stored chapter-based days in the life.

Stories are generated once (seed or Gemini) and stored; opening a story never
calls Gemini. Student position is saved so a story can be resumed.
"""

from __future__ import annotations

import re
import time
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.logging_config import get_logger
from app.models import Career, CareerStory, CareerStoryScene, User, UserCareerProgress
from app.modules.careerverse import gemini_service
from app.modules.careerverse.career_service import _progress

logger = get_logger(__name__)

VISUAL_KEYS = ("call", "whiteboard", "coffee", "arrival", "desk", "analysis", "code", "meeting", "presentation", "document", "design", "security", "field", "review", "wrapup")


def active_story(db: Session, career: Career) -> CareerStory | None:
    return db.scalar(
        select(CareerStory)
        .options(selectinload(CareerStory.scenes))
        .where(CareerStory.career_id == career.id, CareerStory.is_active.is_(True))
        .order_by(CareerStory.version.desc())
    )


def _scene_out(s: CareerStoryScene, total: int) -> dict[str, Any]:
    return {
        "scene_number": s.scene_number,
        "total_scenes": total,
        "time_of_day": s.time_of_day,
        "heading": s.heading,
        "narrative": s.narrative,
        "activities": s.activities,
        "tools": s.tools,
        "responsibilities": s.responsibilities,
        "industry_context": s.industry_context,
        "environment": s.environment,
        "visual_key": s.visual_key,
        "previous_scene": s.scene_number - 1 if s.scene_number > 1 else None,
        "next_scene": s.scene_number + 1 if s.scene_number < total else None,
    }


def story_overview(db: Session, career: Career, user: User) -> dict[str, Any] | None:
    story = active_story(db, career)
    if story is None:
        return None
    p = db.scalar(select(UserCareerProgress).where(UserCareerProgress.user_id == user.id, UserCareerProgress.career_id == career.id))
    total = len(story.scenes)
    last = min(p.last_scene_number, total) if p else 0
    return {
        "career": {"id": career.id, "slug": career.slug, "title": career.title, "industry": career.industry, "visual_theme": career.visual_theme},
        "story_id": story.id,
        "title": story.title,
        "summary": story.summary,
        "source": story.source,
        "scene_count": total,
        "scenes": [{"scene_number": s.scene_number, "heading": s.heading, "time_of_day": s.time_of_day, "visual_key": s.visual_key} for s in story.scenes],
        "progress": {
            "last_scene_number": last,
            "furthest_scene_number": min(p.furthest_scene_number, total) if p else 0,
            "completed": bool(p and p.story_completed),
            "resume_scene": last if 0 < last < total else 1,
            "can_resume": 0 < last < total,
        },
    }


def get_scene(db: Session, career: Career, user: User, scene_number: int) -> dict[str, Any] | None:
    story = active_story(db, career)
    if story is None:
        return None
    total = len(story.scenes)
    scene = next((s for s in story.scenes if s.scene_number == scene_number), None)
    if scene is None:
        return None
    p = _progress(db, user, career)
    from app.models import UserCareerView

    if p.last_scene_number == 0 or scene_number == 1:
        db.add(UserCareerView(user_id=user.id, career_id=career.id, view_type="story"))
    p.story_id = story.id
    p.last_scene_number = scene_number
    p.furthest_scene_number = max(p.furthest_scene_number, scene_number)
    if scene_number == total:
        p.story_completed = True
    db.commit()
    return _scene_out(scene, total)


# ------------------------------------------------------------------ Gemini generation
def _prompt(career: Career) -> str:
    facts = {
        "profession": career.title,
        "industry": career.industry,
        "description": career.description,
        "daily_responsibilities": career.responsibilities,
        "required_skills": [s.name for s in career.skills if s.kind in ("technical", "knowledge")],
        "tools_and_software": [s.name for s in career.skills if s.kind == "tool"],
        "work_environment": career.work_environment,
        "typical_working_hours": (career.work_life_balance or {}).get("hours"),
        "typical_locations": career.geography[:4],
        "career_levels": [t.designation for t in career.trajectory],
        "industry_drivers": (career.outlook or {}).get("growth_drivers"),
        "onet_tasks": (career.onet_data or {}).get("tasks"),
    }
    return (
        "Write a realistic, chronological 'day in the life' story for a student exploring this profession. "
        "It must reflect real professional workflows from the data, not generic fiction, and it is NOT a game: "
        "no questions, no choices. Third person present tense or second person, easy to understand, specific.\n"
        "Return JSON: {\"title\": str, \"summary\": str, \"scenes\": [ {\"time_of_day\": \"09:30 AM\", \"heading\": str, "
        "\"narrative\": 90-140 words describing what happens and why, \"activities\": [3-4 concrete strings], "
        "\"tools\": [2-5 tools/software], \"responsibilities\": [1-2 strings from the data], "
        "\"industry_context\": 1-2 sentences, \"environment\": 1 sentence about the physical/virtual workplace, "
        f"\"visual_key\": one of {list(VISUAL_KEYS)} }} ]}}.\n"
        "Produce 9 or 10 scenes from arrival to the end of the working day. Use ONLY the tools and tasks in the data "
        f"(or very standard ones for this job). {gemini_service.NO_INVENTION_RULES}\n\nDATA:\n{facts}"
    )


def validate_generated(career: Career, data: Any) -> list[dict[str, Any]] | None:
    """Structural checks plus verification against the career dataset."""
    scenes = data.get("scenes") if isinstance(data, dict) else None
    if not isinstance(scenes, list) or not 8 <= len(scenes) <= 12:
        return None
    clean: list[dict[str, Any]] = []
    for i, s in enumerate(scenes, start=1):
        if not isinstance(s, dict) or not all(isinstance(s.get(k), str) and s[k].strip() for k in ("time_of_day", "heading", "narrative")):
            return None
        key = s.get("visual_key") if s.get("visual_key") in VISUAL_KEYS else "desk"
        lst = lambda k: [str(x) for x in s.get(k, []) if isinstance(x, str)][:6]  # noqa: E731
        clean.append(dict(scene_number=i, time_of_day=s["time_of_day"][:40], heading=s["heading"][:200], narrative=s["narrative"].strip(),
                          activities=lst("activities"), tools=lst("tools"), responsibilities=lst("responsibilities"),
                          industry_context=(s.get("industry_context") or None), environment=(s.get("environment") or None), visual_key=key))
    # Verification: the story must mention a meaningful share of this
    # profession's own tools/skills, otherwise it is generic fiction.
    blob = " ".join(f"{c['heading']} {c['narrative']} {' '.join(c['tools'])}" for c in clean).lower()
    vocab = [s.name for s in career.skills if s.kind in ("tool", "technical")]
    hits = sum(1 for name in vocab if re.sub(r"\s*\(.*?\)", "", name).lower().split("/")[0].strip() in blob)
    if vocab and hits < min(3, len(vocab)):
        logger.warning("Story for %s rejected: only %d/%d dataset terms present", career.slug, hits, len(vocab))
        return None
    return clean


def generate_story_with_gemini(db: Session, career: Career) -> dict[str, Any]:
    """Generate once and store as the new active version. Raises if unavailable."""
    data = gemini_service.generate_json(_prompt(career), temperature=0.6)
    scenes = validate_generated(career, data)
    if scenes is None:
        raise gemini_service.GeminiUnavailable("Generated story failed validation against the career dataset.")
    latest = db.scalar(select(CareerStory.version).where(CareerStory.career_id == career.id).order_by(CareerStory.version.desc())) or 0
    db.execute(update(CareerStory).where(CareerStory.career_id == career.id).values(is_active=False))
    story = CareerStory(career_id=career.id, version=latest + 1, title=str(data.get("title") or f"A day in the life: {career.title}")[:200],
                        summary=str(data.get("summary") or "") or None, source="gemini", model=settings.GEMINI_MODEL, scene_count=len(scenes), is_active=True)
    db.add(story)
    db.flush()
    for sc in scenes:
        db.add(CareerStoryScene(story_id=story.id, **sc))
    db.commit()
    return {"career": career.slug, "version": story.version, "scenes": len(scenes)}


def generate_missing_stories(db: Session, delay_seconds: float = 4.0) -> dict[str, Any]:
    """Upgrade every career still on seed text. Rate-limit friendly and resumable."""
    if not settings.gemini_enabled:
        return {"skipped": "GEMINI_API_KEY not set", "generated": 0}
    careers = list(db.scalars(select(Career).order_by(Career.id)))
    done, failed = 0, []
    for c in careers:
        story = active_story(db, c)
        if story is not None and story.source == "gemini":
            continue
        try:
            generate_story_with_gemini(db, c)
            done += 1
        except gemini_service.GeminiUnavailable as exc:
            db.rollback()
            failed.append(c.slug)
            logger.warning("%s: %s", c.slug, exc)
        time.sleep(delay_seconds)
    return {"generated": done, "failed": failed}
