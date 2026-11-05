"""Resume upload, parsing and review-then-merge flow.

Merging is additive and explicit. Parsed resume data never silently overwrites
something the student typed: the student picks what to import, blank profile
fields are filled, and existing entries are left alone.
"""

from __future__ import annotations

import datetime as dt
import uuid
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging_config import get_logger
from app.models import (
    Achievement,
    Certification,
    Experience,
    Project,
    Resume,
    Skill,
    StudentSkill,
    User,
)
from app.modules.profile.service import get_or_create_profile
from app.modules.profile.skills import (
    link_project_technologies,
    recompute_skill_evidence,
    resolve_skill,
)
from app.modules.resume.extract import (
    ALLOWED_CONTENT_TYPES,
    ALLOWED_EXTENSIONS,
    ExtractionError,
    extract_text,
    sniff_matches_extension,
)
from app.modules.resume.parser import parse_resume
from app.modules.resume.quality import build_quality_report

logger = get_logger(__name__)

CHUNK_SIZE = 64 * 1024


def catalogue_map(db: Session) -> dict[str, str]:
    """Lowercase skill name/alias -> canonical display name."""
    mapping: dict[str, str] = {}
    for skill in db.scalars(select(Skill).where(Skill.is_custom.is_(False))):
        mapping[skill.name.lower()] = skill.name
        mapping[skill.slug.replace("-", " ")] = skill.name
        for alias in skill.aliases or []:
            mapping[str(alias).lower()] = skill.name
    return mapping


async def store_upload(db: Session, user: User, upload: UploadFile) -> Resume:
    """Validate and persist the uploaded file, then parse it."""
    original_name = Path(upload.filename or "resume").name
    extension = Path(original_name).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF and DOCX resumes are supported.",
        )
    content_type = (upload.content_type or "application/octet-stream").split(";")[0].strip()
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unexpected content type '{content_type}'. Upload a PDF or DOCX file.",
        )

    stored_name = f"{user.id}_{uuid.uuid4().hex}{extension}"
    destination = settings.resume_dir / stored_name

    size = 0
    first_chunk = b""
    try:
        with destination.open("wb") as handle:
            while True:
                chunk = await upload.read(CHUNK_SIZE)
                if not chunk:
                    break
                if not first_chunk:
                    first_chunk = chunk[:8]
                size += len(chunk)
                if size > settings.max_upload_bytes:
                    handle.close()
                    destination.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File is larger than {settings.MAX_UPLOAD_SIZE_MB} MB.",
                    )
                handle.write(chunk)
    except HTTPException:
        raise
    except OSError as exc:
        destination.unlink(missing_ok=True)
        logger.exception("Failed to write upload")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save the uploaded file.",
        ) from exc
    finally:
        await upload.close()

    if size == 0:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    if not sniff_matches_extension(first_chunk, extension):
        destination.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File contents do not match its extension. Re-export the resume and retry.",
        )

    # Previous resumes stay on record but stop being the active one.
    for old in db.scalars(
        select(Resume).where(Resume.user_id == user.id, Resume.is_active.is_(True))
    ):
        old.is_active = False

    resume = Resume(
        user_id=user.id,
        original_filename=original_name[:260],
        stored_filename=stored_name,
        file_path=str(destination),
        content_type=content_type,
        file_size_bytes=size,
        file_extension=extension,
        parse_status="pending",
        is_active=True,
        uploaded_at=dt.datetime.now(dt.timezone.utc),
    )
    db.add(resume)
    db.flush()

    parse_resume_record(db, resume)
    return resume


def parse_resume_record(db: Session, resume: Resume) -> Resume:
    """Extract text, parse it and store the quality report."""
    try:
        text = extract_text(Path(resume.file_path), resume.file_extension)
    except ExtractionError as exc:
        resume.parse_status = "failed"
        resume.parse_error = str(exc)
        resume.extracted_text = None
        resume.parsed_data = {}
        resume.quality_report = {}
        resume.quality_score = None
        db.flush()
        return resume

    parsed = parse_resume(text, catalogue_map(db))
    report = build_quality_report(parsed)

    resume.extracted_text = text
    resume.parsed_data = parsed
    resume.quality_report = report
    resume.quality_score = report["score"]
    resume.parse_status = "parsed"
    resume.parse_error = None
    db.flush()
    return resume


# --------------------------------------------------------------------------
# Review payload
# --------------------------------------------------------------------------
def build_review_payload(db: Session, user: User, resume: Resume) -> dict[str, Any]:
    """What the parser found, annotated with whether the profile already has it."""
    if resume.parse_status != "parsed":
        return {
            "resume_id": resume.id,
            "parse_status": resume.parse_status,
            "parse_error": resume.parse_error,
            "suggestions": None,
            "quality": resume.quality_report or None,
        }

    parsed = resume.parsed_data or {}
    existing_skills = {
        row.skill.name.lower()
        for row in db.scalars(select(StudentSkill).where(StudentSkill.user_id == user.id))
    }
    existing_projects = {
        (title or "").lower()
        for title in db.scalars(select(Project.title).where(Project.user_id == user.id))
    }
    existing_experience = {
        f"{title}|{org}".lower()
        for title, org in db.execute(
            select(Experience.title, Experience.organization).where(
                Experience.user_id == user.id
            )
        ).all()
    }
    existing_certs = {
        (name or "").lower()
        for name in db.scalars(select(Certification.name).where(Certification.user_id == user.id))
    }
    existing_achievements = {
        (title or "").lower()
        for title in db.scalars(select(Achievement.title).where(Achievement.user_id == user.id))
    }

    profile = get_or_create_profile(db, user)
    contact = parsed.get("contact", {})

    skills = [
        {
            "name": name,
            "already_in_profile": name.lower() in existing_skills,
            "suggested_proficiency": "intermediate",
        }
        for name in (parsed.get("skills", {}).get("all") or [])
    ]
    projects = [
        {
            **project,
            "already_in_profile": (project.get("title") or "").lower() in existing_projects,
        }
        for project in (parsed.get("projects") or [])
    ]
    experience = [
        {
            **item,
            "already_in_profile": (
                f"{item.get('title')}|{item.get('organization')}".lower()
                in existing_experience
            ),
        }
        for item in (parsed.get("experience") or [])
    ]
    certifications = [
        {**item, "already_in_profile": (item.get("name") or "").lower() in existing_certs}
        for item in (parsed.get("certifications") or [])
    ]
    achievements = [
        {
            **item,
            "already_in_profile": (item.get("title") or "").lower() in existing_achievements,
        }
        for item in (parsed.get("achievements") or [])
    ]

    contact_suggestions = {
        "email": {
            "value": contact.get("email"),
            "current": user.email,
            "fills_blank": False,
        },
        "phone": {
            "value": contact.get("phone"),
            "current": profile.phone,
            "fills_blank": not profile.phone,
        },
        "github_url": {
            "value": contact.get("github_url"),
            "current": profile.github_url,
            "fills_blank": not profile.github_url,
        },
        "linkedin_url": {
            "value": contact.get("linkedin_url"),
            "current": profile.linkedin_url,
            "fills_blank": not profile.linkedin_url,
        },
    }

    return {
        "resume_id": resume.id,
        "parse_status": resume.parse_status,
        "parse_error": None,
        "quality": resume.quality_report,
        "stats": parsed.get("stats", {}),
        "sections_found": parsed.get("sections_found", []),
        "education": parsed.get("education", []),
        "suggestions": {
            "contact": contact_suggestions,
            "skills": skills,
            "projects": projects,
            "experience": experience,
            "certifications": certifications,
            "achievements": achievements,
        },
        "notice": (
            "Nothing is imported until you confirm. Existing entries are kept as-is; "
            "only blank profile fields are filled."
        ),
    }


# --------------------------------------------------------------------------
# Merge
# --------------------------------------------------------------------------
def apply_resume_data(
    db: Session, user: User, resume: Resume, selection: dict[str, Any]
) -> dict[str, Any]:
    """Import the student-approved subset of parsed data. Additive only."""
    parsed = resume.parsed_data or {}
    added = {
        "skills": 0,
        "projects": 0,
        "experience": 0,
        "certifications": 0,
        "achievements": 0,
        "contact_fields": 0,
    }

    profile = get_or_create_profile(db, user)
    contact = parsed.get("contact", {})

    # --- contact: fill blanks only, never overwrite ---
    if selection.get("import_contact", True):
        if not profile.phone and contact.get("phone"):
            profile.phone = str(contact["phone"])[:25]
            added["contact_fields"] += 1
        if not profile.github_url and contact.get("github_url"):
            profile.github_url = str(contact["github_url"])[:300]
            added["contact_fields"] += 1
        if not profile.linkedin_url and contact.get("linkedin_url"):
            profile.linkedin_url = str(contact["linkedin_url"])[:300]
            added["contact_fields"] += 1

    # --- skills: add missing ones, never downgrade an existing proficiency ---
    wanted_skills: list[str] = [
        str(name) for name in (selection.get("skills") or []) if str(name).strip()
    ]
    existing_skill_ids = {
        row.skill_id
        for row in db.scalars(select(StudentSkill).where(StudentSkill.user_id == user.id))
    }
    for name in wanted_skills[:60]:
        skill = resolve_skill(db, name, user_id=user.id)
        if skill is None or skill.id in existing_skill_ids:
            continue
        db.add(
            StudentSkill(
                user_id=user.id,
                skill_id=skill.id,
                proficiency="intermediate",
                source="resume",
            )
        )
        existing_skill_ids.add(skill.id)
        added["skills"] += 1

    # --- projects ---
    existing_titles = {
        (title or "").lower()
        for title in db.scalars(select(Project.title).where(Project.user_id == user.id))
    }
    parsed_projects = {
        (p.get("title") or "").lower(): p for p in (parsed.get("projects") or [])
    }
    for title in selection.get("projects") or []:
        item = parsed_projects.get(str(title).lower())
        if item is None or str(title).lower() in existing_titles:
            continue
        project = Project(
            user_id=user.id,
            title=str(item.get("title"))[:180],
            description=(item.get("description") or None),
            category="From resume",
            source="resume",
        )
        db.add(project)
        db.flush()
        link_project_technologies(db, project, item.get("technologies") or [], user.id)
        existing_titles.add(str(title).lower())
        added["projects"] += 1

    # --- experience ---
    existing_experience = {
        f"{t}|{o}".lower()
        for t, o in db.execute(
            select(Experience.title, Experience.organization).where(
                Experience.user_id == user.id
            )
        ).all()
    }
    parsed_experience = {
        f"{e.get('title')}|{e.get('organization')}".lower(): e
        for e in (parsed.get("experience") or [])
    }
    for key in selection.get("experience") or []:
        item = parsed_experience.get(str(key).lower())
        if item is None or str(key).lower() in existing_experience:
            continue
        db.add(
            Experience(
                user_id=user.id,
                experience_type=item.get("experience_type") or "internship",
                organization=str(item.get("organization"))[:180],
                title=str(item.get("title"))[:180],
                description=item.get("description"),
                source="resume",
            )
        )
        existing_experience.add(str(key).lower())
        added["experience"] += 1

    # --- certifications ---
    existing_certs = {
        (name or "").lower()
        for name in db.scalars(
            select(Certification.name).where(Certification.user_id == user.id)
        )
    }
    parsed_certs = {
        (c.get("name") or "").lower(): c for c in (parsed.get("certifications") or [])
    }
    for name in selection.get("certifications") or []:
        item = parsed_certs.get(str(name).lower())
        if item is None or str(name).lower() in existing_certs:
            continue
        issue_date = None
        if item.get("year"):
            try:
                issue_date = dt.date(int(item["year"]), 1, 1)
            except (TypeError, ValueError):
                issue_date = None
        db.add(
            Certification(
                user_id=user.id,
                name=str(item.get("name"))[:200],
                issuer=item.get("issuer"),
                issue_date=issue_date,
                source="resume",
            )
        )
        existing_certs.add(str(name).lower())
        added["certifications"] += 1

    # --- achievements ---
    existing_achievements = {
        (title or "").lower()
        for title in db.scalars(
            select(Achievement.title).where(Achievement.user_id == user.id)
        )
    }
    parsed_achievements = {
        (a.get("title") or "").lower(): a for a in (parsed.get("achievements") or [])
    }
    for title in selection.get("achievements") or []:
        item = parsed_achievements.get(str(title).lower())
        if item is None or str(title).lower() in existing_achievements:
            continue
        date_awarded = None
        if item.get("year"):
            try:
                date_awarded = dt.date(int(item["year"]), 1, 1)
            except (TypeError, ValueError):
                date_awarded = None
        db.add(
            Achievement(
                user_id=user.id,
                title=str(item.get("title"))[:200],
                category=item.get("category") or "other",
                date_awarded=date_awarded,
                source="resume",
            )
        )
        existing_achievements.add(str(title).lower())
        added["achievements"] += 1

    resume.reviewed_by_student = True
    db.flush()
    recompute_skill_evidence(db, user.id)
    db.flush()
    return added
