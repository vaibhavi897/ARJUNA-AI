"""Activity-log helper shared by every module."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import StudentActivityLog

_ICONS = {
    "account_created": "sparkles",
    "login": "login",
    "logout": "logout",
    "onboarding_step_completed": "steps",
    "onboarding_completed": "flag",
    "profile_updated": "user",
    "academics_updated": "graduation",
    "skill_added": "zap",
    "skill_removed": "minus",
    "project_added": "folder",
    "project_updated": "folder",
    "project_removed": "minus",
    "experience_added": "briefcase",
    "experience_removed": "minus",
    "certification_added": "badge",
    "achievement_added": "trophy",
    "resume_uploaded": "file",
    "resume_reviewed": "check",
    "preferences_updated": "target",
    "assessment_completed": "gauge",
    "roadmap_generated": "map",
    "roadmap_task_completed": "check",
    "password_changed": "lock",
    "settings_updated": "settings",
}


def log_activity(
    db: Session,
    user_id: int,
    activity_type: str,
    title: str,
    description: str | None = None,
    details: dict[str, Any] | None = None,
) -> StudentActivityLog:
    """Append one row to the student's activity feed. Caller commits."""
    entry = StudentActivityLog(
        user_id=user_id,
        activity_type=activity_type,
        title=title,
        description=description,
        icon=_ICONS.get(activity_type, "dot"),
        details=details or {},
    )
    db.add(entry)
    return entry
