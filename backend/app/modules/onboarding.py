"""Onboarding wizard state.

Step completion is derived from stored data rather than a counter, so a student
can leave at any point, return later and resume exactly where they stopped -
even if they jumped between steps.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    AcademicDetail,
    Achievement,
    Certification,
    Experience,
    Project,
    Resume,
    StudentCareerPreference,
    StudentProfile,
    StudentSkill,
    User,
)

TOTAL_STEPS = 7


@dataclass(frozen=True, slots=True)
class StepDefinition:
    step: int
    key: str
    title: str
    subtitle: str
    optional: bool
    companion_message: str
    companion_done: str


STEPS: tuple[StepDefinition, ...] = (
    StepDefinition(
        1,
        "personal",
        "Personal Information",
        "The basics placement teams always ask for",
        False,
        "Let's get to know you first! These details decide which cohort and roles you are compared against.",
        "Great - your identity is set. Now let's look at your academics.",
    ),
    StepDefinition(
        2,
        "academics",
        "Academic Background",
        "Your education history and coursework",
        False,
        "Your academic record sets the baseline. Some roles screen on CGPA, others care more about relevant coursework.",
        "Academics captured. Next: what you can actually do.",
    ),
    StepDefinition(
        3,
        "skills",
        "Skills & Technical Knowledge",
        "Add any skill - technical, finance or business",
        False,
        "Tell me what you're good at. Every skill counts, and you can add your own if it is not in the list.",
        "Good list. I will check which of these your projects actually prove.",
    ),
    StepDefinition(
        4,
        "projects",
        "Projects",
        "Where your skills become evidence",
        False,
        "Your projects demonstrate how you apply your knowledge. A skill used in a project scores far higher than one that is only listed.",
        "Strong - projects are the highest-signal part of a student profile.",
    ),
    StepDefinition(
        5,
        "experience",
        "Experience & Achievements",
        "Internships, responsibilities, certifications, wins",
        False,
        "Internships, positions of responsibility and certifications all feed different parts of your readiness score.",
        "Noted. That rounds out your practical track record.",
    ),
    StepDefinition(
        6,
        "resume",
        "Resume Upload",
        "PDF or DOCX - reviewed by you before anything is imported",
        True,
        "Let's analyse your professional profile. I will read your resume and show you what I found - you decide what gets imported.",
        "Resume analysed. Nothing was changed without your confirmation.",
    ),
    StepDefinition(
        7,
        "preferences",
        "Portfolio & Career Preferences",
        "Pick the roles you want to be measured against",
        False,
        "Which career path would you like to explore? Pick as many roles as you like - I will score each one separately.",
        "All set. Generating your role-wise readiness scores now.",
    ),
)

STEP_BY_KEY = {definition.key: definition for definition in STEPS}
STEP_BY_NUMBER = {definition.step: definition for definition in STEPS}
REQUIRED_STEPS = tuple(d.step for d in STEPS if not d.optional)


def _count(db: Session, model: type, user_id: int) -> int:
    return int(
        db.scalar(select(func.count()).select_from(model).where(model.user_id == user_id)) or 0
    )


def completed_steps(db: Session, user: User) -> dict[int, bool]:
    """Which steps currently hold enough data to count as done."""
    profile = db.scalar(select(StudentProfile).where(StudentProfile.user_id == user.id))

    step1 = bool(
        profile
        and profile.college
        and profile.degree
        and profile.branch
        and profile.graduation_year
    )
    step2 = _count(db, AcademicDetail, user.id) > 0
    step3 = _count(db, StudentSkill, user.id) > 0
    step4 = _count(db, Project, user.id) > 0
    step5 = (
        _count(db, Experience, user.id)
        + _count(db, Certification, user.id)
        + _count(db, Achievement, user.id)
    ) > 0
    step6 = (
        db.scalar(
            select(Resume.id).where(Resume.user_id == user.id, Resume.is_active.is_(True))
        )
        is not None
    )
    step7 = _count(db, StudentCareerPreference, user.id) > 0

    return {1: step1, 2: step2, 3: step3, 4: step4, 5: step5, 6: step6, 7: step7}


def first_incomplete_step(flags: dict[int, bool]) -> int:
    for definition in STEPS:
        if definition.optional:
            continue
        if not flags.get(definition.step):
            return definition.step
    # All required steps done: land on the last step for review.
    return TOTAL_STEPS


def all_required_complete(flags: dict[int, bool]) -> bool:
    return all(flags.get(step) for step in REQUIRED_STEPS)


def sync_onboarding_state(db: Session, user: User) -> dict[int, bool]:
    """Keep ``users.onboarding_step`` in step with the derived flags."""
    flags = completed_steps(db, user)
    highest = 0
    for definition in STEPS:
        if flags.get(definition.step):
            highest = max(highest, definition.step)
    user.onboarding_step = highest
    if all_required_complete(flags):
        user.onboarding_completed = True
    return flags


def build_status(db: Session, user: User) -> dict:
    flags = completed_steps(db, user)
    profile = db.scalar(select(StudentProfile).where(StudentProfile.user_id == user.id))
    required_done = sum(1 for step in REQUIRED_STEPS if flags.get(step))
    completed = all_required_complete(flags)
    next_step = first_incomplete_step(flags)

    return {
        "current_step": next_step,
        "total_steps": TOTAL_STEPS,
        "completed": completed and user.onboarding_completed,
        "percent_complete": int(round(100 * required_done / len(REQUIRED_STEPS))),
        "profile_completion": profile.profile_completion if profile else 0,
        "steps": [
            {
                "step": definition.step,
                "key": definition.key,
                "title": definition.title,
                "subtitle": definition.subtitle,
                "is_complete": bool(flags.get(definition.step)),
                "is_optional": definition.optional,
                "companion_message": (
                    definition.companion_done
                    if flags.get(definition.step)
                    else definition.companion_message
                ),
            }
            for definition in STEPS
        ],
        "next_route": (
            "/app/dashboard"
            if (completed and user.onboarding_completed)
            else f"/onboarding?step={next_step}"
        ),
    }


def companion_message_for(step: int, *, done: bool = False) -> str:
    definition = STEP_BY_NUMBER.get(step)
    if definition is None:
        return ""
    return definition.companion_done if done else definition.companion_message
