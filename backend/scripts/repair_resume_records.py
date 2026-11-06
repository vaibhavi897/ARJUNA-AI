"""Rebuild resume-derived profile rows with the corrected parser.

The original parser treated every wrapped layout line as its own entry, so a
single bullet could become a "project" and a company name could become a
"job". This script re-reads each stored resume, re-parses it, replaces only
the rows that came from a resume (``source == "resume"``) and leaves anything
the student typed in by hand untouched.

Usage (from ``backend/``)::

    python -m scripts.repair_resume_records --dry-run
    python -m scripts.repair_resume_records
    python -m scripts.repair_resume_records --user-id 17
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.db.session import SessionLocal
from app.models import (
    Achievement,
    Certification,
    Experience,
    Project,
    Resume,
    User,
)
from app.modules.onboarding import sync_onboarding_state
from app.modules.profile.service import compute_profile_completion
from app.modules.profile.skills import recompute_skill_evidence
from app.modules.resume import service as resume_service
from app.modules.scoring.service import refresh_scores

logger = get_logger(__name__)

RESUME_SOURCED = (Project, Experience, Certification, Achievement)


def _full_selection(parsed: dict) -> dict:
    """Re-import everything the corrected parse found for this resume.

    The student's original per-item ticks were never stored, and the rows that
    exist prove they accepted the import, so the corrected equivalent of the
    whole parse is the closest faithful reconstruction.
    """
    return {
        "import_contact": True,
        "skills": list(parsed.get("skills", {}).get("all") or []),
        "projects": [p.get("title") for p in parsed.get("projects") or []],
        "experience": [
            f"{e.get('title')}|{e.get('organization')}" for e in parsed.get("experience") or []
        ],
        "certifications": [c.get("name") for c in parsed.get("certifications") or []],
        "achievements": [a.get("title") for a in parsed.get("achievements") or []],
    }


def _delete_resume_rows(db: Session, user_id: int) -> dict[str, int]:
    removed: dict[str, int] = {}
    for model in RESUME_SOURCED:
        rows = list(
            db.scalars(
                select(model).where(model.user_id == user_id, model.source == "resume")
            )
        )
        for row in rows:
            db.delete(row)
        removed[model.__tablename__] = len(rows)
    db.flush()
    return removed


def repair_user(db: Session, user: User, resume: Resume, *, dry_run: bool) -> dict:
    """Re-parse one resume and rebuild the rows it produced."""
    report: dict = {"user_id": user.id, "email": user.email, "resume_id": resume.id}

    if not Path(resume.file_path).exists():
        report["skipped"] = "stored file is missing"
        return report

    resume_service.parse_resume_record(db, resume)
    if resume.parse_status != "parsed":
        report["skipped"] = f"re-parse failed: {resume.parse_error}"
        return report

    parsed = resume.parsed_data or {}
    report["parsed"] = {
        "projects": len(parsed.get("projects") or []),
        "experience": len(parsed.get("experience") or []),
        "certifications": len(parsed.get("certifications") or []),
        "achievements": len(parsed.get("achievements") or []),
    }
    report["quality_score"] = resume.quality_score

    if not resume.reviewed_by_student:
        report["rows"] = "resume never imported; parsed data refreshed only"
        return report

    report["removed"] = _delete_resume_rows(db, user.id)
    report["added"] = resume_service.apply_resume_data(
        db, user, resume, _full_selection(parsed)
    )

    recompute_skill_evidence(db, user.id)
    compute_profile_completion(db, user)
    sync_onboarding_state(db, user)
    if user.onboarding_completed:
        report["rescored"] = refresh_scores(db, user, change="resume")["recalculated_roles"]
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user-id", type=int, help="repair a single student")
    parser.add_argument(
        "--dry-run", action="store_true", help="roll back instead of committing"
    )
    args = parser.parse_args(argv)

    with SessionLocal() as db:
        query = select(Resume).where(Resume.is_active.is_(True)).order_by(Resume.user_id)
        if args.user_id:
            query = query.where(Resume.user_id == args.user_id)
        resumes = list(db.scalars(query))

        if not resumes:
            print("No active resumes found.")
            return 0

        for resume in resumes:
            user = db.get(User, resume.user_id)
            if user is None:
                continue
            report = repair_user(db, user, resume, dry_run=args.dry_run)
            print(report)

        if args.dry_run:
            db.rollback()
            print("\nDry run: nothing was written.")
        else:
            db.commit()
            print("\nCommitted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
