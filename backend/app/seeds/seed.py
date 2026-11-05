"""Idempotent database seeder.

Run it as many times as you like: catalogue rows are matched by slug and demo
students by username, so repeat runs update instead of duplicating.

    python -m app.seeds.seed              # catalogue + demo students
    python -m app.seeds.seed --catalog-only
    python -m app.seeds.seed --reset-demo # delete demo students, then reseed

Only accounts created by this script (``users.is_demo = true``) are ever
touched. Accounts registered through the app are never modified or deleted.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging_config import configure_logging, get_logger
from app.core.security import hash_password
from app.db.session import SessionLocal, engine
from app.models import (
    AcademicDetail,
    Achievement,
    CareerDomain,
    Certification,
    Experience,
    JobRole,
    Project,
    ProjectTechnology,
    Resume,
    RoleRequiredSkill,
    Skill,
    StudentCareerPreference,
    StudentProfile,
    StudentSettings,
    StudentSkill,
    User,
)
from app.modules.activity import log_activity
from app.modules.profile.service import compute_profile_completion
from app.modules.profile.skills import recompute_skill_evidence, resolve_skill
from app.modules.resume.service import parse_resume_record
from app.modules.scoring.service import refresh_scores
from app.seeds.catalog_data import DOMAINS, ROLES, SKILLS
from app.seeds.resume_builder import build_docx_resume
from app.seeds.student_data import DEMO_PASSWORD, STUDENTS

logger = get_logger(__name__)


# --------------------------------------------------------------------------
# Catalogue
# --------------------------------------------------------------------------
def seed_skills(db: Session) -> dict[str, Skill]:
    existing = {skill.slug: skill for skill in db.scalars(select(Skill))}
    created = updated = 0

    for name, slug, category, aliases in SKILLS:
        skill = existing.get(slug)
        if skill is None:
            skill = Skill(name=name, slug=slug, category=category, aliases=aliases)
            db.add(skill)
            existing[slug] = skill
            created += 1
        else:
            skill.name = name
            skill.category = category
            skill.aliases = aliases
            skill.is_custom = False
            updated += 1

    db.flush()
    logger.info("Skills: %s created, %s updated", created, updated)
    return existing


def seed_domains(db: Session) -> dict[str, CareerDomain]:
    existing = {domain.slug: domain for domain in db.scalars(select(CareerDomain))}
    created = updated = 0

    for payload in DOMAINS:
        domain = existing.get(payload["slug"])
        if domain is None:
            domain = CareerDomain(**payload)
            db.add(domain)
            existing[payload["slug"]] = domain
            created += 1
        else:
            for key, value in payload.items():
                setattr(domain, key, value)
            domain.is_active = True
            updated += 1

    db.flush()
    logger.info("Career domains: %s created, %s updated", created, updated)
    return existing


def seed_roles(
    db: Session, domains: dict[str, CareerDomain], skills: dict[str, Skill]
) -> dict[str, JobRole]:
    existing = {role.slug: role for role in db.scalars(select(JobRole))}
    created = updated = 0
    missing_skills: set[str] = set()

    for payload in ROLES:
        domain = domains[payload["domain_slug"]]
        role = existing.get(payload["slug"])
        if role is None:
            role = JobRole(slug=payload["slug"], name=payload["name"], domain_id=domain.id)
            db.add(role)
            existing[payload["slug"]] = role
            created += 1
        else:
            updated += 1

        role.name = payload["name"]
        role.domain_id = domain.id
        role.short_label = payload["short_label"]
        role.description = payload["description"]
        role.display_order = payload["display_order"]
        role.is_active = True

        weights = payload["weights"]
        role.weight_skills = weights["skills"]
        role.weight_projects = weights["projects"]
        role.weight_academics = weights["academics"]
        role.weight_experience = weights["experience"]
        role.weight_certifications = weights["certifications"]
        role.weight_domain_knowledge = weights["domain_knowledge"]
        role.weight_resume_quality = weights["resume_quality"]

        role.min_cgpa = payload["min_cgpa"]
        role.target_cgpa = payload["target_cgpa"]
        role.expected_projects = payload["expected_projects"]
        role.expected_internships = payload["expected_internships"]
        role.expected_certifications = payload["expected_certifications"]
        role.resume_keywords = payload["resume_keywords"]
        role.relevant_project_categories = payload["relevant_project_categories"]
        db.flush()

        # Rewrite this role's requirement rows so the rubric matches the file.
        current = {
            req.skill_id: req
            for req in db.scalars(
                select(RoleRequiredSkill).where(RoleRequiredSkill.role_id == role.id)
            )
        }
        wanted_ids: set[int] = set()
        for skill_slug, importance, proficiency, weight in payload["required_skills"]:
            skill = skills.get(skill_slug)
            if skill is None:
                missing_skills.add(skill_slug)
                continue
            wanted_ids.add(skill.id)
            req = current.get(skill.id)
            if req is None:
                req = RoleRequiredSkill(role_id=role.id, skill_id=skill.id)
                db.add(req)
            req.importance = importance
            req.expected_proficiency = proficiency
            req.weight = weight

        for skill_id, req in current.items():
            if skill_id not in wanted_ids:
                db.delete(req)

    db.flush()
    if missing_skills:
        logger.warning("Role rubrics referenced unknown skills: %s", sorted(missing_skills))
    logger.info("Job roles: %s created, %s updated", created, updated)
    return existing


# --------------------------------------------------------------------------
# Demo students
# --------------------------------------------------------------------------
def delete_demo_students(db: Session) -> int:
    """Remove only accounts this seeder created."""
    demo_users = list(db.scalars(select(User).where(User.is_demo.is_(True))))
    for user in demo_users:
        for resume in db.scalars(select(Resume).where(Resume.user_id == user.id)):
            Path(resume.file_path).unlink(missing_ok=True)
        db.delete(user)
    db.flush()
    logger.info("Deleted %s demo student(s)", len(demo_users))
    return len(demo_users)


def _replace_children(db: Session, model: Any, user_id: int) -> None:
    for row in db.scalars(select(model).where(model.user_id == user_id)):
        db.delete(row)
    db.flush()


def seed_student(db: Session, payload: dict[str, Any], roles: dict[str, JobRole]) -> User:
    """Create or refresh one demo student, then score them."""
    user = db.scalar(select(User).where(User.username == payload["username"]))
    is_new = user is None
    if user is None:
        user = User(
            username=payload["username"],
            email=payload["email"],
            full_name=payload["full_name"],
            password_hash=hash_password(DEMO_PASSWORD),
            role="student",
            is_demo=True,
        )
        db.add(user)
        db.flush()
    else:
        user.full_name = payload["full_name"]
        user.email = payload["email"]
        user.is_demo = True

    # --- profile ---
    profile = db.scalar(select(StudentProfile).where(StudentProfile.user_id == user.id))
    if profile is None:
        profile = StudentProfile(user_id=user.id)
        db.add(profile)
    for key, value in payload["profile"].items():
        setattr(profile, key, value)

    if db.scalar(select(StudentSettings).where(StudentSettings.user_id == user.id)) is None:
        db.add(StudentSettings(user_id=user.id))
    db.flush()

    # --- academics ---
    _replace_children(db, AcademicDetail, user.id)
    for entry in payload.get("academics", []):
        db.add(AcademicDetail(user_id=user.id, **entry))

    # --- skills ---
    _replace_children(db, StudentSkill, user.id)
    for name, proficiency in payload.get("skills", []):
        skill = resolve_skill(db, name, user_id=user.id)
        if skill is None:
            continue
        db.add(
            StudentSkill(
                user_id=user.id,
                skill_id=skill.id,
                proficiency=proficiency,
                source="manual",
            )
        )
    db.flush()

    # --- projects ---
    for project in db.scalars(select(Project).where(Project.user_id == user.id)):
        db.delete(project)
    db.flush()
    for entry in payload.get("projects", []):
        technologies = entry.pop("technologies", []) if "technologies" in entry else []
        project = Project(
            user_id=user.id,
            title=entry["title"],
            description=entry.get("description"),
            contribution=entry.get("contribution"),
            category=entry.get("category"),
            duration_months=entry.get("duration_months"),
            team_size=entry.get("team_size"),
            github_url=entry.get("github_url"),
            live_url=entry.get("live_url"),
            source="manual",
        )
        db.add(project)
        db.flush()
        for tech in technologies:
            skill = resolve_skill(db, tech, user_id=user.id)
            db.add(
                ProjectTechnology(
                    project_id=project.id,
                    skill_id=skill.id if skill else None,
                    raw_name=tech,
                )
            )
        entry["technologies"] = technologies  # keep the dataset reusable

    # --- experience / certifications / achievements ---
    _replace_children(db, Experience, user.id)
    for entry in payload.get("experiences", []):
        db.add(
            Experience(
                user_id=user.id,
                experience_type=entry["experience_type"],
                organization=entry["organization"],
                title=entry["title"],
                description=entry.get("description"),
                duration_months=entry.get("duration_months"),
                skills_used=entry.get("skills_used", []),
                source="manual",
            )
        )

    _replace_children(db, Certification, user.id)
    for entry in payload.get("certifications", []):
        issue_date = dt.date(entry["year"], 6, 1) if entry.get("year") else None
        db.add(
            Certification(
                user_id=user.id,
                name=entry["name"],
                issuer=entry.get("issuer"),
                issue_date=issue_date,
                related_skills=entry.get("related_skills", []),
                source="manual",
            )
        )

    _replace_children(db, Achievement, user.id)
    for entry in payload.get("achievements", []):
        date_awarded = dt.date(entry["year"], 4, 1) if entry.get("year") else None
        db.add(
            Achievement(
                user_id=user.id,
                title=entry["title"],
                category=entry.get("category", "other"),
                scope=entry.get("scope"),
                date_awarded=date_awarded,
                source="manual",
            )
        )

    # --- career preferences ---
    _replace_children(db, StudentCareerPreference, user.id)
    db.flush()
    for index, role_slug in enumerate(payload.get("preferences", [])):
        role = roles.get(role_slug)
        if role is None:
            logger.warning("Unknown role slug in demo data: %s", role_slug)
            continue
        db.add(
            StudentCareerPreference(
                user_id=user.id,
                role_id=role.id,
                priority=index + 1,
                is_primary=role_slug == payload.get("primary"),
            )
        )

    # --- resume (generated from this student's own data, then really parsed) ---
    if payload.get("generate_resume"):
        for resume in db.scalars(select(Resume).where(Resume.user_id == user.id)):
            Path(resume.file_path).unlink(missing_ok=True)
            db.delete(resume)
        db.flush()

        filename = f"{user.id}_demo_{payload['username'].replace('.', '_')}.docx"
        destination = settings.resume_dir / filename
        build_docx_resume(payload, destination)
        resume = Resume(
            user_id=user.id,
            original_filename=f"{payload['full_name'].replace(' ', '_')}_Resume.docx",
            stored_filename=filename,
            file_path=str(destination),
            content_type=(
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ),
            file_size_bytes=destination.stat().st_size,
            file_extension=".docx",
            parse_status="pending",
            is_active=True,
            reviewed_by_student=True,
            uploaded_at=dt.datetime.now(dt.timezone.utc),
        )
        db.add(resume)
        db.flush()
        parse_resume_record(db, resume)

    user.onboarding_completed = True
    user.onboarding_step = 7
    db.flush()

    recompute_skill_evidence(db, user.id)
    compute_profile_completion(db, user)
    db.flush()

    if is_new:
        log_activity(
            db,
            user.id,
            "account_created",
            "Demo account created",
            "Synthetic demonstration profile seeded by the Arjuna AI seeder.",
        )
        log_activity(db, user.id, "onboarding_completed", "Onboarding completed", None)

    refresh_scores(db, user, change="onboarding_completed", log=True)
    db.commit()
    return user


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------
def run(catalog_only: bool = False, reset_demo: bool = False) -> int:
    configure_logging()

    try:
        with engine.connect():
            pass
    except Exception as exc:  # pragma: no cover - environment dependent
        logger.error("Cannot connect to the database: %s", exc)
        logger.error("Check DATABASE_URL in backend/.env, then run the migrations.")
        return 2

    with SessionLocal() as db:
        skills = seed_skills(db)
        domains = seed_domains(db)
        roles = seed_roles(db, domains, skills)
        db.commit()

        if catalog_only:
            logger.info("Catalogue seeded (%s skills, %s roles).", len(skills), len(roles))
            return 0

        if reset_demo:
            delete_demo_students(db)
            db.commit()

        for payload in STUDENTS:
            user = seed_student(db, payload, roles)
            logger.info("Seeded demo student %s (id=%s)", user.username, user.id)

    logger.info("-" * 70)
    logger.info("Seed complete. %s demo students available.", len(STUDENTS))
    logger.info("Demo password for every seeded account: %s", DEMO_PASSWORD)
    logger.info("Primary demo login: %s / %s", STUDENTS[0]["email"], DEMO_PASSWORD)
    logger.info("-" * 70)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed the Arjuna AI database.")
    parser.add_argument(
        "--catalog-only",
        action="store_true",
        help="Seed only skills, domains and role rubrics.",
    )
    parser.add_argument(
        "--reset-demo",
        action="store_true",
        help="Delete seeded demo students first (never touches real accounts).",
    )
    args = parser.parse_args()
    return run(catalog_only=args.catalog_only, reset_demo=args.reset_demo)


if __name__ == "__main__":
    sys.exit(main())
