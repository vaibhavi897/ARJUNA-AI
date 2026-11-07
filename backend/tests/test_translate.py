"""Translation module: chunking, shared cache and failure behaviour (provider stubbed in tests only)."""

import asyncio
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.core.config import settings
from app.db.session import SessionLocal
from app.main import app
from app.models import TranslationCache, User
from app.modules import translate as tr

LANG = "hi-IN"


def test_split_text_respects_limit_and_keeps_words():
    long = " ".join(f"Sentence number {i} says something useful." for i in range(60))
    parts = tr.split_text(long, 200)
    assert all(len(p) <= 200 for p in parts) and len(parts) > 3
    assert " ".join(parts).split() == long.split()
    one = "word " * 500
    assert all(len(p) <= 100 for p in tr.split_text(one, 100))


def test_translate_many_caches_and_preserves_order():
    calls: list[str] = []

    async def fake(text: str, lang: str) -> str:
        calls.append(text)
        return f"[{lang}] {text}"

    marker = uuid.uuid4().hex[:8]
    texts = [f"Dashboard {marker}", "", f"Dashboard {marker}", f"Settings {marker}"]
    with SessionLocal() as db:
        try:
            first = asyncio.run(tr.translate_many(db, texts, LANG, sender=fake))
            assert first == [f"[{LANG}] Dashboard {marker}", "", f"[{LANG}] Dashboard {marker}", f"[{LANG}] Settings {marker}"]
            assert sorted(calls) == sorted([f"Dashboard {marker}", f"Settings {marker}"])      # duplicates sent once
            calls.clear()
            again = asyncio.run(tr.translate_many(db, texts, LANG, sender=fake))
            assert again == first and calls == []                                                 # second time: all from cache
            assert asyncio.run(tr.translate_many(db, ["Hello"], "en-IN", sender=fake)) == ["Hello"]
        finally:
            db.execute(delete(TranslationCache).where(TranslationCache.source_text.like(f"%{marker}")))
            db.commit()


def test_unsupported_language_rejected():
    with SessionLocal() as db, pytest.raises(ValueError):
        asyncio.run(tr.translate_many(db, ["x"], "xx-XX"))


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _user(client):
    name = "tr" + uuid.uuid4().hex[:10]
    r = client.post("/api/auth/register", json={"full_name": "Tr Test", "email": f"{name}@example.com", "username": name, "password": "Test@12345!Trans", "confirm_password": "Test@12345!Trans"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}, name


def test_api_requires_login_and_reports_missing_key(client, monkeypatch):
    assert client.post("/api/translate", json={"lang": LANG, "texts": ["Hi"]}).status_code in (401, 403)
    hdr, name = _user(client)
    try:
        monkeypatch.setattr(settings, "SARVAM_API_KEY", None)
        r = client.post("/api/translate", headers=hdr, json={"lang": LANG, "texts": ["Hi"]})
        assert r.status_code == 503 and "not configured" in r.json()["detail"].lower()
        assert client.get("/api/translate/languages", headers=hdr).json()["configured"] is False
        assert client.post("/api/translate", headers=hdr, json={"lang": "xx", "texts": ["Hi"]}).status_code == 422
        # English passes straight through without needing the provider
        assert client.post("/api/translate", headers=hdr, json={"lang": "en-IN", "texts": ["Hi"]}).json()["texts"] == ["Hi"]
    finally:
        with SessionLocal() as db:
            u = db.scalar(select(User).where(User.username == name))
            if u:
                db.delete(u); db.commit()
