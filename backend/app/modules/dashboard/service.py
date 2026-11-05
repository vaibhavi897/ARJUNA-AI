"""Dashboard assembly. Every number here is read from the student's own rows."""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Achievement,
    AssessmentScoreBreakdown,
    Certification,
    Experience,
    ImprovementRoadmap,
    JobRole,
    Project,
    Resume,
    RoadmapTask,
    RoleAssessment,
    RoleRequiredSkill,
    SkillGapAnalysis,
    StudentActivityLog,
    StudentCareerPreference,
    StudentProfile,
    StudentSkill,
    User,
)
from app.modules.insights import ai_mode, build_ai_insights, build_greeting
from app.modules.profile.service import compute_profile_completion, get_or_create_profile
from app.modules.resume.quality import missing_role_keywords
from app.modules.scoring.engine import band_for
from app.modules.scoring.roadmap import roadmap_payload

TECHNICAL_CATEGORIES = {"programming", "data_ai", "cloud_devops", "cs_fundamentals"}
BUSINESS_CATEGORIES = {"finance", "business"}
CATEGORY_LABELS = {
    "programming": "Programming",
    "data_ai": "Data & AI",
    "cloud_devops": "Cloud & DevOps",
    "cs_fundamentals": "CS Fundamentals",
    "finance": "Finance",
    "business": "Business & Strategy",
    "tools": "Tools & Platforms",
    "soft_skills": "Soft Skills",
    "other": "Other",
}
PROFICIENCY_SCORE = {"beginner": 40, "intermediate": 70, "advanced": 100}


# --------------------------------------------------------------------------
# Assessment reads
# --------------------------------------------------------------------------
def current_assessments(db: Session, user_id: int) -> list[RoleAssessment]:
    return list(
        db.scalars(
            select(RoleAssessment)
            .options(
                selectinload(RoleAssessment.role).selectinload(JobRole.domain),
            )
            .where(
                RoleAssessment.user_id == user_id,
                RoleAssessment.is_current.is_(True),
            )
            .order_by(RoleAssessment.overall_score.desc())
        )
    )


def _preference_map(db: Session, user_id: int) -> dict[int, StudentCareerPreference]:
    return {
        row.role_id: row
        for row in db.scalars(
            select(StudentCareerPreference).where(StudentCareerPreference.user_id == user_id)
        )
    }


def _role_score_rows(
    assessments: list[RoleAssessment], preferences: dict[int, StudentCareerPreference]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for assessment in assessments:
        role = assessment.role
        preference = preferences.get(role.id)
        rows.append(
            {
                "role_id": role.id,
                "role_slug": role.slug,
                "role_name": role.name,
                "short_label": role.short_label,
                "domain_id": role.domain_id,
                "domain_name": role.domain.name,
                "domain_slug": role.domain.slug,
                "accent_color": role.domain.accent_color,
                "score": assessment.overall_score,
                "band": assessment.readiness_band,
                "previous_score": assessment.previous_score,
                "score_delta": assessment.score_delta,
                "is_preferred": preference is not None,
                "is_primary": bool(preference and preference.is_primary),
                "computed_at": assessment.computed_at,
                "matched_required": assessment.match_summary.get("required_matched", 0),
                "total_required": assessment.match_summary.get("required_total", 0),
                "engine_version": assessment.engine_version,
                "ai_enriched": assessment.ai_enriched,
            }
        )
    return rows


def _domain_averages(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[row["domain_slug"]].append(row)
    out = []
    for slug, items in buckets.items():
        scores = [item["score"] for item in items]
        out.append(
            {
                "domain_slug": slug,
                "domain_name": items[0]["domain_name"],
                "accent_color": items[0]["accent_color"],
                "average_score": round(sum(scores) / len(scores), 1),
                "best_score": max(scores),
                "role_count": len(items),
                "best_role": max(items, key=lambda i: i["score"])["role_name"],
            }
        )
    out.sort(key=lambda item: item["average_score"], reverse=True)
    return out


# --------------------------------------------------------------------------
# Sections
# --------------------------------------------------------------------------
def _skill_analysis(
    db: Session, user_id: int, focus_role_id: int | None
) -> dict[str, Any]:
    rows = list(
        db.scalars(
            select(StudentSkill)
            .options(selectinload(StudentSkill.skill))
            .where(StudentSkill.user_id == user_id)
        )
    )

    by_category: dict[str, dict[str, Any]] = {}
    by_proficiency: dict[str, int] = {"beginner": 0, "intermediate": 0, "advanced": 0}
    category_scores: dict[str, list[int]] = defaultdict(list)

    for row in rows:
        category = row.skill.category
        entry = by_category.setdefault(
            category,
            {
                "category": category,
                "label": CATEGORY_LABELS.get(category, category.title()),
                "count": 0,
                "evidence_backed": 0,
                "skills": [],
            },
        )
        entry["count"] += 1
        if row.is_evidence_backed:
            entry["evidence_backed"] += 1
        entry["skills"].append(
            {
                "name": row.skill.name,
                "proficiency": row.proficiency,
                "evidence_count": row.evidence_count,
                "is_evidence_backed": row.is_evidence_backed,
            }
        )
        by_proficiency[row.proficiency] = by_proficiency.get(row.proficiency, 0) + 1
        category_scores[category].append(PROFICIENCY_SCORE.get(row.proficiency, 40))

    technical = sum(
        entry["count"] for cat, entry in by_category.items() if cat in TECHNICAL_CATEGORIES
    )
    business = sum(
        entry["count"] for cat, entry in by_category.items() if cat in BUSINESS_CATEGORIES
    )
    other = len(rows) - technical - business

    radar = [
        {
            "category": category,
            "label": CATEGORY_LABELS.get(category, category.title()),
            "value": round(sum(scores) / len(scores)),
            "count": len(scores),
        }
        for category, scores in sorted(category_scores.items())
    ]

    role_gaps: list[dict[str, Any]] = []
    if focus_role_id:
        for gap in db.scalars(
            select(SkillGapAnalysis)
            .where(
                SkillGapAnalysis.user_id == user_id,
                SkillGapAnalysis.role_id == focus_role_id,
            )
            .order_by(SkillGapAnalysis.points_lost.desc())
            .limit(12)
        ):
            role_gaps.append(
                {
                    "skill_name": gap.skill_name,
                    "status": gap.status,
                    "importance": gap.importance,
                    "expected_proficiency": gap.expected_proficiency,
                    "student_proficiency": gap.student_proficiency,
                    "points_lost": gap.points_lost,
                    "recommendation": gap.recommendation,
                }
            )

    top_skills = sorted(
        (
            {
                "name": row.skill.name,
                "category": row.skill.category,
                "proficiency": row.proficiency,
                "evidence_count": row.evidence_count,
                "score": PROFICIENCY_SCORE.get(row.proficiency, 40)
                + min(row.evidence_count, 3) * 5,
            }
            for row in rows
        ),
        key=lambda item: item["score"],
        reverse=True,
    )[:10]

    return {
        "total_skills": len(rows),
        "evidence_backed": sum(1 for row in rows if row.is_evidence_backed),
        "claimed_only": sum(1 for row in rows if not row.is_evidence_backed),
        "by_category": sorted(
            by_category.values(), key=lambda item: item["count"], reverse=True
        ),
        "by_proficiency": [
            {"level": level, "count": count} for level, count in by_proficiency.items()
        ],
        "technical_vs_business": [
            {"label": "Technical", "count": technical},
            {"label": "Finance & Business", "count": business},
            {"label": "Tools & Soft Skills", "count": max(other, 0)},
        ],
        "top_skills": top_skills,
        "radar": radar,
        "role_gaps": role_gaps,
    }


def _resume_insights(
    db: Session, user_id: int, focus_role: JobRole | None
) -> dict[str, Any]:
    resume = db.scalar(
        select(Resume)
        .where(Resume.user_id == user_id, Resume.is_active.is_(True))
        .order_by(Resume.uploaded_at.desc())
    )
    if resume is None:
        return {
            "has_resume": False,
            "resume": None,
            "quality_score": None,
            "strengths": [],
            "improvements": [
                "Upload a PDF or DOCX resume to unlock keyword and quality analysis."
            ],
            "missing_keywords": [],
            "identified_skills": [],
            "sections_found": [],
            "sections_missing": [],
            "word_count": None,
            "parse_status": None,
        }

    report = resume.quality_report or {}
    parsed = resume.parsed_data or {}
    keywords = missing_role_keywords(
        resume.extracted_text, (focus_role.resume_keywords if focus_role else []) or []
    )

    return {
        "has_resume": True,
        "resume": {
            "id": resume.id,
            "filename": resume.original_filename,
            "uploaded_at": resume.uploaded_at,
            "size_kb": round(resume.file_size_bytes / 1024, 1),
            "reviewed": resume.reviewed_by_student,
            "checks": report.get("checks", []),
            "focus_role": focus_role.name if focus_role else None,
        },
        "quality_score": resume.quality_score,
        "strengths": report.get("strengths", []),
        "improvements": report.get("improvements", []),
        "missing_keywords": keywords,
        "identified_skills": (parsed.get("skills", {}) or {}).get("all", [])[:30],
        "sections_found": report.get("sections_found", []),
        "sections_missing": report.get("sections_missing", []),
        "word_count": report.get("word_count"),
        "parse_status": resume.parse_status,
    }


def _portfolio_overview(db: Session, user_id: int, profile: StudentProfile) -> dict[str, Any]:
    experiences = list(db.scalars(select(Experience).where(Experience.user_id == user_id)))
    projects = list(
        db.scalars(
            select(Project)
            .options(selectinload(Project.technologies))
            .where(Project.user_id == user_id)
            .order_by(Project.id.desc())
        )
    )

    def count_type(kind: str) -> int:
        return sum(1 for e in experiences if e.experience_type == kind)

    total_months = 0
    for exp in experiences:
        if exp.experience_type in ("internship", "job"):
            total_months += exp.duration_months or 0

    certifications = int(
        db.scalar(
            select(func.count()).select_from(Certification).where(Certification.user_id == user_id)
        )
        or 0
    )
    achievements = int(
        db.scalar(
            select(func.count()).select_from(Achievement).where(Achievement.user_id == user_id)
        )
        or 0
    )

    return {
        "projects": len(projects),
        "internships": count_type("internship"),
        "work_experience": count_type("job"),
        "positions_of_responsibility": count_type("position_of_responsibility"),
        "certifications": certifications,
        "achievements": achievements,
        "extracurriculars": count_type("extracurricular"),
        "total_experience_months": total_months,
        "links": {
            "github": profile.github_url,
            "linkedin": profile.linkedin_url,
            "portfolio": profile.portfolio_url,
            "others": profile.other_links or [],
        },
        "recent_projects": [
            {
                "id": project.id,
                "title": project.title,
                "category": project.category,
                "technologies": [t.raw_name for t in project.technologies][:6],
                "has_link": bool(project.github_url or project.live_url),
            }
            for project in projects[:4]
        ],
    }


def _career_fit(
    db: Session, user_id: int, assessments: list[RoleAssessment]
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for assessment in assessments[:6]:
        role = assessment.role
        why = [item.get("title", "") for item in (assessment.strengths or [])][:3]
        missing = [item.get("title", "") for item in (assessment.improvements or [])][:3]
        score = assessment.overall_score
        if score >= 80:
            fit_label = "Excellent match"
        elif score >= 65:
            fit_label = "Good match"
        elif score >= 50:
            fit_label = "Possible with work"
        else:
            fit_label = "Stretch target"
        out.append(
            {
                "role_id": role.id,
                "role_slug": role.slug,
                "role_name": role.name,
                "domain_name": role.domain.name,
                "score": score,
                "band": assessment.readiness_band,
                "fit_label": fit_label,
                "why_good_fit": [w for w in why if w],
                "whats_missing": [m for m in missing if m],
            }
        )
    return out


def _progress_history(db: Session, user_id: int) -> dict[str, Any]:
    rows = list(
        db.scalars(
            select(RoleAssessment)
            .options(selectinload(RoleAssessment.role))
            .where(RoleAssessment.user_id == user_id)
            .order_by(RoleAssessment.computed_at)
        )
    )

    series_map: dict[str, dict[str, Any]] = {}
    per_time: dict[dt.datetime, list[float]] = defaultdict(list)
    for row in rows:
        entry = series_map.setdefault(
            row.role.slug,
            {"role_slug": row.role.slug, "role_name": row.role.name, "points": []},
        )
        entry["points"].append(
            {
                "at": row.computed_at,
                "score": row.overall_score,
                "band": row.readiness_band,
                "version": row.version,
            }
        )
        per_time[row.computed_at].append(row.overall_score)

    overall_series = [
        {
            "at": moment,
            "score": round(sum(scores) / len(scores), 1),
            "roles": len(scores),
        }
        for moment, scores in sorted(per_time.items())
    ]

    best_improvement: dict[str, Any] | None = None
    for entry in series_map.values():
        points = entry["points"]
        if len(points) < 2:
            continue
        delta = round(points[-1]["score"] - points[0]["score"], 1)
        if best_improvement is None or delta > best_improvement["delta"]:
            best_improvement = {
                "role_name": entry["role_name"],
                "role_slug": entry["role_slug"],
                "delta": delta,
                "from_score": points[0]["score"],
                "to_score": points[-1]["score"],
            }

    completed_tasks = list(
        db.scalars(
            select(RoadmapTask)
            .join(ImprovementRoadmap, ImprovementRoadmap.id == RoadmapTask.roadmap_id)
            .where(
                ImprovementRoadmap.user_id == user_id,
                RoadmapTask.status == "completed",
            )
            .order_by(RoadmapTask.completed_at.desc())
            .limit(10)
        )
    )

    return {
        "series": sorted(series_map.values(), key=lambda item: item["role_name"]),
        "overall_series": overall_series,
        "assessment_count": len(rows),
        "first_assessed_at": rows[0].computed_at if rows else None,
        "last_assessed_at": rows[-1].computed_at if rows else None,
        "best_improvement": best_improvement,
        "completed_roadmap_tasks": [
            {
                "title": task.title,
                "completed_at": task.completed_at,
                "area": task.expected_improvement_area,
                "priority": task.priority,
            }
            for task in completed_tasks
        ],
    }


def recent_activity(db: Session, user_id: int, limit: int = 15) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(StudentActivityLog)
        .where(StudentActivityLog.user_id == user_id)
        .order_by(StudentActivityLog.created_at.desc(), StudentActivityLog.id.desc())
        .limit(limit)
    )
    return [
        {
            "id": row.id,
            "activity_type": row.activity_type,
            "title": row.title,
            "description": row.description,
            "icon": row.icon,
            "details": row.details or {},
            "created_at": row.created_at,
        }
        for row in rows
    ]


# --------------------------------------------------------------------------
# Top-level build
# --------------------------------------------------------------------------
def build_dashboard(db: Session, user: User) -> dict[str, Any]:
    profile = get_or_create_profile(db, user)
    completion, breakdown = compute_profile_completion(db, user)
    db.commit()

    assessments = current_assessments(db, user.id)
    preferences = _preference_map(db, user.id)
    rows = _role_score_rows(assessments, preferences)

    preferred_rows = [row for row in rows if row["is_preferred"]]
    best_matches = rows[:3]

    focus_row = next(
        (row for row in preferred_rows if row["is_primary"]),
        preferred_rows[0] if preferred_rows else (rows[0] if rows else None),
    )
    focus_assessment = next(
        (a for a in assessments if focus_row and a.role_id == focus_row["role_id"]), None
    )
    focus_role = focus_assessment.role if focus_assessment else None

    roadmap = roadmap_payload(db, user)
    pending = roadmap["total_tasks"] - roadmap["completed_tasks"]

    skills = _skill_analysis(db, user.id, focus_role.id if focus_role else None)
    resume_insights = _resume_insights(db, user.id, focus_role)
    portfolio = _portfolio_overview(db, user.id, profile)
    progress = _progress_history(db, user.id)
    domain_averages = _domain_averages(rows)

    greeting = build_greeting(
        full_name=user.full_name,
        profile_completion=completion,
        role_scores=rows,
        roadmap_pending=pending,
        roadmap_completed=roadmap["completed_tasks"],
    )

    top_gaps = (
        [
            {"skill_name": gap["skill_name"], "status": gap["status"]}
            for gap in skills["role_gaps"][:3]
        ]
        if skills["role_gaps"]
        else []
    )

    ai_insights = build_ai_insights(
        role_scores=rows,
        domain_averages=domain_averages,
        skills_total=skills["total_skills"],
        skills_evidence_backed=skills["evidence_backed"],
        projects_count=portfolio["projects"],
        internships_count=portfolio["internships"],
        resume_present=resume_insights["has_resume"],
        resume_quality=resume_insights["quality_score"],
        profile_completion=completion,
        roadmap_pending=pending,
        top_gaps=top_gaps,
    )

    overall = (
        round(sum(row["score"] for row in (preferred_rows or rows)) / len(preferred_rows or rows), 1)
        if rows
        else None
    )

    return {
        "generated_at": dt.datetime.now(dt.timezone.utc),
        "welcome": {
            "full_name": user.full_name,
            "first_name": user.full_name.split()[0] if user.full_name else user.username,
            "username": user.username,
            "email": user.email,
            "college": profile.college,
            "degree": profile.degree,
            "branch": profile.branch,
            "graduation_year": profile.graduation_year,
            "current_academic_year": profile.current_academic_year,
            "cgpa": profile.cgpa,
            "cgpa_scale": profile.cgpa_scale,
            "profile_completion": completion,
            "completion_breakdown": breakdown,
            "career_interests": [
                row["role_name"] for row in sorted(preferred_rows, key=lambda r: r["role_name"])
            ],
            "greeting": greeting,
            "greeting_source": ai_mode(),
            "member_since": user.created_at,
            "last_assessment_at": progress["last_assessed_at"],
        },
        "readiness": {
            "has_assessments": bool(rows),
            "overall_score": overall,
            "overall_band": band_for(overall) if overall is not None else None,
            "last_assessed_at": progress["last_assessed_at"],
            "engine_version": rows[0]["engine_version"] if rows else None,
            "roles": rows,
            "preferred_roles": preferred_rows,
            "best_matches": best_matches,
            "domain_averages": domain_averages,
        },
        "strengths": (focus_assessment.strengths if focus_assessment else []),
        "improvements": (focus_assessment.improvements if focus_assessment else []),
        "skills": skills,
        "roadmap": roadmap,
        "resume_insights": resume_insights,
        "portfolio": portfolio,
        "career_fit": _career_fit(db, user.id, assessments),
        "progress": progress,
        "recent_activity": recent_activity(db, user.id),
        "ai_insights": ai_insights,
        "ai_mode": ai_mode(),
    }


def build_role_detail(db: Session, user: User, role_slug: str) -> dict[str, Any] | None:
    """Full explainable breakdown for one role."""
    assessment = db.scalar(
        select(RoleAssessment)
        .options(
            selectinload(RoleAssessment.role).selectinload(JobRole.domain),
            selectinload(RoleAssessment.role)
            .selectinload(JobRole.required_skills)
            .selectinload(RoleRequiredSkill.skill),
            selectinload(RoleAssessment.breakdowns),
        )
        .join(JobRole, JobRole.id == RoleAssessment.role_id)
        .where(
            RoleAssessment.user_id == user.id,
            JobRole.slug == role_slug,
            RoleAssessment.is_current.is_(True),
        )
        .order_by(RoleAssessment.computed_at.desc())
    )
    if assessment is None:
        return None

    role = assessment.role
    student_skills = {
        row.skill_id: row
        for row in db.scalars(
            select(StudentSkill)
            .options(selectinload(StudentSkill.skill))
            .where(StudentSkill.user_id == user.id)
        )
    }

    comparison = []
    for requirement in sorted(
        role.required_skills, key=lambda r: (r.importance != "required", r.skill.name)
    ):
        owned = student_skills.get(requirement.skill_id)
        comparison.append(
            {
                "skill_name": requirement.skill.name,
                "category": requirement.skill.category,
                "importance": requirement.importance,
                "expected_proficiency": requirement.expected_proficiency,
                "student_proficiency": owned.proficiency if owned else None,
                "has_skill": owned is not None,
                "is_evidence_backed": bool(owned and owned.is_evidence_backed),
                "evidence_count": owned.evidence_count if owned else 0,
                "expected_value": PROFICIENCY_SCORE.get(requirement.expected_proficiency, 70),
                "student_value": PROFICIENCY_SCORE.get(owned.proficiency, 0) if owned else 0,
            }
        )

    gaps = [
        {
            "skill_id": gap.skill_id,
            "skill_name": gap.skill_name,
            "status": gap.status,
            "importance": gap.importance,
            "expected_proficiency": gap.expected_proficiency,
            "student_proficiency": gap.student_proficiency,
            "is_evidence_backed": gap.is_evidence_backed,
            "points_lost": gap.points_lost,
            "recommendation": gap.recommendation,
        }
        for gap in db.scalars(
            select(SkillGapAnalysis)
            .where(
                SkillGapAnalysis.user_id == user.id,
                SkillGapAnalysis.role_id == role.id,
            )
            .order_by(SkillGapAnalysis.points_lost.desc())
        )
    ]

    history = [
        {
            "at": row.computed_at,
            "score": row.overall_score,
            "band": row.readiness_band,
            "version": row.version,
            "trigger": row.trigger_reason,
        }
        for row in db.scalars(
            select(RoleAssessment)
            .where(
                RoleAssessment.user_id == user.id,
                RoleAssessment.role_id == role.id,
            )
            .order_by(RoleAssessment.computed_at)
        )
    ]

    breakdowns = sorted(assessment.breakdowns, key=lambda b: b.display_order)

    return {
        "role": {
            "id": role.id,
            "name": role.name,
            "slug": role.slug,
            "short_label": role.short_label,
            "description": role.description,
            "domain_name": role.domain.name,
            "domain_slug": role.domain.slug,
            "accent_color": role.domain.accent_color,
            "min_cgpa": role.min_cgpa,
            "target_cgpa": role.target_cgpa,
            "expected_projects": role.expected_projects,
            "expected_internships": role.expected_internships,
            "expected_certifications": role.expected_certifications,
        },
        "score": assessment.overall_score,
        "band": assessment.readiness_band,
        "previous_score": assessment.previous_score,
        "score_delta": assessment.score_delta,
        "computed_at": assessment.computed_at,
        "engine_version": assessment.engine_version,
        "ai_enriched": assessment.ai_enriched,
        "weights": {
            "skills": role.weight_skills,
            "projects": role.weight_projects,
            "academics": role.weight_academics,
            "experience": role.weight_experience,
            "certifications": role.weight_certifications,
            "domain_knowledge": role.weight_domain_knowledge,
            "resume_quality": role.weight_resume_quality,
        },
        "breakdowns": [
            {
                "component": b.component,
                "label": b.label,
                "weight": b.weight,
                "raw_ratio": b.raw_ratio,
                "points_earned": b.points_earned,
                "points_possible": b.points_possible,
                "explanation": b.explanation,
                "details": b.details or {},
            }
            for b in breakdowns
        ],
        "strengths": assessment.strengths or [],
        "improvements": assessment.improvements or [],
        "insights": assessment.insights or [],
        "match_summary": assessment.match_summary or {},
        "skill_gaps": gaps,
        "skill_comparison": comparison,
        "history": history,
    }
