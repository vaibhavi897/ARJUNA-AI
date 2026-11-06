"""Seed realistic India salary ESTIMATES for every profession that draws a salary.

These are illustrative planning ranges written by ARJUNA AI, NOT survey data.
Every row is stored with source_name "ARJUNA AI estimate ..." and no URL, and the
UI shows an "Estimate" badge. Replace any of them with sourced figures by adding
entries to app/data/india_salary_benchmarks.json (sourced rows are never touched
by this script).

    python -m app.seeds.india_estimates

Midpoints are annual base pay in lakh rupees (LPA) for (entry, mid, senior).
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import delete, select

from app.core.logging_config import configure_logging, get_logger
from app.db.session import SessionLocal
from app.models import Career, CareerSalary

logger = get_logger(__name__)
LABEL = "ARJUNA AI estimate (illustrative range, not survey data)"

# slug: (entry, mid, senior) base-pay midpoints in LPA
BASE_LPA: dict[str, tuple[float, float, float]] = {
    "investment-banker": (18, 40, 80), "equity-research-analyst": (8, 18, 40), "quantitative-analyst": (20, 45, 90),
    "financial-analyst": (6, 14, 30), "portfolio-manager": (12, 35, 80), "credit-analyst": (6, 14, 30), "risk-analyst": (7, 16, 35),
    "management-consultant": (16, 32, 60), "strategy-consultant": (18, 35, 65), "business-analyst": (6, 14, 28),
    "operations-consultant": (10, 22, 45), "risk-consultant": (8, 18, 38),
    "software-engineer": (8, 22, 50), "backend-developer": (8, 22, 48), "frontend-developer": (7, 20, 42),
    "full-stack-developer": (8, 22, 46), "devops-engineer": (8, 22, 45), "cloud-engineer": (8, 22, 45),
    "data-scientist": (9, 24, 50), "data-analyst": (5, 12, 25), "data-engineer": (9, 24, 48),
    "machine-learning-engineer": (11, 28, 58), "ai-engineer": (12, 30, 60), "business-intelligence-analyst": (5, 12, 26),
    "product-manager": (14, 32, 65), "product-analyst": (8, 18, 35), "ux-designer": (6, 16, 35), "ui-designer": (5, 12, 28),
    "business-product-manager": (14, 30, 60), "business-development-manager": (5, 14, 32), "growth-manager": (7, 18, 38),
    "marketing-manager": (6, 16, 35), "operations-manager": (6, 16, 35), "project-manager": (6, 16, 34),
    "cybersecurity-analyst": (6, 15, 32), "security-engineer": (9, 24, 50), "it-auditor": (5, 12, 26),
    "venture-capital-associate": (15, 35, 80), "private-equity-associate": (22, 50, 110),
    "hr-manager": (5, 14, 32), "economist": (7, 15, 35), "corporate-lawyer": (10, 25, 60), "supply-chain-manager": (6, 16, 38),
    "management-accountant": (5, 11, 26), "actuary": (7, 18, 45), "research-scientist": (6, 14, 32),
    "startup-founder": (3, 10, 30),  # founder draw / early-stage pay; highly variable
    "corporate-strategy-manager": (14, 30, 60), "investment-operations-analyst": (4, 9, 20), "treasury-analyst": (6, 14, 32),
}
# total compensation / base, by sector and level (bonus, ESOPs, variable pay)
TOTAL_RATIO = {
    "Finance": (1.30, 1.45, 1.80), "Consulting": (1.15, 1.20, 1.30), "Technology": (1.10, 1.20, 1.40), "AI & Data": (1.08, 1.18, 1.30),
    "Product & Design": (1.10, 1.20, 1.35), "Business": (1.15, 1.25, 1.40), "Security": (1.08, 1.15, 1.30),
    "Investments & Entrepreneurship": (1.35, 1.60, 2.20), "Other": (1.08, 1.15, 1.25),
}
# city multipliers applied to the mid-level base
CITY = {
    "Finance": {"Mumbai": 1.10, "Delhi NCR": 1.00, "Bengaluru": 0.98, "Hyderabad": 0.92, "Pune": 0.88, "Chennai": 0.88},
    "Consulting": {"Mumbai": 1.05, "Delhi NCR": 1.05, "Bengaluru": 1.00, "Hyderabad": 0.92, "Pune": 0.88, "Chennai": 0.88},
    "_tech": {"Bengaluru": 1.08, "Hyderabad": 1.00, "Pune": 0.93, "Delhi NCR": 1.00, "Mumbai": 0.98, "Chennai": 0.90},
}
TECHY = {"Technology", "AI & Data", "Security", "Product & Design"}
DEMAND = {"Technology": 4, "AI & Data": 5, "Security": 5, "Finance": 3, "Consulting": 3, "Product & Design": 4, "Business": 3, "Investments & Entrepreneurship": 2, "Other": 3}
# US estimates ONLY for roles with no BLS series (no SOC mapping). Annual USD (p10, median, p90).
US_BASE = {"research-scientist": (62000, 104000, 165000), "investment-operations-analyst": (48000, 76000, 122000)}
LEVELS = ("entry", "mid", "senior")
LAKH = 100_000


def seed_estimates(db) -> dict[str, int]:  # noqa: ANN001
    today = dt.date.today()
    careers = {c.slug: c for c in db.scalars(select(Career))}
    unknown = set(BASE_LPA) - set(careers)
    if unknown:
        raise SystemExit(f"Unknown slugs: {sorted(unknown)}")
    rows = 0
    for slug, (e, m, s) in BASE_LPA.items():
        c = careers[slug]
        db.execute(delete(CareerSalary).where(CareerSalary.career_id == c.id, CareerSalary.region == "india", CareerSalary.source_name == LABEL))
        traj = {t.stage: t for t in c.trajectory}
        mids = dict(zip(LEVELS, (e, m, s)))

        def add(level: str, lpa: float, salary_type: str, location: str | None = None, spread: float = 0.2) -> None:
            nonlocal rows
            st = {"entry": 1, "mid": 2, "senior": 3}[level]
            db.add(CareerSalary(
                career_id=c.id, region="india", location=location, country="India", currency="INR", salary_type=salary_type, level=level,
                experience_min_years=traj[st].experience_min_years if st in traj else None,
                experience_max_years=traj[st].experience_max_years if st in traj else None,
                amount=round(lpa * LAKH), range_low=round(lpa * (1 - spread) * LAKH), range_high=round(lpa * (1 + spread) * LAKH),
                period="year", source_name=LABEL, source_url=None, reference_year=today.year, last_verified=today,
            ))
            rows += 1

        ratios = TOTAL_RATIO[c.industry]
        for i, lvl in enumerate(LEVELS):
            add(lvl, mids[lvl], "base")
            add(lvl, mids[lvl] * ratios[i], "total_compensation", spread=0.28)
        city_map = CITY.get(c.industry) or (CITY["_tech"] if c.industry in TECHY else {"Mumbai": 1.05, "Delhi NCR": 1.02, "Bengaluru": 1.02, "Hyderabad": 0.94, "Pune": 0.9, "Chennai": 0.9})
        for city, mult in city_map.items():
            add("mid", mids["mid"] * mult, "base", location=city, spread=0.18)
        c.outlook = {**c.outlook, "demand_rating": DEMAND[c.industry], "demand_rating_basis": "ARJUNA AI editorial estimate (1 = low, 5 = very high)"}
    for slug, (p10, med, p90) in US_BASE.items():
        c = careers[slug]
        if any(x.region == "us" and not x.source_name.startswith("ARJUNA AI estimate") for x in c.salaries):
            continue
        db.execute(delete(CareerSalary).where(CareerSalary.career_id == c.id, CareerSalary.region == "us", CareerSalary.source_name == LABEL))
        for level, val in (("p10", p10), ("median", med), ("p90", p90)):
            db.add(CareerSalary(career_id=c.id, region="us", country="United States", currency="USD", salary_type="annual_wage", level=level, amount=val, period="year", source_name=LABEL, source_url=None, reference_year=today.year, last_verified=today))
            rows += 1
    db.commit()
    return {"careers": len(BASE_LPA), "rows": rows}


def main() -> None:
    configure_logging()
    with SessionLocal() as db:
        print(seed_estimates(db))


if __name__ == "__main__":
    main()
