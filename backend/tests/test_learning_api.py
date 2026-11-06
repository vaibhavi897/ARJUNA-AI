"""Integration tests for the AI Learning Hub API.

Runs against the real FastAPI app and database with throw-away users. Gemini is
stubbed here (tests only) so results are deterministic and offline; the stubs
return the same shapes the real schemas validate.
"""

import datetime as dt
import itertools
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.session import SessionLocal
from app.main import app
from app.models import User
from app.modules.learning import ai, evaluation, skill_gap, youtube

PW = "Test@12345!Learning"
TODAY = dt.date.today()
_counter = itertools.count()


def fake_units(**kw):
    n = max(2, int(kw["budget_minutes"] / 70))
    return [dict(title=f"{kw['phase_title']} unit {i}", topic=f"{kw['phase_key']} topic {i // 2}", subtopics=["a", "b"], objectives=["o1"], assignment="Do the exercise", est_minutes=70, difficulty="medium",
                 category="project" if kw["phase_key"] == "projects" else "learn", resources=[{"kind": "docs", "name": "Official docs", "search_query": "topic docs"}]) for i in range(n)]


def fake_questions(**kw):
    k = next(_counter)
    return [
        dict(qtype="mcq", difficulty="easy", topic=kw["topic"], subtopic="basics", prompt=f"MCQ {k}?", options=["a", "b", "c", "d"], answer_index=1, explanation="because b"),
        dict(qtype="true_false", difficulty="medium", topic=kw["topic"], subtopic="basics", prompt=f"TF {k}", answer_bool=True, explanation="true"),
        dict(qtype="output_prediction", difficulty="hard", topic=kw["topic"], subtopic="advanced", prompt=f"print(1+{k})", answer_text=str(1 + k), alternatives=[], explanation="arithmetic"),
        dict(qtype="short_answer", difficulty="medium", topic=kw["topic"], subtopic="advanced", prompt=f"Explain {k}", rubric=[{"criterion": "Key idea", "marks": 2}], explanation="x"),
        dict(qtype="coding", difficulty="medium", topic=kw["topic"], subtopic="coding", prompt=f"Add two numbers {k}", entry_function="add", starter_code="def add(a, b):\n    pass", reference_solution="def add(a, b):\n    return a + b",
             test_cases=[{"args": [1, 2], "expected": 3}, {"args": [5, 5], "expected": 10}], explanation="sum"),
        dict(qtype="coding", difficulty="hard", topic=kw["topic"], subtopic="coding", prompt="BROKEN question", entry_function="f", starter_code="", reference_solution="def f(x):\n    return 0", test_cases=[{"args": [1], "expected": 99}, {"args": [2], "expected": 98}]),
    ][: kw["count"] + 2]


@pytest.fixture(autouse=True)
def stub_ai(monkeypatch):
    monkeypatch.setattr(ai, "phase_units", lambda **kw: fake_units(**kw))
    monkeypatch.setattr(ai, "quiz_questions", lambda **kw: fake_questions(**kw))
    # stub at the service boundary so fake text is never written to the shared AI cache table
    monkeypatch.setattr(skill_gap, "explain", lambda db, role, analysis: {"summary": "test summary", "strengths": [], "priority_gaps": [], "advice": [], "source": "rule_based"})
    monkeypatch.setattr(ai, "material", lambda *a, **k: {"title": "Stub notes", "summary": "s", "explanation": [{"heading": "h", "body": "b"}], "key_takeaways": ["k"], "definitions": [], "examples": [], "code_snippets": [], "formulas": [], "real_world_applications": [], "common_mistakes": [], "interview_relevance": [], "practice_problems": [], "revision_summary": "r", "sources": []})
    monkeypatch.setattr(ai, "summarise_video", lambda t, txt: {"overview": "o", "chapters": [{"title": "c", "start_seconds": 0, "summary": "s", "key_points": []}], "key_concepts": [], "examples": [], "takeaways": [], "flashcards": [], "quiz": []})
    monkeypatch.setattr(ai, "follow_up", lambda *a, **k: "stub answer")
    monkeypatch.setattr(evaluation, "score_subjective", lambda *a, **k: (0.5, {"marks": [], "overall_feedback": "ok"}, "gemini"))
    monkeypatch.setattr(youtube, "fetch_metadata", lambda v: {"title": "Stub video", "channel": "Stub", "thumbnail": None})
    monkeypatch.setattr(youtube, "fetch_transcript", lambda v: ("available", [{"start": 0.0, "text": "hello world"}], None) if v == "aaaaaaaaaaa" else ("unavailable", [], "Captions disabled."))


def make_user(client):
    name = "lh" + uuid.uuid4().hex[:10]
    r = client.post("/api/auth/register", json={"full_name": "LH Test", "email": f"{name}@example.com", "username": name, "password": PW, "confirm_password": PW})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}, name


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth(client):
    headers, name = make_user(client)
    yield headers
    with SessionLocal() as db:
        db.execute(delete(User).where(User.username == name))
        db.commit()


@pytest.fixture()
def other(client):
    headers, name = make_user(client)
    yield headers
    with SessionLocal() as db:
        db.execute(delete(User).where(User.username == name))
        db.commit()


def goal(**over):
    g = {"target_role": "Backend Developer", "track_slug": "backend-developer", "duration_days": 100, "daily_hours": 2, "study_days": [0, 1, 2, 3, 4], "start_date": TODAY.isoformat(), "focus_areas": ["APIs"], "target_companies": []}
    g.update(over)
    return g


def make_plan(client, auth, **over):
    r = client.post("/api/learning/plans", json=goal(**over), headers=auth)
    assert r.status_code == 201, r.text
    return r.json()


def cal(client, auth, plan_id, **params):
    r = client.get(f"/api/learning/plans/{plan_id}/calendar", params=params, headers=auth)
    assert r.status_code == 200, r.text
    return r.json()


# ------------------------------------------------------------------ auth & isolation
def test_every_learning_route_requires_login(client):
    for path in ("/api/learning/overview", "/api/learning/progress", "/api/learning/plans/active", "/api/learning/notebooks", "/api/learning/quizzes", "/api/learning/materials"):
        assert client.get(path).status_code == 401


def test_tracks_are_seeded(client, auth):
    items = client.get("/api/learning/tracks", headers=auth).json()["items"]
    assert len(items) >= 20 and all(t["topics"] >= 8 for t in items)


# ------------------------------------------------------------------ planner
def test_100_day_plan_covers_every_date_with_realistic_load(client, auth):
    plan = make_plan(client, auth)
    c = cal(client, auth, plan["id"])
    dates = {d["date"] for d in c["days"]}
    assert len(dates) == 100  # every calendar day has an entry (study or rest)
    study = [d for d in c["days"] if not d["rest"]]
    assert all(d["minutes"] <= 120 for d in study)
    assert any(d["milestone"] for d in c["days"])
    assert [p["key"] for p in plan["phases"]][0] == "foundation" and plan["milestones"]
    cats = {t["category"] for d in c["days"] for t in d["tasks"]}
    assert {"learn", "revision", "assessment", "rest"} <= cats
    last = [d for d in c["days"] if not d["rest"]][-1]
    assert any(t["title"] == "Final assessment" for t in last["tasks"])


def test_plan_validation(client, auth):
    assert client.post("/api/learning/plans", json=goal(duration_days=3), headers=auth).status_code == 422
    assert client.post("/api/learning/plans", json=goal(study_days=[]), headers=auth).status_code == 422
    assert client.post("/api/learning/plans", json=goal(daily_hours=0.1), headers=auth).status_code == 422
    assert client.post("/api/learning/plans", json=goal(start_date="2020-01-01"), headers=auth).status_code == 422


def test_failed_generation_saves_nothing(client, auth, monkeypatch):
    from app.modules.careerverse import gemini_service

    def boom(**kw):
        raise gemini_service.GeminiUnavailable("down")

    monkeypatch.setattr(ai, "phase_units", boom)
    r = client.post("/api/learning/plans", json=goal(duration_days=30), headers=auth)
    assert r.status_code == 502
    assert client.get("/api/learning/plans/active", headers=auth).json()["plan"] is None


def test_task_status_reschedule_and_filters(client, auth):
    plan = make_plan(client, auth, duration_days=30)
    days = cal(client, auth, plan["id"])["days"]
    t1 = next(t for d in days for t in d["tasks"] if t["category"] == "learn")
    r = client.patch(f"/api/learning/tasks/{t1['id']}", json={"status": "completed", "actual_minutes": 55, "self_difficulty": 4, "notes": "done"}, headers=auth)
    assert r.status_code == 200 and r.json()["status"] == "completed" and r.json()["progress_pct"] == 100
    done = cal(client, auth, plan["id"], filter="completed")
    assert any(t["id"] == t1["id"] for d in done["days"] for t in d["tasks"])
    pend = cal(client, auth, plan["id"], filter="pending")
    assert all(t["status"] in ("pending", "rescheduled") for d in pend["days"] for t in d["tasks"])
    t2 = next(t for d in days for t in d["tasks"] if t["category"] == "learn" and t["id"] != t1["id"])
    far = (TODAY + dt.timedelta(days=20)).isoformat()
    r = client.patch(f"/api/learning/tasks/{t2['id']}", json={"date": far}, headers=auth)
    assert r.json()["date"] == far and r.json()["status"] == "rescheduled" and r.json()["original_date"] == t2["original_date"]
    assert client.patch(f"/api/learning/tasks/{t2['id']}", json={"date": "2099-01-01"}, headers=auth).status_code == 422
    assert client.patch(f"/api/learning/tasks/{t2['id']}", json={"status": "partial", "progress_pct": 40}, headers=auth).json()["progress_pct"] == 40
    # completing a learn task starts spaced repetition for its topic
    revs = client.get("/api/learning/revisions", headers=auth).json()["items"]
    assert any(t1["topic"] == r["topic"] for r in revs)


def test_missed_work_preview_requires_confirmation_then_redistributes(client, auth):
    plan = make_plan(client, auth, duration_days=30, start_date=(TODAY - dt.timedelta(days=1)).isoformat())
    pv = client.get(f"/api/learning/plans/{plan['id']}/missed", headers=auth).json()
    assert pv["missed"] > 0 and pv["moves"] and all(m["to"] >= TODAY.isoformat() for m in pv["moves"])
    before = cal(client, auth, plan["id"], filter="missed")
    assert any(d["tasks"] for d in before["days"])
    if pv["significant"]:
        assert client.post(f"/api/learning/plans/{plan['id']}/missed/apply", json={"confirm": False}, headers=auth).status_code == 409
    res = client.post(f"/api/learning/plans/{plan['id']}/missed/apply", json={"confirm": True}, headers=auth)
    assert res.status_code == 200 and res.json()["moved"] == len(pv["moves"])
    after = cal(client, auth, plan["id"], filter="missed")
    assert sum(len(d["tasks"]) for d in after["days"]) < sum(len(d["tasks"]) for d in before["days"])


def test_regenerate_keeps_completed_work(client, auth):
    plan = make_plan(client, auth, duration_days=40, start_date=(TODAY - dt.timedelta(days=1)).isoformat())
    days = cal(client, auth, plan["id"])["days"]
    past = next(t for d in days for t in d["tasks"] if t["category"] == "learn" and t["date"] < TODAY.isoformat())
    client.patch(f"/api/learning/tasks/{past['id']}", json={"status": "completed"}, headers=auth)
    r = client.post(f"/api/learning/plans/{plan['id']}/regenerate", headers=auth)
    assert r.status_code == 200 and r.json()["replaced"] > 0 and r.json()["plan"]["version"] == plan["version"] + 1
    again = cal(client, auth, plan["id"])["days"]
    assert any(t["id"] == past["id"] and t["status"] == "completed" for d in again for t in d["tasks"])
    assert len({d["date"] for d in again}) == 40


def test_changing_availability_updates_future_rest_days(client, auth):
    plan = make_plan(client, auth, duration_days=35)
    rest_before = sum(1 for d in cal(client, auth, plan["id"])["days"] if d["rest"])
    r = client.put(f"/api/learning/plans/{plan['id']}/availability", json={"study_days": [0, 1, 2]}, headers=auth)
    assert r.status_code == 200
    days = cal(client, auth, plan["id"])["days"]
    assert sum(1 for d in days if d["rest"]) > rest_before
    assert all(dt.date.fromisoformat(d["date"]).weekday() in (0, 1, 2) for d in days if not d["rest"] and d["date"] > TODAY.isoformat())


def test_plans_are_private_between_users(client, auth, other):
    plan = make_plan(client, auth, duration_days=14)
    assert client.get(f"/api/learning/plans/{plan['id']}", headers=other).status_code == 404
    assert client.get(f"/api/learning/plans/{plan['id']}/calendar", headers=other).status_code == 404
    tid = cal(client, auth, plan["id"])["days"][0]["tasks"][0]["id"]
    assert client.patch(f"/api/learning/tasks/{tid}", json={"status": "completed"}, headers=other).status_code == 404


# ------------------------------------------------------------------ notebooks (real lock)
def test_locked_notebook_is_enforced_by_the_server(client, auth, other):
    nb = client.post("/api/learning/notebooks", json={"title": "Secret", "password": "hunter22"}, headers=auth).json()
    assert nb["locked"] is True and nb["description"] is None
    nid = nb["id"]
    assert client.get(f"/api/learning/notebooks/{nid}/index", headers=auth).status_code == 423
    assert client.get(f"/api/learning/notebooks/{nid}/pages/1", headers=auth).status_code == 423
    assert client.get(f"/api/learning/notebooks/{nid}/search", params={"q": "x"}, headers=auth).status_code == 423
    assert client.post(f"/api/learning/notebooks/{nid}/unlock", json={"password": "wrong"}, headers=auth).status_code == 403
    tok = client.post(f"/api/learning/notebooks/{nid}/unlock", json={"password": "hunter22"}, headers=auth).json()["token"]
    assert tok
    ok = client.get(f"/api/learning/notebooks/{nid}/index", headers={**auth, "X-Notebook-Token": tok})
    assert ok.status_code == 200 and ok.json()["pages"]
    # a notebook token is not a login token, and does not unlock a different notebook
    assert client.get("/api/learning/overview", headers={"Authorization": f"Bearer {tok}"}).status_code == 401
    nb2 = client.post("/api/learning/notebooks", json={"title": "Other", "password": "secret99"}, headers=auth).json()
    assert client.get(f"/api/learning/notebooks/{nb2['id']}/index", headers={**auth, "X-Notebook-Token": tok}).status_code == 423
    # another user can neither see nor unlock it
    assert client.get(f"/api/learning/notebooks/{nid}/index", headers={**other, "X-Notebook-Token": tok}).status_code == 404
    assert client.post(f"/api/learning/notebooks/{nid}/unlock", json={"password": "hunter22"}, headers=other).status_code == 404
    # removing the lock requires the current password
    assert client.put(f"/api/learning/notebooks/{nid}/lock", json={"new_password": None, "current_password": "nope"}, headers=auth).status_code == 403
    assert client.put(f"/api/learning/notebooks/{nid}/lock", json={"new_password": None, "current_password": "hunter22"}, headers=auth).json()["locked"] is False
    assert client.get(f"/api/learning/notebooks/{nid}/index", headers=auth).status_code == 200


def test_unlock_is_rate_limited(client, auth):
    nid = client.post("/api/learning/notebooks", json={"title": "Brute", "password": "correct1"}, headers=auth).json()["id"]
    codes = [client.post(f"/api/learning/notebooks/{nid}/unlock", json={"password": f"bad{i}"}, headers=auth).status_code for i in range(7)]
    assert codes[:5] == [403] * 5 and codes[5] == 429
    assert client.post(f"/api/learning/notebooks/{nid}/unlock", json={"password": "correct1"}, headers=auth).status_code == 429


def test_notebook_pages_chapters_history_search_bookmarks(client, auth):
    nid = client.post("/api/learning/notebooks", json={"title": "Diary", "cover_style": "ocean"}, headers=auth).json()["id"]
    base = f"/api/learning/notebooks/{nid}"
    ch = client.post(f"{base}/chapters", json={"title": "SQL"}, headers=auth).json()
    assert client.patch(f"{base}/chapters/{ch['id']}", json={"title": "SQL Joins"}, headers=auth).json()["title"] == "SQL Joins"
    p2 = client.post(f"{base}/pages", json={"title": "Joins", "content": "inner join basics", "chapter_id": ch["id"]}, headers=auth).json()
    assert p2["page_no"] == 2
    client.post(f"{base}/pages", json={"title": "Third", "content": "left outer"}, headers=auth)
    r = client.patch(f"{base}/pages/2", json={"content": "inner join basics, now with examples", "snapshot": True, "bookmarked": True}, headers=auth).json()
    assert r["bookmarked"] is True
    hist = client.get(f"{base}/pages/2/history", headers=auth).json()["items"]
    assert hist and hist[0]["content"] == "inner join basics"
    assert client.post(f"{base}/pages/2/restore/{hist[0]['id']}", headers=auth).json()["content"] == "inner join basics"
    assert client.get(f"{base}/search", params={"q": "outer"}, headers=auth).json()["items"][0]["page_no"] == 3
    assert client.delete(f"{base}/pages/2", headers=auth).status_code == 204
    idx = client.get(f"{base}/index", headers=auth).json()
    assert [p["page_no"] for p in idx["pages"]] == [1, 2]  # numbering stays contiguous
    up = client.post(f"{base}/upload", files={"file": ("notes.txt", b"Line one.\n\nLine two about indexes.", "text/plain")}, headers=auth)
    assert up.status_code == 201 and up.json()["pages"][0]["source_type"] == "upload"
    assert client.post(f"{base}/upload", files={"file": ("x.exe", b"MZ", "application/octet-stream")}, headers=auth).status_code == 422


# ------------------------------------------------------------------ materials & youtube
def test_material_generate_cache_actions_and_save_to_notebook(client, auth):
    m = client.post("/api/learning/materials", json={"topic": "SQL Joins", "level": "beginner", "depth": "standard"}, headers=auth).json()
    again = client.post("/api/learning/materials", json={"topic": "SQL Joins", "level": "beginner", "depth": "standard"}, headers=auth).json()
    assert again["id"] == m["id"]  # saved, not regenerated
    new = client.post(f"/api/learning/materials/{m['id']}/action", json={"action": "simplify"}, headers=auth)
    assert new.status_code == 201 and new.json()["parent_id"] == m["id"]
    assert client.post(f"/api/learning/materials/{m['id']}/ask", json={"question": "why?"}, headers=auth).json()["answer"] == "stub answer"
    nid = client.post("/api/learning/notebooks", json={"title": "N"}, headers=auth).json()["id"]
    page = client.post(f"/api/learning/notebooks/{nid}/save-material/{m['id']}", json={}, headers=auth)
    assert page.status_code == 201 and page.json()["source_type"] == "gemini" and "Stub notes" in page.json()["content"]


def test_youtube_with_and_without_transcript(client, auth):
    ok = client.post("/api/learning/youtube", json={"url": "https://youtu.be/aaaaaaaaaaa"}, headers=auth).json()
    assert ok["transcript_status"] == "available" and ok["summary"]
    no = client.post("/api/learning/youtube", json={"url": "https://youtu.be/bbbbbbbbbbb"}, headers=auth).json()
    assert no["needs_transcript"] and no["summary"] is None and "disabled" in no["reason"]
    fixed = client.post(f"/api/learning/youtube/{no['id']}/summarise", json={"url": "https://youtu.be/bbbbbbbbbbb", "transcript": "00:01 hello\n00:30 world"}, headers=auth).json()
    assert fixed["transcript_status"] == "pasted" and fixed["summary"]
    assert client.post("/api/learning/youtube", json={"url": "https://vimeo.com/1"}, headers=auth).status_code == 422


# ------------------------------------------------------------------ quizzes
def test_quiz_scoring_report_mastery_and_retry(client, auth):
    q = client.post("/api/learning/quizzes", json={"topic": "SQL Joins", "count": 5, "types": ["mcq", "true_false", "output_prediction", "short_answer", "coding"]}, headers=auth)
    assert q.status_code == 201, q.text
    quiz = q.json()
    assert all("answer_key" not in x and "explanation" not in x for x in quiz["questions"])  # no answers before submitting
    assert not any(x["prompt"] == "BROKEN question" for x in quiz["questions"])  # reference solution failed its own tests, so it was dropped
    ans = {}
    for x in quiz["questions"]:
        if x["qtype"] == "mcq":
            ans[x["id"]] = {"choice": 1}
        elif x["qtype"] == "true_false":
            ans[x["id"]] = {"value": False}  # wrong on purpose
        elif x["qtype"] == "output_prediction":
            ans[x["id"]] = {"text": x["prompt"].split("+")[1].rstrip(")")}  # wrong: gives k, expected k+1
        elif x["qtype"] == "short_answer":
            ans[x["id"]] = {"text": "some answer"}
        else:
            ans[x["id"]] = {"code": "def add(a, b):\n    return a + b"}
    rep = client.post(f"/api/learning/quizzes/{quiz['id']}/submit", json={"answers": ans}, headers=auth).json()
    wrong_types = {w["qtype"] for w in rep["incorrect"]}
    assert "mcq" not in wrong_types and "coding" not in wrong_types and "true_false" in wrong_types and "output_prediction" in wrong_types
    assert 0 < rep["accuracy"] < 100 and rep["by_topic"] and rep["time_taken_seconds"] >= 0 and rep["recommended_revisions"]
    assert all(w["explanation"] for w in rep["incorrect"] if w["qtype"] != "short_answer")
    again = client.post(f"/api/learning/quizzes/{quiz['id']}/submit", json={"answers": {}}, headers=auth).json()
    assert again["score"] == rep["score"]  # submitting twice cannot change the score
    results = client.get(f"/api/learning/quizzes/{quiz['id']}/results", headers=auth).json()
    assert results["quiz"]["questions"][0].get("answer_key") is not None  # revealed only after submission
    prog = client.get("/api/learning/progress", headers=auth).json()
    assert prog["mastery"] and prog["mastery"][0]["status"] in prog["status_labels"] and prog["quiz_trend"]
    assert client.get("/api/learning/revisions", headers=auth).json()["items"]
    retry = client.post(f"/api/learning/quizzes/{quiz['id']}/retry", headers=auth).json()
    assert retry["id"] != quiz["id"] and {x["prompt"] for x in retry["questions"]}.isdisjoint({x["prompt"] for x in quiz["questions"]})
    rev = client.post("/api/learning/quizzes", json={"scope": "revision", "count": 3}, headers=auth)
    assert rev.status_code == 201  # revision quiz built from the weak topic created above


def test_revision_quiz_needs_history_and_quizzes_are_private(client, auth, other):
    assert client.post("/api/learning/quizzes", json={"scope": "revision"}, headers=auth).status_code == 422
    q = client.post("/api/learning/quizzes", json={"topic": "Topic X", "count": 3}, headers=auth).json()
    assert client.get(f"/api/learning/quizzes/{q['id']}", headers=other).status_code == 404
    assert client.post(f"/api/learning/quizzes/{q['id']}/submit", json={"answers": {}}, headers=other).status_code == 404
    assert client.get(f"/api/learning/quizzes/{q['id']}/results", headers=auth).status_code == 409


def test_overview_and_recommendations_explain_themselves(client, auth):
    ov = client.get("/api/learning/overview", headers=auth).json()
    assert ov["has_plan"] is False and ov["recommendations"][0]["reason"]
    make_plan(client, auth, duration_days=21, start_date=(TODAY - dt.timedelta(days=1)).isoformat())
    ov = client.get("/api/learning/overview", headers=auth).json()
    assert ov["plan"]["total_days"] == 21 and ov["plan"]["missed"] > 0 and ov["plan"]["today"]
    assert all(r["reason"] for r in ov["recommendations"]) and any(r["kind"] == "reschedule" for r in ov["recommendations"])
    assert client.get("/api/learning/personalization", headers=auth).json()["rl_ready"] is False
