"""Spaced-repetition scheduling and automatic revision tasks in the planner."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import LearningPlan, LearningSettings, LearningTask, RevisionSchedule, User
from app.modules.learning import events, mastery, scheduler, srs


def settings_for(db: Session, user: User) -> LearningSettings:
    s = db.scalar(select(LearningSettings).where(LearningSettings.user_id == user.id))
    if s is None:
        s = LearningSettings(user_id=user.id)
        db.add(s)
        db.flush()
    return s


def ensure_schedule(db: Session, user: User, topic: str, today: dt.date | None = None) -> RevisionSchedule:
    """Start tracking a topic for revision (first review tomorrow)."""
    today = today or dt.date.today()
    key = mastery.topic_key(topic)
    row = db.scalar(select(RevisionSchedule).where(RevisionSchedule.user_id == user.id, RevisionSchedule.topic_key == key))
    if row is None:
        row = RevisionSchedule(user_id=user.id, topic_key=key, topic=topic[:200], due_date=today + dt.timedelta(days=1))
        db.add(row)
        db.flush()
    return row


def record_review(db: Session, user: User, topic: str, accuracy: float, today: dt.date | None = None) -> RevisionSchedule:
    """Apply an assessment outcome to the topic's SRS state and set the next due date."""
    today = today or dt.date.today()
    row = ensure_schedule(db, user, topic, today)
    scale = settings_for(db, user).interval_scale
    quality = srs.quality_from_accuracy(accuracy)
    new = srs.review(srs.SrsState(row.ease, row.interval_days, row.repetitions, row.lapses), quality, scale)
    row.ease, row.interval_days, row.repetitions, row.lapses = new.ease, new.interval_days, new.repetitions, new.lapses
    row.due_date = srs.due_date(today, new)
    row.last_quality = quality
    row.last_reviewed_at = dt.datetime.now(dt.timezone.utc)
    events.log(db, user.id, "revision_reviewed", "topic", None, topic=topic, quality=quality, next_in_days=new.interval_days)
    return row


def due_reviews(db: Session, user: User, within_days: int = 7, today: dt.date | None = None) -> list[RevisionSchedule]:
    today = today or dt.date.today()
    return list(db.scalars(select(RevisionSchedule).where(RevisionSchedule.user_id == user.id, RevisionSchedule.due_date <= today + dt.timedelta(days=within_days)).order_by(RevisionSchedule.due_date)))


def sync_revision_tasks(db: Session, user: User, plan: LearningPlan, today: dt.date | None = None) -> int:
    """Create planner tasks for topics whose spaced-repetition review is due inside the plan."""
    today = today or dt.date.today()
    goal = plan.goal
    study_dates, _ = scheduler.plan_dates(max(today, plan.start_date), max(1, (plan.end_date - max(today, plan.start_date)).days + 1), goal.study_days, goal.breaks)
    if not study_dates:
        return 0
    existing = {(t.topic, t.date) for t in db.scalars(select(LearningTask).where(LearningTask.plan_id == plan.id, LearningTask.category == "revision", LearningTask.title.like("Spaced revision:%")))}
    created = 0
    for r in due_reviews(db, user, within_days=14, today=today):
        day = next((d for d in study_dates if d >= max(r.due_date, today)), None)
        if day is None or (r.topic, day) in existing:
            continue
        pos = db.scalar(select(LearningTask.position).where(LearningTask.plan_id == plan.id, LearningTask.date == day).order_by(LearningTask.position.desc()).limit(1))
        db.add(LearningTask(plan_id=plan.id, user_id=user.id, date=day, original_date=day, position=(pos or 0) + 1, category="revision", title=f"Spaced revision: {r.topic}", topic=r.topic,
                            subtopics=[], objectives=["Recall the key ideas from memory before opening notes", "Take a short quiz to confirm retention"], assignment=f"Generate a quick revision quiz on {r.topic}", est_minutes=20))
        existing.add((r.topic, day))
        created += 1
    return created
