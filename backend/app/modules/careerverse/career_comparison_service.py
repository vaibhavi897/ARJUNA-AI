"""Side-by-side comparison of two or three careers, using stored data only."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Career
from app.modules.careerverse import career_salary_service, career_service, gemini_service


def _load(db: Session, ids: list[int]) -> list[Career]:
    rows = {
        c.id: c
        for c in db.scalars(
            select(Career)
            .options(selectinload(Career.skills), selectinload(Career.qualifications), selectinload(Career.trajectory), selectinload(Career.exits), selectinload(Career.companies))
            .where(Career.id.in_(ids))
        )
    }
    return [rows[i] for i in ids if i in rows]


def _column(db: Session, c: Career) -> dict[str, Any]:
    skills = career_service.skills_view(c)
    sal = career_salary_service.salary_view(db, c)
    wlb = c.work_life_balance or {}
    us_median = next((r for r in sal["us"]["rows"] if r["level"] == "median"), None)
    return {
        **career_service.summary_card(c),
        "responsibilities": c.responsibilities[:5],
        "salary": {
            "us_median": us_median,
            "india_available": sal["india"]["available"],
            "india_rows": sal["india"]["rows"],
            "note": None if (us_median or sal["india"]["available"]) else "No sourced salary data yet for this profession.",
        },
        "skills": {"technical": skills["technical_skills"][:6], "tools": skills["tools"][:5], "soft": skills["soft_skills"][:4]},
        "growth": {
            "current_demand": (c.outlook or {}).get("current_demand"),
            "emerging_technologies": (c.outlook or {}).get("emerging_technologies", [])[:3],
            "us_employment": (c.outlook or {}).get("us_employment"),
        },
        "lifestyle": {k: wlb.get(k) for k in ("hours", "weekend", "pressure", "remote", "travel", "client", "flexibility")},
        "opportunities": {
            "trajectory": [t.designation for t in c.trajectory],
            "exit_roles": [e.name for e in c.exits if e.kind == "role"][:5],
            "entry_requirements": skills["degrees"][:2],
        },
    }


def _rule_differences(cols: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    pressure = [(c["title"], c["lifestyle"].get("pressure")) for c in cols if c["lifestyle"].get("pressure")]
    if len(pressure) >= 2:
        hi, lo = max(pressure, key=lambda x: x[1]), min(pressure, key=lambda x: x[1])
        if hi[1] != lo[1]:
            out.append(f"{hi[0]} is rated as the heavier workload ({hi[1]}/5) compared with {lo[0]} ({lo[1]}/5) in our editorial estimate.")
    remote = {c["title"]: c["lifestyle"].get("remote") for c in cols}
    out.append("Remote/hybrid: " + "; ".join(f"{t}: {v}" for t, v in remote.items() if v) + ".")
    tech = {c["title"]: ", ".join(c["skills"]["technical"][:3]) for c in cols}
    out.append("Core skills differ: " + "; ".join(f"{t}: {v}" for t, v in tech.items()) + ".")
    return out


def compare(db: Session, ids: list[int]) -> dict[str, Any]:
    careers = _load(db, ids)
    cols = [_column(db, c) for c in careers]
    ai = None
    if len(cols) >= 2:
        facts = [{k: v for k, v in c.items() if k not in ("id", "slug", "visual_theme")} for c in cols]
        prompt = (
            "Compare these professions for a student choosing between them. Use ONLY the data given. "
            "Return JSON: {\"summary\": 2-3 sentences, \"key_differences\": [4 short strings covering responsibilities, skills, lifestyle, growth], "
            "\"choose_first_if\": {\"<profession title>\": \"one sentence on who it suits\"}}. "
            f"{gemini_service.NO_INVENTION_RULES}\n\nDATA:\n{json.dumps(facts, default=str)}"
        )
        ai = gemini_service.cached_json(db, "comparison", (sorted(c.id for c in careers), str(max(c.last_updated for c in careers if c.last_updated) if any(c.last_updated for c in careers) else "")), prompt)
        db.commit()
    return {
        "careers": cols,
        "ai_explanation": ai,
        "rule_based_differences": _rule_differences(cols) if len(cols) >= 2 else [],
        "ai_available": gemini_service.is_enabled(),
    }
