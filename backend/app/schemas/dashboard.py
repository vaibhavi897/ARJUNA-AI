"""Dashboard response schemas. Everything here is derived from stored data."""

from __future__ import annotations

import datetime as dt
from typing import Any

from pydantic import BaseModel


class WelcomeOut(BaseModel):
    full_name: str
    first_name: str
    username: str
    email: str
    college: str | None
    degree: str | None
    branch: str | None
    graduation_year: int | None
    current_academic_year: str | None
    cgpa: float | None
    cgpa_scale: float
    profile_completion: int
    completion_breakdown: dict[str, Any]
    career_interests: list[str]
    greeting: str
    greeting_source: str
    member_since: dt.datetime
    last_assessment_at: dt.datetime | None


class RoleScoreOut(BaseModel):
    role_id: int
    role_slug: str
    role_name: str
    short_label: str | None
    domain_id: int
    domain_name: str
    domain_slug: str
    accent_color: str | None
    score: float
    band: str
    previous_score: float | None
    score_delta: float | None
    is_preferred: bool
    is_primary: bool
    computed_at: dt.datetime
    matched_required: int
    total_required: int
    engine_version: str
    ai_enriched: bool


class ReadinessOverviewOut(BaseModel):
    has_assessments: bool
    overall_score: float | None
    overall_band: str | None
    last_assessed_at: dt.datetime | None
    engine_version: str | None
    roles: list[RoleScoreOut]
    preferred_roles: list[RoleScoreOut]
    best_matches: list[RoleScoreOut]
    domain_averages: list[dict[str, Any]]


class ScoreBreakdownOut(BaseModel):
    component: str
    label: str
    weight: float
    raw_ratio: float
    points_earned: float
    points_possible: float
    explanation: str
    details: dict[str, Any]


class SkillGapOut(BaseModel):
    skill_id: int
    skill_name: str
    status: str
    importance: str
    expected_proficiency: str
    student_proficiency: str | None
    is_evidence_backed: bool
    points_lost: float
    recommendation: str | None


class RoleAssessmentDetailOut(BaseModel):
    role: dict[str, Any]
    score: float
    band: str
    previous_score: float | None
    score_delta: float | None
    computed_at: dt.datetime
    engine_version: str
    ai_enriched: bool
    weights: dict[str, float]
    breakdowns: list[ScoreBreakdownOut]
    strengths: list[dict[str, Any]]
    improvements: list[dict[str, Any]]
    insights: list[dict[str, Any]]
    match_summary: dict[str, Any]
    skill_gaps: list[SkillGapOut]
    skill_comparison: list[dict[str, Any]]
    history: list[dict[str, Any]]


class SkillAnalysisOut(BaseModel):
    total_skills: int
    evidence_backed: int
    claimed_only: int
    by_category: list[dict[str, Any]]
    by_proficiency: list[dict[str, Any]]
    technical_vs_business: list[dict[str, Any]]
    top_skills: list[dict[str, Any]]
    radar: list[dict[str, Any]]
    role_gaps: list[dict[str, Any]]


class RoadmapTaskOut(BaseModel):
    id: int
    title: str
    reason: str
    priority: str
    suggested_duration: str | None
    expected_improvement_area: str | None
    expected_score_gain: float | None
    action_type: str
    status: str
    completed_at: dt.datetime | None
    related_skill: str | None
    role_name: str | None
    role_slug: str | None


class RoadmapOut(BaseModel):
    generated_at: dt.datetime | None
    generator: str
    total_tasks: int
    completed_tasks: int
    completion_percent: int
    tasks: list[RoadmapTaskOut]


class ResumeInsightsOut(BaseModel):
    has_resume: bool
    resume: dict[str, Any] | None
    quality_score: float | None
    strengths: list[str]
    improvements: list[str]
    missing_keywords: list[dict[str, Any]]
    identified_skills: list[str]
    sections_found: list[str]
    sections_missing: list[str]
    word_count: int | None
    parse_status: str | None


class PortfolioOverviewOut(BaseModel):
    projects: int
    internships: int
    work_experience: int
    positions_of_responsibility: int
    certifications: int
    achievements: int
    extracurriculars: int
    total_experience_months: int
    links: dict[str, Any]
    recent_projects: list[dict[str, Any]]


class CareerFitOut(BaseModel):
    role_id: int
    role_slug: str
    role_name: str
    domain_name: str
    score: float
    band: str
    fit_label: str
    why_good_fit: list[str]
    whats_missing: list[str]


class ActivityOut(BaseModel):
    id: int
    activity_type: str
    title: str
    description: str | None
    icon: str | None
    details: dict[str, Any]
    created_at: dt.datetime


class InsightOut(BaseModel):
    kind: str
    title: str
    body: str
    severity: str


class ProgressHistoryOut(BaseModel):
    series: list[dict[str, Any]]
    overall_series: list[dict[str, Any]]
    assessment_count: int
    first_assessed_at: dt.datetime | None
    last_assessed_at: dt.datetime | None
    best_improvement: dict[str, Any] | None
    completed_roadmap_tasks: list[dict[str, Any]]


class DashboardOut(BaseModel):
    generated_at: dt.datetime
    welcome: WelcomeOut
    readiness: ReadinessOverviewOut
    strengths: list[dict[str, Any]]
    improvements: list[dict[str, Any]]
    skills: SkillAnalysisOut
    roadmap: RoadmapOut
    resume_insights: ResumeInsightsOut
    portfolio: PortfolioOverviewOut
    career_fit: list[CareerFitOut]
    progress: ProgressHistoryOut
    recent_activity: list[ActivityOut]
    ai_insights: list[InsightOut]
    ai_mode: str
