"""Role-based career readiness scoring engine.

Design rules this module enforces:

* **One rubric per role.** Weights, expectations and keywords come from the
  ``job_roles`` / ``role_required_skills`` rows, never from hardcoded formulas.
* **Nothing is random.** The same profile and the same rubric always produce
  the same score.
* **Every point is attributable.** Each component returns an explanation plus
  the raw details behind it, and these are persisted so the score stays
  explainable after the fact.
* **Claims are worth less than evidence.** A listed skill earns
  ``CLAIM_ONLY_CREDIT`` of what a skill demonstrated in a project or internship
  earns.
* **Optional sections are never a penalty.** Projects, experience and
  certifications are optional at onboarding, so a section the student does not
  have is *removed from the denominator* and its weight is redistributed over
  the evidence they do have - it is not scored as a zero. A fresher with no
  internship is measured on their projects, not punished for the gap.
* **Adding something can never cost you points.** The evidence pool is the
  best result obtainable by ignoring at most one weak optional kind, so a
  modest position of responsibility can only help (see
  :func:`_combine_evidence`).
* **Quality, not quantity.** Components score the best few pieces of work on
  their relevance and depth. A fourth thin project adds nothing.
* **No double counting.** Role keywords that merely restate a rubric skill are
  dropped from domain knowledge, which measures the concepts the skills rubric
  does *not* already test.

The engine is deliberately separate from the ORM write path: :func:`score_role`
is pure, and :func:`recalculate_assessments` handles persistence. Swapping in a
trained model later means replacing the component functions, not the plumbing.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.logging_config import get_logger
from app.models import (
    AcademicDetail,
    Achievement,
    AssessmentScoreBreakdown,
    Certification,
    Experience,
    JobRole,
    Project,
    Resume,
    RoleAssessment,
    RoleRequiredSkill,
    SkillGapAnalysis,
    StudentCareerPreference,
    StudentProfile,
    StudentSkill,
    User,
)
from app.models.catalog import PROFICIENCY_RANK

logger = get_logger(__name__)

ENGINE_VERSION = "2.0.0"

# A skill the student claims but has not demonstrated earns this share of the
# points an evidence-backed skill of the same proficiency would earn.
CLAIM_ONLY_CREDIT = 0.55
# Importance multipliers applied on top of each requirement's own weight.
IMPORTANCE_MULTIPLIER = {"required": 1.0, "preferred": 0.45}

# Components that are optional at onboarding and share one evidence pool.
EVIDENCE_COMPONENTS = ("projects", "experience", "certifications")
# An optional kind scoring below this may be ignored rather than averaged in,
# so that a weak entry never drags the score below having nothing at all.
WEAK_EVIDENCE_THRESHOLD = 0.5
# Evidence from a single kind cannot reach the full pool: projects and
# internships prove different things. Applied symmetrically, so neither a
# projects-only nor an internships-only student is singled out.
SINGLE_SOURCE_CAP = 0.92
# A position of responsibility is real experience, but not hands-on work.
POR_CREDIT = 0.5
# Experience and project quality are read off at most this many entries.
MAX_SCORED_SLOTS = 4

BANDS: tuple[tuple[float, str], ...] = (
    (85.0, "Placement Ready"),
    (70.0, "Strong"),
    (55.0, "Developing"),
    (40.0, "Emerging"),
    (0.0, "Early Stage"),
)

COMPONENT_LABELS = {
    "skills": "Role Skills Match",
    "projects": "Projects & Practical Work",
    "academics": "Academic Profile",
    "experience": "Internships & Experience",
    "certifications": "Certifications",
    "domain_knowledge": "Domain Knowledge",
    "resume_quality": "Resume Quality",
}

COMPONENT_ORDER = (
    "skills",
    "projects",
    "experience",
    "academics",
    "domain_knowledge",
    "certifications",
    "resume_quality",
)

_METRIC_RE = re.compile(
    r"(\d+(?:[.,]\d+)?\s*(?:%|percent|x\b|k\b|lakh|crore|million|mn\b|bn\b|billion|"
    r"users?|teams?|students?|participants?|months?|hours?|ms\b|seconds?)|[$₹]\s?\d|\d+\+)",
    re.I,
)
_WORD_SPLIT_RE = re.compile(r"[^a-z0-9+#.]+")


def band_for(score: float) -> str:
    for threshold, label in BANDS:
        if score >= threshold:
            return label
    return BANDS[-1][1]


# --------------------------------------------------------------------------
# Profile snapshot
# --------------------------------------------------------------------------
@dataclass(slots=True)
class SkillFact:
    skill_id: int
    name: str
    slug: str
    category: str
    proficiency: str
    evidence_count: int
    is_evidence_backed: bool

    @property
    def rank(self) -> int:
        return PROFICIENCY_RANK.get(self.proficiency, 1)


@dataclass(slots=True)
class ProjectFact:
    id: int
    title: str
    category: str | None
    description: str
    contribution: str
    skill_ids: set[int]
    tech_names: list[str]
    has_link: bool
    duration_months: int | None

    @property
    def text(self) -> str:
        return f"{self.title} {self.description} {self.contribution} {' '.join(self.tech_names)}"

    @property
    def metric_count(self) -> int:
        return len(_METRIC_RE.findall(f"{self.description} {self.contribution}"))


@dataclass(slots=True)
class ExperienceFact:
    id: int
    experience_type: str
    organization: str
    title: str
    description: str
    duration_months: int
    skills_used: list[str]

    @property
    def text(self) -> str:
        return f"{self.title} {self.organization} {self.description} {' '.join(self.skills_used)}"

    @property
    def metric_count(self) -> int:
        return len(_METRIC_RE.findall(self.description))

    @property
    def is_work(self) -> bool:
        return self.experience_type in ("internship", "job")


@dataclass(slots=True)
class EducationFact:
    level: str
    institution: str
    degree: str | None
    score: float | None
    has_years: bool
    coursework: list[str]
    achievements: bool


@dataclass(slots=True)
class ProfileSnapshot:
    """Everything the engine is allowed to look at, gathered once per run."""

    user_id: int
    full_name: str
    cgpa_on_10: float | None
    cgpa_provided: bool
    graduation_year: int | None
    skills: list[SkillFact]
    projects: list[ProjectFact]
    experiences: list[ExperienceFact]
    certifications: list[dict[str, Any]]
    achievements: list[dict[str, Any]]
    education: list[EducationFact]
    coursework: list[str]
    academic_achievements: int
    resume_quality: float | None
    resume_text: str
    resume_present: bool
    searchable_text: str = ""
    skills_by_id: dict[int, SkillFact] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.skills_by_id = {skill.skill_id: skill for skill in self.skills}
        parts = [skill.name for skill in self.skills]
        parts += [project.text for project in self.projects]
        parts += [experience.text for experience in self.experiences]
        parts += [str(c.get("name", "")) for c in self.certifications]
        parts += [str(a.get("title", "")) for a in self.achievements]
        parts += self.coursework
        self.searchable_text = " ".join(parts).lower()

    @property
    def work_experiences(self) -> list[ExperienceFact]:
        return [e for e in self.experiences if e.is_work]

    @property
    def responsibility_experiences(self) -> list[ExperienceFact]:
        return [e for e in self.experiences if not e.is_work]

    @property
    def internship_count(self) -> int:
        return sum(1 for e in self.experiences if e.experience_type == "internship")

    @property
    def job_count(self) -> int:
        return sum(1 for e in self.experiences if e.experience_type == "job")

    @property
    def total_experience_months(self) -> int:
        return sum(e.duration_months for e in self.work_experiences)


def _months_between(start: dt.date | None, end: dt.date | None, is_current: bool) -> int:
    if start is None:
        return 0
    finish = end or (dt.date.today() if is_current else None)
    if finish is None:
        return 0
    months = (finish.year - start.year) * 12 + (finish.month - start.month)
    return max(months, 1)


def build_snapshot(db: Session, user: User) -> ProfileSnapshot:
    """Load one consistent view of the student's profile."""
    profile = db.scalar(select(StudentProfile).where(StudentProfile.user_id == user.id))

    cgpa_on_10: float | None = None
    if profile and profile.cgpa is not None:
        scale = profile.cgpa_scale or 10.0
        if scale > 0:
            cgpa_on_10 = round(min(profile.cgpa / scale * 10.0, 10.0), 2)

    skill_rows = db.scalars(
        select(StudentSkill)
        .options(selectinload(StudentSkill.skill))
        .where(StudentSkill.user_id == user.id)
    )
    skills = [
        SkillFact(
            skill_id=row.skill_id,
            name=row.skill.name,
            slug=row.skill.slug,
            category=row.skill.category,
            proficiency=row.proficiency,
            evidence_count=row.evidence_count,
            is_evidence_backed=row.is_evidence_backed,
        )
        for row in skill_rows
    ]

    project_rows = db.scalars(
        select(Project)
        .options(selectinload(Project.technologies))
        .where(Project.user_id == user.id)
    )
    projects = [
        ProjectFact(
            id=row.id,
            title=row.title,
            category=row.category,
            description=row.description or "",
            contribution=row.contribution or "",
            skill_ids={t.skill_id for t in row.technologies if t.skill_id},
            tech_names=[t.raw_name for t in row.technologies],
            has_link=bool(row.github_url or row.live_url),
            duration_months=row.duration_months,
        )
        for row in project_rows
    ]

    experience_rows = db.scalars(select(Experience).where(Experience.user_id == user.id))
    experiences = [
        ExperienceFact(
            id=row.id,
            experience_type=row.experience_type,
            organization=row.organization,
            title=row.title,
            description=row.description or "",
            duration_months=row.duration_months
            or _months_between(row.start_date, row.end_date, row.is_current),
            skills_used=list(row.skills_used or []),
        )
        for row in experience_rows
    ]

    certifications = [
        {"name": row.name, "issuer": row.issuer, "related_skills": row.related_skills}
        for row in db.scalars(select(Certification).where(Certification.user_id == user.id))
    ]
    achievements = [
        {"title": row.title, "category": row.category, "scope": row.scope}
        for row in db.scalars(select(Achievement).where(Achievement.user_id == user.id))
    ]

    education: list[EducationFact] = []
    coursework: list[str] = []
    academic_achievements = 0
    for row in db.scalars(select(AcademicDetail).where(AcademicDetail.user_id == user.id)):
        coursework.extend(row.relevant_coursework or [])
        if row.achievements:
            academic_achievements += 1
        education.append(
            EducationFact(
                level=row.level,
                institution=row.institution,
                degree=row.degree_or_program,
                score=row.score,
                has_years=bool(row.start_year or row.end_year),
                coursework=list(row.relevant_coursework or []),
                achievements=bool(row.achievements),
            )
        )

    resume = db.scalar(
        select(Resume)
        .where(Resume.user_id == user.id, Resume.is_active.is_(True))
        .order_by(Resume.uploaded_at.desc())
    )

    return ProfileSnapshot(
        user_id=user.id,
        full_name=user.full_name,
        cgpa_on_10=cgpa_on_10,
        cgpa_provided=cgpa_on_10 is not None,
        graduation_year=profile.graduation_year if profile else None,
        skills=skills,
        projects=projects,
        experiences=experiences,
        certifications=certifications,
        achievements=achievements,
        education=education,
        coursework=coursework,
        academic_achievements=academic_achievements,
        resume_quality=resume.quality_score if resume else None,
        resume_text=(resume.extracted_text or "") if resume else "",
        resume_present=resume is not None and resume.parse_status == "parsed",
    )


# --------------------------------------------------------------------------
# Component results
# --------------------------------------------------------------------------
@dataclass(slots=True)
class ComponentResult:
    component: str
    weight: float
    ratio: float
    explanation: str
    details: dict[str, Any] = field(default_factory=dict)
    # False when the student does not have this optional section at all. The
    # component then carries no weight and its share moves elsewhere.
    applicable: bool = True

    @property
    def points(self) -> float:
        return round(self.ratio * self.weight, 2)

    @property
    def label(self) -> str:
        return COMPONENT_LABELS[self.component]


@dataclass(slots=True)
class GapRecord:
    skill_id: int
    skill_name: str
    status: str
    importance: str
    expected_proficiency: str
    student_proficiency: str | None
    is_evidence_backed: bool
    points_lost: float
    recommendation: str


@dataclass(slots=True)
class RoleScoreResult:
    role_id: int
    role_slug: str
    role_name: str
    score: float
    band: str
    components: list[ComponentResult]
    gaps: list[GapRecord]
    strengths: list[dict[str, Any]]
    improvements: list[dict[str, Any]]
    insights: list[dict[str, Any]]
    match_summary: dict[str, Any]


def _keyword_hits(text: str, keywords: list[str]) -> tuple[list[str], list[str]]:
    hits: list[str] = []
    misses: list[str] = []
    lowered = text.lower()
    for keyword in keywords:
        if keyword.lower() in lowered:
            hits.append(keyword)
        else:
            misses.append(keyword)
    return hits, misses


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


# --------------------------------------------------------------------------
# Skills
# --------------------------------------------------------------------------
def _score_skills(
    snapshot: ProfileSnapshot, role: JobRole
) -> tuple[ComponentResult, list[GapRecord]]:
    requirements = role.required_skills
    weight = role.weight_skills
    gaps: list[GapRecord] = []

    if not requirements:
        return (
            ComponentResult(
                "skills",
                weight,
                0.5,
                "This role has no skill rubric configured yet, so a neutral score is used.",
                {"configured": False},
            ),
            gaps,
        )

    total_possible = 0.0
    total_earned = 0.0
    matched: list[dict[str, Any]] = []

    for requirement in requirements:
        multiplier = IMPORTANCE_MULTIPLIER.get(requirement.importance, 1.0)
        slot_weight = max(requirement.weight, 0.1) * multiplier
        total_possible += slot_weight

        expected_rank = PROFICIENCY_RANK.get(requirement.expected_proficiency, 2)
        student = snapshot.skills_by_id.get(requirement.skill_id)
        skill_name = requirement.skill.name

        if student is None:
            gaps.append(
                GapRecord(
                    skill_id=requirement.skill_id,
                    skill_name=skill_name,
                    status="missing",
                    importance=requirement.importance,
                    expected_proficiency=requirement.expected_proficiency,
                    student_proficiency=None,
                    is_evidence_backed=False,
                    points_lost=round(slot_weight, 2),
                    recommendation=(
                        f"Learn {skill_name} to at least "
                        f"{requirement.expected_proficiency} level"
                        + (
                            " - it is a core requirement for this role."
                            if requirement.importance == "required"
                            else "."
                        )
                    ),
                )
            )
            continue

        proficiency_ratio = min(student.rank / expected_rank, 1.0)
        if student.is_evidence_backed:
            # A second piece of evidence nudges credit up, capped at full.
            evidence_factor = min(1.0, 0.85 + 0.15 * min(student.evidence_count, 2))
        else:
            evidence_factor = CLAIM_ONLY_CREDIT

        earned = slot_weight * proficiency_ratio * evidence_factor
        total_earned += earned
        lost = round(slot_weight - earned, 2)

        if student.rank < expected_rank:
            status = "below_expected"
            recommendation = (
                f"Move {skill_name} from {student.proficiency} to "
                f"{requirement.expected_proficiency} level."
            )
        elif not student.is_evidence_backed:
            status = "claimed_only"
            recommendation = (
                f"{skill_name} is listed but not demonstrated. Use it in a project "
                "or internship so it counts fully."
            )
        else:
            status = "met"
            recommendation = ""

        if status != "met" or lost > 0.01:
            gaps.append(
                GapRecord(
                    skill_id=requirement.skill_id,
                    skill_name=skill_name,
                    status=status,
                    importance=requirement.importance,
                    expected_proficiency=requirement.expected_proficiency,
                    student_proficiency=student.proficiency,
                    is_evidence_backed=student.is_evidence_backed,
                    points_lost=max(lost, 0.0),
                    recommendation=recommendation,
                )
            )

        matched.append(
            {
                "skill": skill_name,
                "importance": requirement.importance,
                "student_proficiency": student.proficiency,
                "expected_proficiency": requirement.expected_proficiency,
                "evidence_backed": student.is_evidence_backed,
                "evidence_count": student.evidence_count,
                "credit_ratio": round(proficiency_ratio * evidence_factor, 3),
            }
        )

    ratio = total_earned / total_possible if total_possible else 0.0
    required_total = sum(1 for r in requirements if r.importance == "required")
    required_matched = sum(
        1
        for r in requirements
        if r.importance == "required" and r.skill_id in snapshot.skills_by_id
    )
    evidence_backed = sum(1 for m in matched if m["evidence_backed"])

    explanation = (
        f"Matched {len(matched)} of {len(requirements)} rubric skills "
        f"({required_matched}/{required_total} marked required). "
        f"{evidence_backed} are backed by a project or internship; claimed-only skills "
        f"earn {int(CLAIM_ONLY_CREDIT * 100)}% credit."
    )

    return (
        ComponentResult(
            "skills",
            weight,
            round(min(ratio, 1.0), 4),
            explanation,
            {
                "matched": matched,
                "required_total": required_total,
                "required_matched": required_matched,
                "rubric_total": len(requirements),
                "evidence_backed": evidence_backed,
                "missing": [g.skill_name for g in gaps if g.status == "missing"],
            },
        ),
        gaps,
    )


# --------------------------------------------------------------------------
# Projects
# --------------------------------------------------------------------------
def _project_relevance(project: ProjectFact, role: JobRole, role_skill_ids: set[int]) -> float:
    """0..1 relevance of one project to one role.

    Skill overlap is deliberately the smaller share: the skills component
    already scores those same skills, and weighting them heavily here would
    count one fact twice.
    """
    score = 0.0
    if role_skill_ids and project.skill_ids:
        overlap = len(project.skill_ids & role_skill_ids)
        score += min(overlap / 2, 1.0) * 0.35
    categories = [c.lower() for c in (role.relevant_project_categories or [])]
    if project.category and any(c in project.category.lower() for c in categories):
        score += 0.25
    hits, _ = _keyword_hits(project.text, role.resume_keywords or [])
    if hits:
        score += min(len(hits) / 3, 1.0) * 0.40
    return min(score, 1.0)


def _project_depth(project: ProjectFact) -> float:
    """0..1 on how substantial the entry is, independent of the role."""
    signals = [
        min(len(project.description) / 240.0, 1.0),
        1.0 if project.contribution.strip() else 0.0,
        min(project.metric_count / 2.0, 1.0),
        1.0 if project.tech_names else 0.0,
        1.0 if project.has_link else 0.0,
    ]
    # Description and measurable outcomes carry more than a link does.
    weights = [0.30, 0.20, 0.25, 0.15, 0.10]
    return sum(signal * weight for signal, weight in zip(signals, weights))


def _score_projects(snapshot: ProfileSnapshot, role: JobRole) -> ComponentResult:
    weight = role.weight_projects
    expected = min(max(role.expected_projects, 1), MAX_SCORED_SLOTS)
    role_skill_ids = {r.skill_id for r in role.required_skills}

    if not snapshot.projects:
        return ComponentResult(
            "projects",
            weight,
            0.0,
            "No projects on file. Projects are optional, so this weight has been "
            "moved to the evidence you do have.",
            {"count": 0, "expected": expected, "projects": []},
            applicable=False,
        )

    scored: list[dict[str, Any]] = []
    for project in snapshot.projects:
        relevance = _project_relevance(project, role, role_skill_ids)
        depth = _project_depth(project)
        scored.append(
            {
                "id": project.id,
                "title": project.title,
                "relevance": round(relevance, 3),
                "depth": round(depth, 3),
                "quality": round(0.6 * relevance + 0.4 * depth, 3),
                "category": project.category,
            }
        )

    scored.sort(key=lambda item: item["quality"], reverse=True)
    top = scored[:expected]
    # Quality of the best work, not a count of entries: a fourth thin project
    # adds nothing, and one excellent project is nearly as good as three.
    quality_ratio = _mean([item["quality"] for item in top])
    breadth = min(len(scored) / expected, 1.0)
    ratio = quality_ratio * (0.85 + 0.15 * breadth)
    strongly_relevant = [item for item in scored if item["relevance"] >= 0.5]

    explanation = (
        f"Judged on your {min(len(scored), expected)} strongest project(s) of "
        f"{len(scored)} ({len(strongly_relevant)} clearly relevant to this role). "
        "Relevance comes from technologies, category and role keywords; depth from "
        "the description, your stated contribution, measurable outcomes and links."
    )

    return ComponentResult(
        "projects",
        weight,
        round(min(ratio, 1.0), 4),
        explanation,
        {
            "count": len(scored),
            "expected": expected,
            "relevant_count": len(strongly_relevant),
            "projects": scored[:8],
            "quality_ratio": round(quality_ratio, 3),
            "breadth": round(breadth, 3),
        },
    )


# --------------------------------------------------------------------------
# Experience
# --------------------------------------------------------------------------
def _experience_quality(
    item: ExperienceFact, role: JobRole, role_skill_names: set[str]
) -> tuple[float, float, float]:
    """``(quality, relevance, depth)`` for one experience entry."""
    keywords = role.resume_keywords or []
    hits, _ = _keyword_hits(item.text, keywords)
    keyword_ratio = min(len(hits) / 3, 1.0) if keywords else 0.0

    words = {w for w in _WORD_SPLIT_RE.split(item.text.lower()) if w}
    skill_overlap = len(words & role_skill_names)
    skill_ratio = min(skill_overlap / 2, 1.0) if role_skill_names else 0.0
    relevance = max(keyword_ratio, 0.0) * 0.65 + skill_ratio * 0.35
    if not keywords and not role_skill_names:
        relevance = 0.5

    depth_signals = [
        min(len(item.description) / 200.0, 1.0),
        min(item.metric_count / 2.0, 1.0),
        min(item.duration_months / 2.0, 1.0) if item.duration_months else 0.0,
    ]
    depth = sum(s * w for s, w in zip(depth_signals, (0.40, 0.35, 0.25)))

    quality = 0.55 * min(relevance, 1.0) + 0.45 * depth
    return min(quality, 1.0), min(relevance, 1.0), depth


def _score_experience(snapshot: ProfileSnapshot, role: JobRole) -> ComponentResult:
    weight = role.weight_experience
    expected = min(max(role.expected_internships, 1), MAX_SCORED_SLOTS)
    role_skill_names = {
        word
        for r in role.required_skills
        for word in _WORD_SPLIT_RE.split(r.skill.name.lower())
        if len(word) > 2
    }

    work = snapshot.work_experiences
    responsibilities = snapshot.responsibility_experiences

    if not work and not responsibilities:
        return ComponentResult(
            "experience",
            weight,
            0.0,
            "No internships, jobs or positions of responsibility on file. "
            "Experience is optional, so this weight has been moved to the "
            "evidence you do have rather than scored as a zero.",
            {
                "internships": 0,
                "jobs": 0,
                "positions_of_responsibility": 0,
                "expected_internships": expected,
            },
            applicable=False,
        )

    scored: list[dict[str, Any]] = []
    for item in work:
        quality, relevance, depth = _experience_quality(item, role, role_skill_names)
        scored.append(
            {
                "id": item.id,
                "title": item.title,
                "organization": item.organization,
                "type": item.experience_type,
                "relevance": round(relevance, 3),
                "depth": round(depth, 3),
                "quality": round(quality, 3),
                "months": item.duration_months,
            }
        )
    for item in responsibilities:
        quality, relevance, depth = _experience_quality(item, role, role_skill_names)
        scored.append(
            {
                "id": item.id,
                "title": item.title,
                "organization": item.organization,
                "type": item.experience_type,
                "relevance": round(relevance, 3),
                "depth": round(depth, 3),
                # A position of responsibility is real, but it is not the same
                # evidence an employer-supervised role gives.
                "quality": round(quality * POR_CREDIT, 3),
                "months": item.duration_months,
            }
        )

    scored.sort(key=lambda item: item["quality"], reverse=True)
    top = scored[:expected]
    quality_ratio = _mean([item["quality"] for item in top])
    breadth = min(len(scored) / expected, 1.0)
    ratio = quality_ratio * (0.85 + 0.15 * breadth)

    relevant = sum(1 for item in scored if item["relevance"] >= 0.5)
    por_count = len(responsibilities)
    explanation = (
        f"{snapshot.internship_count} internship(s), {snapshot.job_count} job(s) and "
        f"{por_count} position(s) of responsibility, about "
        f"{snapshot.total_experience_months} month(s) of hands-on work; {relevant} "
        f"judged relevant to this role. Scored on your {min(len(scored), expected)} "
        "strongest entr(ies) - depth and measurable outcomes, not entry count. "
        f"Positions of responsibility count at {int(POR_CREDIT * 100)}% of a role."
    )

    return ComponentResult(
        "experience",
        weight,
        round(min(ratio, 1.0), 4),
        explanation,
        {
            "internships": snapshot.internship_count,
            "jobs": snapshot.job_count,
            "positions_of_responsibility": por_count,
            "total_months": snapshot.total_experience_months,
            "relevant_count": relevant,
            "expected_internships": expected,
            "entries": scored[:8],
            "quality_ratio": round(quality_ratio, 3),
            "work_experience_present": bool(work),
        },
    )


# --------------------------------------------------------------------------
# Certifications
# --------------------------------------------------------------------------
def _score_certifications(snapshot: ProfileSnapshot, role: JobRole) -> ComponentResult:
    weight = role.weight_certifications
    expected = max(role.expected_certifications, 1)
    count = len(snapshot.certifications)

    if count == 0:
        return ComponentResult(
            "certifications",
            weight,
            0.0,
            "No certifications on file. Certifications are optional, so this weight "
            "has been moved to the evidence you do have.",
            {"count": 0, "expected": expected, "relevant": 0},
            applicable=False,
        )

    relevant = 0
    for cert in snapshot.certifications:
        blob = (
            f"{cert.get('name', '')} {cert.get('issuer') or ''} "
            f"{' '.join(cert.get('related_skills') or [])}"
        )
        hits, _ = _keyword_hits(blob, role.resume_keywords or [])
        if hits:
            relevant += 1

    # Relevance first: three unrelated certificates are not worth one relevant
    # one, so the count only tops up a genuinely relevant set.
    relevance_ratio = relevant / count
    count_ratio = min(relevant / expected, 1.0) if relevant else 0.0
    ratio = 0.65 * relevance_ratio + 0.35 * count_ratio

    return ComponentResult(
        "certifications",
        weight,
        round(min(ratio, 1.0), 4),
        f"{count} certification(s), {relevant} relevant to this role "
        f"(this rubric expects about {expected}). Relevance matters more than count.",
        {"count": count, "expected": expected, "relevant": relevant},
    )


# --------------------------------------------------------------------------
# Academics
# --------------------------------------------------------------------------
def _score_academics(snapshot: ProfileSnapshot, role: JobRole) -> ComponentResult:
    weight = role.weight_academics
    floor = role.min_cgpa
    target = max(role.target_cgpa, floor + 0.1)

    # Sub-weights are renormalised over the parts the student actually
    # provided, so an omitted CGPA moves its share onto the record and
    # coursework instead of scoring zero or an arbitrary placeholder.
    parts: list[tuple[str, float, float]] = []

    if snapshot.cgpa_provided and snapshot.cgpa_on_10 is not None:
        cgpa = snapshot.cgpa_on_10
        if cgpa >= target:
            cgpa_ratio = 1.0
        elif cgpa >= floor:
            cgpa_ratio = 0.6 + 0.4 * (cgpa - floor) / (target - floor)
        else:
            cgpa_ratio = 0.6 * max(cgpa / floor, 0.0) if floor > 0 else 0.0
        parts.append(("cgpa", 0.70, min(cgpa_ratio, 1.0)))
    else:
        cgpa_ratio = None

    record_signals = [
        1.0 if snapshot.education else 0.0,
        1.0 if any(e.degree for e in snapshot.education) else 0.0,
        1.0 if any(e.has_years for e in snapshot.education) else 0.0,
        1.0 if len(snapshot.education) >= 2 else 0.0,
    ]
    parts.append(("record", 0.15, _mean(record_signals)))

    if snapshot.coursework or snapshot.academic_achievements:
        enrichment = _mean(
            [
                min(len(snapshot.coursework) / 4.0, 1.0),
                min(snapshot.academic_achievements / 1.0, 1.0),
            ]
        )
        parts.append(("enrichment", 0.15, enrichment))

    total_weight = sum(part[1] for part in parts)
    ratio = sum(part[1] * part[2] for part in parts) / total_weight if total_weight else 0.0

    if cgpa_ratio is None:
        explanation = (
            "CGPA was not provided, so it is left out of this component entirely "
            "and its share is carried by your education record and coursework - "
            "no placeholder, no penalty. Add your CGPA for a sharper score."
        )
    else:
        explanation = (
            f"CGPA {snapshot.cgpa_on_10}/10 against this role's floor of {floor} and "
            f"target of {target}. {len(snapshot.education)} education record(s), "
            f"{len(snapshot.coursework)} relevant course(s) and "
            f"{snapshot.academic_achievements} academic achievement entr(ies)."
        )

    return ComponentResult(
        "academics",
        weight,
        round(min(ratio, 1.0), 4),
        explanation,
        {
            "cgpa_provided": cgpa_ratio is not None,
            "cgpa_on_10": snapshot.cgpa_on_10,
            "min_cgpa": floor,
            "target_cgpa": target,
            "cgpa_ratio": round(cgpa_ratio, 3) if cgpa_ratio is not None else None,
            "coursework_count": len(snapshot.coursework),
            "education_records": len(snapshot.education),
            "academic_achievements": snapshot.academic_achievements,
            "sub_weights": {name: round(w / total_weight, 3) for name, w, _ in parts},
        },
    )


# --------------------------------------------------------------------------
# Domain knowledge
# --------------------------------------------------------------------------
def _distinct_keywords(role: JobRole) -> list[str]:
    """Role keywords that the skills rubric does not already test.

    "machine learning" is both a rubric skill and a domain keyword; counting
    it in both components would score the same fact twice.
    """
    skill_text = " ".join(
        [r.skill.name.lower() for r in role.required_skills]
        + [alias.lower() for r in role.required_skills for alias in (r.skill.aliases or [])]
    )
    out: list[str] = []
    for keyword in role.resume_keywords or []:
        lowered = keyword.lower()
        if lowered in skill_text:
            continue
        out.append(keyword)
    return out


def _score_domain_knowledge(snapshot: ProfileSnapshot, role: JobRole) -> ComponentResult:
    weight = role.weight_domain_knowledge
    keywords = _distinct_keywords(role)
    total_keywords = len(role.resume_keywords or [])

    if not keywords:
        return ComponentResult(
            "domain_knowledge",
            weight,
            0.0,
            "Every domain concept for this role is already covered by its skills "
            "rubric, so this component is not scored separately and its weight "
            "moves to the skills match.",
            {"configured": False, "overlapping_with_skills": total_keywords},
            applicable=False,
        )

    corpus = snapshot.searchable_text + " " + snapshot.resume_text.lower()
    hits, misses = _keyword_hits(corpus, keywords)
    ratio = len(hits) / len(keywords)

    return ComponentResult(
        "domain_knowledge",
        weight,
        round(min(ratio, 1.0), 4),
        f"Your profile and resume mention {len(hits)} of {len(keywords)} domain "
        f"concepts that this role's skills rubric does not already test"
        + (f". Missing: {', '.join(misses[:6])}." if misses else "."),
        {
            "hits": hits,
            "missing": misses,
            "total": len(keywords),
            "excluded_as_rubric_skills": total_keywords - len(keywords),
        },
    )


# --------------------------------------------------------------------------
# Resume quality
# --------------------------------------------------------------------------
def _score_resume_quality(snapshot: ProfileSnapshot, role: JobRole) -> ComponentResult:
    weight = role.weight_resume_quality

    if not snapshot.resume_present or snapshot.resume_quality is None:
        return ComponentResult(
            "resume_quality",
            weight,
            0.0,
            "A resume is required for the readiness assessment and none has been "
            f"read yet. Uploading one puts {round(weight, 1)} points in play.",
            {"has_resume": False, "points_available": round(weight, 1)},
        )

    ratio = max(0.0, min(snapshot.resume_quality / 100.0, 1.0))
    keywords = role.resume_keywords or []
    hits, misses = _keyword_hits(snapshot.resume_text, keywords)

    return ComponentResult(
        "resume_quality",
        weight,
        round(ratio, 4),
        f"Resume quality score {snapshot.resume_quality}/100. It mentions {len(hits)} of "
        f"{len(keywords)} role keywords.",
        {
            "has_resume": True,
            "quality_score": snapshot.resume_quality,
            "keyword_hits": hits,
            "keyword_misses": misses,
        },
    )


# --------------------------------------------------------------------------
# Weight redistribution
# --------------------------------------------------------------------------
def _combine_evidence(
    components: dict[str, ComponentResult],
) -> tuple[dict[str, float], dict[str, Any]]:
    """Decide the effective weight of each evidence component.

    Every optional section the student does not have gives its weight to the
    sections they do have. Beyond that, one weak optional kind may be ignored
    if doing so produces a better pool ratio, which is what guarantees that
    adding a modest entry can never cost points.

    Returns ``(effective_weights, detail)``. The caller keeps each component's
    own ratio; only the weights move.
    """
    present = [key for key in EVIDENCE_COMPONENTS if components[key].applicable]
    absent = [key for key in EVIDENCE_COMPONENTS if not components[key].applicable]
    pool_weight = sum(components[key].weight for key in EVIDENCE_COMPONENTS)

    if not present:
        # Nothing to show at all: the pool keeps its weight and scores zero.
        return (
            {key: components[key].weight for key in EVIDENCE_COMPONENTS},
            {
                "counted": [],
                "dropped_as_absent": absent,
                "ignored_as_weak": [],
                "single_source_cap_applied": False,
                "pool_weight": round(pool_weight, 2),
                "note": "No projects, experience or certifications on file.",
            },
        )

    def pool_ratio(subset: list[str]) -> float:
        base = sum(components[key].weight for key in subset)
        if base <= 0:
            return 0.0
        raw = sum(components[key].weight * components[key].ratio for key in subset) / base
        # One kind of evidence cannot stand in fully for every other kind.
        primary = [k for k in subset if k in ("projects", "experience")]
        return raw * SINGLE_SOURCE_CAP if len(primary) < 2 else raw

    # Candidate subsets: everything present, or everything present minus one
    # weak optional kind. Only one removal, so the strongest kind can never
    # simply replace the whole pool.
    candidates: list[list[str]] = [present]
    for key in present:
        if len(present) > 1 and components[key].ratio < WEAK_EVIDENCE_THRESHOLD:
            candidates.append([k for k in present if k != key])

    best = max(candidates, key=pool_ratio)
    ignored = [key for key in present if key not in best]

    base = sum(components[key].weight for key in best)
    weights = {key: 0.0 for key in EVIDENCE_COMPONENTS}
    for key in best:
        share = components[key].weight / base if base else 1 / len(best)
        weights[key] = pool_weight * share

    capped = len([k for k in best if k in ("projects", "experience")]) < 2

    detail = {
        "counted": best,
        "dropped_as_absent": absent,
        "ignored_as_weak": ignored,
        "single_source_cap_applied": capped,
        "pool_weight": round(pool_weight, 2),
        "pool_ratio": round(pool_ratio(best), 4),
    }
    return weights, detail


def _apply_weights(
    components: dict[str, ComponentResult],
) -> tuple[list[ComponentResult], dict[str, Any]]:
    """Set each component's effective weight, redistributing optional sections."""
    evidence_weights, evidence_detail = _combine_evidence(components)

    for key in EVIDENCE_COMPONENTS:
        component = components[key]
        new_weight = evidence_weights[key]
        if new_weight <= 0.001 and component.weight > 0:
            moved_to = ", ".join(
                COMPONENT_LABELS[k] for k in evidence_detail["counted"]
            ) or "the rest of the rubric"
            if key in evidence_detail["ignored_as_weak"]:
                component.explanation += (
                    f" This section scored below {int(WEAK_EVIDENCE_THRESHOLD * 100)}%, "
                    f"so its {round(component.weight, 1)} point(s) were moved to "
                    f"{moved_to} instead of pulling your score down."
                )
            else:
                component.explanation += (
                    f" Its {round(component.weight, 1)} point(s) moved to {moved_to}."
                )
        component.weight = round(new_weight, 2)

    # The single-source cap reduces the ratio, not the available points, so a
    # student can still see what the missing kind of evidence would be worth.
    if evidence_detail.get("single_source_cap_applied"):
        for key in evidence_detail["counted"]:
            components[key].ratio = round(components[key].ratio * SINGLE_SOURCE_CAP, 4)
            components[key].details["single_source_cap"] = SINGLE_SOURCE_CAP

    # Domain knowledge folds into skills when it has nothing distinct to test.
    domain = components["domain_knowledge"]
    if not domain.applicable and domain.weight > 0:
        components["skills"].weight = round(components["skills"].weight + domain.weight, 2)
        domain.weight = 0.0

    for key in EVIDENCE_COMPONENTS:
        components[key].details["weighting"] = evidence_detail

    return [components[key] for key in COMPONENT_ORDER], evidence_detail


# --------------------------------------------------------------------------
# Role scoring
# --------------------------------------------------------------------------
def score_role(snapshot: ProfileSnapshot, role: JobRole) -> RoleScoreResult:
    """Pure function: profile snapshot + role rubric -> explainable score."""
    skills_component, gaps = _score_skills(snapshot, role)
    components = {
        "skills": skills_component,
        "projects": _score_projects(snapshot, role),
        "academics": _score_academics(snapshot, role),
        "experience": _score_experience(snapshot, role),
        "certifications": _score_certifications(snapshot, role),
        "domain_knowledge": _score_domain_knowledge(snapshot, role),
        "resume_quality": _score_resume_quality(snapshot, role),
    }
    ordered, evidence_detail = _apply_weights(components)

    total_weight = sum(c.weight for c in ordered)
    earned = sum(c.points for c in ordered)
    # Normalise in case a rubric's weights do not sum to exactly 100.
    score = round(100 * earned / total_weight, 1) if total_weight else 0.0
    score = max(0.0, min(score, 100.0))

    strengths = _build_strengths(snapshot, role, components)
    improvements = _build_improvements(snapshot, role, components, gaps)
    insights = _build_role_insights(snapshot, role, components, score)

    return RoleScoreResult(
        role_id=role.id,
        role_slug=role.slug,
        role_name=role.name,
        score=score,
        band=band_for(score),
        components=ordered,
        gaps=gaps,
        strengths=strengths,
        improvements=improvements,
        insights=insights,
        match_summary={
            "required_total": skills_component.details.get("required_total", 0),
            "required_matched": skills_component.details.get("required_matched", 0),
            "rubric_skills": skills_component.details.get("rubric_total", 0),
            "evidence_backed_skills": skills_component.details.get("evidence_backed", 0),
            "relevant_projects": components["projects"].details.get("relevant_count", 0),
            "internships": snapshot.internship_count,
            "evidence_counted": evidence_detail.get("counted", []),
            "evidence_not_applicable": evidence_detail.get("dropped_as_absent", []),
            "points_earned": round(earned, 2),
            "points_possible": round(total_weight, 2),
            "engine_version": ENGINE_VERSION,
        },
    )


def _build_strengths(
    snapshot: ProfileSnapshot, role: JobRole, components: dict[str, ComponentResult]
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    for key in COMPONENT_ORDER:
        component = components[key]
        if component.ratio >= 0.7 and component.weight > 0:
            out.append(
                {
                    "type": "component",
                    "area": component.label,
                    "title": f"{component.label} is a strong point",
                    "detail": component.explanation,
                    "score_contribution": component.points,
                }
            )

    strong_skills = [
        m
        for m in components["skills"].details.get("matched", [])
        if m.get("evidence_backed") and m.get("credit_ratio", 0) >= 0.85
    ]
    if strong_skills:
        names = ", ".join(m["skill"] for m in strong_skills[:5])
        out.append(
            {
                "type": "skills",
                "area": "Evidence-backed skills",
                "title": f"{len(strong_skills)} skill(s) proven through your work",
                "detail": f"{names} appear in your projects or internships, not just your skill list.",
                "score_contribution": None,
            }
        )

    strong_projects = [
        p for p in components["projects"].details.get("projects", []) if p["quality"] >= 0.55
    ]
    if strong_projects:
        out.append(
            {
                "type": "projects",
                "area": "Relevant projects",
                "title": f"{len(strong_projects)} project(s) map onto this role",
                "detail": "Strongest: " + ", ".join(p["title"] for p in strong_projects[:3]),
                "score_contribution": None,
            }
        )

    if snapshot.internship_count:
        out.append(
            {
                "type": "experience",
                "area": "Experience",
                "title": f"{snapshot.internship_count} internship(s) on record",
                "detail": f"About {snapshot.total_experience_months} month(s) of hands-on exposure.",
                "score_contribution": None,
            }
        )

    if snapshot.cgpa_provided and snapshot.cgpa_on_10 and snapshot.cgpa_on_10 >= role.target_cgpa:
        out.append(
            {
                "type": "academics",
                "area": "Academics",
                "title": f"CGPA {snapshot.cgpa_on_10}/10 clears this role's target",
                "detail": f"This role targets {role.target_cgpa}/10.",
                "score_contribution": None,
            }
        )

    return out[:8]


def _build_improvements(
    snapshot: ProfileSnapshot,
    role: JobRole,
    components: dict[str, ComponentResult],
    gaps: list[GapRecord],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    missing_required = [
        g for g in gaps if g.status == "missing" and g.importance == "required"
    ]
    if missing_required:
        missing_required.sort(key=lambda g: g.points_lost, reverse=True)
        out.append(
            {
                "type": "missing_skills",
                "area": "Missing skills",
                "title": f"{len(missing_required)} required skill(s) missing",
                "detail": "Highest impact first: "
                + ", ".join(g.skill_name for g in missing_required[:5]),
                "points_at_stake": round(sum(g.points_lost for g in missing_required), 1),
            }
        )

    claimed_only = [g for g in gaps if g.status == "claimed_only"]
    if claimed_only:
        out.append(
            {
                "type": "unproven_skills",
                "area": "Unproven skills",
                "title": f"{len(claimed_only)} skill(s) claimed but not demonstrated",
                "detail": "Add a project or internship that uses "
                + ", ".join(g.skill_name for g in claimed_only[:5])
                + f". Claimed-only skills earn {int(CLAIM_ONLY_CREDIT * 100)}% credit.",
                "points_at_stake": round(sum(g.points_lost for g in claimed_only), 1),
            }
        )

    below = [g for g in gaps if g.status == "below_expected"]
    if below:
        out.append(
            {
                "type": "weak_proficiency",
                "area": "Proficiency depth",
                "title": f"{len(below)} skill(s) below the expected level",
                "detail": ", ".join(
                    f"{g.skill_name} ({g.student_proficiency} -> {g.expected_proficiency})"
                    for g in below[:5]
                ),
                "points_at_stake": round(sum(g.points_lost for g in below), 1),
            }
        )

    projects = components["projects"]
    if not projects.applicable:
        out.append(
            {
                "type": "projects",
                "area": "Projects",
                "title": "Adding a project would raise this score",
                "detail": "You are currently assessed without a project portfolio. "
                "One relevant, well-described project is the fastest way to turn "
                "listed skills into evidence.",
                "points_at_stake": round(
                    components["experience"].weight * 0.3 + components["skills"].weight * 0.1, 1
                ),
            }
        )
    elif projects.ratio < 0.6:
        out.append(
            {
                "type": "projects",
                "area": "Projects",
                "title": "Project portfolio is thin for this role",
                "detail": f"{projects.details.get('relevant_count', 0)} clearly relevant "
                f"project(s). {projects.explanation}",
                "points_at_stake": round(projects.weight - projects.points, 1),
            }
        )

    domain = components["domain_knowledge"]
    if domain.weight > 0 and domain.ratio < 0.6 and domain.details.get("missing"):
        out.append(
            {
                "type": "domain_knowledge",
                "area": "Domain knowledge",
                "title": "Core domain concepts are not visible in your profile",
                "detail": "Not mentioned anywhere: "
                + ", ".join(domain.details["missing"][:6]),
                "points_at_stake": round(domain.weight - domain.points, 1),
            }
        )

    experience = components["experience"]
    if not experience.applicable:
        out.append(
            {
                "type": "experience",
                "area": "Experience",
                "title": "An internship would strengthen this profile",
                "detail": "You are assessed on projects and skills rather than "
                "penalised for having no internship yet, but an internship is the "
                "evidence employers weigh most heavily.",
                "points_at_stake": round(components["projects"].weight * 0.25, 1),
            }
        )
    elif experience.ratio < 0.5:
        out.append(
            {
                "type": "experience",
                "area": "Experience",
                "title": "Experience entries need more detail",
                "detail": experience.explanation,
                "points_at_stake": round(experience.weight - experience.points, 1),
            }
        )

    resume = components["resume_quality"]
    if not resume.details.get("has_resume"):
        out.append(
            {
                "type": "resume",
                "area": "Resume",
                "title": "No resume uploaded",
                "detail": resume.explanation,
                "points_at_stake": round(resume.weight, 1),
            }
        )
    elif resume.ratio < 0.7:
        out.append(
            {
                "type": "resume",
                "area": "Resume",
                "title": "Resume quality can be improved",
                "detail": resume.explanation,
                "points_at_stake": round(resume.weight - resume.points, 1),
            }
        )

    certifications = components["certifications"]
    if certifications.weight > 0 and certifications.ratio < 0.5:
        out.append(
            {
                "type": "certifications",
                "area": "Certifications",
                "title": "A relevant certification would help",
                "detail": certifications.explanation,
                "points_at_stake": round(certifications.weight - certifications.points, 1),
            }
        )

    out.sort(key=lambda item: item.get("points_at_stake") or 0, reverse=True)
    return out[:8]


def _build_role_insights(
    snapshot: ProfileSnapshot,
    role: JobRole,
    components: dict[str, ComponentResult],
    score: float,
) -> list[dict[str, Any]]:
    insights: list[dict[str, Any]] = []
    scored = [components[key] for key in COMPONENT_ORDER if components[key].weight > 0]
    weakest = min(scored, key=lambda c: c.ratio, default=None)
    if weakest is not None:
        headroom = round(weakest.weight - weakest.points, 1)
        insights.append(
            {
                "kind": "biggest_lever",
                "title": f"Biggest lever: {weakest.label}",
                "body": f"{headroom} point(s) of this role's score are still available in "
                f"{weakest.label.lower()}. {weakest.explanation}",
                "severity": "high" if headroom >= 10 else "medium",
            }
        )

    not_applicable = [
        components[key].label for key in EVIDENCE_COMPONENTS if not components[key].applicable
    ]
    if not_applicable:
        insights.append(
            {
                "kind": "fair_assessment",
                "title": "Scored on what you have",
                "body": f"{', '.join(not_applicable)} are optional and you have none on "
                "file, so their weight was redistributed rather than scored as zero. "
                "Your score reflects the evidence you do have.",
                "severity": "low",
            }
        )

    if score >= 70:
        insights.append(
            {
                "kind": "positioning",
                "title": f"You are competitive for {role.name}",
                "body": f"A score of {score}/100 places you in the '{band_for(score)}' band "
                "for this role. Focus on depth, not breadth, from here.",
                "severity": "low",
            }
        )
    elif score < 45:
        insights.append(
            {
                "kind": "positioning",
                "title": f"{role.name} needs foundational work",
                "body": f"At {score}/100 the gap is structural rather than cosmetic - "
                "prioritise the required skills and one strong, relevant project.",
                "severity": "high",
            }
        )

    return insights


# --------------------------------------------------------------------------
# Persistence
# --------------------------------------------------------------------------
def roles_for_scoring(db: Session, user: User) -> list[JobRole]:
    """Every active role is scored so cross-domain comparison is possible."""
    return list(
        db.scalars(
            select(JobRole)
            .options(
                selectinload(JobRole.required_skills).selectinload(
                    RoleRequiredSkill.skill
                ),
                selectinload(JobRole.domain),
            )
            .where(JobRole.is_active.is_(True))
            .order_by(JobRole.display_order, JobRole.id)
        )
    )


def recalculate_assessments(
    db: Session,
    user: User,
    *,
    role_ids: list[int] | None = None,
    reason: str = "profile_update",
) -> list[RoleScoreResult]:
    """Rescore the requested roles (all active roles by default) and persist.

    Previous rows are kept as snapshots; only the newest per role is current.
    """
    snapshot = build_snapshot(db, user)
    roles = roles_for_scoring(db, user)
    if role_ids is not None:
        wanted = set(role_ids)
        roles = [role for role in roles if role.id in wanted]
    if not roles:
        return []

    now = dt.datetime.now(dt.timezone.utc)
    results: list[RoleScoreResult] = []

    for role in roles:
        result = score_role(snapshot, role)
        results.append(result)

        previous = db.scalar(
            select(RoleAssessment)
            .where(
                RoleAssessment.user_id == user.id,
                RoleAssessment.role_id == role.id,
                RoleAssessment.is_current.is_(True),
            )
            .order_by(RoleAssessment.computed_at.desc())
        )

        version = 1
        previous_score: float | None = None
        if previous is not None:
            previous.is_current = False
            previous_score = previous.overall_score
            version = previous.version + 1

        assessment = RoleAssessment(
            user_id=user.id,
            role_id=role.id,
            overall_score=result.score,
            readiness_band=result.band,
            previous_score=previous_score,
            score_delta=(
                round(result.score - previous_score, 1) if previous_score is not None else None
            ),
            is_current=True,
            version=version,
            engine_version=ENGINE_VERSION,
            trigger_reason=reason,
            strengths=result.strengths,
            improvements=result.improvements,
            insights=result.insights,
            match_summary=result.match_summary,
            ai_enriched=False,
            computed_at=now,
        )
        db.add(assessment)
        db.flush()

        for order, component in enumerate(result.components):
            db.add(
                AssessmentScoreBreakdown(
                    assessment_id=assessment.id,
                    component=component.component,
                    label=component.label,
                    weight=round(component.weight, 2),
                    raw_ratio=component.ratio,
                    points_earned=component.points,
                    points_possible=round(component.weight, 2),
                    explanation=component.explanation,
                    details=component.details,
                    display_order=order,
                )
            )

        # Replace this role's gap rows with the fresh set.
        for old_gap in db.scalars(
            select(SkillGapAnalysis).where(
                SkillGapAnalysis.user_id == user.id, SkillGapAnalysis.role_id == role.id
            )
        ):
            db.delete(old_gap)
        db.flush()

        for gap in result.gaps:
            db.add(
                SkillGapAnalysis(
                    user_id=user.id,
                    role_id=role.id,
                    assessment_id=assessment.id,
                    skill_id=gap.skill_id,
                    skill_name=gap.skill_name,
                    status=gap.status,
                    importance=gap.importance,
                    expected_proficiency=gap.expected_proficiency,
                    student_proficiency=gap.student_proficiency,
                    is_evidence_backed=gap.is_evidence_backed,
                    points_lost=gap.points_lost,
                    recommendation=gap.recommendation or None,
                )
            )

    db.flush()
    logger.info(
        "Scored %s role(s) for user=%s reason=%s engine=%s",
        len(results),
        user.id,
        reason,
        ENGINE_VERSION,
    )
    return results


def preferred_role_ids(db: Session, user: User) -> list[int]:
    return list(
        db.scalars(
            select(StudentCareerPreference.role_id)
            .where(StudentCareerPreference.user_id == user.id)
            .order_by(StudentCareerPreference.priority)
        )
    )
