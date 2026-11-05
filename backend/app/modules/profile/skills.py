"""Skill catalogue resolution and evidence tracking.

Two ideas matter here:

1. A free-text skill typed by a student is matched against the catalogue by
   slug, name and alias before a new custom skill row is created. That keeps
   "Node JS" and "node.js" from becoming two different skills.
2. Evidence is derived, never claimed. ``evidence_count`` counts the projects
   and experiences that actually reference a skill, so the scoring engine can
   separate a claim from a demonstrated skill.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Experience, Project, ProjectTechnology, Skill, StudentSkill

_NON_ALNUM = re.compile(r"[^a-z0-9]+")

# Common shorthand students type; maps to the canonical catalogue slug.
ALIAS_HINTS: dict[str, str] = {
    "js": "javascript",
    "ts": "typescript",
    "nodejs": "node-js",
    "node": "node-js",
    "reactjs": "react",
    "py": "python",
    "ml": "machine-learning",
    "dl": "deep-learning",
    "ai": "artificial-intelligence",
    "dsa": "data-structures-algorithms",
    "ds-algo": "data-structures-algorithms",
    "oops": "object-oriented-programming",
    "db": "sql",
    "postgres": "postgresql",
    "psql": "postgresql",
    "ms-excel": "excel",
    "advanced-excel": "excel",
    "powerbi": "power-bi",
    "tableau-desktop": "tableau",
    "fin-modelling": "financial-modelling",
    "financial-modeling": "financial-modelling",
    "valuations": "valuation",
    "dcf": "valuation",
    "cfa": "financial-statement-analysis",
    "aws-cloud": "aws",
    "gcp": "google-cloud",
    "k8s": "kubernetes",
    "sklearn": "scikit-learn",
    "scikit": "scikit-learn",
    "nlp": "natural-language-processing",
}

CATEGORY_HINTS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"python|java|c\+\+|golang|rust|javascript|typescript|react|node|django|flask|spring|html|css"), "programming"),
    (re.compile(r"machine|deep|neural|nlp|vision|tensor|pytorch|pandas|numpy|statistic|data analysis|data science|llm"), "data_ai"),
    (re.compile(r"aws|azure|gcp|cloud|docker|kubernetes|devops|ci/cd|terraform|linux"), "cloud_devops"),
    (re.compile(r"algorithm|data structure|operating system|dbms|computer network|oop|system design"), "cs_fundamentals"),
    (re.compile(r"financ|valuation|account|audit|equity|derivative|risk|credit|treasury|ifrs|capital market|m&a|lbo|dcf"), "finance"),
    (re.compile(r"consult|strategy|business|market|product|operation|stakeholder|negotiat|supply chain"), "business"),
    (re.compile(r"excel|powerpoint|tableau|power bi|sql|jira|figma|git|bloomberg|capital iq"), "tools"),
    (re.compile(r"communicat|leader|team|present|writing|time management|problem solving"), "soft_skills"),
)


def slugify(value: str) -> str:
    slug = _NON_ALNUM.sub("-", value.strip().lower()).strip("-")
    return slug or "skill"


def guess_category(name: str) -> str:
    lowered = name.lower()
    for pattern, category in CATEGORY_HINTS:
        if pattern.search(lowered):
            return category
    return "other"


def resolve_skill(
    db: Session,
    name: str,
    *,
    category: str | None = None,
    user_id: int | None = None,
    create_if_missing: bool = True,
) -> Skill | None:
    """Find the catalogue skill for a free-text name, creating it if allowed."""
    cleaned = " ".join(name.split())[:120]
    if not cleaned:
        return None

    slug = slugify(cleaned)
    slug = ALIAS_HINTS.get(slug, slug)

    skill = db.scalar(select(Skill).where(Skill.slug == slug))
    if skill is not None:
        return skill

    skill = db.scalar(select(Skill).where(func.lower(Skill.name) == cleaned.lower()))
    if skill is not None:
        return skill

    # Alias match: aliases is a JSONB array of lowercase strings.
    skill = db.scalar(
        select(Skill).where(Skill.aliases.contains([cleaned.lower()]))  # type: ignore[arg-type]
    )
    if skill is not None:
        return skill

    if not create_if_missing:
        return None

    skill = Skill(
        name=cleaned,
        slug=slug,
        category=category or guess_category(cleaned),
        is_custom=True,
        created_by_user_id=user_id,
        aliases=[],
    )
    db.add(skill)
    db.flush()
    return skill


def recompute_skill_evidence(db: Session, user_id: int) -> None:
    """Recount project/experience evidence for every skill this student claims.

    Called after any change to skills, projects or experience.
    """
    student_skills = list(
        db.scalars(select(StudentSkill).where(StudentSkill.user_id == user_id))
    )
    if not student_skills:
        return

    # Evidence source 1: linked project technologies.
    project_rows = db.execute(
        select(ProjectTechnology.skill_id, func.count(func.distinct(ProjectTechnology.project_id)))
        .join(Project, Project.id == ProjectTechnology.project_id)
        .where(Project.user_id == user_id, ProjectTechnology.skill_id.is_not(None))
        .group_by(ProjectTechnology.skill_id)
    ).all()
    project_counts = {row[0]: row[1] for row in project_rows}

    # Evidence source 2: free-text project technologies that never matched a skill.
    unmatched_tech = [
        (row[0] or "").lower()
        for row in db.execute(
            select(ProjectTechnology.raw_name)
            .join(Project, Project.id == ProjectTechnology.project_id)
            .where(Project.user_id == user_id, ProjectTechnology.skill_id.is_(None))
        ).all()
    ]

    # Evidence source 3: skills listed against internships/jobs.
    experience_skill_text: list[str] = []
    for exp in db.scalars(select(Experience).where(Experience.user_id == user_id)):
        experience_skill_text.extend((s or "").lower() for s in (exp.skills_used or []))
        if exp.description:
            experience_skill_text.append(exp.description.lower())

    for student_skill in student_skills:
        skill = student_skill.skill
        count = project_counts.get(student_skill.skill_id, 0)
        needle = skill.name.lower()
        needle_slug = skill.slug.replace("-", " ")
        count += sum(1 for text in unmatched_tech if needle in text or needle_slug in text)
        count += sum(
            1
            for text in experience_skill_text
            if needle and (needle in text or needle_slug in text)
        )
        student_skill.evidence_count = count
        student_skill.is_evidence_backed = count > 0


def link_project_technologies(
    db: Session, project: Project, technologies: Iterable[str], user_id: int
) -> None:
    """Replace a project's technology rows, linking each to the skill catalogue."""
    project.technologies.clear()
    db.flush()
    seen: set[str] = set()
    for raw in technologies:
        cleaned = " ".join(str(raw).split())[:120]
        if not cleaned or cleaned.lower() in seen:
            continue
        seen.add(cleaned.lower())
        skill = resolve_skill(db, cleaned, user_id=user_id)
        project.technologies.append(
            ProjectTechnology(
                skill_id=skill.id if skill else None,
                raw_name=cleaned,
            )
        )
