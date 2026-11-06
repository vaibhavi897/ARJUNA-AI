"""Recompute stored topic proficiency from quiz attempts, SRS state and revision lateness."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import QuizAttempt, QuizQuestion, QuizSession, RevisionSchedule, TopicProficiency, User
from app.modules.learning import mastery


def recompute_topic(db: Session, user: User, topic: str) -> TopicProficiency:
    key = mastery.topic_key(topic)
    rows = db.execute(
        select(QuizAttempt, QuizQuestion, QuizSession)
        .join(QuizQuestion, QuizQuestion.id == QuizAttempt.question_id)
        .join(QuizSession, QuizSession.id == QuizAttempt.session_id)
        .where(QuizAttempt.user_id == user.id, QuizSession.status == "submitted")
    ).all()
    mine = [(a, q, s) for a, q, s in rows if mastery.topic_key(q.topic) == key and a.evaluated_by != "unavailable"]
    signals = [
        mastery.AttemptSignal(
            fraction=a.score / q.points if q.points else 0.0, difficulty=q.difficulty, subtopic=q.subtopic, session_id=s.id,
            when=a.created_at or dt.datetime.now(dt.timezone.utc), is_coding=q.qtype in ("coding", "debugging"),
        )
        for a, q, s in mine
    ]
    known = len({q.subtopic for _, q, _ in mine if q.subtopic})
    srs_row = db.scalar(select(RevisionSchedule).where(RevisionSchedule.user_id == user.id, RevisionSchedule.topic_key == key))
    overdue = bool(srs_row and srs_row.due_date < dt.date.today() - dt.timedelta(days=3) and srs_row.repetitions > 0)
    res = mastery.compute(signals, known_subtopics=max(known, 3), srs_reps=srs_row.repetitions if srs_row else 0, srs_lapses=srs_row.lapses if srs_row else 0, revision_overdue=overdue)

    row = db.scalar(select(TopicProficiency).where(TopicProficiency.user_id == user.id, TopicProficiency.topic_key == key))
    if row is None:
        row = TopicProficiency(user_id=user.id, topic_key=key, topic=topic[:200])
        db.add(row)
    row.mastery_score, row.status, row.attempts, row.signals = res["score"], res["status"], len(signals), {**res["signals"], "sessions": res.get("sessions", 0)}
    if signals:
        row.last_assessed_at = max(s.when for s in signals)
    db.flush()
    return row
