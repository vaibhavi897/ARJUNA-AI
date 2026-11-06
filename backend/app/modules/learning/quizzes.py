"""On-demand assessments: Gemini writes the questions; the backend scores them."""

from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.logging_config import get_logger
from app.models import LearningPlan, LearningTask, QuizAttempt, QuizQuestion, QuizSession, TopicProficiency, User
from app.modules.careerverse import gemini_service
from app.modules.learning import ai, evaluation, events, mastery, mastery_service, revision, tasks as task_service

logger = get_logger(__name__)
DIFF_POINTS = {"easy": 1.0, "medium": 2.0, "hard": 3.0}
DEFAULT_TYPES = ["mcq", "true_false", "short_answer"]
ALL_TYPES = ["mcq", "true_false", "output_prediction", "code_tracing", "short_answer", "scenario", "coding", "debugging"]


class QuizError(RuntimeError):
    pass


def _valid(q: dict[str, Any]) -> dict[str, Any] | None:
    """Normalise one generated question into DB fields, or reject it."""
    t = q["qtype"]
    key: dict[str, Any] = {}
    rubric: list[dict[str, Any]] = []
    options = [str(o) for o in q.get("options", [])]
    tests = q.get("test_cases", [])
    if t == "mcq":
        if len(options) < 3 or q.get("answer_index") is None or not 0 <= q["answer_index"] < len(options):
            return None
        key = {"index": q["answer_index"]}
    elif t == "true_false":
        if q.get("answer_bool") is None:
            return None
        key, options = {"value": bool(q["answer_bool"])}, []
    elif t in ("output_prediction", "code_tracing"):
        if not (q.get("answer_text") or "").strip():
            return None
        key, options = {"answer": q["answer_text"].strip(), "alternatives": q.get("alternatives", [])}, []
    elif t in ("short_answer", "scenario"):
        rubric = [{"criterion": str(c.get("criterion", "")).strip(), "marks": float(c.get("marks", 1))} for c in q.get("rubric", []) if str(c.get("criterion", "")).strip()]
        if not rubric:
            rubric = [{"criterion": "Accuracy and completeness of the key points", "marks": 3.0}, {"criterion": "Clarity of reasoning", "marks": 2.0}]
        key = {"model_answer": q.get("answer_text") or ""}
        options = []
    elif t in ("coding", "debugging"):
        entry, ref = q.get("entry_function"), q.get("reference_solution")
        if not entry or not ref or len(tests) < 2:
            return None
        run = evaluation.run_sandboxed(ref, entry, tests)
        if "fatal" in run or not all(r.get("ok") for r in run.get("results", [])):
            logger.info("dropped coding question: reference solution failed its own tests")
            return None
        key, options = {"entry_function": entry, "reference_solution": ref}, []
        rubric = []
    else:
        return None
    return {"qtype": t, "difficulty": q.get("difficulty", "medium"), "topic": q["topic"], "subtopic": q.get("subtopic") or None, "prompt": q["prompt"], "options": options,
            "answer_key": key, "explanation": q.get("explanation") or None, "rubric": rubric, "test_cases": tests if t in ("coding", "debugging") else [], "starter_code": q.get("starter_code") if t in ("coding", "debugging") else None}


def _scope_topics(db: Session, user: User, scope: str, topic: str, plan: LearningPlan | None, week: int | None) -> tuple[str, str, list[str]]:
    """Return (topic label, scope note for the prompt, weak topics)."""
    weak = [r.topic for r in db.scalars(select(TopicProficiency).where(TopicProficiency.user_id == user.id, TopicProficiency.status.in_(("learning", "developing", "needs_revision"))).order_by(TopicProficiency.mastery_score).limit(8))]
    if scope == "revision":
        if not weak:
            raise QuizError("You have no weak topics yet. Take a topic quiz first, then revision quizzes will target what you struggled with.")
        return "Revision: " + ", ".join(weak[:4]), f"This is a REVISION quiz. Cover these topics the student struggled with: {', '.join(weak)}.", weak
    if scope in ("week", "roadmap"):
        if plan is None:
            raise QuizError("Create a learning plan first to quiz your weekly or roadmap material.")
        q = select(LearningTask).where(LearningTask.plan_id == plan.id, LearningTask.category.in_(("learn", "practice", "project")), LearningTask.topic.is_not(None))
        rows = list(db.scalars(q.order_by(LearningTask.date)))
        if scope == "week":
            if not week:
                raise QuizError("Choose which week to quiz.")
            lo = plan.start_date + dt.timedelta(days=(week - 1) * 7)
            rows = [t for t in rows if lo <= t.date < lo + dt.timedelta(days=7)]
        else:
            rows = [t for t in rows if t.status in ("completed", "partial")] or rows
        topics = list(dict.fromkeys(t.topic for t in rows if t.topic))
        if not topics:
            raise QuizError("No studied topics found for that range yet.")
        label = f"Week {week} review" if scope == "week" else "Full roadmap review"
        return label, f"Cover these topics, spread evenly: {', '.join(topics[:20])}.", weak
    return topic.strip(), ("Cover the whole subject broadly across its main areas." if scope == "subject" else "Focus tightly on this topic and its subtopics."), weak


def generate(db: Session, user: User, *, topic: str, scope: str, count: int, difficulty: str, time_limit: int | None, types: list[str], plan: LearningPlan | None, week: int | None, level: str, retry_of: QuizSession | None = None) -> QuizSession:
    label, note, weak = _scope_topics(db, user, scope, topic, plan, week)
    types = [t for t in (types or DEFAULT_TYPES) if t in ALL_TYPES] or DEFAULT_TYPES
    if retry_of:
        previous = [q.prompt[:90] for q in retry_of.questions]
        note += f" These questions were used before; write DIFFERENT ones testing the same ideas: {previous}"
    collected: list[dict[str, Any]] = []
    for attempt in range(2):
        need = count - len(collected)
        if need <= 0:
            break
        try:
            raw = ai.quiz_questions(topic=label, scope_note=note, count=need + (2 if attempt == 0 and any(t in types for t in ("coding", "debugging")) else 0), difficulty=difficulty, types=types, level=level, weak=weak, language="Python")
        except gemini_service.GeminiUnavailable as exc:
            if collected:
                break
            raise QuizError(f"Gemini could not write this quiz right now. Please try again shortly. ({str(exc)[:100]})") from exc
        for q in raw:
            v = _valid(q)
            if v:
                collected.append(v)
    if not collected:
        raise QuizError("The generated questions did not pass validation. Please try again.")
    collected = collected[:count]
    s = QuizSession(user_id=user.id, plan_id=plan.id if plan else None, topic=label[:240], scope=scope, config={"count": count, "difficulty": difficulty, "types": types, "level": level, "week": week, "requested_topic": topic}, time_limit_minutes=time_limit, retry_of=retry_of.id if retry_of else None)
    db.add(s)
    db.flush()
    for i, v in enumerate(collected, 1):
        pts = DIFF_POINTS.get(v["difficulty"], 2.0) + (1.0 if v["qtype"] in ("coding", "debugging") else 0.0)
        db.add(QuizQuestion(session_id=s.id, position=i, points=pts, **v))
    events.log(db, user.id, "quiz_generated", "quiz", s.id, topic=label, scope=scope, count=len(collected))
    db.commit()
    return load(db, user, s.id)


def load(db: Session, user: User, session_id: int) -> QuizSession:
    s = db.scalar(select(QuizSession).options(selectinload(QuizSession.questions)).where(QuizSession.id == session_id, QuizSession.user_id == user.id))
    if s is None:
        raise LookupError("Quiz not found")
    return s


def session_out(s: QuizSession, reveal: bool = False) -> dict[str, Any]:
    qs = []
    for q in s.questions:
        d = {"id": q.id, "position": q.position, "qtype": q.qtype, "difficulty": q.difficulty, "topic": q.topic, "subtopic": q.subtopic, "prompt": q.prompt, "options": q.options, "points": q.points, "starter_code": q.starter_code,
             "entry_function": q.answer_key.get("entry_function") if q.qtype in ("coding", "debugging") else None, "examples": q.test_cases[:2] if q.qtype in ("coding", "debugging") else []}
        if reveal:
            d.update(answer_key={k: v for k, v in q.answer_key.items()}, explanation=q.explanation, rubric=q.rubric)
        qs.append(d)
    return {"id": s.id, "topic": s.topic, "scope": s.scope, "status": s.status, "config": s.config, "time_limit_minutes": s.time_limit_minutes, "started_at": s.started_at.isoformat() if s.started_at else None,
            "score": s.score, "max_score": s.max_score, "questions": qs}


def submit(db: Session, user: User, s: QuizSession, answers: dict[int, dict[str, Any]]) -> dict[str, Any]:
    if s.status == "submitted":
        return s.report
    now = dt.datetime.now(dt.timezone.utc)
    taken = int((now - s.started_at).total_seconds())
    overtime = bool(s.time_limit_minutes and taken > s.time_limit_minutes * 60 + 30)
    total = got = 0.0
    for q in s.questions:
        resp = answers.get(q.id, {}) or {}
        fb: dict[str, Any] = {}
        by = "deterministic"
        if q.qtype in evaluation.OBJECTIVE:
            frac, fb = evaluation.score_objective(q.qtype, q.answer_key, resp)
        elif q.qtype in evaluation.CODING:
            frac, fb = evaluation.score_coding(q.answer_key, q.test_cases, str(resp.get("code", "")))
            by = "sandbox"
        else:
            frac, fb, by = evaluation.score_subjective(q.prompt, q.rubric, str(resp.get("text", "")))
        score = round(frac * q.points, 3)
        total += q.points
        if by != "unavailable":
            got += score
        db.add(QuizAttempt(session_id=s.id, question_id=q.id, user_id=user.id, response=resp, score=score, is_correct=frac >= 0.999, evaluated_by=by, feedback=fb))
    s.status, s.submitted_at, s.time_taken_seconds, s.score, s.max_score = "submitted", now, taken, round(got, 2), round(total, 2)
    db.flush()
    s.report = build_report(db, user, s, overtime)
    events.log(db, user.id, "quiz_submitted", "quiz", s.id, accuracy=s.report["accuracy"], topic=s.topic, seconds=taken)
    # learning loop: spaced repetition, mastery, planner revision tasks
    for t in s.report["by_topic"]:
        revision.record_review(db, user, t["topic"], t["accuracy"] / 100)
        mastery_service.recompute_topic(db, user, t["topic"])
    plan = db.get(LearningPlan, s.plan_id) if s.plan_id else task_service.active_plan(db, user)
    if plan:
        revision.sync_revision_tasks(db, user, plan)
    db.commit()
    return s.report


def build_report(db: Session, user: User, s: QuizSession, overtime: bool = False) -> dict[str, Any]:
    attempts = {a.question_id: a for a in db.scalars(select(QuizAttempt).where(QuizAttempt.session_id == s.id))}
    topics: dict[str, dict[str, float]] = {}
    sub: dict[str, dict[str, float]] = {}
    wrong, ungraded = [], 0
    for q in s.questions:
        a = attempts[q.id]
        if a.evaluated_by == "unavailable":
            ungraded += 1
            continue
        for bucket, k in ((topics, q.topic), (sub, f"{q.topic} > {q.subtopic}" if q.subtopic else None)):
            if k:
                b = bucket.setdefault(k, {"got": 0.0, "max": 0.0})
                b["got"] += a.score
                b["max"] += q.points
        if not a.is_correct:
            wrong.append({"question_id": q.id, "position": q.position, "qtype": q.qtype, "difficulty": q.difficulty, "topic": q.topic, "subtopic": q.subtopic, "prompt": q.prompt, "your_answer": a.response, "score": a.score, "points": q.points,
                          "correct": q.answer_key if q.qtype != "coding" else {"reference_solution": q.answer_key.get("reference_solution")}, "explanation": q.explanation, "feedback": a.feedback})

    def rows(bucket: dict[str, dict[str, float]]) -> list[dict[str, Any]]:
        return sorted(({"topic": k, "accuracy": round(100 * v["got"] / v["max"], 1) if v["max"] else 0.0, "score": round(v["got"], 2), "max": v["max"]} for k, v in bucket.items()), key=lambda r: r["accuracy"])

    by_topic, by_sub = rows(topics), rows(sub)
    max_graded = sum(q.points for q in s.questions if attempts[q.id].evaluated_by != "unavailable")
    accuracy = round(100 * (s.score or 0) / max_graded, 1) if max_graded else 0.0
    strong = [r["topic"] for r in by_sub + by_topic if r["accuracy"] >= 80][:6]
    weak = [r["topic"] for r in by_sub + by_topic if r["accuracy"] < 60][:6]
    return {
        "session_id": s.id, "topic": s.topic, "score": s.score, "max_score": s.max_score, "accuracy": accuracy, "time_taken_seconds": s.time_taken_seconds, "time_limit_minutes": s.time_limit_minutes,
        "overtime": overtime, "questions": len(s.questions), "correct": sum(1 for a in attempts.values() if a.is_correct), "ungraded": ungraded,
        "by_topic": by_topic, "by_subtopic": by_sub, "strong_areas": strong, "weak_areas": weak, "incorrect": wrong,
        "recommended_revisions": [{"topic": w, "reason": "Scored below 60% in this assessment."} for w in weak] or [{"topic": "Keep going", "reason": "No weak areas detected this time. Try a harder quiz."}],
    }
