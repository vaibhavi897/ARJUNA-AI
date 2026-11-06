"""Skill-gap analysis: compare the student's EXISTING profile with a track's taxonomy.

Transparent method (no model training): token overlap + TF-IDF cosine between
the learner's profile text (skills, projects, experience, education,
certifications from the existing tables) and each topic title. Gemini only
explains the result in plain language.
"""

from __future__ import annotations

import re
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.models import LearningTopic, LearningTrack, User
from app.modules.careerverse import career_fit_service, gemini_service
from app.modules.learning import ai

logger = get_logger(__name__)
STOP = {"and", "the", "for", "with", "basics", "fundamentals", "core", "essentials", "introduction", "to", "of", "in", "or", "practice", "using"}


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9+#.]{2,}", text.lower()) if t not in STOP}


def profile_text(db: Session, user: User) -> tuple[str, dict[str, Any]]:
    f = career_fit_service.student_features(db, user)
    text = " ".join([" ".join(f["skills"]), f["education_text"], f["project_text"], f["experience_text"], f["certification_text"]])
    return text, f


def analyse(db: Session, user: User, track: LearningTrack, skip: list[str] | None = None, existing_knowledge: str = "") -> dict[str, Any]:
    text, f = profile_text(db, user)
    text = f"{text} {existing_knowledge}".strip()
    topics: list[LearningTopic] = [t for t in track.topics]
    skip_set = {s.lower() for s in (skip or [])}
    ptokens = _tokens(text)

    scores: dict[str, float] = {}
    if text.strip() and topics:
        vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
        m = vec.fit_transform([t.title for t in topics] + [text])
        sims = cosine_similarity(m[-1], m[:-1]).ravel()
        scores = {t.slug: float(s) for t, s in zip(topics, sims)}

    matched, missing = [], []
    for t in topics:
        title_tokens = _tokens(t.title)
        overlap = len(title_tokens & ptokens) / len(title_tokens) if title_tokens else 0.0
        known = overlap >= 0.6 or scores.get(t.slug, 0.0) >= 0.22 or t.title.lower() in skip_set or t.slug in skip_set
        (matched if known else missing).append(t)

    def cover(phase: str) -> float:
        group = [t for t in topics if t.phase == phase]
        return round(sum(1 for t in group if t in matched) / len(group), 2) if group else 0.0

    coverage = {p: cover(p) for p in ("foundation", "intermediate", "advanced")}
    if coverage["foundation"] >= 0.85 and coverage["intermediate"] >= 0.5:
        level = "advanced"
    elif coverage["foundation"] >= 0.55:
        level = "intermediate"
    else:
        level = "beginner"
    has_profile = bool(text.strip())
    return {
        "starting_level": level,
        "profile_has_data": has_profile,
        "coverage": coverage,
        "matched": [t.slug for t in matched],
        "missing": [t.slug for t in missing],
        "matched_titles": [t.title for t in matched],
        "missing_titles": [t.title for t in missing],
        "topic_scores": {k: round(v, 3) for k, v in scores.items()},
        "method": "token overlap + TF-IDF cosine against your existing profile (skills, projects, experience, education, certifications)",
    }


def explain(db: Session, role: str, analysis: dict[str, Any]) -> dict[str, Any]:
    """Gemini explanation, cached. Falls back to a rule-based summary."""
    key = gemini_service.make_key("skill_gap", role, analysis["starting_level"], analysis["matched"], analysis["missing"])
    cached = gemini_service.get_cached(db, key)
    if cached:
        return {**cached, "source": "gemini"}
    if gemini_service.is_enabled():
        try:
            out = ai.explain_gap(role, analysis["starting_level"], analysis["matched_titles"], analysis["missing_titles"])
            gemini_service.put_cached(db, key, "skill_gap", out)
            return {**out, "source": "gemini"}
        except gemini_service.GeminiUnavailable as exc:
            logger.warning("skill-gap explanation unavailable: %s", exc)
    matched, missing = analysis["matched_titles"], analysis["missing_titles"]
    return {
        "summary": f"Your profile supports {len(matched)} of {len(matched) + len(missing)} topics in this track. Starting level estimated as {analysis['starting_level']}.",
        "strengths": matched[:4],
        "priority_gaps": missing[:5],
        "advice": ["Start with the foundation topics you have not yet evidenced.", "Add projects and skills to your profile as you learn so the plan adapts."],
        "source": "rule_based",
    }
