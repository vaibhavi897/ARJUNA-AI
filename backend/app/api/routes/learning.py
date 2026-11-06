"""AI Learning Hub API. Every route requires the existing JWT session and is scoped to the caller."""

from __future__ import annotations

import datetime as dt
import functools
import tempfile
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, File, Header, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.routes.careerverse import _rate_limit
from app.core.config import settings
from app.core.logging_config import get_logger
from app.models import GeneratedMaterial, LearningGoal, LearningPlan, LearningTask, LearningTrack, Notebook, NotebookChapter, NotebookPageVersion, QuizSession, YoutubeImport
from app.modules.auth.dependencies import CurrentUser, DbSession
from app.modules.careerverse import gemini_service
from app.modules.learning import ai, analytics, events, materials, notebooks, planner, quizzes, revision, skill_gap, tasks as task_service, youtube

router = APIRouter(prefix="/learning", tags=["learning"])
logger = get_logger(__name__)


def _ai_guard(fn):  # noqa: ANN001, ANN202
    """Translate AI/planning failures into clear HTTP errors."""
    @functools.wraps(fn)
    def wrapper(*a, **kw):  # noqa: ANN002, ANN003
        try:
            return fn(*a, **kw)
        except planner.PlanError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
        except quizzes.QuizError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        except gemini_service.GeminiUnavailable as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="The AI service is busy or not configured. Nothing was lost; please try again shortly.") from exc
    return wrapper


# =============================================================== schemas
class BreakIn(BaseModel):
    start: dt.date
    end: dt.date
    reason: str = ""

    @field_validator("end")
    @classmethod
    def _order(cls, v: dt.date, info) -> dt.date:  # noqa: ANN001
        if "start" in info.data and v < info.data["start"]:
            raise ValueError("Break end must not be before its start.")
        return v


class GoalIn(BaseModel):
    target_role: str = Field(min_length=2, max_length=160)
    track_slug: str | None = None
    duration_days: int = Field(ge=7, le=365)
    daily_hours: float = Field(ge=0.5, le=12)
    study_days: list[int] = Field(min_length=1, max_length=7)
    start_date: dt.date
    existing_knowledge: str | None = Field(default=None, max_length=1500)
    skip_topics: list[str] = Field(default_factory=list, max_length=30)
    focus_areas: list[str] = Field(default_factory=list, max_length=15)
    target_companies: list[str] = Field(default_factory=list, max_length=15)
    breaks: list[BreakIn] = Field(default_factory=list, max_length=12)

    @field_validator("study_days")
    @classmethod
    def _days(cls, v: list[int]) -> list[int]:
        if any(d < 0 or d > 6 for d in v):
            raise ValueError("Study days are 0 (Mon) to 6 (Sun).")
        return sorted(set(v))

    @field_validator("start_date")
    @classmethod
    def _start(cls, v: dt.date) -> dt.date:
        if v < dt.date.today() - dt.timedelta(days=1):
            raise ValueError("Start date cannot be in the past.")
        return v


class TaskPatch(BaseModel):
    status: Literal["pending", "completed", "partial", "skipped"] | None = None
    progress_pct: int | None = Field(default=None, ge=0, le=100)
    actual_minutes: int | None = Field(default=None, ge=0, le=900)
    self_difficulty: int | None = Field(default=None, ge=1, le=5)
    notes: str | None = Field(default=None, max_length=4000)
    date: dt.date | None = None
    locked: bool | None = None


class AvailabilityIn(BaseModel):
    study_days: list[int] | None = Field(default=None, min_length=1, max_length=7)
    daily_hours: float | None = Field(default=None, ge=0.5, le=12)
    breaks: list[BreakIn] | None = None


class MaterialIn(BaseModel):
    topic: str = Field(min_length=2, max_length=200)
    level: Literal["beginner", "intermediate", "advanced"] = "beginner"
    depth: Literal["brief", "standard", "deep"] = "standard"
    task_id: int | None = None
    force: bool = False


class ActionIn(BaseModel):
    action: Literal["simplify", "deeper", "examples", "implementation", "diagram", "regenerate"]


class AskIn(BaseModel):
    question: str = Field(min_length=3, max_length=800)


class YoutubeIn(BaseModel):
    url: str = Field(min_length=5, max_length=300)
    transcript: str | None = Field(default=None, max_length=200_000)


class NotebookIn(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    cover_style: str = "forest"
    description: str | None = Field(default=None, max_length=300)
    folder: str | None = Field(default=None, max_length=80)
    tags: list[str] = Field(default_factory=list, max_length=10)
    password: str | None = Field(default=None, max_length=128)


class NotebookPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    cover_style: str | None = None
    description: str | None = Field(default=None, max_length=300)
    folder: str | None = Field(default=None, max_length=80)
    tags: list[str] | None = Field(default=None, max_length=10)


class PasswordIn(BaseModel):
    password: str = Field(min_length=1, max_length=128)


class LockIn(BaseModel):
    new_password: str | None = Field(default=None, max_length=128)
    current_password: str | None = Field(default=None, max_length=128)


class ChapterIn(BaseModel):
    title: str = Field(min_length=1, max_length=160)


class PageIn(BaseModel):
    title: str = Field(default="Untitled page", max_length=200)
    content: str = Field(default="", max_length=200_000)
    chapter_id: int | None = None
    tags: list[str] = Field(default_factory=list, max_length=15)
    task_id: int | None = None


class PagePatch(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    content: str | None = Field(default=None, max_length=200_000)
    chapter_id: int | None = None
    tags: list[str] | None = Field(default=None, max_length=15)
    bookmarked: bool | None = None
    task_id: int | None = None
    snapshot: bool = False


class QuizIn(BaseModel):
    topic: str = Field(default="", max_length=200)
    scope: Literal["topic", "subject", "week", "roadmap", "revision"] = "topic"
    count: int = Field(default=10, ge=3, le=30)
    difficulty: Literal["easy", "medium", "hard", "mixed"] = "mixed"
    time_limit_minutes: int | None = Field(default=None, ge=1, le=240)
    types: list[str] = Field(default_factory=lambda: list(quizzes.DEFAULT_TYPES))
    week: int | None = Field(default=None, ge=1, le=60)
    level: Literal["beginner", "intermediate", "advanced"] = "intermediate"

    @field_validator("topic")
    @classmethod
    def _topic(cls, v: str) -> str:
        return v.strip()


class SubmitIn(BaseModel):
    answers: dict[int, dict[str, Any]] = Field(default_factory=dict)


class SettingsIn(BaseModel):
    interval_scale: float | None = Field(default=None, ge=0.5, le=2.0)
    preferred_depth: Literal["brief", "standard", "deep"] | None = None


class FeedbackIn(BaseModel):
    kind: Literal["satisfaction", "recommendation", "difficulty"]
    ref: str | None = Field(default=None, max_length=120)
    value: dict[str, Any] = Field(default_factory=dict)


# =============================================================== helpers
def _plan(db, user, plan_id: int) -> LearningPlan:  # noqa: ANN001
    p = db.scalar(select(LearningPlan).options(selectinload(LearningPlan.milestones), selectinload(LearningPlan.goal)).where(LearningPlan.id == plan_id, LearningPlan.user_id == user.id))
    if p is None:
        raise HTTPException(status_code=404, detail="Plan not found.")
    return p


def _task(db, user, task_id: int) -> LearningTask:  # noqa: ANN001
    t = db.scalar(select(LearningTask).where(LearningTask.id == task_id, LearningTask.user_id == user.id))
    if t is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    return t


def _plan_out(p: LearningPlan) -> dict[str, Any]:
    g = p.goal
    return {"id": p.id, "version": p.version, "status": p.status, "summary": p.summary, "starting_level": p.starting_level, "skill_gap": p.skill_gap, "phases": p.phases, "start_date": p.start_date.isoformat(), "end_date": p.end_date.isoformat(),
            "goal": {"id": g.id, "target_role": g.target_role, "duration_days": g.duration_days, "daily_hours": g.daily_hours, "study_days": g.study_days, "breaks": g.breaks, "focus_areas": g.focus_areas, "target_companies": g.target_companies, "skip_topics": g.skip_topics, "existing_knowledge": g.existing_knowledge},
            "milestones": [{"id": m.id, "week": m.week_no, "title": m.title, "description": m.description, "phase": m.phase, "due": m.due_date.isoformat(), "completed": m.completed} for m in p.milestones], "model": p.model}


def _nb(db, user, nid: int, token: str | None, need_unlock: bool = True) -> Notebook:  # noqa: ANN001
    try:
        nb = notebooks.get_notebook(db, user, nid)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Notebook not found.") from exc
    if need_unlock:
        try:
            notebooks.check_access(user, nb, token)
        except notebooks.LockedError as exc:
            raise HTTPException(status_code=423, detail=str(exc)) from exc
    return nb


# =============================================================== overview, progress, tracks
@router.get("/overview")
def overview(user: CurrentUser, db: DbSession) -> dict[str, Any]:
    return analytics.overview(db, user)


@router.get("/progress")
def progress(user: CurrentUser, db: DbSession) -> dict[str, Any]:
    return analytics.progress(db, user)


@router.get("/personalization")
def personalization(user: CurrentUser, db: DbSession) -> dict[str, Any]:
    return analytics.personalization_status(db, user)


@router.get("/tracks")
def tracks(user: CurrentUser, db: DbSession) -> dict[str, Any]:
    rows = db.scalars(select(LearningTrack).options(selectinload(LearningTrack.topics)).order_by(LearningTrack.category, LearningTrack.title))
    return {"items": [{"slug": t.slug, "title": t.title, "category": t.category, "description": t.description, "topics": len(t.topics), "hours": round(sum(x.est_hours for x in t.topics))} for t in rows]}


@router.get("/skill-gap")
@_ai_guard
def skill_gap_view(user: CurrentUser, db: DbSession, track: str = Query(max_length=80), role: str = Query(default="", max_length=160)) -> dict[str, Any]:
    t = db.scalar(select(LearningTrack).options(selectinload(LearningTrack.topics)).where(LearningTrack.slug == track))
    if t is None:
        raise HTTPException(status_code=404, detail="Track not found.")
    analysis = skill_gap.analyse(db, user, t)
    explanation = skill_gap.explain(db, role or t.title, analysis)
    db.commit()
    return {**{k: analysis[k] for k in ("starting_level", "coverage", "matched_titles", "missing_titles", "profile_has_data", "method")}, "explanation": explanation}


# =============================================================== planner
@router.post("/plans", status_code=201)
@_ai_guard
def create_plan(body: GoalIn, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    """Create a goal and generate the full calendar. Nothing is saved unless generation fully succeeds."""
    _rate_limit(user.id, "plan", limit=4, per_seconds=600)
    goal = planner.create_goal(db, user, {**body.model_dump(mode="python"), "breaks": [{"start": b.start.isoformat(), "end": b.end.isoformat(), "reason": b.reason} for b in body.breaks]})
    try:
        plan = planner.generate_plan(db, user, goal)
    except Exception:
        db.rollback()
        raise
    return _plan_out(_plan(db, user, plan.id))


@router.get("/plans")
def list_plans(user: CurrentUser, db: DbSession) -> dict[str, Any]:
    rows = db.scalars(select(LearningPlan).options(selectinload(LearningPlan.goal), selectinload(LearningPlan.milestones)).where(LearningPlan.user_id == user.id).order_by(LearningPlan.id.desc()))
    return {"items": [{"id": p.id, "status": p.status, "role": p.goal.target_role, "start": p.start_date.isoformat(), "end": p.end_date.isoformat(), "version": p.version} for p in rows]}


@router.get("/plans/active")
def active(user: CurrentUser, db: DbSession) -> dict[str, Any]:
    p = task_service.active_plan(db, user)
    return {"plan": _plan_out(_plan(db, user, p.id)) if p else None}


@router.get("/plans/{plan_id}")
def get_plan(plan_id: int, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    return _plan_out(_plan(db, user, plan_id))


@router.post("/plans/{plan_id}/archive")
def archive_plan(plan_id: int, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    p = _plan(db, user, plan_id)
    p.status = "archived"
    db.commit()
    return {"id": p.id, "status": p.status}


@router.get("/plans/{plan_id}/calendar")
def calendar(plan_id: int, user: CurrentUser, db: DbSession, start: dt.date | None = None, end: dt.date | None = None, filter: str = Query(default="all", pattern="^(all|pending|completed|revision|assessments|missed)$")) -> dict[str, Any]:  # noqa: A002
    p = _plan(db, user, plan_id)
    s, e = start or p.start_date, end or p.end_date
    if (e - s).days > 400:
        raise HTTPException(status_code=422, detail="Choose a range of at most 400 days.")
    return task_service.calendar(db, p, s, e, filter)


@router.post("/plans/{plan_id}/regenerate")
@_ai_guard
def regenerate(plan_id: int, user: CurrentUser, db: DbSession, daily_minutes: int | None = Query(default=None, ge=20, le=720)) -> dict[str, Any]:
    _rate_limit(user.id, "plan", limit=4, per_seconds=600)
    p = _plan(db, user, plan_id)
    try:
        res = planner.regenerate_future(db, user, p, daily_minutes=daily_minutes, reason="manual")
    except planner.PlanError:
        db.rollback()
        raise
    return {**res, "plan": _plan_out(_plan(db, user, plan_id))}


@router.put("/plans/{plan_id}/availability")
@_ai_guard
def availability(plan_id: int, body: AvailabilityIn, user: CurrentUser, db: DbSession, regenerate_future: bool = True) -> dict[str, Any]:
    """Change study days, daily hours or breaks. Completed work is never touched."""
    p = _plan(db, user, plan_id)
    g = p.goal
    if body.study_days is not None:
        if any(d < 0 or d > 6 for d in body.study_days):
            raise HTTPException(status_code=422, detail="Study days are 0 (Mon) to 6 (Sun).")
        g.study_days = sorted(set(body.study_days))
    if body.daily_hours is not None:
        g.daily_hours = body.daily_hours
    if body.breaks is not None:
        g.breaks = [{"start": b.start.isoformat(), "end": b.end.isoformat(), "reason": b.reason} for b in body.breaks]
    db.flush()
    result: dict[str, Any] = {"saved": True}
    if regenerate_future:
        _rate_limit(user.id, "plan", limit=4, per_seconds=600)
        try:
            result.update(planner.regenerate_future(db, user, p, reason="availability changed"))
        except planner.PlanError:
            db.rollback()
            raise
    else:
        db.commit()
    return {**result, "plan": _plan_out(_plan(db, user, plan_id))}


@router.get("/plans/{plan_id}/adjustments")
def adjustments(plan_id: int, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    return planner.adaptive_adjustments(db, _plan(db, user, plan_id))


@router.get("/plans/{plan_id}/missed")
def missed(plan_id: int, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    """Preview only: nothing changes until the learner confirms."""
    return planner.missed_preview(db, _plan(db, user, plan_id))


class ConfirmIn(BaseModel):
    confirm: bool = False


@router.post("/plans/{plan_id}/missed/apply")
def missed_apply(plan_id: int, body: ConfirmIn, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    p = _plan(db, user, plan_id)
    preview = planner.missed_preview(db, p)
    if preview["significant"] and not body.confirm:
        raise HTTPException(status_code=409, detail="This is a significant change. Review the preview and confirm.")
    return planner.missed_apply(db, user, p)


@router.get("/tasks/{task_id}")
def get_task(task_id: int, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    return task_service.task_out(_task(db, user, task_id))


@router.patch("/tasks/{task_id}")
def patch_task(task_id: int, body: TaskPatch, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    t = _task(db, user, task_id)
    if t.category == "rest":
        raise HTTPException(status_code=422, detail="Rest days cannot be edited.")
    try:
        task_service.update_task(db, user, t, body.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    return task_service.task_out(t)


# =============================================================== materials
@router.get("/materials")
def list_materials(user: CurrentUser, db: DbSession, q: str | None = Query(default=None, max_length=100)) -> dict[str, Any]:
    stmt = select(GeneratedMaterial).where(GeneratedMaterial.user_id == user.id).order_by(GeneratedMaterial.id.desc()).limit(60)
    if q:
        stmt = stmt.where(GeneratedMaterial.topic.ilike(f"%{q}%"))
    return {"items": [{"id": m.id, "topic": m.topic, "level": m.level, "depth": m.depth, "kind": m.kind, "created_at": m.created_at.isoformat() if m.created_at else None} for m in db.scalars(stmt)]}


@router.post("/materials", status_code=201)
@_ai_guard
def create_material(body: MaterialIn, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    _rate_limit(user.id, "material", limit=15)
    m = materials.generate(db, user, body.topic.strip(), body.level, body.depth, body.task_id, body.force)
    db.commit()
    return materials.out(m)


def _material(db, user, mid: int) -> GeneratedMaterial:  # noqa: ANN001
    m = db.scalar(select(GeneratedMaterial).where(GeneratedMaterial.id == mid, GeneratedMaterial.user_id == user.id))
    if m is None:
        raise HTTPException(status_code=404, detail="Material not found.")
    return m


@router.get("/materials/{material_id}")
def get_material(material_id: int, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    return materials.out(_material(db, user, material_id))


@router.post("/materials/{material_id}/action", status_code=201)
@_ai_guard
def material_action(material_id: int, body: ActionIn, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    _rate_limit(user.id, "material", limit=15)
    m = materials.transform(db, user, _material(db, user, material_id), body.action)
    db.commit()
    return materials.out(m)


@router.post("/materials/{material_id}/ask")
@_ai_guard
def material_ask(material_id: int, body: AskIn, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    _rate_limit(user.id, "material", limit=15)
    entry = materials.ask(db, user, _material(db, user, material_id), body.question)
    db.commit()
    return entry


@router.delete("/materials/{material_id}", status_code=204)
def delete_material(material_id: int, user: CurrentUser, db: DbSession) -> None:
    db.delete(_material(db, user, material_id))
    db.commit()


# =============================================================== YouTube
def _yt_out(y: YoutubeImport) -> dict[str, Any]:
    return {"id": y.id, "video_id": y.video_id, "url": y.url, "title": y.title, "channel": y.channel, "thumbnail": y.thumbnail, "transcript_status": y.transcript_status, "segments": len(y.transcript), "summary": y.summary or None, "created_at": y.created_at.isoformat() if y.created_at else None}


@router.get("/youtube")
def yt_list(user: CurrentUser, db: DbSession) -> dict[str, Any]:
    return {"items": [_yt_out(y) for y in db.scalars(select(YoutubeImport).where(YoutubeImport.user_id == user.id).order_by(YoutubeImport.id.desc()).limit(40))]}


@router.post("/youtube", status_code=201)
@_ai_guard
def yt_import(body: YoutubeIn, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    """Fetch metadata and captions, then summarise. If captions are unavailable, the import is saved so a transcript can be pasted."""
    _rate_limit(user.id, "youtube", limit=8)
    vid = youtube.parse_video_id(body.url)
    if not vid:
        raise HTTPException(status_code=422, detail="That does not look like a YouTube link.")
    meta = youtube.fetch_metadata(vid)
    reason = None
    if body.transcript and body.transcript.strip():
        segs, st = youtube.parse_pasted(body.transcript), "pasted"
    else:
        st, segs, reason = youtube.fetch_transcript(vid)
    y = YoutubeImport(user_id=user.id, video_id=vid, url=f"https://www.youtube.com/watch?v={vid}", transcript_status=st, transcript=segs, **meta)
    db.add(y)
    db.flush()
    if segs:
        y.summary = ai.summarise_video(y.title or "", youtube.to_prompt_text(segs))
        y.model = settings.GEMINI_MODEL
        events.log(db, user.id, "youtube_summarised", "youtube", y.id)
    db.commit()
    return {**_yt_out(y), "reason": reason, "needs_transcript": not segs}


@router.post("/youtube/{import_id}/summarise")
@_ai_guard
def yt_summarise(import_id: int, user: CurrentUser, db: DbSession, body: YoutubeIn | None = None) -> dict[str, Any]:
    _rate_limit(user.id, "youtube", limit=8)
    y = db.scalar(select(YoutubeImport).where(YoutubeImport.id == import_id, YoutubeImport.user_id == user.id))
    if y is None:
        raise HTTPException(status_code=404, detail="Import not found.")
    if body and body.transcript and body.transcript.strip():
        y.transcript, y.transcript_status = youtube.parse_pasted(body.transcript), "pasted"
    if not y.transcript:
        raise HTTPException(status_code=422, detail="Paste a transcript to summarise this video.")
    y.summary = ai.summarise_video(y.title or "", youtube.to_prompt_text(y.transcript))
    y.model = settings.GEMINI_MODEL
    db.commit()
    return _yt_out(y)


@router.get("/youtube/{import_id}")
def yt_get(import_id: int, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    y = db.scalar(select(YoutubeImport).where(YoutubeImport.id == import_id, YoutubeImport.user_id == user.id))
    if y is None:
        raise HTTPException(status_code=404, detail="Import not found.")
    return _yt_out(y)


# =============================================================== notebooks
@router.get("/notebooks")
def nb_list(user: CurrentUser, db: DbSession) -> dict[str, Any]:
    rows = db.scalars(select(Notebook).where(Notebook.user_id == user.id).order_by(Notebook.updated_at.desc()))
    return {"items": [notebooks.notebook_out(db, n) for n in rows], "covers": list(notebooks.COVERS)}


@router.post("/notebooks", status_code=201)
def nb_create(body: NotebookIn, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    try:
        nb = notebooks.create_notebook(db, user, body.title, body.cover_style, body.description, body.folder, body.tags, body.password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    return notebooks.notebook_out(db, nb)


@router.patch("/notebooks/{nid}")
def nb_patch(nid: int, body: NotebookPatch, user: CurrentUser, db: DbSession, x_notebook_token: str | None = Header(default=None)) -> dict[str, Any]:
    nb = _nb(db, user, nid, x_notebook_token)
    for k, v in body.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(nb, k, v if k != "cover_style" or v in notebooks.COVERS else nb.cover_style)
    db.commit()
    return notebooks.notebook_out(db, nb)


@router.delete("/notebooks/{nid}", status_code=204)
def nb_delete(nid: int, user: CurrentUser, db: DbSession, x_notebook_token: str | None = Header(default=None)) -> None:
    db.delete(_nb(db, user, nid, x_notebook_token))
    db.commit()


@router.post("/notebooks/{nid}/unlock")
def nb_unlock(nid: int, body: PasswordIn, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    nb = _nb(db, user, nid, None, need_unlock=False)
    try:
        return notebooks.unlock(user, nb, body.password)
    except notebooks.LockedError as exc:
        raise HTTPException(status_code=403 if "Incorrect" in str(exc) else 429, detail=str(exc)) from exc


@router.put("/notebooks/{nid}/lock")
def nb_lock(nid: int, body: LockIn, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    nb = _nb(db, user, nid, None, need_unlock=False)
    try:
        notebooks.set_lock(user, nb, body.new_password, body.current_password)
    except notebooks.LockedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    return notebooks.notebook_out(db, nb)


@router.get("/notebooks/{nid}/index")
def nb_index(nid: int, user: CurrentUser, db: DbSession, x_notebook_token: str | None = Header(default=None)) -> dict[str, Any]:
    return notebooks.index(db, _nb(db, user, nid, x_notebook_token))


@router.post("/notebooks/{nid}/chapters", status_code=201)
def ch_create(nid: int, body: ChapterIn, user: CurrentUser, db: DbSession, x_notebook_token: str | None = Header(default=None)) -> dict[str, Any]:
    nb = _nb(db, user, nid, x_notebook_token)
    pos = len(nb.chapters)
    c = NotebookChapter(notebook_id=nb.id, title=body.title.strip(), position=pos)
    db.add(c)
    db.commit()
    return {"id": c.id, "title": c.title, "position": c.position}


@router.patch("/notebooks/{nid}/chapters/{cid}")
def ch_rename(nid: int, cid: int, body: ChapterIn, user: CurrentUser, db: DbSession, x_notebook_token: str | None = Header(default=None)) -> dict[str, Any]:
    nb = _nb(db, user, nid, x_notebook_token)
    c = db.scalar(select(NotebookChapter).where(NotebookChapter.id == cid, NotebookChapter.notebook_id == nb.id))
    if c is None:
        raise HTTPException(status_code=404, detail="Chapter not found.")
    c.title = body.title.strip()
    db.commit()
    return {"id": c.id, "title": c.title}


@router.delete("/notebooks/{nid}/chapters/{cid}", status_code=204)
def ch_delete(nid: int, cid: int, user: CurrentUser, db: DbSession, x_notebook_token: str | None = Header(default=None)) -> None:
    nb = _nb(db, user, nid, x_notebook_token)
    c = db.scalar(select(NotebookChapter).where(NotebookChapter.id == cid, NotebookChapter.notebook_id == nb.id))
    if c:
        db.delete(c)
        db.commit()


@router.post("/notebooks/{nid}/pages", status_code=201)
def pg_create(nid: int, body: PageIn, user: CurrentUser, db: DbSession, x_notebook_token: str | None = Header(default=None)) -> dict[str, Any]:
    nb = _nb(db, user, nid, x_notebook_token)
    p = notebooks.add_page(db, nb, body.title, body.content, body.chapter_id, task_id=body.task_id, tags=body.tags)
    db.commit()
    return notebooks.page_out(p)


@router.get("/notebooks/{nid}/search")
def pg_search(nid: int, user: CurrentUser, db: DbSession, q: str = Query(min_length=1, max_length=100), x_notebook_token: str | None = Header(default=None)) -> dict[str, Any]:
    return {"items": notebooks.search(db, _nb(db, user, nid, x_notebook_token), q)}


@router.get("/notebooks/{nid}/pages/{page_no}")
def pg_get(nid: int, page_no: int, user: CurrentUser, db: DbSession, x_notebook_token: str | None = Header(default=None)) -> dict[str, Any]:
    nb = _nb(db, user, nid, x_notebook_token)
    try:
        return notebooks.page_out(notebooks.get_page(db, nb, page_no))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Page not found.") from exc


@router.patch("/notebooks/{nid}/pages/{page_no}")
def pg_patch(nid: int, page_no: int, body: PagePatch, user: CurrentUser, db: DbSession, x_notebook_token: str | None = Header(default=None)) -> dict[str, Any]:
    nb = _nb(db, user, nid, x_notebook_token)
    try:
        p = notebooks.get_page(db, nb, page_no)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Page not found.") from exc
    notebooks.update_page(db, p, body.model_dump(exclude_unset=True, exclude={"snapshot"}), snapshot=body.snapshot)
    nb.updated_at = dt.datetime.now(dt.timezone.utc)
    db.commit()
    return notebooks.page_out(p)


@router.delete("/notebooks/{nid}/pages/{page_no}", status_code=204)
def pg_delete(nid: int, page_no: int, user: CurrentUser, db: DbSession, x_notebook_token: str | None = Header(default=None)) -> None:
    nb = _nb(db, user, nid, x_notebook_token)
    try:
        p = notebooks.get_page(db, nb, page_no)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Page not found.") from exc
    if len(nb.pages) <= 1:
        raise HTTPException(status_code=422, detail="A notebook needs at least one page.")
    notebooks.delete_page(db, p)
    db.commit()


@router.get("/notebooks/{nid}/pages/{page_no}/history")
def pg_history(nid: int, page_no: int, user: CurrentUser, db: DbSession, x_notebook_token: str | None = Header(default=None)) -> dict[str, Any]:
    nb = _nb(db, user, nid, x_notebook_token)
    try:
        p = notebooks.get_page(db, nb, page_no)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Page not found.") from exc
    vs = db.scalars(select(NotebookPageVersion).where(NotebookPageVersion.page_id == p.id).order_by(NotebookPageVersion.id.desc()).limit(30))
    return {"items": [{"id": v.id, "title": v.title, "content": v.content, "saved_at": v.saved_at.isoformat()} for v in vs]}


@router.post("/notebooks/{nid}/pages/{page_no}/restore/{version_id}")
def pg_restore(nid: int, page_no: int, version_id: int, user: CurrentUser, db: DbSession, x_notebook_token: str | None = Header(default=None)) -> dict[str, Any]:
    nb = _nb(db, user, nid, x_notebook_token)
    try:
        p = notebooks.get_page(db, nb, page_no)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Page not found.") from exc
    v = db.scalar(select(NotebookPageVersion).where(NotebookPageVersion.id == version_id, NotebookPageVersion.page_id == p.id))
    if v is None:
        raise HTTPException(status_code=404, detail="Version not found.")
    notebooks.update_page(db, p, {"title": v.title, "content": v.content}, snapshot=True)
    db.commit()
    return notebooks.page_out(p)


class SaveIn(BaseModel):
    chapter_id: int | None = None
    task_id: int | None = None


@router.post("/notebooks/{nid}/save-material/{material_id}", status_code=201)
def nb_save_material(nid: int, material_id: int, body: SaveIn, user: CurrentUser, db: DbSession, x_notebook_token: str | None = Header(default=None)) -> dict[str, Any]:
    nb = _nb(db, user, nid, x_notebook_token)
    m = _material(db, user, material_id)
    if m.kind != "notes":
        raise HTTPException(status_code=422, detail="Only written notes can be saved to a notebook.")
    p = notebooks.add_page(db, nb, m.content.get("title", m.topic), notebooks.material_to_markdown(m.content), body.chapter_id, "gemini", m.id, body.task_id, tags=[m.level])
    db.commit()
    return notebooks.page_out(p)


@router.post("/notebooks/{nid}/save-video/{import_id}", status_code=201)
def nb_save_video(nid: int, import_id: int, body: SaveIn, user: CurrentUser, db: DbSession, x_notebook_token: str | None = Header(default=None)) -> dict[str, Any]:
    nb = _nb(db, user, nid, x_notebook_token)
    y = db.scalar(select(YoutubeImport).where(YoutubeImport.id == import_id, YoutubeImport.user_id == user.id))
    if y is None or not y.summary:
        raise HTTPException(status_code=404, detail="No summary to save.")
    p = notebooks.add_page(db, nb, y.title or "Video notes", notebooks.video_to_markdown(y.title, y.url, y.summary), body.chapter_id, "youtube", y.id, body.task_id, tags=["video"])
    db.commit()
    return notebooks.page_out(p)


@router.post("/notebooks/{nid}/upload", status_code=201)
async def nb_upload(nid: int, user: CurrentUser, db: DbSession, file: UploadFile = File(...), x_notebook_token: str | None = Header(default=None)) -> dict[str, Any]:
    nb = _nb(db, user, nid, x_notebook_token)
    ext = Path(file.filename or "").suffix.lower()
    if ext not in (".pdf", ".docx", ".txt"):
        raise HTTPException(status_code=422, detail="Only PDF, DOCX and TXT files are supported.")
    data = await file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail=f"File is larger than {settings.MAX_UPLOAD_SIZE_MB} MB.")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"upload{ext}"
        path.write_bytes(data)
        path = path.rename(Path(tmp) / (Path(file.filename or "upload").stem[:60] + ext))
        try:
            parts = notebooks.pages_from_upload(path, ext)
        except Exception as exc:  # noqa: BLE001 - extraction errors are user-facing
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    created = [notebooks.add_page(db, nb, title, text, None, "upload") for title, text in parts]
    db.commit()
    return {"pages": [notebooks.page_out(p) for p in created]}


# =============================================================== quizzes
@router.post("/quizzes", status_code=201)
@_ai_guard
def quiz_create(body: QuizIn, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    _rate_limit(user.id, "quiz", limit=8)
    if body.scope in ("topic", "subject") and len(body.topic) < 2:
        raise HTTPException(status_code=422, detail="Enter a topic or subject.")
    plan = task_service.active_plan(db, user)
    s = quizzes.generate(db, user, topic=body.topic, scope=body.scope, count=body.count, difficulty=body.difficulty, time_limit=body.time_limit_minutes, types=body.types, plan=plan, week=body.week, level=body.level)
    return quizzes.session_out(s)


@router.get("/quizzes")
def quiz_list(user: CurrentUser, db: DbSession) -> dict[str, Any]:
    rows = db.scalars(select(QuizSession).where(QuizSession.user_id == user.id).order_by(QuizSession.id.desc()).limit(40))
    return {"items": [{"id": s.id, "topic": s.topic, "scope": s.scope, "status": s.status, "accuracy": s.report.get("accuracy") if s.report else None, "score": s.score, "max_score": s.max_score, "questions": s.config.get("count"), "started_at": s.started_at.isoformat() if s.started_at else None} for s in rows]}


def _quiz(db, user, qid: int) -> QuizSession:  # noqa: ANN001
    try:
        return quizzes.load(db, user, qid)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Quiz not found.") from exc


@router.get("/quizzes/{quiz_id}")
def quiz_get(quiz_id: int, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    s = _quiz(db, user, quiz_id)
    return quizzes.session_out(s, reveal=s.status == "submitted")


@router.post("/quizzes/{quiz_id}/submit")
@_ai_guard
def quiz_submit(quiz_id: int, body: SubmitIn, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    s = _quiz(db, user, quiz_id)
    return quizzes.submit(db, user, s, body.answers)


@router.get("/quizzes/{quiz_id}/results")
def quiz_results(quiz_id: int, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    s = _quiz(db, user, quiz_id)
    if s.status != "submitted":
        raise HTTPException(status_code=409, detail="Submit the quiz to see results.")
    return {"report": s.report, "quiz": quizzes.session_out(s, reveal=True)}


@router.post("/quizzes/{quiz_id}/retry", status_code=201)
@_ai_guard
def quiz_retry(quiz_id: int, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    """New questions on the same topic and settings: never the same fixed set."""
    _rate_limit(user.id, "quiz", limit=8)
    old = _quiz(db, user, quiz_id)
    c = old.config
    plan = db.get(LearningPlan, old.plan_id) if old.plan_id else None
    s = quizzes.generate(db, user, topic=c.get("requested_topic") or old.topic, scope=old.scope, count=c.get("count", 10), difficulty=c.get("difficulty", "mixed"), time_limit=old.time_limit_minutes, types=c.get("types") or quizzes.DEFAULT_TYPES, plan=plan, week=c.get("week"), level=c.get("level", "intermediate"), retry_of=old)
    return quizzes.session_out(s)


# =============================================================== revision, settings, feedback
@router.get("/revisions")
def revisions(user: CurrentUser, db: DbSession) -> dict[str, Any]:
    return {"items": [{"topic": r.topic, "due": r.due_date.isoformat(), "interval_days": r.interval_days, "ease": round(r.ease, 2), "repetitions": r.repetitions, "lapses": r.lapses, "overdue": r.due_date < dt.date.today()} for r in revision.due_reviews(db, user, within_days=30)]}


@router.get("/settings")
def get_settings(user: CurrentUser, db: DbSession) -> dict[str, Any]:
    s = revision.settings_for(db, user)
    db.commit()
    return {"interval_scale": s.interval_scale, "preferred_depth": s.preferred_depth}


@router.put("/settings")
def put_settings(body: SettingsIn, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    s = revision.settings_for(db, user)
    for k, v in body.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(s, k, v)
    db.commit()
    return {"interval_scale": s.interval_scale, "preferred_depth": s.preferred_depth}


@router.post("/feedback", status_code=201)
def feedback(body: FeedbackIn, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    events.feedback(db, user.id, body.kind, body.ref, body.value)
    db.commit()
    return {"ok": True}
