"""Interview communication analysis: pure functions and the end-to-end report (Gemini stubbed in tests only)."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.routes import interviews
from app.db.session import SessionLocal
from app.main import app
from app.models import User
from app.modules import interview_speech as sp

PW = "Test@12345!Speech"
CLEAN = ("First, I profiled the endpoint and found that N+1 queries caused latency of 900 ms. Therefore I introduced eager loading, which reduced the response time by 60 percent. "
         "For example, the orders listing dropped from 900 to 360 milliseconds, and as a result support tickets fell noticeably across the quarter.")
MESSY = ("So, um, I think basically what I did was, like, I built a REST API. You know, it was kind of a big project and I guess it went okay. "
         "Maybe we could have done better because the requirements changed, you know, like, um.")


def test_fillers_counted_and_ranked():
    assert sp.filler_report(MESSY)["per_100_words"] > sp.filler_report(CLEAN)["per_100_words"]
    top = {t["word"] for t in sp.filler_report(MESSY)["top"]}
    assert {"um", "you know"} <= top


def test_clarity_rewards_structure_and_penalises_hedging():
    assert sp.clarity(CLEAN)["score"] > sp.clarity(MESSY)["score"]
    assert sp.clarity(MESSY)["hedges"] >= 3


def test_short_text_is_not_scored():
    assert sp.vocabulary("Yes.")["available"] is False
    assert sp.filler_report("Yes.")["available"] is False


def test_filler_words_never_count_as_advanced_vocabulary():
    v = sp.vocabulary(MESSY + " " + CLEAN)
    assert "basically" not in v["advanced_words"]


def test_delivery_only_from_spoken_answers():
    assert sp.delivery([])["available"] is False
    ok = sp.delivery([{"spoken": True, "words": 60, "spoken_seconds": 24, "total_seconds": 28, "long_pauses": 1, "volume_mean": 0.04, "volume_cv": 0.3}])
    assert ok["available"] and 100 <= ok["words_per_minute"] <= 160
    fast = sp.delivery([{"spoken": True, "words": 120, "spoken_seconds": 25, "total_seconds": 26, "long_pauses": 0, "volume_mean": 0.04, "volume_cv": 0.3}])
    assert fast["words_per_minute"] > 175 and any("fast" in n for n in fast["notes"])
    # a clip too short to judge is ignored, not guessed at
    assert sp.delivery([{"spoken": True, "words": 5, "spoken_seconds": 2, "total_seconds": 3, "long_pauses": 0}])["available"] is False


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def test_report_includes_communication(client, monkeypatch):
    async def fake(prompt: str):
        if "final report" in prompt:
            return {"overall_score": 70, "category_scores": {"technical": 70}, "strengths": [], "weaknesses": [], "improvement_areas": [], "skill_gaps": [], "preparation_recommendations": [], "question_feedback": []}
        if "Evaluate the most recent" in prompt:
            return {"evaluation": {"score": 70, "feedback": "ok", "strengths": [], "improvements": []}, "next_question": "Next?", "next_category": "technical", "next_persona": "Technical Interviewer", "closing": False}
        return {"question": "Tell me about a project.", "category": "technical", "persona": "Technical Interviewer"}

    monkeypatch.setattr(interviews, "_gemini", fake)
    name = "sp" + uuid.uuid4().hex[:10]
    r = client.post("/api/auth/register", json={"full_name": "Speech Test", "email": f"{name}@example.com", "username": name, "password": PW, "confirm_password": PW})
    assert r.status_code == 201, r.text
    hdr = {"Authorization": f"Bearer {r.json()['access_token']}"}
    try:
        s = client.post("/api/interviews", headers=hdr, json={"domain": "Software Engineering", "personas": ["Technical Interviewer"], "focus": {"technical": 60, "behavioural": 40}})
        assert s.status_code in (200, 201), s.text
        sid = s.json()["id"]
        voice = {"spoken": True, "words": 60, "spoken_seconds": 24, "total_seconds": 28, "long_pauses": 1, "volume_mean": 0.04, "volume_cv": 0.3}
        for i, text in enumerate([MESSY, CLEAN, CLEAN]):
            a = client.post(f"/api/interviews/{sid}/answer", headers=hdr, json={"answer": text, **({"voice": voice} if i == 0 else {})})
            assert a.status_code == 200, a.text
        # absurd client values are rejected, not stored
        assert client.post(f"/api/interviews/{sid}/answer", headers=hdr, json={"answer": "x", "voice": {"spoken": True, "words": -5}}).status_code in (409, 422)
        end = client.post(f"/api/interviews/{sid}/end", headers=hdr, json={"integrity_signals": []})
        assert end.status_code == 200, end.text
        comm = end.json()["report"]["communication"]
        assert comm["fillers"]["available"] and comm["delivery"]["available"] and comm["vocabulary"]["available"]
        assert comm["per_answer"][0]["spoken"] is True and comm["per_answer"][1]["spoken"] is False
    finally:
        with SessionLocal() as db:
            u = db.scalar(select(User).where(User.username == name))
            if u:
                db.delete(u)
                db.commit()
