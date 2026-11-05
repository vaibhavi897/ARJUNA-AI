"""Role-based career readiness scoring engine.

Design rules this module enforces:

* One rubric per role. Weights, expectations and keywords come from the
  ``job_roles`` / ``role_required_skills`` rows, never from hardcoded formulas.
* Nothing is random. The same profile and the same rubric always produce the
  same score.
* Every point is attributable: each component returns an explanation plus the
  raw details behind it, and these are persisted so the score stays explainable
  after the fact.
* A claimed skill earns less than a skill demonstrated in a project or
  internship (see ``CLAIM_ONLY_CREDIT``).
* Missing optional information is handled explicitly. Where absence cannot be
  judged fairly, the component returns a neutral ratio and says so, rather than
  silently scoring zero.

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

ENGINE_VERSION = "1.0.0"

# A skill the student claims but has not demonstrated earns this share of the
# points an evidence-backed skill of the same proficiency would earn.
CLAIM_ONLY_CREDIT = 0.55
# Importance multipliers applied on top of each requirement's own weight.
IMPORTANCE_MULTIPLIER = {"required": 1.0, "preferred": 0.45}

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

_WORD = re.compile(r"[a-z0-9+#.]+")


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


@dataclass(slots=True)
class ExperienceFact:
    id: int
    experience_type: str
    organization: str
    title: str
    description: str
    duration_months: int
    skills_used: list[str]


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
        parts += [p.title + " " + p.description + " " + p.contribution for p in self.projects]
        parts += [" ".join(p.tech_names) for p in self.projects]
        parts += [
            f"{e.title} {e.organization} {e.description} {' '.join(e.skills_used)}"
            for e in self.experiences
        ]
        parts += [str(c.get("name", "")) for c in self.certifications]
        parts += [str(a.get("title", "")) for a in self.achievements]
        parts += self.coursework
        self.searchable_text = " ".join(parts).lower()

    @property
    def internship_count(self) -> int:
        return sum(1 for e in self.experiences if e.experience_type == "internship")

    @property
    def job_count(self) -> int:
        return sum(1 for e in self.experiences if e.experience_type == "job")

    @property
    def total_experience_months(self) -> int:
        return sum(
            e.duration_months
            for e in self.experiences
            if e.experience_type in ("internship", "job")
        )


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

    coursework: list[str] = []
    academic_achievements = 0
    for row in db.scalars(select(AcademicDetail).where(AcademicDetail.user_id == user.id)):
        coursework.extend(row.relevant_coursework or [])
        if row.achievements:
            academic_achievements += 1

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
    for keyword in keywords:
        if keyword.lower() in text:
            hits.append(keyword)
        else:
            misses.append(keyword)
    return hits, misses


# --------------------------------------------------------------------------
# Components
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
                        + (" - it is a core requirement for this role." if requirement.importance == "required" else ".")
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


def _project_relevance(project: ProjectFact, role: JobRole, role_skill_ids: set[int]) -> float:
    """0..1 relevance of one project to one role."""
    score = 0.0
    if role_skill_ids and project.skill_ids:
        overlap = len(project.skill_ids & role_skill_ids)
        score += min(overlap / 2, 1.0) * 0.6
    categories = [c.lower() for c in (role.relevant_project_categories or [])]
    if project.category and any(c in project.category.lower() for c in categories):
        score += 0.25
    blob = f"{project.title} {project.description} {project.contribution} {' '.join(project.tech_names)}".lower()
    hits, _ = _keyword_hits(blob, role.resume_keywords or [])
    if hits:
        score += min(len(hits) / 3, 1.0) * 0.3
    return min(score, 1.0)


def _score_projects(snapshot: ProfileSnapshot, role: JobRole) -> ComponentResult:
    weight = role.weight_projects
    role_skill_ids = {r.skill_id for r in role.required_skills}
    expected = max(role.expected_projects, 1)

    if not snapshot.projects:
        return ComponentResult(
            "projects",
            weight,
            0.0,
            f"No projects added yet. This role expects about {expected} relevant "
            "project(s) as practical evidence.",
            {"count": 0, "expected": expected, "relevant": []},
        )

    scored = []
    for project in snapshot.projects:
        relevance = _project_relevance(project, role, role_skill_ids)
        depth_signals = [
            len(project.description) >= 120,
            bool(project.contribution),
            project.has_link,
            bool(project.tech_names),
        ]
        depth = sum(1 for s in depth_signals if s) / len(depth_signals)
        scored.append(
            {
                "id": project.id,
                "title": project.title,
                "relevance": round(relevance, 3),
                "depth": round(depth, 3),
                "category": project.category,
            }
        )

    scored.sort(key=lambda item: item["relevance"], reverse=True)
    top = scored[:expected]
    relevance_ratio = sum(item["relevance"] for item in top) / expected
    depth_ratio = sum(item["depth"] for item in top) / max(len(top), 1)
    coverage_ratio = min(len(snapshot.projects) / expected, 1.0)

    ratio = 0.55 * min(relevance_ratio, 1.0) + 0.25 * coverage_ratio + 0.20 * depth_ratio
    strongly_relevant = [item for item in scored if item["relevance"] >= 0.5]

    explanation = (
        f"{len(snapshot.projects)} project(s) on file, {len(strongly_relevant)} clearly "
        f"relevant to this role (expected: {expected}). Relevance is judged on the "
        "technologies used, project category and role keywords; depth on description, "
        "stated contribution and links."
    )

    return ComponentResult(
        "projects",
        weight,
        round(min(ratio, 1.0), 4),
        explanation,
        {
            "count": len(snapshot.projects),
            "expected": expected,
            "relevant_count": len(strongly_relevant),
            "projects": scored[:8],
            "relevance_ratio": round(min(relevance_ratio, 1.0), 3),
            "depth_ratio": round(depth_ratio, 3),
        },
    )


def _score_academics(snapshot: ProfileSnapshot, role: JobRole) -> ComponentResult:
    weight = role.weight_academics
    floor = role.min_cgpa
    target = max(role.target_cgpa, floor + 0.1)

    if not snapshot.cgpa_provided or snapshot.cgpa_on_10 is None:
        # CGPA is optional at onboarding. Absence is reported, not punished.
        return ComponentResult(
            "academics",
            weight,
            0.5,
            "CGPA was not provided, so this component uses a neutral 50% placeholder "
            "rather than a penalty. Add your CGPA for an accurate score.",
            {"cgpa_provided": False, "min_cgpa": floor, "target_cgpa": target},
        )

    cgpa = snapshot.cgpa_on_10
    if cgpa >= target:
        cgpa_ratio = 1.0
    elif cgpa >= floor:
        cgpa_ratio = 0.6 + 0.4 * (cgpa - floor) / (target - floor)
    else:
        # Below the role's floor still earns partial credit proportionally.
        cgpa_ratio = 0.6 * max(cgpa / floor, 0.0) if floor > 0 else 0.0

    achievement_ratio = min(snapshot.academic_achievements / 1, 1.0)
    coursework_ratio = min(len(snapshot.coursework) / 4, 1.0)
    ratio = 0.75 * cgpa_ratio + 0.15 * achievement_ratio + 0.10 * coursework_ratio

    explanation = (
        f"CGPA {cgpa}/10 against this role's floor of {floor} and target of {target}. "
        f"{snapshot.academic_achievements} academic achievement entr(ies) and "
        f"{len(snapshot.coursework)} relevant course(s) recorded."
    )

    return ComponentResult(
        "academics",
        weight,
        round(min(ratio, 1.0), 4),
        explanation,
        {
            "cgpa_provided": True,
            "cgpa_on_10": cgpa,
            "min_cgpa": floor,
            "target_cgpa": target,
            "cgpa_ratio": round(cgpa_ratio, 3),
            "coursework_count": len(snapshot.coursework),
            "academic_achievements": snapshot.academic_achievements,
        },
    )


def _score_experience(snapshot: ProfileSnapshot, role: JobRole) -> ComponentResult:
    weight = role.weight_experience
    expected = max(role.expected_internships, 1)
    expected_months = expected * 2

    relevant = 0
    relevance_scores: list[float] = []
    for exp in snapshot.experiences:
        if exp.experience_type not in ("internship", "job"):
            continue
        blob = f"{exp.title} {exp.organization} {exp.description} {' '.join(exp.skills_used)}".lower()
        hits, _ = _keyword_hits(blob, role.resume_keywords or [])
        relevance = min(len(hits) / 2, 1.0) if role.resume_keywords else 0.5
        relevance_scores.append(relevance)
        if relevance >= 0.5:
            relevant += 1

    count = snapshot.internship_count + snapshot.job_count
    por_count = sum(
        1 for e in snapshot.experiences if e.experience_type == "position_of_responsibility"
    )

    if count == 0:
        ratio = 0.08 * min(por_count, 2) / 2  # leadership alone is a weak signal
        explanation = (
            "No internships or work experience recorded. This role typically expects "
            f"{expected} internship(s). "
            + (
                f"{por_count} position(s) of responsibility give a small amount of credit."
                if por_count
                else ""
            )
        )
    else:
        count_ratio = min(count / expected, 1.0)
        duration_ratio = min(snapshot.total_experience_months / expected_months, 1.0)
        relevance_ratio = (
            sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.0
        )
        por_ratio = min(por_count / 2, 1.0)
        ratio = (
            0.40 * count_ratio
            + 0.25 * duration_ratio
            + 0.25 * relevance_ratio
            + 0.10 * por_ratio
        )
        explanation = (
            f"{snapshot.internship_count} internship(s) and {snapshot.job_count} role(s) "
            f"totalling about {snapshot.total_experience_months} month(s); {relevant} judged "
            f"relevant to this role. Expected: {expected} internship(s) "
            f"(~{expected_months} months)."
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
        },
    )


def _score_certifications(snapshot: ProfileSnapshot, role: JobRole) -> ComponentResult:
    weight = role.weight_certifications
    expected = max(role.expected_certifications, 1)
    count = len(snapshot.certifications)

    relevant = 0
    for cert in snapshot.certifications:
        blob = f"{cert.get('name', '')} {cert.get('issuer') or ''} {' '.join(cert.get('related_skills') or [])}".lower()
        hits, _ = _keyword_hits(blob, role.resume_keywords or [])
        if hits:
            relevant += 1

    if count == 0:
        return ComponentResult(
            "certifications",
            weight,
            0.0,
            f"No certifications recorded. This role's rubric expects about {expected}; "
            "a relevant certification is the quickest way to earn these points.",
            {"count": 0, "expected": expected, "relevant": 0},
        )

    count_ratio = min(count / expected, 1.0)
    relevance_ratio = relevant / count
    ratio = 0.6 * count_ratio + 0.4 * relevance_ratio

    return ComponentResult(
        "certifications",
        weight,
        round(min(ratio, 1.0), 4),
        f"{count} certification(s), {relevant} relevant to this role (expected: {expected}).",
        {"count": count, "expected": expected, "relevant": relevant},
    )


def _score_domain_knowledge(snapshot: ProfileSnapshot, role: JobRole) -> ComponentResult:
    weight = role.weight_domain_knowledge
    keywords = role.resume_keywords or []

    if not keywords:
        return ComponentResult(
            "domain_knowledge",
            weight,
            0.5,
            "No domain keyword list is configured for this role, so a neutral score is used.",
            {"configured": False},
        )

    corpus = snapshot.searchable_text + " " + snapshot.resume_text.lower()
    hits, misses = _keyword_hits(corpus, keywords)
    ratio = len(hits) / len(keywords)

    return ComponentResult(
        "domain_knowledge",
        weight,
        round(min(ratio, 1.0), 4),
        f"Your profile mentions {len(hits)} of {len(keywords)} domain concepts for this "
        f"role. Missing concepts: {', '.join(misses[:6]) if misses else 'none'}.",
        {"hits": hits, "missing": misses, "total": len(keywords)},
    )


def _score_resume_quality(snapshot: ProfileSnapshot, role: JobRole) -> ComponentResult:
    weight = role.weight_resume_quality

    if not snapshot.resume_present or snapshot.resume_quality is None:
        return ComponentResult(
            "resume_quality",
            weight,
            0.0,
            "Resume quality cannot be assessed until a readable resume is uploaded. "
            f"Uploading one puts {round(weight, 1)} points in play.",
            {"has_resume": False, "points_available": round(weight, 1)},
        )

    ratio = max(0.0, min(snapshot.resume_quality / 100.0, 1.0))
    keywords = role.resume_keywords or []
    hits, misses = _keyword_hits(snapshot.resume_text.lower(), keywords)

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


COMPONENT_ORDER = (
    "skills",
    "projects",
    "experience",
    "academics",
    "domain_knowledge",
    "certifications",
    "resume_quality",
)


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
    ordered = [components[key] for key in COMPONENT_ORDER]

    total_weight = sum(c.weight for c in ordered)
    earned = sum(c.points for c in ordered)
    # Normalise in case a rubric's weights do not sum to exactly 100.
    score = round(100 * earned / total_weight, 1) if total_weight else 0.0
    score = max(0.0, min(score, 100.0))

    strengths = _build_strengths(snapshot, role, components)
    improvements = _build_improvements(snapshot, role, components, gaps)
    insights = _build_role_insights(snapshot, role, components, score)

    required_total = skills_component.details.get("required_total", 0)
    required_matched = skills_component.details.get("required_matched", 0)

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
            "required_total": required_total,
            "required_matched": required_matched,
            "rubric_skills": skills_component.details.get("rubric_total", 0),
            "evidence_backed_skills": skills_component.details.get("evidence_backed", 0),
            "relevant_projects": components["projects"].details.get("relevant_count", 0),
            "internships": snapshot.internship_count,
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

    relevant_projects = [
        p for p in components["projects"].details.get("projects", []) if p["relevance"] >= 0.5
    ]
    if relevant_projects:
        out.append(
            {
                "type": "projects",
                "area": "Relevant projects",
                "title": f"{len(relevant_projects)} project(s) map onto this role",
                "detail": "Most relevant: "
                + ", ".join(p["title"] for p in relevant_projects[:3]),
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
    if projects.ratio < 0.6:
        expected = projects.details.get("expected", 2)
        out.append(
            {
                "type": "projects",
                "area": "Projects",
                "title": "Project portfolio is thin for this role",
                "detail": f"{projects.details.get('relevant_count', 0)} clearly relevant "
                f"project(s) against an expectation of {expected}. {projects.explanation}",
                "points_at_stake": round(projects.weight - projects.points, 1),
            }
        )

    domain = components["domain_knowledge"]
    if domain.ratio < 0.6 and domain.details.get("missing"):
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
    if experience.ratio < 0.5:
        out.append(
            {
                "type": "experience",
                "area": "Experience",
                "title": "Limited internship or work exposure",
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
    if certifications.ratio < 0.5:
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
    weakest = min(
        (components[key] for key in COMPONENT_ORDER if components[key].weight > 0),
        key=lambda c: c.ratio,
        default=None,
    )
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
            # Identical score and inputs: refresh the timestamp instead of
            # writing a duplicate snapshot row.
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
