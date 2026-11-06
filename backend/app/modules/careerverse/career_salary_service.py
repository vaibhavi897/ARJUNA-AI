"""Salary intelligence. Every figure shown has a stored source.

India and US data are kept apart and never converted into each other: a
conversion rate would be an invented number, and BLS data is US-only.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.models import Career, CareerSalary, CareerSource
from app.modules.careerverse import career_research_service as research

logger = get_logger(__name__)

LEVEL_LABELS = {
    "entry": "Entry level",
    "mid": "Mid level",
    "senior": "Senior level",
    "p10": "Lower end (10th percentile)",
    "median": "Median",
    "p90": "Top end (90th percentile)",
    "top": "Top end",
}
LEVEL_ORDER = ["entry", "p10", "mid", "median", "senior", "p90", "top"]
BLS_OEWS_URL = "https://www.bls.gov/oes/"


def _row(s: CareerSalary) -> dict[str, Any]:
    return {
        "id": s.id,
        "region": s.region,
        "location": s.location,
        "country": s.country,
        "currency": s.currency,
        "salary_type": s.salary_type,
        "level": s.level,
        "level_label": LEVEL_LABELS.get(s.level, s.level.title()),
        "experience_min_years": s.experience_min_years,
        "experience_max_years": s.experience_max_years,
        "amount": s.amount,
        "range_low": s.range_low,
        "range_high": s.range_high,
        "period": s.period,
        "source_name": s.source_name,
        "source_url": s.source_url,
        "is_estimate": s.source_name.startswith("ARJUNA AI estimate"),
        "reference_year": s.reference_year,
        "last_verified": s.last_verified.isoformat() if s.last_verified else None,
    }


def salary_view(db: Session, career: Career) -> dict[str, Any]:
    rows = list(db.scalars(select(CareerSalary).where(CareerSalary.career_id == career.id)))
    rows.sort(key=lambda r: (LEVEL_ORDER.index(r.level) if r.level in LEVEL_ORDER else 99))
    india = [_row(r) for r in rows if r.region == "india"]
    us = [_row(r) for r in rows if r.region == "us"]
    other = [_row(r) for r in rows if r.region not in ("india", "us")]
    all_rows = india + us + other
    return {
        "career_id": career.id,
        "available": bool(all_rows),
        "india": {
            "rows": india,
            "available": bool(india),
            "note": None if india else "No verified Indian salary benchmark has been added for this profession yet. ARJUNA AI does not estimate salaries.",
        },
        "us": {
            "rows": us,
            "available": bool(us),
            "note": "US Bureau of Labor Statistics data (United States only; not Indian salaries)." if us else "US wage data has not been synced yet.",
        },
        "international": other,
        "experience_wise": [r for r in all_rows if r["experience_min_years"] is not None],
        "location_wise": [r for r in all_rows if r["location"]],
        "compensation_split": [r for r in all_rows if r["salary_type"] in ("base", "total_compensation")],
        "comparison_note": "India and US figures use different currencies and sources and are shown side by side without conversion.",
    }


def sync_bls_salaries(db: Session) -> dict[str, int]:
    """Fetch US OEWS wages for every mapped career and store them with sources."""
    careers = list(db.scalars(select(Career).where(Career.soc_code.is_not(None))))
    data = research.fetch_bls_oews([c.soc_code for c in careers if c.soc_code])
    today = dt.date.today()
    updated = 0
    for c in careers:
        d = data.get(c.soc_code or "")
        if not d or "median" not in d:
            continue
        db.execute(delete(CareerSalary).where(CareerSalary.career_id == c.id, CareerSalary.region == "us", CareerSalary.source_name.like("US BLS OEWS%")))
        soc_plain = (c.soc_code or "").replace("-", "")
        url = f"https://www.bls.gov/oes/current/oes{soc_plain}.htm"
        for level, key in (("p10", "p10"), ("median", "median"), ("p90", "p90")):
            if key in d:
                db.add(
                    CareerSalary(
                        career_id=c.id, region="us", country="United States", currency="USD",
                        salary_type="annual_wage", level=level, amount=d[key], period="year",
                        source_name=f"US BLS OEWS (national, SOC {c.soc_code})", source_url=url,
                        reference_year=d.get("year"), last_verified=today,
                    )
                )
        if "employment" in d:
            c.outlook = {**c.outlook, "us_employment": {"value": int(d["employment"]), "year": d.get("year"), "source": "US BLS OEWS", "scope": "United States only"}}
        db.add(CareerSource(career_id=c.id, kind="bls", name="US BLS OEWS wage sync", url=url, covers="US annual wage percentiles and employment", last_verified=today))
        updated += 1
    db.commit()
    return {"requested": len(careers), "updated": updated}


def sync_onet_profiles(db: Session) -> dict[str, int]:
    """Attach O*NET tasks/skills/knowledge to careers with a mapped occupation."""
    if not research.onet_enabled():
        return {"requested": 0, "updated": 0}
    careers = list(db.scalars(select(Career).where(Career.onet_code.is_not(None))))
    updated = 0
    for c in careers:
        profile = research.fetch_onet_profile(c.onet_code or "")
        if not profile:
            continue
        c.onet_data = profile
        c.onet_synced_at = dt.datetime.now(dt.timezone.utc)
        updated += 1
    db.commit()
    return {"requested": len(careers), "updated": updated}
