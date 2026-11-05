"""Profile reads and writes. Every section write is id-aware (upsert + prune)."""

from __future__ import annotations

from typing import Any, TypeVar

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.logging_config import get_logger
from app.models import (
    AcademicDetail,
    Achievement,
    Certification,
    Experience,
    JobRole,
    Project,
    Resume,
    Skill,
    StudentCareerPreference,
    StudentProfile,
    StudentSkill,
    User,
)
from app.modules.profile.skills import (
    link_project_technologies,
    recompute_skill_evidence,
    resolve_skill,
)
from app.schemas.profile import (
    AcademicDetailOut,
    AcademicStepIn,
    AchievementIn,
    AchievementOut,
    CareerPreferenceOut,
    CertificationIn,
    CertificationOut,
    ExperienceIn,
    ExperienceOut,
    ExperienceStepIn,
    FullProfileOut,
    PersonalInfoIn,
    PreferencesStepIn,
    ProfileCoreOut,
    ProjectOut,
    ProjectsStepIn,
    ResumeSummaryOut,
    SkillsStepIn,
    StudentSkillOut,
)

logger = get_logger(__name__)

T = TypeVar("T")

# Section weights for the profile-completion percentage (total = 100).
COMPLETION_WEIGHTS = {
    "personal": 20,
    "academics": 10,
    "skills": 20,
    "projects": 20,
    "experience": 10,
    "resume": 10,
    "preferences": 10,
}


def get_or_create_profile(db: Session, user: User) -> StudentProfile:
    profile = db.scalar(select(StudentProfile).where(StudentProfile.user_id == user.id))
    if profile is None:
        profile = StudentProfile(user_id=user.id)
        db.add(profile)
        db.flush()
    return profile


# --------------------------------------------------------------------------
# Completion
# --------------------------------------------------------------------------
def compute_profile_completion(db: Session, user: User) -> tuple[int, dict[str, Any]]:
    """Recompute and persist the completion percentage and its breakdown."""
    profile = get_or_create_profile(db, user)

    personal_fields = [
        profile.college,
        profile.degree,
        profile.branch,
        profile.graduation_year,
        profile.current_academic_year,
        profile.cgpa,
    ]
    personal_ratio = sum(1 for f in personal_fields if f not in (None, "")) / len(
        personal_fields
    )

    academics_count = _count(db, AcademicDetail, user.id)
    skills_count = _count(db, StudentSkill, user.id)
    projects_count = _count(db, Project, user.id)
    experience_count = _count(db, Experience, user.id)
    certs_count = _count(db, Certification, user.id)
    achievements_count = _count(db, Achievement, user.id)
    prefs_count = _count(db, StudentCareerPreference, user.id)
    has_resume = (
        db.scalar(
            select(Resume.id).where(Resume.user_id == user.id, Resume.is_active.is_(True))
        )
        is not None
    )

    ratios = {
        "personal": personal_ratio,
        "academics": min(academics_count / 1, 1.0),
        "skills": min(skills_count / 5, 1.0),
        "projects": min(projects_count / 2, 1.0),
        "experience": min(
            (experience_count + certs_count + achievements_count) / 2, 1.0
        ),
        "resume": 1.0 if has_resume else 0.0,
        "preferences": min(prefs_count / 1, 1.0),
    }

    breakdown: dict[str, Any] = {}
    total = 0.0
    for key, weight in COMPLETION_WEIGHTS.items():
        earned = round(ratios[key] * weight, 1)
        total += earned
        breakdown[key] = {
            "label": key.replace("_", " ").title(),
            "weight": weight,
            "earned": earned,
            "complete": ratios[key] >= 0.999,
        }

    percent = int(round(min(total, 100)))
    profile.profile_completion = percent
    profile.completion_breakdown = breakdown
    return percent, breakdown


def _count(db: Session, model: Any, user_id: int) -> int:
    from sqlalchemy import func

    return int(
        db.scalar(select(func.count()).select_from(model).where(model.user_id == user_id)) or 0
    )


# --------------------------------------------------------------------------
# Generic id-aware list sync
# --------------------------------------------------------------------------
def _sync_collection(
    db: Session,
    model: type[T],
    user_id: int,
    payload_items: list[Any],
    field_map: dict[str, str],
    *,
    after_create: Any = None,
    after_update: Any = None,
) -> tuple[int, int, int]:
    """Upsert the submitted rows and delete this user's rows that were omitted.

    ``field_map`` maps payload attribute -> column attribute.
    Returns (created, updated, deleted).
    """
    existing = {
        row.id: row
        for row in db.scalars(select(model).where(model.user_id == user_id))  # type: ignore[attr-defined]
    }
    submitted_ids: set[int] = set()
    created = updated = 0

    for item in payload_items:
        item_id = getattr(item, "id", None)
        if item_id and item_id in existing:
            row = existing[item_id]
            submitted_ids.add(item_id)
            updated += 1
            is_new = False
        else:
            row = model(user_id=user_id)  # type: ignore[call-arg]
            db.add(row)
            created += 1
            is_new = True

        for payload_attr, column_attr in field_map.items():
            setattr(row, column_attr, getattr(item, payload_attr))

        db.flush()
        if is_new:
            submitted_ids.add(row.id)
            if after_create is not None:
                after_create(row, item)
        elif after_update is not None:
            after_update(row, item)

    deleted = 0
    for row_id, row in existing.items():
        if row_id not in submitted_ids:
            db.delete(row)
            deleted += 1

    db.flush()
    return created, updated, deleted


# --------------------------------------------------------------------------
# Step 1 - personal info
# --------------------------------------------------------------------------
def save_personal_info(db: Session, user: User, payload: PersonalInfoIn) -> None:
    profile = get_or_create_profile(db, user)

    user.full_name = payload.full_name
    if payload.email.lower() != user.email.lower():
        from sqlalchemy import func

        clash = db.scalar(
            select(User.id).where(
                func.lower(User.email) == payload.email.lower(), User.id != user.id
            )
        )
        if clash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="That email is already used by another account.",
            )
        user.email = payload.email.lower()

    profile.phone = payload.phone
    profile.location = payload.location
    profile.college = payload.college
    profile.degree = payload.degree
    profile.branch = payload.branch
    profile.graduation_year = payload.graduation_year
    profile.current_academic_year = payload.current_academic_year
    profile.cgpa = payload.cgpa
    profile.cgpa_scale = payload.cgpa_scale
    profile.headline = payload.headline
    profile.bio = payload.bio
    db.flush()


# --------------------------------------------------------------------------
# Step 2 - academics
# --------------------------------------------------------------------------
def save_academics(db: Session, user: User, payload: AcademicStepIn) -> tuple[int, int, int]:
    return _sync_collection(
        db,
        AcademicDetail,
        user.id,
        payload.entries,
        {
            "level": "level",
            "institution": "institution",
            "board_or_university": "board_or_university",
            "degree_or_program": "degree_or_program",
            "specialization": "specialization",
            "score": "score",
            "score_type": "score_type",
            "start_year": "start_year",
            "end_year": "end_year",
            "is_current": "is_current",
            "achievements": "achievements",
            "relevant_coursework": "relevant_coursework",
        },
    )


# --------------------------------------------------------------------------
# Step 3 - skills
# --------------------------------------------------------------------------
def save_skills(db: Session, user: User, payload: SkillsStepIn) -> dict[str, int]:
    """Replace the student's skill set. Claimed proficiency is stored as given;
    evidence is recomputed separately and never taken from the client."""
    existing = {
        row.skill_id: row
        for row in db.scalars(select(StudentSkill).where(StudentSkill.user_id == user.id))
    }
    kept: set[int] = set()
    created = updated = 0

    for item in payload.skills:
        skill: Skill | None = None
        if item.skill_id:
            skill = db.get(Skill, item.skill_id)
        if skill is None and item.name:
            skill = resolve_skill(db, item.name, category=item.category, user_id=user.id)
        if skill is None:
            continue

        if skill.id in kept:
            continue
        kept.add(skill.id)

        row = existing.get(skill.id)
        if row is None:
            row = StudentSkill(user_id=user.id, skill_id=skill.id, source="manual")
            db.add(row)
            created += 1
        else:
            updated += 1
        row.proficiency = item.proficiency
        row.years_of_experience = item.years_of_experience
        row.notes = item.notes

    deleted = 0
    for skill_id, row in existing.items():
        if skill_id not in kept:
            db.delete(row)
            deleted += 1

    db.flush()
    recompute_skill_evidence(db, user.id)
    db.flush()
    return {"created": created, "updated": updated, "deleted": deleted}


# --------------------------------------------------------------------------
# Step 4 - projects
# --------------------------------------------------------------------------
def save_projects(db: Session, user: User, payload: ProjectsStepIn) -> tuple[int, int, int]:
    def _link(row: Project, item: Any) -> None:
        link_project_technologies(db, row, item.technologies, user.id)

    result = _sync_collection(
        db,
        Project,
        user.id,
        payload.projects,
        {
            "title": "title",
            "description": "description",
            "contribution": "contribution",
            "category": "category",
            "duration_months": "duration_months",
            "start_date": "start_date",
            "end_date": "end_date",
            "is_ongoing": "is_ongoing",
            "team_size": "team_size",
            "github_url": "github_url",
            "live_url": "live_url",
        },
        after_create=_link,
        after_update=_link,
    )
    recompute_skill_evidence(db, user.id)
    db.flush()
    return result


# --------------------------------------------------------------------------
# Step 5 - experience, certifications, achievements
# --------------------------------------------------------------------------
def save_experience_step(db: Session, user: User, payload: ExperienceStepIn) -> dict[str, Any]:
    exp = _sync_collection(
        db,
        Experience,
        user.id,
        payload.experiences,
        {
            "experience_type": "experience_type",
            "organization": "organization",
            "title": "title",
            "description": "description",
            "location": "location",
            "start_date": "start_date",
            "end_date": "end_date",
            "is_current": "is_current",
            "duration_months": "duration_months",
            "skills_used": "skills_used",
        },
    )
    certs = _sync_collection(
        db,
        Certification,
        user.id,
        payload.certifications,
        {
            "name": "name",
            "issuer": "issuer",
            "issue_date": "issue_date",
            "expiry_date": "expiry_date",
            "credential_id": "credential_id",
            "credential_url": "credential_url",
            "related_skills": "related_skills",
        },
    )
    achievements = _sync_collection(
        db,
        Achievement,
        user.id,
        payload.achievements,
        {
            "title": "title",
            "description": "description",
            "category": "category",
            "scope": "scope",
            "date_awarded": "date_awarded",
        },
    )
    recompute_skill_evidence(db, user.id)
    db.flush()
    return {
        "experiences": {"created": exp[0], "updated": exp[1], "deleted": exp[2]},
        "certifications": {"created": certs[0], "updated": certs[1], "deleted": certs[2]},
        "achievements": {
            "created": achievements[0],
            "updated": achievements[1],
            "deleted": achievements[2],
        },
    }


# --------------------------------------------------------------------------
# Step 7 - portfolio + career preferences
# --------------------------------------------------------------------------
def save_preferences(db: Session, user: User, payload: PreferencesStepIn) -> dict[str, Any]:
    profile = get_or_create_profile(db, user)
    profile.github_url = payload.github_url
    profile.linkedin_url = payload.linkedin_url
    profile.portfolio_url = payload.portfolio_url
    profile.other_links = [link.model_dump() for link in payload.other_links]

    valid_roles = list(
        db.scalars(
            select(JobRole).where(JobRole.id.in_(payload.role_ids or []), JobRole.is_active.is_(True))
        )
    )
    valid_ids = {role.id for role in valid_roles}
    unknown = [rid for rid in (payload.role_ids or []) if rid not in valid_ids]
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown or inactive role ids: {unknown}",
        )

    primary_id = payload.primary_role_id
    if primary_id is not None and primary_id not in valid_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="primary_role_id must be one of the selected roles.",
        )
    if primary_id is None and payload.role_ids:
        primary_id = payload.role_ids[0]

    existing = {
        row.role_id: row
        for row in db.scalars(
            select(StudentCareerPreference).where(
                StudentCareerPreference.user_id == user.id
            )
        )
    }
    for index, role_id in enumerate(payload.role_ids or []):
        row = existing.get(role_id)
        if row is None:
            row = StudentCareerPreference(user_id=user.id, role_id=role_id)
            db.add(row)
        row.priority = index + 1
        row.is_primary = role_id == primary_id

    for role_id, row in existing.items():
        if role_id not in valid_ids:
            db.delete(row)

    db.flush()
    return {"selected_roles": [role.name for role in valid_roles]}


# --------------------------------------------------------------------------
# Reads
# --------------------------------------------------------------------------
def load_student_skills(db: Session, user_id: int) -> list[StudentSkillOut]:
    rows = db.scalars(
        select(StudentSkill)
        .options(selectinload(StudentSkill.skill))
        .where(StudentSkill.user_id == user_id)
        .order_by(StudentSkill.id)
    )
    return [
        StudentSkillOut(
            id=row.id,
            skill_id=row.skill_id,
            name=row.skill.name,
            slug=row.skill.slug,
            category=row.skill.category,
            proficiency=row.proficiency,
            years_of_experience=row.years_of_experience,
            source=row.source,
            evidence_count=row.evidence_count,
            is_evidence_backed=row.is_evidence_backed,
            notes=row.notes,
        )
        for row in rows
    ]


def load_projects(db: Session, user_id: int) -> list[ProjectOut]:
    rows = db.scalars(
        select(Project)
        .options(selectinload(Project.technologies))
        .where(Project.user_id == user_id)
        .order_by(Project.id)
    )
    out: list[ProjectOut] = []
    for row in rows:
        # Built field by field: the ORM's ``technologies`` relationship holds
        # ProjectTechnology rows, while the schema exposes plain names.
        out.append(
            ProjectOut(
                id=row.id,
                title=row.title,
                description=row.description,
                contribution=row.contribution,
                category=row.category,
                duration_months=row.duration_months,
                start_date=row.start_date,
                end_date=row.end_date,
                is_ongoing=row.is_ongoing,
                team_size=row.team_size,
                github_url=row.github_url,
                live_url=row.live_url,
                source=row.source,
                technologies=[tech.raw_name for tech in row.technologies],
            )
        )
    return out


def load_preferences(db: Session, user_id: int) -> list[CareerPreferenceOut]:
    rows = db.scalars(
        select(StudentCareerPreference)
        .options(
            selectinload(StudentCareerPreference.role).selectinload(JobRole.domain)
        )
        .where(StudentCareerPreference.user_id == user_id)
        .order_by(StudentCareerPreference.priority)
    )
    return [
        CareerPreferenceOut(
            role_id=row.role_id,
            role_name=row.role.name,
            role_slug=row.role.slug,
            domain_id=row.role.domain_id,
            domain_name=row.role.domain.name,
            priority=row.priority,
            is_primary=row.is_primary,
        )
        for row in rows
    ]


def active_resume(db: Session, user_id: int) -> Resume | None:
    return db.scalar(
        select(Resume)
        .where(Resume.user_id == user_id, Resume.is_active.is_(True))
        .order_by(Resume.uploaded_at.desc())
    )


def build_full_profile(db: Session, user: User) -> FullProfileOut:
    profile = get_or_create_profile(db, user)
    resume = active_resume(db, user.id)

    academics = db.scalars(
        select(AcademicDetail)
        .where(AcademicDetail.user_id == user.id)
        .order_by(AcademicDetail.end_year.desc().nullslast(), AcademicDetail.id)
    )
    experiences = db.scalars(
        select(Experience).where(Experience.user_id == user.id).order_by(Experience.id)
    )
    certifications = db.scalars(
        select(Certification).where(Certification.user_id == user.id).order_by(Certification.id)
    )
    achievements = db.scalars(
        select(Achievement).where(Achievement.user_id == user.id).order_by(Achievement.id)
    )

    return FullProfileOut(
        user={
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "username": user.username,
            "onboarding_step": user.onboarding_step,
            "onboarding_completed": user.onboarding_completed,
            "is_demo": user.is_demo,
            "created_at": user.created_at,
        },
        profile=ProfileCoreOut.model_validate(profile),
        academics=[AcademicDetailOut.model_validate(row) for row in academics],
        skills=load_student_skills(db, user.id),
        projects=load_projects(db, user.id),
        experiences=[ExperienceOut.model_validate(row) for row in experiences],
        certifications=[CertificationOut.model_validate(row) for row in certifications],
        achievements=[AchievementOut.model_validate(row) for row in achievements],
        preferences=load_preferences(db, user.id),
        resume=ResumeSummaryOut(
            id=resume.id,
            original_filename=resume.original_filename,
            file_extension=resume.file_extension,
            file_size_bytes=resume.file_size_bytes,
            parse_status=resume.parse_status,
            parse_error=resume.parse_error,
            quality_score=resume.quality_score,
            reviewed_by_student=resume.reviewed_by_student,
            uploaded_at=resume.uploaded_at,
        )
        if resume
        else None,
    )


# Re-exported for routers that only need the type.
__all__ = [
    "AchievementIn",
    "CertificationIn",
    "ExperienceIn",
    "build_full_profile",
    "compute_profile_completion",
    "get_or_create_profile",
    "load_preferences",
    "load_projects",
    "load_student_skills",
    "save_academics",
    "save_experience_step",
    "save_personal_info",
    "save_preferences",
    "save_projects",
    "save_skills",
]
