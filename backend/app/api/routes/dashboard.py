"""Dashboard, role breakdown and roadmap endpoints."""

from __future__ import annotations

import datetime as dt
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import ImprovementRoadmap, RoadmapTask
from app.modules.activity import log_activity
from app.modules.auth.dependencies import CurrentUser, DbSession
from app.modules.dashboard import service as dashboard_service
from app.modules.scoring.service import refresh_scores
from app.schemas.common import ActionResult
from app.schemas.dashboard import DashboardOut, RoleAssessmentDetailOut

router = APIRouter(tags=["dashboard"])


class TaskStatusUpdate(BaseModel):
    status: str = Field(pattern="^(pending|in_progress|completed)$")


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(user: CurrentUser, db: DbSession) -> DashboardOut:
    """Everything the dashboard renders, built from this student's rows only."""
    if not user.onboarding_completed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Complete onboarding to see your dashboard.",
        )
    return DashboardOut(**dashboard_service.build_dashboard(db, user))


@router.get("/dashboard/roles/{role_slug}", response_model=RoleAssessmentDetailOut)
def role_breakdown(
    role_slug: str, user: CurrentUser, db: DbSession
) -> RoleAssessmentDetailOut:
    """Component-by-component explanation of one role score."""
    detail = dashboard_service.build_role_detail(db, user, role_slug)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No assessment found for this role yet.",
        )
    return RoleAssessmentDetailOut(**detail)


@router.post("/dashboard/recalculate", response_model=ActionResult)
def recalculate(user: CurrentUser, db: DbSession) -> ActionResult:
    """Force a fresh assessment of every active role."""
    if not user.onboarding_completed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Complete onboarding before running an assessment.",
        )
    result = refresh_scores(db, user, change="manual")
    db.commit()
    return ActionResult(
        message=f"Re-assessed {len(result['recalculated_roles'])} role(s).",
        recalculated_roles=result["recalculated_roles"],
        data={"scored": result["scored"]},
    )


@router.get("/roadmap")
def roadmap(user: CurrentUser, db: DbSession) -> dict[str, Any]:
    from app.modules.scoring.roadmap import roadmap_payload

    return roadmap_payload(db, user)


@router.patch("/roadmap/tasks/{task_id}", response_model=ActionResult)
def update_task(
    task_id: int, payload: TaskStatusUpdate, user: CurrentUser, db: DbSession
) -> ActionResult:
    """Mark a recommendation as pending / in progress / completed."""
    task = db.scalar(
        select(RoadmapTask)
        .join(ImprovementRoadmap, ImprovementRoadmap.id == RoadmapTask.roadmap_id)
        .options(selectinload(RoadmapTask.roadmap))
        .where(RoadmapTask.id == task_id, ImprovementRoadmap.user_id == user.id)
    )
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

    previous = task.status
    task.status = payload.status
    task.completed_at = (
        dt.datetime.now(dt.timezone.utc) if payload.status == "completed" else None
    )

    if payload.status == "completed" and previous != "completed":
        log_activity(
            db,
            user.id,
            "roadmap_task_completed",
            f"Completed: {task.title}",
            task.expected_improvement_area,
            details={"task_id": task.id, "priority": task.priority},
        )

    db.commit()
    return ActionResult(
        message="Roadmap updated.",
        data={"task_id": task.id, "status": task.status},
    )


@router.get("/activity")
def activity(
    user: CurrentUser,
    db: DbSession,
    limit: int = Query(default=30, ge=1, le=100),
) -> dict[str, Any]:
    return {"items": dashboard_service.recent_activity(db, user.id, limit)}
