"""Read the learner's EXISTING profile and turn it into resume candidates.

Nothing is copied or stored: items are rebuilt from the profile tables on demand,
so edits to the profile are picked up the next time a resume is generated.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import AcademicDetail, Achievement, Certification, Experience, Project, StudentProfile, StudentSkill, User

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


@dataclass
class Item:
    kind: str                     # experience | leadership | project | certification | achievement
    id: int
    title: str
    org: str = ""
    start: dt.date | None = None
    end: dt.date | None = None
    current: bool = False
    text: str = ""                # everything we know, used for relevance and as the ONLY fact source for tailoring
    sentences: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def ref(self) -> str:
        return f"{self.kind}:{self.id}"


def fmt_month(d: dt.date | None) -> str:
    return f"{MONTHS[d.month - 1]} {d.year}" if d else ""


def date_range(start: dt.date | None, end: dt.date | None, current: bool) -> str:
    a = fmt_month(start)
    b = "Present" if current else fmt_month(end)
    if a and b and a != b:
        return f"{a} – {b}"
    return a or b


def split_sentences(*texts: str | None) -> list[str]:
    out: list[str] = []
    for t in texts:
        if not t:
            continue
        for part in re.split(r"(?:\r?\n)+|(?<=[.!?])\s+(?=[A-Z])", t):
            part = re.sub(r"^[\s\-\*•●\d.)]+", "", part).strip()
            if len(part) >= 12:
                out.append(part.rstrip())
    return out


def numbers_in(text: str) -> set[str]:
    return {n.replace(",", "") for n in NUM.findall(text or "")}


@dataclass
class Pool:
    name: str
    contacts: list[str]
    education: list[dict[str, Any]]
    items: list[Item]
    skills: list[dict[str, str]]          # {"name", "group"}
    profile_ok: bool


def _clean_url(u: str | None) -> str | None:
    if not u:
        return None
    return re.sub(r"^https?://(www\.)?", "", u.strip()).rstrip("/") or None


def load(db: Session, user: User) -> Pool:
    profile = db.scalar(select(StudentProfile).where(StudentProfile.user_id == user.id))
    contacts = [c for c in [
        profile.phone if profile else None, user.email,
        _clean_url(profile.linkedin_url) if profile else None, _clean_url(profile.github_url) if profile else None,
    ] if c]

    # ---- education: structured rows first, profile fallback
    education: list[dict[str, Any]] = []
    rows = list(db.scalars(select(AcademicDetail).where(AcademicDetail.user_id == user.id)))
    rank = {"postgraduate": 0, "undergraduate": 1, "diploma": 2, "class_12": 3, "class_10": 4, "other": 5}
    rows.sort(key=lambda r: (rank.get(r.level, 6), -(r.end_year or 9999)))
    for r in rows[:3]:
        if r.level in ("class_10", "class_12") and len(rows) > 2:
            continue
        degree = r.degree_or_program or ""
        if r.specialization:
            degree = f"{degree} in {r.specialization}" if degree else r.specialization
        score = None
        if r.score:
            scale = (profile.cgpa_scale if profile and r.score_type == "cgpa" else 10)
            score = f"CGPA: {r.score:g}/{scale:g}" if r.score_type == "cgpa" else f"{r.score:g}%"
        s, e = (dt.date(r.start_year, 8, 1) if r.start_year else None), (dt.date(r.end_year, 6, 1) if r.end_year else None)
        education.append({"institution": r.institution, "degree": degree, "right": date_range(s, e, r.is_current), "score": score, "id": r.id})
    if not education and profile and profile.college:
        deg = " in ".join(x for x in (profile.degree, profile.branch) if x)
        s = None
        education.append({"institution": profile.college, "degree": deg, "right": f"Expected {profile.graduation_year}" if profile.graduation_year else "",
                          "score": f"CGPA: {profile.cgpa:g}/{profile.cgpa_scale:g}" if profile.cgpa else None, "id": 0})

    items: list[Item] = []
    for e in db.scalars(select(Experience).where(Experience.user_id == user.id)):
        kind = "experience" if e.experience_type in ("internship", "job") else "leadership"
        text = " ".join(x for x in [e.title, e.organization, e.description or "", " ".join(e.skills_used or [])] if x)
        items.append(Item(kind, e.id, e.title, e.organization, e.start_date, e.end_date, e.is_current, text, split_sentences(e.description), list(e.skills_used or []),
                          {"experience_type": e.experience_type, "location": e.location, "months": e.duration_months}))
    for p in db.scalars(select(Project).options(selectinload(Project.technologies)).where(Project.user_id == user.id)):
        techs = [t.raw_name for t in p.technologies]
        text = " ".join(x for x in [p.title, p.description or "", p.contribution or "", " ".join(techs), p.category or ""] if x)
        items.append(Item("project", p.id, p.title, "", p.start_date, p.end_date, p.is_ongoing, text, split_sentences(p.description, p.contribution), techs,
                          {"team_size": p.team_size, "github": p.github_url, "live": p.live_url}))
    for c in db.scalars(select(Certification).where(Certification.user_id == user.id)):
        items.append(Item("certification", c.id, c.name, c.issuer or "", c.issue_date, None, False, f"{c.name} {c.issuer or ''} {' '.join(c.related_skills or [])}", [], list(c.related_skills or [])))
    for a in db.scalars(select(Achievement).where(Achievement.user_id == user.id)):
        items.append(Item("achievement", a.id, a.title, "", a.date_awarded, None, False, f"{a.title} {a.description or ''} {a.scope or ''}", split_sentences(a.description), [],
                          {"category": a.category, "scope": a.scope}))

    skills: list[dict[str, str]] = []
    cat_group = {"programming": "Technical", "data_ai": "Technical", "cloud_devops": "Technical", "tools": "Technical",
                 "cs_fundamentals": "Concepts", "finance": "Concepts", "business": "Concepts", "other": "Concepts", "soft_skills": "Soft Skills"}
    for s in db.scalars(select(StudentSkill).options(selectinload(StudentSkill.skill)).where(StudentSkill.user_id == user.id)):
        if s.skill:
            skills.append({"name": s.skill.name, "group": cat_group.get(s.skill.category, "Concepts")})

    ok = bool(items or skills or education)
    return Pool(user.full_name, contacts, education, items, skills, ok)
