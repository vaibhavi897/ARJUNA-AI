"""Seed loader: careers_seed.json -> PostgreSQL. Idempotent (matched by slug)."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.models import (
    Career,
    CareerCompany,
    CareerExit,
    CareerQualification,
    CareerSalary,
    CareerSkill,
    CareerSource,
    CareerStory,
    CareerStoryScene,
    CareerTrajectory,
)

logger = get_logger(__name__)
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
SEED_FILE = DATA_DIR / "careers_seed.json"
INDIA_FILE = DATA_DIR / "india_salary_benchmarks.json"

SKILL_KIND_MAP = {"technical": "technical", "tools": "tool", "knowledge": "knowledge", "soft": "soft"}


def _date(value: str | None) -> dt.date | None:
    return dt.date.fromisoformat(value) if value else None


def _replace_children(db: Session, career: Career, item: dict[str, Any]) -> None:
    # Children owned by the seed are rebuilt. Salary rows (BLS sync / curated
    # India file) are never touched here.
    for model in (CareerSkill, CareerQualification, CareerTrajectory, CareerExit, CareerCompany):
        db.execute(delete(model).where(model.career_id == career.id))
    db.execute(
        delete(CareerSource).where(
            CareerSource.career_id == career.id,
            CareerSource.kind.in_(("curated", "onet", "bls", "ncs")),
        )
    )
    db.flush()

    for group, kind in SKILL_KIND_MAP.items():
        for name in item["skills"].get(group, []):
            db.add(
                CareerSkill(
                    career_id=career.id,
                    name=name,
                    kind=kind,
                    importance="core" if kind in ("technical", "tool") else "supporting",
                )
            )
    for name in item["qualifications"]["degrees"]:
        db.add(CareerQualification(career_id=career.id, kind="degree", name=name, required=True))
    for name in item["qualifications"]["certifications"]:
        db.add(CareerQualification(career_id=career.id, kind="certification", name=name, required=False))
    for t in item["trajectory"]:
        lo, hi = t["years"]
        db.add(
            CareerTrajectory(
                career_id=career.id,
                stage=t["stage"],
                level_name=t["level_name"],
                designation=t["designation"],
                experience_min_years=lo,
                experience_max_years=hi,
            )
        )
    for kind, key in (("role", "roles"), ("industry", "industries"), ("qualification", "qualifications")):
        values = item["exits"][key]
        for name in values if isinstance(values, list) else [values]:
            db.add(CareerExit(career_id=career.id, kind=kind, name=name))
    designations = [t["designation"] for t in item["trajectory"][:2]]
    for pos, co in enumerate(item["companies"]):
        db.add(
            CareerCompany(
                career_id=career.id,
                name=co["name"],
                industry=co["industry"],
                job_titles=designations,
                regions=co["regions"],
                position=pos,
            )
        )
    for s in item["sources"]:
        db.add(
            CareerSource(
                career_id=career.id,
                kind=s["kind"],
                name=s["name"],
                url=s["url"],
                covers=s["covers"],
                last_verified=_date(s["last_verified"]),
            )
        )


def _upsert_story(db: Session, career: Career, story: dict[str, Any]) -> None:
    """Install the seed story as version 1 unless a Gemini version replaced it."""
    existing = db.scalar(
        select(CareerStory).where(CareerStory.career_id == career.id, CareerStory.version == 1)
    )
    if existing is None:
        existing = CareerStory(career_id=career.id, version=1, title=story["title"], source="seed")
        db.add(existing)
        db.flush()
    elif existing.source != "seed":
        return
    existing.title, existing.summary = story["title"], story["summary"]
    db.execute(delete(CareerStoryScene).where(CareerStoryScene.story_id == existing.id))
    db.flush()
    for sc in story["scenes"]:
        db.add(CareerStoryScene(story_id=existing.id, **sc))
    existing.scene_count = len(story["scenes"])


def load_india_benchmarks(db: Session) -> int:
    """Insert curated Indian benchmarks. Rows without full sourcing are rejected."""
    if not INDIA_FILE.exists():
        return 0
    entries = json.loads(INDIA_FILE.read_text(encoding="utf-8")).get("entries", [])
    added = 0
    for e in entries:
        if not (e.get("source_name") and e.get("source_url") and e.get("last_verified") and e.get("currency")):
            logger.warning("Skipping unsourced India salary entry for %s", e.get("career_slug"))
            continue
        career = db.scalar(select(Career).where(Career.slug == e["career_slug"]))
        if career is None:
            continue
        db.execute(
            delete(CareerSalary).where(
                CareerSalary.career_id == career.id,
                CareerSalary.region == "india",
                CareerSalary.location == e.get("location"),
                CareerSalary.level == e["level"],
                CareerSalary.source_name == e["source_name"],
            )
        )
        db.add(
            CareerSalary(
                career_id=career.id,
                region="india",
                location=e.get("location"),
                country="India",
                currency=e["currency"],
                salary_type=e["salary_type"],
                level=e["level"],
                experience_min_years=e.get("experience_min_years"),
                experience_max_years=e.get("experience_max_years"),
                amount=e.get("amount"),
                range_low=e.get("range_low"),
                range_high=e.get("range_high"),
                source_name=e["source_name"],
                source_url=e["source_url"],
                reference_year=e.get("reference_year"),
                last_verified=_date(e["last_verified"]),
            )
        )
        added += 1
    return added


def seed_careers(db: Session) -> dict[str, int]:
    data = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    created = updated = 0
    for item in data["careers"]:
        career = db.scalar(select(Career).where(Career.slug == item["slug"]))
        fields = dict(
            title=item["title"],
            industry=item["industry"],
            short_description=item["short_description"],
            description=item["description"],
            responsibilities=item["responsibilities"],
            industries=item["industries"],
            work_environment=item["work_environment"],
            work_life_balance=item["work_life_balance"],
            outlook=item["outlook"],
            advantages=item["advantages"],
            disadvantages=item["disadvantages"],
            geography=item["geography"],
            visual_theme=item["visual_theme"],
            onet_code=item["onet_code"],
            soc_code=item["soc_code"],
            last_updated=_date(item["last_updated"]),
        )
        if career is None:
            career = Career(slug=item["slug"], **fields)
            db.add(career)
            db.flush()
            created += 1
        else:
            for k, v in fields.items():
                setattr(career, k, v)
            db.flush()
            updated += 1
        _replace_children(db, career, item)
        _upsert_story(db, career, item["story"])
    db.flush()
    india = load_india_benchmarks(db)
    db.commit()
    return {"created": created, "updated": updated, "india_benchmarks": india}
