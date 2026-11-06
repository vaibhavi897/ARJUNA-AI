"""Career catalogue, insight sections and per-student career state."""

from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Career,
    CareerStory,
    User,
    UserCareerProgress,
    UserCareerView,
)
from app.modules.careerverse import career_salary_service, gemini_service


def resolve_career(db: Session, ref: str) -> Career | None:
    """Accepts a numeric id or a slug."""
    stmt = select(Career).options(
        selectinload(Career.skills),
        selectinload(Career.qualifications),
        selectinload(Career.trajectory),
        selectinload(Career.exits),
        selectinload(Career.companies),
        selectinload(Career.sources),
    )
    if ref.isdigit():
        return db.scalar(stmt.where(Career.id == int(ref)))
    return db.scalar(stmt.where(Career.slug == ref))


def _progress_map(db: Session, user: User) -> dict[int, UserCareerProgress]:
    rows = db.scalars(select(UserCareerProgress).where(UserCareerProgress.user_id == user.id))
    return {p.career_id: p for p in rows}


def _story_counts(db: Session) -> dict[int, int]:
    rows = db.execute(
        select(CareerStory.career_id, CareerStory.scene_count).where(CareerStory.is_active.is_(True))
    )
    return {cid: n for cid, n in rows}


def list_industries(db: Session) -> list[dict[str, Any]]:
    rows = db.execute(select(Career.industry, func.count()).group_by(Career.industry).order_by(Career.industry))
    return [{"industry": i, "count": n} for i, n in rows]


def list_careers(
    db: Session, user: User, q: str | None = None, industry: str | None = None
) -> list[dict[str, Any]]:
    stmt = select(Career).order_by(Career.industry, Career.title)
    if industry:
        stmt = stmt.where(Career.industry == industry)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Career.title.ilike(like), Career.short_description.ilike(like), Career.industry.ilike(like)))
    careers = list(db.scalars(stmt))
    progress = _progress_map(db, user)
    counts = _story_counts(db)
    out = []
    for c in careers:
        p = progress.get(c.id)
        out.append(
            {
                "id": c.id,
                "slug": c.slug,
                "title": c.title,
                "industry": c.industry,
                "short_description": c.short_description,
                "visual_theme": c.visual_theme,
                "scene_count": counts.get(c.id, 0),
                "story_last_scene": p.last_scene_number if p else 0,
                "story_completed": p.story_completed if p else False,
                "insights_viewed": p.insights_viewed if p else False,
                "is_saved": p.is_saved if p else False,
            }
        )
    return out


def _skills_grouped(career: Career) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {"technical": [], "tool": [], "knowledge": [], "soft": []}
    for s in career.skills:
        groups.setdefault(s.kind, []).append(s.name)
    return groups


def skills_view(career: Career) -> dict[str, Any]:
    g = _skills_grouped(career)
    return {
        "technical_skills": g["technical"],
        "tools": g["tool"],
        "industry_knowledge": g["knowledge"],
        "soft_skills": g["soft"],
        "degrees": [q.name for q in career.qualifications if q.kind == "degree"],
        "certifications": [q.name for q in career.qualifications if q.kind == "certification"],
        "onet": career.onet_data or None,
        "onet_synced_at": career.onet_synced_at.isoformat() if career.onet_synced_at else None,
    }


def companies_view(career: Career) -> dict[str, Any]:
    return {
        "companies": [
            {"name": c.name, "industry": c.industry, "job_titles": c.job_titles, "regions": c.regions}
            for c in career.companies
        ],
        "disclaimer": "Illustrative employers known to hire for this function. This is a curated list, not live hiring data or a recruitment claim.",
    }


def trajectory_view(career: Career) -> dict[str, Any]:
    return {
        "stages": [
            {
                "stage": t.stage,
                "level": t.level_name,
                "designation": t.designation,
                "experience_min_years": t.experience_min_years,
                "experience_max_years": t.experience_max_years,
            }
            for t in career.trajectory
        ]
    }


def exits_view(career: Career) -> dict[str, Any]:
    def names(kind: str) -> list[str]:
        return [e.name for e in career.exits if e.kind == kind]

    return {
        "roles": names("role"),
        "industries": names("industry"),
        "qualifications": names("qualification"),
    }


def sources_view(career: Career) -> list[dict[str, Any]]:
    return [
        {"kind": s.kind, "name": s.name, "url": s.url, "covers": s.covers, "last_verified": s.last_verified.isoformat() if s.last_verified else None}
        for s in career.sources
    ]


def summary_card(career: Career) -> dict[str, Any]:
    return {
        "id": career.id,
        "slug": career.slug,
        "title": career.title,
        "industry": career.industry,
        "short_description": career.short_description,
        "visual_theme": career.visual_theme,
    }


def career_detail(db: Session, career: Career) -> dict[str, Any]:
    wlb = dict(career.work_life_balance or {})
    ai = gemini_service.get_cached(db, gemini_service.make_key("overview", career.id, str(career.last_updated)))
    return {
        **summary_card(career),
        "overview": {
            "description": career.description,
            "responsibilities": career.responsibilities,
            "industries": career.industries,
            "work_environment": career.work_environment,
        },
        "ai_summary": ai,
        "ai_available": gemini_service.is_enabled(),
        "salary": career_salary_service.salary_view(db, career),
        "companies": companies_view(career),
        "trajectory": trajectory_view(career),
        "work_life_balance": {**wlb, "basis": "ARJUNA AI editorial estimate (1 = light load, 5 = very heavy)"},
        "skills": skills_view(career),
        "outlook": career.outlook,
        "exits": exits_view(career),
        "advantages": career.advantages,
        "disadvantages": career.disadvantages,
        "geography": career.geography,
        "onet_code": career.onet_code,
        "soc_code": career.soc_code,
        "sources": sources_view(career),
        "last_updated": career.last_updated.isoformat() if career.last_updated else None,
    }


def ai_summary(db: Session, career: Career) -> dict[str, Any] | None:
    """Gemini plain-language summary of the stored structured data (cached once)."""
    facts = {
        "title": career.title,
        "description": career.description,
        "responsibilities": career.responsibilities,
        "work_environment": career.work_environment,
        "trajectory": [t.designation for t in career.trajectory],
        "exit_roles": [e.name for e in career.exits if e.kind == "role"],
        "work_life_balance": career.work_life_balance,
        "outlook": {k: v for k, v in (career.outlook or {}).items() if k in ("current_demand", "growth_drivers", "emerging_technologies")},
    }
    prompt = (
        "You are a career guide for Indian university students. Using ONLY this structured data, "
        "write JSON: {\"headline\": one sentence, \"what_it_is\": 2-3 sentences, \"a_typical_week\": 2-3 sentences, "
        "\"who_it_suits\": 2 sentences, \"growth_path\": 2 sentences, \"things_to_know\": [3 short strings]}. "
        f"{gemini_service.NO_INVENTION_RULES}\n\nDATA:\n{facts}"
    )
    return gemini_service.cached_json(db, "overview", (career.id, str(career.last_updated)), prompt)


# ------------------------------------------------------------------ student state
def _progress(db: Session, user: User, career: Career) -> UserCareerProgress:
    p = db.scalar(
        select(UserCareerProgress).where(UserCareerProgress.user_id == user.id, UserCareerProgress.career_id == career.id)
    )
    if p is None:
        p = UserCareerProgress(user_id=user.id, career_id=career.id)
        db.add(p)
        db.flush()
    return p


def record_view(db: Session, user: User, career: Career, view_type: str) -> None:
    db.add(UserCareerView(user_id=user.id, career_id=career.id, view_type=view_type))
    if view_type == "insights":
        _progress(db, user, career).insights_viewed = True
    db.commit()


def set_saved(db: Session, user: User, career: Career, saved: bool) -> UserCareerProgress:
    p = _progress(db, user, career)
    p.is_saved = saved
    db.commit()
    return p


def career_history(db: Session, user: User, limit: int = 30) -> list[dict[str, Any]]:
    rows = db.execute(
        select(UserCareerView.career_id, UserCareerView.view_type, func.max(UserCareerView.viewed_at).label("at"))
        .where(UserCareerView.user_id == user.id)
        .group_by(UserCareerView.career_id, UserCareerView.view_type)
        .order_by(func.max(UserCareerView.viewed_at).desc())
        .limit(limit)
    ).all()
    careers = {c.id: c for c in db.scalars(select(Career).where(Career.id.in_([r.career_id for r in rows] or [0])))}
    return [
        {**summary_card(careers[r.career_id]), "view_type": r.view_type, "viewed_at": r.at.isoformat()}
        for r in rows
        if r.career_id in careers
    ]


def _progress_item(p: UserCareerProgress, scene_count: int) -> dict[str, Any]:
    return {
        **summary_card(p.career),
        "last_scene_number": p.last_scene_number,
        "furthest_scene_number": p.furthest_scene_number,
        "scene_count": scene_count,
        "story_completed": p.story_completed,
        "insights_viewed": p.insights_viewed,
        "is_saved": p.is_saved,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


def career_progress_list(db: Session, user: User) -> list[dict[str, Any]]:
    counts = _story_counts(db)
    rows = db.scalars(
        select(UserCareerProgress)
        .options(selectinload(UserCareerProgress.career))
        .where(UserCareerProgress.user_id == user.id)
        .order_by(UserCareerProgress.updated_at.desc())
    )
    return [_progress_item(p, counts.get(p.career_id, 0)) for p in rows if p.last_scene_number or p.insights_viewed or p.is_saved]


def saved_careers(db: Session, user: User) -> list[dict[str, Any]]:
    counts = _story_counts(db)
    rows = db.scalars(
        select(UserCareerProgress)
        .options(selectinload(UserCareerProgress.career))
        .where(UserCareerProgress.user_id == user.id, UserCareerProgress.is_saved.is_(True))
        .order_by(UserCareerProgress.updated_at.desc())
    )
    return [_progress_item(p, counts.get(p.career_id, 0)) for p in rows]


def now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)
