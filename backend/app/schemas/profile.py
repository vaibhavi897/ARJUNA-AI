"""Profile, academics, skills, projects, experience and preference schemas."""

from __future__ import annotations

import datetime as dt
import re
from typing import Annotated, Any

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.activity import ACTIVITY_TYPES  # noqa: F401  (documentation aid)
from app.models.catalog import PROFICIENCY_LEVELS, SKILL_CATEGORIES
from app.models.profile import (
    ACADEMIC_LEVELS,
    ACHIEVEMENT_CATEGORIES,
    EXPERIENCE_TYPES,
)
from app.schemas.common import ORMModel

Proficiency = Annotated[str, Field(pattern="^(beginner|intermediate|advanced)$")]
_URL_RE = re.compile(r"^https?://[^\s]+$", re.IGNORECASE)
CURRENT_YEAR = dt.date.today().year


def _clean_optional_str(value: Any) -> Any:
    if isinstance(value, str):
        trimmed = value.strip()
        return trimmed or None
    return value


def _clean_optional_url(value: Any) -> Any:
    value = _clean_optional_str(value)
    if value is None:
        return None
    if not isinstance(value, str):
        return value
    candidate = value if "://" in value else f"https://{value}"
    if not _URL_RE.match(candidate):
        raise ValueError("Must be a valid http(s) URL")
    if len(candidate) > 300:
        raise ValueError("URL is too long")
    return candidate


# --------------------------------------------------------------------------
# Step 1 - personal information
# --------------------------------------------------------------------------
class PersonalInfoIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=25)
    location: str | None = Field(default=None, max_length=120)
    college: str = Field(min_length=2, max_length=180)
    degree: str = Field(min_length=2, max_length=120)
    branch: str = Field(min_length=1, max_length=120)
    graduation_year: int = Field(ge=1990, le=CURRENT_YEAR + 10)
    current_academic_year: str = Field(min_length=1, max_length=30)
    cgpa: float | None = Field(default=None, ge=0)
    cgpa_scale: float = Field(default=10.0, gt=0, le=100)
    headline: str | None = Field(default=None, max_length=160)
    bio: str | None = Field(default=None, max_length=2000)

    _clean_phone = field_validator("phone", "location", "headline", "bio", mode="before")(
        _clean_optional_str
    )

    @field_validator("phone")
    @classmethod
    def _valid_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        digits = re.sub(r"[^\d]", "", value)
        if len(digits) < 7 or len(digits) > 15:
            raise ValueError("Phone number must contain between 7 and 15 digits")
        return value

    @field_validator("cgpa")
    @classmethod
    def _cgpa_range(cls, value: float | None) -> float | None:
        if value is not None and value > 100:
            raise ValueError("CGPA looks invalid")
        return value


# --------------------------------------------------------------------------
# Step 2 - academic background
# --------------------------------------------------------------------------
class AcademicDetailIn(BaseModel):
    id: int | None = None
    level: str = Field(default="other")
    institution: str = Field(min_length=2, max_length=180)
    board_or_university: str | None = Field(default=None, max_length=180)
    degree_or_program: str | None = Field(default=None, max_length=160)
    specialization: str | None = Field(default=None, max_length=160)
    score: float | None = Field(default=None, ge=0, le=100)
    score_type: str | None = Field(default=None, max_length=20)
    start_year: int | None = Field(default=None, ge=1950, le=CURRENT_YEAR + 10)
    end_year: int | None = Field(default=None, ge=1950, le=CURRENT_YEAR + 10)
    is_current: bool = False
    achievements: str | None = Field(default=None, max_length=2000)
    relevant_coursework: list[str] = Field(default_factory=list)

    _clean = field_validator(
        "board_or_university",
        "degree_or_program",
        "specialization",
        "score_type",
        "achievements",
        mode="before",
    )(_clean_optional_str)

    @field_validator("level")
    @classmethod
    def _valid_level(cls, value: str) -> str:
        if value not in ACADEMIC_LEVELS:
            raise ValueError(f"level must be one of {', '.join(ACADEMIC_LEVELS)}")
        return value

    @field_validator("relevant_coursework")
    @classmethod
    def _clean_courses(cls, value: list[str]) -> list[str]:
        return [c.strip() for c in value if c and c.strip()][:30]


class AcademicDetailOut(ORMModel):
    id: int
    level: str
    institution: str
    board_or_university: str | None
    degree_or_program: str | None
    specialization: str | None
    score: float | None
    score_type: str | None
    start_year: int | None
    end_year: int | None
    is_current: bool
    achievements: str | None
    relevant_coursework: list[str]


class AcademicStepIn(BaseModel):
    entries: list[AcademicDetailIn] = Field(default_factory=list, max_length=15)


# --------------------------------------------------------------------------
# Step 3 - skills
# --------------------------------------------------------------------------
class StudentSkillIn(BaseModel):
    # Either an existing catalogue skill id, or a free-text name (custom skill).
    skill_id: int | None = None
    name: str | None = Field(default=None, max_length=120)
    category: str | None = None
    proficiency: Proficiency = "beginner"
    years_of_experience: float | None = Field(default=None, ge=0, le=30)
    notes: str | None = Field(default=None, max_length=500)

    _clean = field_validator("name", "notes", mode="before")(_clean_optional_str)

    @field_validator("category")
    @classmethod
    def _valid_category(cls, value: str | None) -> str | None:
        if value in (None, ""):
            return None
        if value not in SKILL_CATEGORIES:
            raise ValueError(f"category must be one of {', '.join(SKILL_CATEGORIES)}")
        return value

    @field_validator("name")
    @classmethod
    def _require_identifier(cls, value: str | None, info: Any) -> str | None:
        return value


class SkillsStepIn(BaseModel):
    skills: list[StudentSkillIn] = Field(default_factory=list, max_length=80)


class StudentSkillOut(BaseModel):
    id: int
    skill_id: int
    name: str
    slug: str
    category: str
    proficiency: str
    years_of_experience: float | None
    source: str
    evidence_count: int
    is_evidence_backed: bool
    notes: str | None


# --------------------------------------------------------------------------
# Step 4 - projects
# --------------------------------------------------------------------------
class ProjectIn(BaseModel):
    id: int | None = None
    title: str = Field(min_length=2, max_length=180)
    description: str | None = Field(default=None, max_length=4000)
    contribution: str | None = Field(default=None, max_length=2000)
    category: str | None = Field(default=None, max_length=80)
    duration_months: int | None = Field(default=None, ge=0, le=120)
    start_date: dt.date | None = None
    end_date: dt.date | None = None
    is_ongoing: bool = False
    team_size: int | None = Field(default=None, ge=1, le=100)
    github_url: str | None = None
    live_url: str | None = None
    technologies: list[str] = Field(default_factory=list, max_length=40)

    _clean = field_validator(
        "description", "contribution", "category", mode="before"
    )(_clean_optional_str)
    _clean_urls = field_validator("github_url", "live_url", mode="before")(
        _clean_optional_url
    )

    @field_validator("technologies")
    @classmethod
    def _clean_tech(cls, value: list[str]) -> list[str]:
        seen: dict[str, str] = {}
        for item in value:
            if not item or not item.strip():
                continue
            cleaned = item.strip()[:120]
            seen.setdefault(cleaned.lower(), cleaned)
        return list(seen.values())


class ProjectsStepIn(BaseModel):
    projects: list[ProjectIn] = Field(default_factory=list, max_length=30)


class ProjectOut(ORMModel):
    id: int
    title: str
    description: str | None
    contribution: str | None
    category: str | None
    duration_months: int | None
    start_date: dt.date | None
    end_date: dt.date | None
    is_ongoing: bool
    team_size: int | None
    github_url: str | None
    live_url: str | None
    source: str
    technologies: list[str] = []


# --------------------------------------------------------------------------
# Step 5 - experience, certifications, achievements
# --------------------------------------------------------------------------
class ExperienceIn(BaseModel):
    id: int | None = None
    experience_type: str = "internship"
    organization: str = Field(min_length=1, max_length=180)
    title: str = Field(min_length=1, max_length=180)
    description: str | None = Field(default=None, max_length=4000)
    location: str | None = Field(default=None, max_length=120)
    start_date: dt.date | None = None
    end_date: dt.date | None = None
    is_current: bool = False
    duration_months: int | None = Field(default=None, ge=0, le=600)
    skills_used: list[str] = Field(default_factory=list, max_length=40)

    _clean = field_validator("description", "location", mode="before")(_clean_optional_str)

    @field_validator("experience_type")
    @classmethod
    def _valid_type(cls, value: str) -> str:
        if value not in EXPERIENCE_TYPES:
            raise ValueError(f"experience_type must be one of {', '.join(EXPERIENCE_TYPES)}")
        return value

    @field_validator("skills_used")
    @classmethod
    def _clean_skills(cls, value: list[str]) -> list[str]:
        return [s.strip() for s in value if s and s.strip()][:40]


class ExperienceOut(ORMModel):
    id: int
    experience_type: str
    organization: str
    title: str
    description: str | None
    location: str | None
    start_date: dt.date | None
    end_date: dt.date | None
    is_current: bool
    duration_months: int | None
    skills_used: list[str]
    source: str


class CertificationIn(BaseModel):
    id: int | None = None
    name: str = Field(min_length=2, max_length=200)
    issuer: str | None = Field(default=None, max_length=160)
    issue_date: dt.date | None = None
    expiry_date: dt.date | None = None
    credential_id: str | None = Field(default=None, max_length=160)
    credential_url: str | None = None
    related_skills: list[str] = Field(default_factory=list, max_length=20)

    _clean = field_validator("issuer", "credential_id", mode="before")(_clean_optional_str)
    _clean_url = field_validator("credential_url", mode="before")(_clean_optional_url)

    @field_validator("related_skills")
    @classmethod
    def _clean_skills(cls, value: list[str]) -> list[str]:
        return [s.strip() for s in value if s and s.strip()][:20]


class CertificationOut(ORMModel):
    id: int
    name: str
    issuer: str | None
    issue_date: dt.date | None
    expiry_date: dt.date | None
    credential_id: str | None
    credential_url: str | None
    related_skills: list[str]
    source: str


class AchievementIn(BaseModel):
    id: int | None = None
    title: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    category: str = "other"
    scope: str | None = Field(default=None, max_length=60)
    date_awarded: dt.date | None = None

    _clean = field_validator("description", "scope", mode="before")(_clean_optional_str)

    @field_validator("category")
    @classmethod
    def _valid_category(cls, value: str) -> str:
        if value not in ACHIEVEMENT_CATEGORIES:
            raise ValueError(
                f"category must be one of {', '.join(ACHIEVEMENT_CATEGORIES)}"
            )
        return value


class AchievementOut(ORMModel):
    id: int
    title: str
    description: str | None
    category: str
    scope: str | None
    date_awarded: dt.date | None
    source: str


class ExperienceStepIn(BaseModel):
    experiences: list[ExperienceIn] = Field(default_factory=list, max_length=30)
    certifications: list[CertificationIn] = Field(default_factory=list, max_length=30)
    achievements: list[AchievementIn] = Field(default_factory=list, max_length=30)


# --------------------------------------------------------------------------
# Step 7 - portfolio and career preferences
# --------------------------------------------------------------------------
class PortfolioLink(BaseModel):
    label: str = Field(min_length=1, max_length=80)
    url: str

    _clean_url = field_validator("url", mode="before")(_clean_optional_url)


class PreferencesStepIn(BaseModel):
    github_url: str | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None
    other_links: list[PortfolioLink] = Field(default_factory=list, max_length=10)
    role_ids: list[int] = Field(default_factory=list, max_length=15)
    primary_role_id: int | None = None

    _clean_urls = field_validator(
        "github_url", "linkedin_url", "portfolio_url", mode="before"
    )(_clean_optional_url)

    @field_validator("role_ids")
    @classmethod
    def _dedupe(cls, value: list[int]) -> list[int]:
        return list(dict.fromkeys(value))


# --------------------------------------------------------------------------
# Aggregate profile output
# --------------------------------------------------------------------------
class ProfileCoreOut(ORMModel):
    phone: str | None = None
    location: str | None = None
    headline: str | None = None
    bio: str | None = None
    college: str | None = None
    degree: str | None = None
    branch: str | None = None
    graduation_year: int | None = None
    current_academic_year: str | None = None
    cgpa: float | None = None
    cgpa_scale: float = 10.0
    github_url: str | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None
    other_links: list[dict[str, Any]] = []
    profile_completion: int = 0
    completion_breakdown: dict[str, Any] = {}


class CareerPreferenceOut(BaseModel):
    role_id: int
    role_name: str
    role_slug: str
    domain_id: int
    domain_name: str
    priority: int
    is_primary: bool


class ResumeSummaryOut(BaseModel):
    id: int
    original_filename: str
    file_extension: str
    file_size_bytes: int
    parse_status: str
    parse_error: str | None = None
    quality_score: float | None = None
    reviewed_by_student: bool
    uploaded_at: dt.datetime


class FullProfileOut(BaseModel):
    user: dict[str, Any]
    profile: ProfileCoreOut
    academics: list[AcademicDetailOut]
    skills: list[StudentSkillOut]
    projects: list[ProjectOut]
    experiences: list[ExperienceOut]
    certifications: list[CertificationOut]
    achievements: list[AchievementOut]
    preferences: list[CareerPreferenceOut]
    resume: ResumeSummaryOut | None
