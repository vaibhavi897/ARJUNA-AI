"""Calendar queries and task updates."""

from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import LearningPlan, LearningTask, User
from app.modules.learning import events, revision

OPEN = ("pending", "rescheduled")
FILTERS = ("all", "pending", "completed", "revision", "assessments", "missed")


def active_plan(db: Session, user: User) -> LearningPlan | None:
    return db.scalar(select(LearningPlan).where(LearningPlan.user_id == user.id, LearningPlan.status == "active").order_by(LearningPlan.id.desc()))


def task_out(t: LearningTask, today: dt.date | None = None) -> dict[str, Any]:
    today = today or dt.date.today()
    return {
        "id": t.id, "plan_id": t.plan_id, "date": t.date.isoformat(), "original_date": t.original_date.isoformat(), "position": t.position,
        "category": t.category, "phase": t.phase, "title": t.title, "topic": t.topic, "subtopics": t.subtopics, "objectives": t.objectives,
        "assignment": t.assignment, "resources": t.resources, "est_minutes": t.est_minutes, "difficulty": t.difficulty, "status": t.status,
        "progress_pct": t.progress_pct, "actual_minutes": t.actual_minutes, "self_difficulty": t.self_difficulty, "notes": t.notes,
        "reschedule_count": t.reschedule_count, "locked": t.locked_by_user, "missed": t.status in OPEN and t.date < today and t.category != "rest",
    }


def _matches(t: LearningTask, flt: str, today: dt.date) -> bool:
    if flt == "all":
        return True
    if flt == "pending":
        return t.status in OPEN and t.category != "rest"
    if flt == "completed":
        return t.status == "completed" and t.category != "rest"
    if flt == "revision":
        return t.category == "revision"
    if flt == "assessments":
        return t.category == "assessment"
    if flt == "missed":
        return t.status in OPEN and t.date < today and t.category != "rest"
    return True


def calendar(db: Session, plan: LearningPlan, start: dt.date, end: dt.date, flt: str = "all") -> dict[str, Any]:
    today = dt.date.today()
    rows = list(db.scalars(select(LearningTask).where(LearningTask.plan_id == plan.id, LearningTask.date >= start, LearningTask.date <= end).order_by(LearningTask.date, LearningTask.position)))
    days: dict[str, dict[str, Any]] = {}
    for t in rows:
        d = days.setdefault(t.date.isoformat(), {"date": t.date.isoformat(), "tasks": [], "minutes": 0, "done": 0, "total": 0, "rest": False, "milestone": None})
        if t.category == "rest":
            d["rest"] = True
        else:
            d["total"] += 1
            d["minutes"] += t.est_minutes
            d["done"] += 1 if t.status == "completed" else 0
        if _matches(t, flt, today):
            d["tasks"].append(task_out(t, today))
    for m in plan.milestones:
        if start <= m.due_date <= end:
            days.setdefault(m.due_date.isoformat(), {"date": m.due_date.isoformat(), "tasks": [], "minutes": 0, "done": 0, "total": 0, "rest": False, "milestone": None})["milestone"] = {"id": m.id, "title": m.title, "week": m.week_no, "completed": m.completed}
    return {"plan_id": plan.id, "start": start.isoformat(), "end": end.isoformat(), "filter": flt, "days": sorted(days.values(), key=lambda d: d["date"])}


def update_task(db: Session, user: User, task: LearningTask, data: dict[str, Any]) -> LearningTask:
    prev = task.status
    if "notes" in data:
        task.notes = data["notes"]
    if data.get("actual_minutes") is not None:
        task.actual_minutes = data["actual_minutes"]
    if data.get("self_difficulty") is not None:
        task.self_difficulty = data["self_difficulty"]
        events.feedback(db, user.id, "difficulty", f"task:{task.id}", {"rating": data["self_difficulty"], "topic": task.topic})
    if "locked" in data:
        task.locked_by_user = bool(data["locked"])
    status = data.get("status")
    if status:
        task.status = status
        if status == "completed":
            task.progress_pct, task.completed_at = 100, dt.datetime.now(dt.timezone.utc)
        elif status == "partial":
            task.progress_pct = int(data.get("progress_pct") or task.progress_pct or 50)
        elif status == "skipped":
            task.progress_pct = 0
        elif status == "pending":
            task.progress_pct, task.completed_at = 0, None
    if data.get("date") and data["date"] != task.date:
        new = data["date"]
        plan = task.plan
        if not (plan.start_date <= new <= plan.end_date):
            raise ValueError("Pick a date inside your plan.")
        task.date = new
        task.status = "rescheduled" if task.status in OPEN else task.status
        task.reschedule_count += 1
        events.log(db, user.id, "task_rescheduled", "task", task.id, to=new.isoformat())
    if status and status != prev:
        events.log(db, user.id, f"task_{status}", "task", task.id, category=task.category, topic=task.topic, minutes=task.actual_minutes or task.est_minutes)
        if status in ("completed", "partial") and task.category in ("learn", "practice", "project") and task.topic:
            revision.ensure_schedule(db, user, task.topic)
            revision.sync_revision_tasks(db, user, task.plan)
    db.flush()
    return task
