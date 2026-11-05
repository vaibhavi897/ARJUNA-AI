"""Reference data endpoints: domains, roles, skill catalogue."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models import CareerDomain, JobRole, RoleRequiredSkill, Skill
from app.modules.auth.dependencies import DbSession
from app.schemas.catalog import (
    CareerDomainOut,
    JobRoleDetailOut,
    JobRoleOut,
    RoleRequiredSkillOut,
    RoleWeightsOut,
    SkillOut,
)

router = APIRouter(prefix="/catalog", tags=["catalog"])


def _role_out(role: JobRole) -> JobRoleOut:
    return JobRoleOut(
        id=role.id,
        name=role.name,
        slug=role.slug,
        short_label=role.short_label,
        description=role.description,
        domain_id=role.domain_id,
        domain_name=role.domain.name,
        domain_slug=role.domain.slug,
        display_order=role.display_order,
    )


@router.get("/domains", response_model=list[CareerDomainOut])
def list_domains(db: DbSession) -> list[CareerDomainOut]:
    """Career domains with their active roles - drives the preferences step."""
    domains = db.scalars(
        select(CareerDomain)
        .options(selectinload(CareerDomain.roles).selectinload(JobRole.domain))
        .where(CareerDomain.is_active.is_(True))
        .order_by(CareerDomain.display_order, CareerDomain.name)
    )
    out: list[CareerDomainOut] = []
    for domain in domains:
        roles = sorted(
            (role for role in domain.roles if role.is_active),
            key=lambda r: (r.display_order, r.name),
        )
        out.append(
            CareerDomainOut(
                id=domain.id,
                name=domain.name,
                slug=domain.slug,
                description=domain.description,
                icon=domain.icon,
                accent_color=domain.accent_color,
                display_order=domain.display_order,
                roles=[_role_out(role) for role in roles],
            )
        )
    return out


@router.get("/roles", response_model=list[JobRoleOut])
def list_roles(db: DbSession) -> list[JobRoleOut]:
    roles = db.scalars(
        select(JobRole)
        .options(selectinload(JobRole.domain))
        .where(JobRole.is_active.is_(True))
        .order_by(JobRole.display_order, JobRole.name)
    )
    return [_role_out(role) for role in roles]


@router.get("/roles/{slug}", response_model=JobRoleDetailOut)
def role_detail(slug: str, db: DbSession) -> JobRoleDetailOut:
    """A role's full rubric. Useful for showing students how they are judged."""
    role = db.scalar(
        select(JobRole)
        .options(
            selectinload(JobRole.domain),
            selectinload(JobRole.required_skills).selectinload(RoleRequiredSkill.skill),
        )
        .where(JobRole.slug == slug)
    )
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found.")

    base = _role_out(role)
    return JobRoleDetailOut(
        **base.model_dump(),
        weights=RoleWeightsOut(
            skills=role.weight_skills,
            projects=role.weight_projects,
            academics=role.weight_academics,
            experience=role.weight_experience,
            certifications=role.weight_certifications,
            domain_knowledge=role.weight_domain_knowledge,
            resume_quality=role.weight_resume_quality,
        ),
        min_cgpa=role.min_cgpa,
        target_cgpa=role.target_cgpa,
        expected_projects=role.expected_projects,
        expected_internships=role.expected_internships,
        expected_certifications=role.expected_certifications,
        required_skills=[
            RoleRequiredSkillOut(
                skill_id=req.skill_id,
                skill_name=req.skill.name,
                category=req.skill.category,
                importance=req.importance,
                expected_proficiency=req.expected_proficiency,
                weight=req.weight,
            )
            for req in sorted(
                role.required_skills,
                key=lambda r: (r.importance != "required", -r.weight, r.skill.name),
            )
        ],
    )


@router.get("/skills", response_model=list[SkillOut])
def list_skills(
    db: DbSession,
    q: str | None = Query(default=None, max_length=80),
    category: str | None = Query(default=None, max_length=40),
    limit: int = Query(default=200, ge=1, le=500),
) -> list[SkillOut]:
    """Skill suggestions for the skills step. Students may still type their own."""
    stmt = select(Skill)
    if q:
        needle = f"%{q.strip().lower()}%"
        stmt = stmt.where(func.lower(Skill.name).like(needle))
    if category:
        stmt = stmt.where(Skill.category == category)
    stmt = stmt.order_by(Skill.is_custom, Skill.name).limit(limit)
    return [SkillOut.model_validate(skill) for skill in db.scalars(stmt)]
