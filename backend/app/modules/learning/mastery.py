"""Topic mastery from several independent signals (never from 'pages opened').

Signals: difficulty- and recency-weighted accuracy, subtopic coverage, coding
performance, retention (spaced-repetition outcomes) and improvement across
sessions. Missing signals are dropped and the weights re-normalised.
"""

from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass
from typing import Any

DIFF_WEIGHT = {"easy": 1.0, "medium": 1.6, "hard": 2.2}
WEIGHTS = {"accuracy": 0.45, "coverage": 0.15, "coding": 0.15, "retention": 0.15, "trend": 0.10}
HALF_LIFE_DAYS = 30.0
STATUSES = ("not_started", "learning", "developing", "needs_revision", "strong", "mastered")


@dataclass
class AttemptSignal:
    fraction: float  # 0..1 score on the question
    difficulty: str
    subtopic: str | None
    session_id: int
    when: dt.datetime
    is_coding: bool = False


def _recency(when: dt.datetime, now: dt.datetime) -> float:
    age = max(0.0, (now - when).total_seconds() / 86400)
    return 0.5 ** (age / HALF_LIFE_DAYS)


def compute(
    attempts: list[AttemptSignal],
    *,
    known_subtopics: int = 0,
    srs_reps: int = 0,
    srs_lapses: int = 0,
    revision_overdue: bool = False,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    now = now or dt.datetime.now(dt.timezone.utc)
    if not attempts:
        return {"score": 0.0, "status": "not_started", "signals": {}, "sessions": 0}

    w = [DIFF_WEIGHT.get(a.difficulty, 1.3) * _recency(a.when, now) for a in attempts]
    accuracy = sum(wi * a.fraction for wi, a in zip(w, attempts)) / (sum(w) or 1)

    subs = {a.subtopic for a in attempts if a.subtopic}
    denom = max(known_subtopics, len(subs), 3)
    coverage = min(1.0, len(subs) / denom) if subs else None

    coding = [a.fraction for a in attempts if a.is_coding]
    coding_score = sum(coding) / len(coding) if coding else None

    reviews = srs_reps + srs_lapses
    retention = srs_reps / reviews if reviews else None

    per_session: dict[int, list[AttemptSignal]] = {}
    for a in attempts:
        per_session.setdefault(a.session_id, []).append(a)
    ordered = sorted(per_session.values(), key=lambda g: min(x.when for x in g))
    session_acc = [sum(x.fraction for x in g) / len(g) for g in ordered]
    trend = None
    if len(session_acc) >= 2:
        trend = max(0.0, min(1.0, 0.5 + (session_acc[-1] - session_acc[0])))

    signals = {"accuracy": accuracy, "coverage": coverage, "coding": coding_score, "retention": retention, "trend": trend}
    active = {k: v for k, v in signals.items() if v is not None}
    total_w = sum(WEIGHTS[k] for k in active)
    score = 100 * sum(WEIGHTS[k] * v for k, v in active.items()) / total_w
    sessions = len(per_session)
    last_acc = session_acc[-1]
    best_acc = max(session_acc)

    if revision_overdue and score >= 50 or (sessions >= 2 and last_acc < 0.5 <= best_acc - 0.15):
        status = "needs_revision"
    elif score >= 85 and sessions >= 3 and (coverage or 0) >= 0.7 and (retention is None or retention >= 0.75):
        status = "mastered"
    elif score >= 65:
        status = "strong"
    elif score >= 40:
        status = "developing"
    else:
        status = "learning"
    return {
        "score": round(score, 1),
        "status": status,
        "sessions": sessions,
        "signals": {k: (None if v is None else round(v, 3)) for k, v in signals.items()},
    }


def topic_key(topic: str) -> str:
    return " ".join(topic.lower().split())[:200]
