"""Idempotent reference-data seeder.

This seeds **reference data only**: the skill catalogue, career domains and
role rubrics. It creates no students and no resumes.

Synthetic student profiles were removed deliberately. Generated resumes and
invented projects were being parsed and scored alongside real ones, which made
extraction look better than it was and made every score impossible to trust.
Every profile in the database is now a real student's own data.

Run it as many times as you like: rows are matched by slug, so repeat runs
update instead of duplicating.

    python -m app.seeds.seed                # skills, domains, role rubrics
    python -m app.seeds.seed --purge-demo   # also delete leftover demo accounts

``--purge-demo`` only ever touches accounts flagged ``users.is_demo = true``,
which is the flag the old seeder set. Accounts registered through the app have
``is_demo = false`` and are never read, modified or deleted by this script.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging_config import configure_logging, get_logger
from app.db.session import SessionLocal, engine
from app.models import (
    CareerDomain,
    JobRole,
    Resume,
    RoleRequiredSkill,
    Skill,
    User,
)
from app.seeds.catalog_data import DOMAINS, ROLES, SKILLS

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
# Demo account cleanup
# --------------------------------------------------------------------------
def purge_demo_students(db: Session) -> int:
    """Delete accounts the old seeder created, and only those.

    ``is_demo`` is set exclusively by the removed demo seeder, so this cannot
    reach a real account. Their uploaded files go with them; cascades handle
    the profile, skill, project, experience and assessment rows.
    """
    demo_users = list(db.scalars(select(User).where(User.is_demo.is_(True))))
    if not demo_users:
        logger.info("No demo accounts found - nothing to purge.")
        return 0

    for user in demo_users:
        for resume in db.scalars(select(Resume).where(Resume.user_id == user.id)):
            try:
                Path(resume.file_path).unlink(missing_ok=True)
            except OSError as exc:  # pragma: no cover - filesystem dependent
                logger.warning("Could not delete %s: %s", resume.file_path, exc)
        logger.info("Deleting demo account %s (id=%s)", user.username, user.id)
        db.delete(user)

    db.flush()
    logger.info("Deleted %s demo account(s). Real accounts were not touched.", len(demo_users))
    return len(demo_users)


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------
def run(purge_demo: bool = False) -> int:
    configure_logging()

    try:
        with engine.connect():
            pass
    except Exception as exc:  # pragma: no cover - environment dependent
        logger.error("Cannot connect to the database: %s", exc)
        logger.error("Check DATABASE_URL in backend/.env, then run the migrations.")
        return 2

    with SessionLocal() as db:
        if purge_demo:
            purge_demo_students(db)
            db.commit()

        skills = seed_skills(db)
        domains = seed_domains(db)
        roles = seed_roles(db, domains, skills)
        db.commit()

    logger.info("-" * 70)
    logger.info(
        "Reference data seeded: %s skills, %s domains, %s role rubrics.",
        len(skills),
        len(domains),
        len(roles),
    )
    logger.info("No student profiles are created - every profile is a real account.")
    logger.info("-" * 70)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Seed Arjuna AI reference data (skills, domains, role rubrics)."
    )
    parser.add_argument(
        "--purge-demo",
        action="store_true",
        help=(
            "Delete accounts flagged is_demo=true, left over from the removed "
            "demo seeder. Never touches real accounts."
        ),
    )
    args = parser.parse_args()
    return run(purge_demo=args.purge_demo)


if __name__ == "__main__":
    sys.exit(main())
