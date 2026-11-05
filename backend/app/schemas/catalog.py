"""Reference-data schemas (skills, domains, roles)."""

from __future__ import annotations

from app.schemas.common import ORMModel


class SkillOut(ORMModel):
    id: int
    name: str
    slug: str
    category: str
    is_custom: bool


class RoleRequiredSkillOut(ORMModel):
    skill_id: int
    skill_name: str
    category: str
    importance: str
    expected_proficiency: str
    weight: float


class JobRoleOut(ORMModel):
    id: int
    name: str
    slug: str
    short_label: str | None
    description: str | None
    domain_id: int
    domain_name: str
    domain_slug: str
    display_order: int


class RoleWeightsOut(ORMModel):
    skills: float
    projects: float
    academics: float
    experience: float
    certifications: float
    domain_knowledge: float
    resume_quality: float


class JobRoleDetailOut(JobRoleOut):
    weights: RoleWeightsOut
    min_cgpa: float
    target_cgpa: float
    expected_projects: int
    expected_internships: int
    expected_certifications: int
    required_skills: list[RoleRequiredSkillOut]


class CareerDomainOut(ORMModel):
    id: int
    name: str
    slug: str
    description: str | None
    icon: str | None
    accent_color: str | None
    display_order: int
    roles: list[JobRoleOut] = []
