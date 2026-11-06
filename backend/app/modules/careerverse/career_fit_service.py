"""Career Fit: transparent, resume-driven alignment between a student and a career.

Method (no black box, no trained model):
  * Each component compares the student's own profile text with the matching
    part of the career dataset using TF-IDF + cosine similarity (scikit-learn).
  * Cosine similarity of short documents is naturally low, so it is calibrated
    (``COSINE_CALIBRATION``) before weighting. This is a documented scaling
    constant, not a learned parameter.
  * Components are combined with configurable weights (default 30/20/20/20/10).

The result is an alignment score out of 100. It is NOT a probability of being
hired or selected. Gemini only words the explanation; it never changes numbers.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.logging_config import get_logger
from app.models import Career, StudentCareerPreference, User, UserCareerFit
from app.models.profile import AcademicDetail, Certification, Experience, Project, StudentProfile, StudentSkill
from app.modules.careerverse import gemini_service

logger = get_logger(__name__)

DEFAULT_WEIGHTS = {"technical": 0.30, "education": 0.20, "projects": 0.20, "experience": 0.20, "certifications": 0.10}
COMPONENT_LABELS = {
    "technical": "Technical skill alignment",
    "education": "Educational alignment",
    "projects": "Project relevance",
    "experience": "Experience alignment",
    "certifications": "Certification alignment",
}
COSINE_CALIBRATION = 0.35  # cosine at/above this counts as a full match for a component


def get_weights() -> dict[str, float]:
    """Weights are configurable via CAREER_FIT_WEIGHTS (JSON); normalised to sum to 1."""
    weights = dict(DEFAULT_WEIGHTS)
    raw = getattr(settings, "CAREER_FIT_WEIGHTS", None)
    if raw:
        try:
            custom = json.loads(raw)
            weights.update({k: float(v) for k, v in custom.items() if k in weights and float(v) >= 0})
        except (ValueError, TypeError):
            logger.warning("Invalid CAREER_FIT_WEIGHTS; using defaults")
    total = sum(weights.values()) or 1.0
    return {k: v / total for k, v in weights.items()}


# ------------------------------------------------------------------ student features
def _clean(parts: list[str | None]) -> str:
    return " ".join(p.strip() for p in parts if p and p.strip())


def student_features(db: Session, user: User) -> dict[str, Any]:
    """Read the existing profile/resume tables. Nothing is copied or stored."""
    profile = db.scalar(select(StudentProfile).where(StudentProfile.user_id == user.id))
    skills = [
        s.skill.name
        for s in db.scalars(select(StudentSkill).options(selectinload(StudentSkill.skill)).where(StudentSkill.user_id == user.id))
        if s.skill
    ]
    academics = list(db.scalars(select(AcademicDetail).where(AcademicDetail.user_id == user.id)))
    projects = list(db.scalars(select(Project).options(selectinload(Project.technologies)).where(Project.user_id == user.id)))
    experiences = list(db.scalars(select(Experience).where(Experience.user_id == user.id)))
    certs = list(db.scalars(select(Certification).where(Certification.user_id == user.id)))
    prefs = list(
        db.scalars(select(StudentCareerPreference).options(selectinload(StudentCareerPreference.role)).where(StudentCareerPreference.user_id == user.id))
    )

    proj_tech = [t.raw_name for p in projects for t in p.technologies]
    education = _clean(
        [profile.degree if profile else None, profile.branch if profile else None]
        + [x for a in academics for x in (a.degree_or_program, a.specialization, a.achievements, " ".join(a.relevant_coursework or []))]
    )
    return {
        "skills": sorted(set(skills + proj_tech + [s for e in experiences for s in (e.skills_used or [])])),
        "claimed_skills": sorted(set(skills)),
        "education_text": education,
        "cgpa": profile.cgpa if profile else None,
        "cgpa_scale": profile.cgpa_scale if profile else 10.0,
        "project_text": _clean([_clean([p.title, p.description, p.contribution, " ".join(t.raw_name for t in p.technologies)]) for p in projects]),
        "project_count": len(projects),
        "experience_text": _clean([_clean([e.title, e.organization, e.description, " ".join(e.skills_used or [])]) for e in experiences]),
        "experience_months": sum(e.duration_months or 0 for e in experiences),
        "experience_count": len(experiences),
        "certification_text": _clean([_clean([c.name, c.issuer, " ".join(c.related_skills or [])]) for c in certs]),
        "certification_count": len(certs),
        "interest_titles": [p.role.title for p in prefs if getattr(p.role, "title", None)],
    }


def profile_has_data(f: dict[str, Any]) -> bool:
    return bool(f["skills"] or f["education_text"] or f["project_text"] or f["experience_text"] or f["certification_text"])


# ------------------------------------------------------------------ career documents
def career_docs(c: Career) -> dict[str, str]:
    by = lambda *kinds: [s.name for s in c.skills if s.kind in kinds]  # noqa: E731
    onet = c.onet_data or {}
    return {
        "technical": _clean(by("technical", "tool", "knowledge") + list(onet.get("skills", []))),
        "education": _clean([q.name for q in c.qualifications if q.kind == "degree"] + by("knowledge")),
        "projects": _clean(list(c.responsibilities) + by("technical", "tool") + list(onet.get("tasks", []))),
        "experience": _clean(list(c.responsibilities) + [t.designation for t in c.trajectory] + list(c.industries)),
        "certifications": _clean([q.name for q in c.qualifications if q.kind == "certification"]),
    }


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9+#.]{2,}", text.lower())}


def _skill_match(student_skill: str, career_skill: str) -> bool:
    a, b = student_skill.lower().strip(), re.sub(r"\s*\(.*?\)", "", career_skill.lower()).strip()
    if not a or not b:
        return False
    if a in b or b in a:
        return True
    parts = [p.strip() for p in re.split(r"[/,]", career_skill.lower())]
    return any(a == p or a in p.split() for p in parts if p)


def _calibrate(cos: float) -> float:
    return float(min(1.0, max(0.0, cos / COSINE_CALIBRATION)))


def _component_cosines(student_texts: dict[str, str], careers: list[Career]) -> dict[int, dict[str, float]]:
    """One TF-IDF space per component, fitted on all careers plus the student."""
    docs = {c.id: career_docs(c) for c in careers}
    out: dict[int, dict[str, float]] = {c.id: {} for c in careers}
    for comp in DEFAULT_WEIGHTS:
        corpus = [docs[c.id][comp] for c in careers]
        student = student_texts.get(comp, "")
        if not student.strip() or not any(corpus):
            for c in careers:
                out[c.id][comp] = 0.0
            continue
        vec = TfidfVectorizer(ngram_range=(1, 2), stop_words="english", sublinear_tf=True, token_pattern=r"(?u)\b[\w+#.]{2,}\b")
        matrix = vec.fit_transform(corpus + [student])
        sims = cosine_similarity(matrix[-1], matrix[:-1]).ravel()
        for c, s in zip(careers, sims):
            out[c.id][comp] = float(s)
    return out


def _score_one(c: Career, f: dict[str, Any], cos: dict[str, float], weights: dict[str, float]) -> dict[str, Any]:
    core = [s.name for s in c.skills if s.kind in ("technical", "tool")]
    matched = [s for s in core if any(_skill_match(ss, s) for ss in f["skills"])]
    overlap = len(matched) / len(core) if core else 0.0

    comps: dict[str, float | None] = {}
    comps["technical"] = (0.6 * _calibrate(cos["technical"]) + 0.4 * min(1.0, overlap / 0.5)) if f["skills"] else None
    if f["education_text"]:
        base = _calibrate(cos["education"])
        cg = f["cgpa"]
        comps["education"] = base * (0.85 + 0.15 * min(1.0, cg / (f["cgpa_scale"] or 10.0))) if cg else base
    else:
        comps["education"] = None
    comps["projects"] = (0.8 * _calibrate(cos["projects"]) + 0.2 * min(1.0, f["project_count"] / 3)) if f["project_text"] else None
    comps["experience"] = (0.75 * _calibrate(cos["experience"]) + 0.25 * min(1.0, f["experience_months"] / 6)) if f["experience_text"] else None
    comps["certifications"] = _calibrate(cos["certifications"]) if f["certification_text"] else None

    score = sum(weights[k] * (v or 0.0) for k, v in comps.items()) * 100
    return {
        "career_id": c.id,
        "score": round(score, 1),
        "components": {
            k: {"label": COMPONENT_LABELS[k], "weight": round(weights[k], 3), "value": None if v is None else round(v * 100, 1), "has_data": v is not None}
            for k, v in comps.items()
        },
        "matched_skills": matched,
        "missing_skills": [s for s in core if s not in matched],
    }


def _rule_based(c: Career, f: dict[str, Any], r: dict[str, Any]) -> dict[str, list[str]]:
    comps = r["components"]
    strengths: list[str] = []
    gaps: list[str] = []
    recs: list[str] = []
    if r["matched_skills"]:
        strengths.append("Skills that match this role: " + ", ".join(r["matched_skills"][:5]) + ".")
    for k, v in sorted(((k, v) for k, v in comps.items() if v["has_data"]), key=lambda kv: -kv[1]["value"]):
        if v["value"] >= 55 and len(strengths) < 4:
            strengths.append(f"{v['label']} is a relative strength ({v['value']:.0f}/100 on this component).")
    if r["missing_skills"]:
        gaps.append("Skills this role typically uses that your profile does not show yet: " + ", ".join(r["missing_skills"][:5]) + ".")
        recs.append("Learn " + r["missing_skills"][0] + (f" and {r['missing_skills'][1]}" if len(r["missing_skills"]) > 1 else "") + ", then apply them in a project you can show.")
    labels = {"projects": "Add a project that mirrors this role's work and list the tools used.",
              "experience": "Look for an internship, simulation or volunteer role that touches this role's day-to-day tasks.",
              "education": "Consider coursework or a programme that covers the role's core knowledge areas.",
              "certifications": None}
    for k, v in comps.items():
        if not v["has_data"]:
            gaps.append(f"No {v['label'].lower().split(' alignment')[0].split(' relevance')[0]} information in your profile yet, so this part scores zero.")
        elif v["value"] < 35:
            gaps.append(f"{v['label']} is low ({v['value']:.0f}/100).")
        if (not v["has_data"] or v["value"] < 35) and labels.get(k):
            recs.append(labels[k])
    certs = [q.name for q in c.qualifications if q.kind == "certification"]
    if certs and (not comps["certifications"]["has_data"] or comps["certifications"]["value"] < 35):
        recs.append(f"Consider a recognised credential such as {certs[0]}.")
    return {"strengths": strengths[:4] or ["Your profile does not yet show strong overlap with this role."], "gaps": gaps[:5], "recommendations": recs[:5]}


def _explain(db: Session, c: Career, r: dict[str, Any], rb: dict[str, list[str]], input_hash: str) -> tuple[str, dict[str, list[str]], str]:
    fallback = (
        f"Your profile aligns with {c.title} at {r['score']:.0f}/100. This compares your skills, education, projects, experience and "
        "certifications with the role's requirements. It is an alignment indicator, not a prediction of getting hired."
    )
    facts = {"profession": c.title, "alignment_score_out_of_100": r["score"], "components": {k: v["value"] for k, v in r["components"].items()},
             "strengths": rb["strengths"], "gaps": rb["gaps"], "recommendations": rb["recommendations"]}
    prompt = (
        "Explain this Career Fit result to a student in a warm, honest tone. Return JSON: "
        "{\"explanation\": 3-4 sentences, \"strengths\": [<=4 short strings], \"gaps\": [<=4 short strings], \"recommendations\": [<=4 short actionable strings]}. "
        "Keep every number exactly as given. State it is an alignment score, not a hiring probability. "
        f"{gemini_service.NO_INVENTION_RULES}\n\nRESULT:\n{json.dumps(facts)}"
    )
    data = gemini_service.cached_json(db, "career_fit", (input_hash,), prompt)
    if data and isinstance(data.get("explanation"), str):
        def lst(k: str) -> list[str]:
            v = data.get(k)
            return [str(x) for x in v][:5] if isinstance(v, list) and v else rb[k]
        return data["explanation"], {"strengths": lst("strengths"), "gaps": lst("gaps"), "recommendations": lst("recommendations")}, "gemini"
    return fallback, rb, "rule_based"


# ------------------------------------------------------------------ public API
def _student_texts(f: dict[str, Any]) -> dict[str, str]:
    return {
        "technical": " ".join(f["skills"]),
        "education": f["education_text"],
        "projects": f["project_text"],
        "experience": f["experience_text"],
        "certifications": f["certification_text"],
    }


def _hash(f: dict[str, Any], weights: dict[str, float], c: Career) -> str:
    payload = json.dumps({"f": {k: v for k, v in f.items() if k != "interest_titles"}, "w": weights, "c": c.id, "u": str(c.last_updated)}, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def _all_careers(db: Session) -> list[Career]:
    return list(db.scalars(select(Career).options(selectinload(Career.skills), selectinload(Career.qualifications), selectinload(Career.trajectory)).order_by(Career.id)))


def _stored(u: UserCareerFit, c: Career, f: dict[str, Any]) -> dict[str, Any]:
    return {
        "career_id": c.id, "career_title": c.title, "score": u.score, "components": u.components, "weights": u.weights,
        "strengths": u.strengths, "gaps": u.gaps, "recommendations": u.recommendations, "explanation": u.explanation,
        "explanation_source": u.explanation_source, "profile_ready": True, "cached": True,
        "targeted_by_student": any(t.lower() in c.title.lower() or c.title.lower() in t.lower() for t in f["interest_titles"]),
        "disclaimer": "Alignment score between your profile and this role's requirements. It is not a probability of being hired.",
    }


def analyse(db: Session, user: User, career: Career) -> dict[str, Any]:
    f = student_features(db, user)
    if not profile_has_data(f):
        return {"career_id": career.id, "career_title": career.title, "profile_ready": False,
                "message": "Add skills, education, projects or upload a resume first. Career Fit needs profile data to compare."}
    weights = get_weights()
    h = _hash(f, weights, career)
    existing = db.scalar(select(UserCareerFit).where(UserCareerFit.user_id == user.id, UserCareerFit.career_id == career.id))
    if existing and existing.input_hash == h:
        return _stored(existing, career, f)

    careers = _all_careers(db)
    cos = _component_cosines(_student_texts(f), careers)
    r = _score_one(career, f, cos[career.id], weights)
    rb = _rule_based(career, f, r)
    explanation, parts, source = _explain(db, career, r, rb, h)
    if existing is None:
        existing = UserCareerFit(user_id=user.id, career_id=career.id, score=r["score"], input_hash=h)
        db.add(existing)
    existing.score, existing.components, existing.weights, existing.input_hash = r["score"], r["components"], weights, h
    existing.strengths, existing.gaps, existing.recommendations = parts["strengths"], parts["gaps"], parts["recommendations"]
    existing.explanation, existing.explanation_source = explanation, source
    db.commit()
    out = _stored(existing, career, f)
    out["cached"] = False
    return out


def recommend(db: Session, user: User, limit: int = 8) -> dict[str, Any]:
    """Rank every career by alignment. Pure scikit-learn; no Gemini, nothing stored."""
    f = student_features(db, user)
    if not profile_has_data(f):
        return {"profile_ready": False, "message": "Complete your profile or upload a resume to get personalised career recommendations.", "scores": {}, "top": []}
    careers = _all_careers(db)
    weights = get_weights()
    cos = _component_cosines(_student_texts(f), careers)
    scored = [_score_one(c, f, cos[c.id], weights) for c in careers]
    by_id = {c.id: c for c in careers}
    scored.sort(key=lambda r: -r["score"])
    return {
        "profile_ready": True,
        "scores": {str(r["career_id"]): r["score"] for r in scored},
        "top": [
            {"career_id": r["career_id"], "slug": by_id[r["career_id"]].slug, "title": by_id[r["career_id"]].title, "industry": by_id[r["career_id"]].industry,
             "score": r["score"], "matched_skills": r["matched_skills"][:4]}
            for r in scored[:limit]
        ],
        "weights": weights,
        "disclaimer": "Ranking shows alignment with each role's requirements. Every profession remains open to explore.",
    }
