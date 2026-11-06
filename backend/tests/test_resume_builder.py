"""Resume builder: layout fit, relevance, tailoring guardrails and the API (Gemini stubbed in tests only)."""

import datetime as dt
import io
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models import AcademicDetail, Achievement, Experience, Project, User
from app.modules.careerverse import gemini_service
from app.modules.resume_builder import layout, pool as P, relevance as R, tailor as T

PW = "Test@12345!Resume"


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(gemini_service, "is_enabled", lambda: False)


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def make_user(client):
    name = "rb" + uuid.uuid4().hex[:10]
    r = client.post("/api/auth/register", json={"full_name": "Riya Test", "email": f"{name}@example.com", "username": name, "password": PW, "confirm_password": PW})
    assert r.status_code == 201, r.text
    hdr = {"Authorization": f"Bearer {r.json()['access_token']}"}
    with SessionLocal() as db:
        u = db.scalar(select(User).where(User.username == name))
        d = dt.date
        db.add(AcademicDetail(user_id=u.id, level="undergraduate", institution="Test University", degree_or_program="B.Tech", specialization="CS", score=8.5, score_type="cgpa", start_year=2022, end_year=2026))
        db.add_all([
            Experience(user_id=u.id, experience_type="internship", organization="SaaSCo", title="Sales Intern", description="Closed 14 enterprise demos and grew the pipeline by 35% in 3 months. Called 200 leads weekly.", start_date=d(2025, 5, 1), end_date=d(2025, 8, 1), is_current=False),
            Experience(user_id=u.id, experience_type="internship", organization="DevCo", title="Backend Intern", description="Built REST APIs in FastAPI with PostgreSQL. Wrote 40 unit tests with pytest.", start_date=d(2025, 1, 1), end_date=d(2025, 4, 1), is_current=False),
            Experience(user_id=u.id, experience_type="position_of_responsibility", organization="Club", title="Treasurer", description="Managed a budget of 50000 rupees for events.", start_date=d(2024, 1, 1), end_date=d(2025, 1, 1), is_current=False),
        ])
        db.add_all([
            Project(user_id=u.id, title="Chat App", description="Real-time chat with WebSockets and Redis. Handled 500 concurrent users.", start_date=d(2025, 2, 1), end_date=d(2025, 3, 1)),
            Project(user_id=u.id, title="Poetry Blog", description="A personal blog about poetry written in plain HTML.", start_date=d(2023, 2, 1), end_date=d(2023, 3, 1)),
        ])
        db.add(Achievement(user_id=u.id, title="First Place - Hackathon", description="Won first place among 120 teams.", category="competition", date_awarded=d(2025, 3, 1)))
        db.commit()
    return hdr, name


def cleanup(name):
    with SessionLocal() as db:
        u = db.scalar(select(User).where(User.username == name))
        if u:
            db.delete(u)
            db.commit()


def test_relevance_prefers_matching_items():
    items = [P.Item("project", 1, "Chat App", text="Real-time chat WebSockets Redis backend API", sentences=[]),
             P.Item("project", 2, "Poetry Blog", text="personal blog poetry html", sentences=[])]
    an = R.local_analysis("Backend Engineer", "Build APIs, WebSockets and Redis services")
    assert an["role_type"] == "tech"
    s = R.score_items(items, an, "Backend Engineer", "Build APIs, WebSockets and Redis services")
    assert s["project:1"]["score"] > s["project:2"]["score"]


def test_role_detection():
    assert R.local_analysis("Sales Development Representative", "")["role_type"] == "sales"
    assert R.local_analysis("Investment Banking Analyst", "")["role_type"] == "finance"


def test_tailor_rejects_invented_numbers(monkeypatch):
    it = P.Item("project", 1, "X", text="Built an API handling 500 users", sentences=["Built an API handling 500 users in production."])
    bullets, flags = T._validate(it, ["Built an API serving **500** users", "Boosted revenue by 90% across the platform quickly"], "sales")
    assert len(bullets) == 1 and "500" in bullets[0]
    assert any("unsupported number" in f for f in flags)


def test_original_wording_fallback_and_flags():
    it = P.Item("experience", 1, "Intern", "Co", text="Intern Co Wrote reports for the team every week.", sentences=["Wrote reports for the team every week."])
    out = T.tailor(None, [it], {"role_type": "sales", "keywords": []}, "Sales", None)
    r = out["experience:1"]
    assert r["source"] == "original" and r["bullets"]
    assert any("measurable" in f for f in r["flags"])


def test_layout_fit_and_overflow():
    small = {"header": {"name": "A B", "contacts": ["a@b.com"]}, "sections": [{"key": "skills", "title": "Skills", "type": "lines", "lines": [{"label": "Technical", "text": "Python, SQL"}]}]}
    assert layout.measure(small)["fits"]
    big = {"header": {"name": "A B", "contacts": []}, "sections": [{"key": "projects", "title": "Projects", "type": "entries", "entries": [
        {"title": f"**P{i}**", "right": "2025", "bullets": ["word " * 60] * 3} for i in range(8)]}]}
    f = layout.measure(big)
    assert not f["fits"] and f["overflow_lines"] > 0


def test_end_to_end_generate_edit_export(client):
    hdr, name = make_user(client)
    try:
        assert client.get("/api/resume-builder/versions").status_code in (401, 403)
        r = client.post("/api/resume-builder/generate", headers=hdr, json={"job_title": "Sales Executive", "company": "Acme", "job_description": "Drive pipeline, demos, revenue growth and customer outreach."})
        assert r.status_code == 201, r.text
        v = r.json()
        assert v["role_type"] == "sales" and v["fit"]["fits"]
        refs = [e["source"]["ref"] for s in v["content"]["sections"] if s["type"] == "entries" for e in s["entries"]]
        # the sales internship must outrank the backend one for a sales job, and appear first in selection
        inc = [i["ref"] for i in v["selection"]["included"]]
        assert inc.index(next(r for r in inc if r.startswith("experience:") and "SaaSCo" in next(i["org"] for i in v["selection"]["included"] if i["ref"] == r))) == 0
        # every number in bullets must come from the profile
        blob = " ".join(b for s in v["content"]["sections"] if s["type"] == "entries" for e in s["entries"] for b in e["bullets"])
        assert all(n in "14 35 3 200 40 500 120 50000 2022 2026 8.5" for n in P.numbers_in(blob))
        pdf = client.get(f"/api/resume-builder/versions/{v['id']}/pdf", headers=hdr)
        assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
        from pypdf import PdfReader
        assert len(PdfReader(io.BytesIO(pdf.content)).pages) == 1
        docx = client.get(f"/api/resume-builder/versions/{v['id']}/docx", headers=hdr)
        assert docx.status_code == 200 and docx.content[:2] == b"PK"
        from docx import Document
        text = "\n".join(p.text for p in Document(io.BytesIO(docx.content)).paragraphs)
        assert "Test University" in text and "Education" in text
        # manual edit persists, is sanitised, and fit is re-measured
        content = v["content"]
        content["header"]["name"] = "Riya \x00Edited"
        content["sections"][1]["entries"][0]["bullets"][0] = "Hand-written **bullet** after editing it myself."
        s = client.put(f"/api/resume-builder/versions/{v['id']}", headers=hdr, json={"content": content})
        assert s.status_code == 200 and s.json()["edited"] and s.json()["content"]["header"]["name"] == "Riya Edited"
        assert "Hand-written" in client.get(f"/api/resume-builder/versions/{v['id']}", headers=hdr).json()["content"]["sections"][1]["entries"][0]["bullets"][0]
        # overflow edit is reported, not silently exported
        huge = {"header": {"name": "X", "contacts": []}, "sections": [{"key": "projects", "title": "P", "type": "entries", "entries": [{"title": f"**E{i}**", "bullets": ["word " * 70] * 4} for i in range(12)]}]}
        assert client.post("/api/resume-builder/fit", headers=hdr, json={"content": huge}).json()["fits"] is False
        assert client.post("/api/resume-builder/preview", headers=hdr, json={"content": huge}).status_code == 422
        # another user cannot read it
        hdr2, name2 = make_user(client)
        try:
            assert client.get(f"/api/resume-builder/versions/{v['id']}", headers=hdr2).status_code == 404
        finally:
            cleanup(name2)
        assert client.delete(f"/api/resume-builder/versions/{v['id']}", headers=hdr).status_code == 204
    finally:
        cleanup(name)


def test_empty_profile_is_rejected(client):
    name = "rb" + uuid.uuid4().hex[:10]
    r = client.post("/api/auth/register", json={"full_name": "Empty One", "email": f"{name}@example.com", "username": name, "password": PW, "confirm_password": PW})
    hdr = {"Authorization": f"Bearer {r.json()['access_token']}"}
    try:
        g = client.post("/api/resume-builder/generate", headers=hdr, json={"job_title": "Engineer"})
        assert g.status_code == 422 and "profile" in g.json()["detail"].lower()
    finally:
        cleanup(name)


def test_tailor_rejects_unsupported_terms():
    it = P.Item("project", 1, "Chat App", text="Real-time chat with WebSockets and Redis for 500 users", sentences=[])
    bullets, flags = T._validate(it, ["Developed real-time chat using WebSockets and Redis for **500** users", "Built chat with Kafka and Kubernetes for **500** users at scale"], "tech")
    assert len(bullets) == 1 and "Redis" in bullets[0]
    assert any("not in your profile" in f for f in flags)
