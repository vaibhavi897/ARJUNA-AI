"""One score email per interview, and only for a completed, analysed session."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.routes import interviews
from app.db.session import SessionLocal
from app.main import app
from app.models import InterviewSession, User
from app.modules import interview_email, mailer

PW = "Test@12345!Email"
ANSWER = ("I profiled the endpoint, found N+1 queries behind a 900 ms response, introduced eager loading "
          "and brought the listing down to 360 ms, which cut the support tickets we saw that quarter.")


async def _fake_gemini(prompt: str):
    if "final report" in prompt:
        return {"overall_score": 72, "category_scores": {"technical": 72}, "strengths": [], "weaknesses": [],
                "improvement_areas": [], "skill_gaps": [], "preparation_recommendations": [], "question_feedback": []}
    if "Evaluate the most recent" in prompt:
        return {"evaluation": {"score": 72, "feedback": "ok", "strengths": [], "improvements": []},
                "next_question": "Next?", "next_category": "technical",
                "next_persona": "Technical Interviewer", "closing": False}
    return {"question": "Tell me about a project.", "category": "technical", "persona": "Technical Interviewer"}


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def sent(monkeypatch):
    """Capture every message the mailer is asked to send."""
    messages: list[dict[str, str]] = []

    def fake_send(to, subject, text_body, html_body=None, *, bcc=None, from_name="Arjuna AI"):
        messages.append({"to": to, "subject": subject})
        return True

    monkeypatch.setattr(mailer, "is_configured", lambda: True)
    monkeypatch.setattr(mailer, "send", fake_send)
    return messages


@pytest.fixture()
def account(client):
    name = "em" + uuid.uuid4().hex[:10]
    r = client.post("/api/auth/register", json={"full_name": "Email Test", "email": f"{name}@example.com",
                                                "username": name, "password": PW, "confirm_password": PW})
    assert r.status_code == 201, r.text
    yield name, {"Authorization": f"Bearer {r.json()['access_token']}"}
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == name))
        if user:
            db.delete(user)
            db.commit()


def _start(client, hdr) -> int:
    s = client.post("/api/interviews", headers=hdr, json={"domain": "Software Engineering",
                                                          "personas": ["Technical Interviewer"],
                                                          "focus": {"technical": 60, "behavioural": 40}})
    assert s.status_code in (200, 201), s.text
    return s.json()["id"]


def _stamp(session_id: int) -> str | None:
    with SessionLocal() as db:
        return db.get(InterviewSession, session_id).score_email_sent_at


def test_completed_interview_with_analysis_is_emailed_exactly_once(client, monkeypatch, sent, account):
    monkeypatch.setattr(interviews, "_gemini", _fake_gemini)
    _, hdr = account
    sid = _start(client, hdr)
    for _ in range(3):
        assert client.post(f"/api/interviews/{sid}/answer", headers=hdr, json={"answer": ANSWER}).status_code == 200

    end = client.post(f"/api/interviews/{sid}/end", headers=hdr, json={"integrity_signals": []})
    assert end.status_code == 200, end.text
    assert end.json()["report"]["sufficient_data"] is True
    assert len(sent) == 1, sent
    assert "72/100" in sent[0]["subject"]
    assert _stamp(sid) is not None

    # Ending again (a retry, a double click, a replayed request) sends nothing.
    assert client.post(f"/api/interviews/{sid}/end", headers=hdr, json={"integrity_signals": []}).status_code == 200
    assert len(sent) == 1, sent


def test_interview_without_analysis_is_not_emailed(client, monkeypatch, sent, account):
    monkeypatch.setattr(interviews, "_gemini", _fake_gemini)
    _, hdr = account
    sid = _start(client, hdr)
    # One attempted answer is below the threshold for a report, so the session
    # ends with sufficient_data false and there is no score to email.
    assert client.post(f"/api/interviews/{sid}/answer", headers=hdr, json={"answer": ANSWER}).status_code == 200

    end = client.post(f"/api/interviews/{sid}/end", headers=hdr, json={"integrity_signals": []})
    assert end.status_code == 200, end.text
    assert end.json()["report"]["sufficient_data"] is False
    assert sent == []
    assert _stamp(sid) is None


def test_prepare_refuses_unfinished_unanalysed_and_already_sent(client, monkeypatch, sent, account):
    monkeypatch.setattr(interviews, "_gemini", _fake_gemini)
    name, hdr = account
    sid = _start(client, hdr)
    for _ in range(3):
        assert client.post(f"/api/interviews/{sid}/answer", headers=hdr, json={"answer": ANSWER}).status_code == 200

    with SessionLocal() as db:
        session = db.get(InterviewSession, sid)
        user = db.scalar(select(User).where(User.username == name))

        # still running
        assert interview_email.prepare(session, user) is None

        # completed, but the report carries no analysis
        session.status = "completed"
        session.report = {"sufficient_data": False, "attempted_count": 3}
        assert interview_email.prepare(session, user) is None

        # completed and analysed: this one is worth sending
        session.report = {"sufficient_data": True, "overall_score": 72, "attempted_count": 3}
        assert interview_email.prepare(session, user) is not None

        # ...but only until it has been sent once
        session.score_email_sent_at = "2026-11-08T00:00:00+00:00"
        assert interview_email.prepare(session, user) is None
