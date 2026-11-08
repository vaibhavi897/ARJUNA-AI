"""Notebooks, chapters and pages: a personal learning diary.

Privacy model (honest): a locked notebook is protected by SERVER-SIDE ACCESS CONTROL.
The Argon2 password hash never leaves the server, and every page/index/search
endpoint refuses to answer without a short-lived signed unlock token that is only
issued after the password verifies. This is authentication, not end-to-end
encryption: page text is stored in the database unencrypted.
"""

from __future__ import annotations

import re

import datetime as dt
import time
from pathlib import Path
from typing import Any

import jwt
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.security import ALGORITHM, create_access_token, hash_password, verify_password
from app.models import Notebook, NotebookChapter, NotebookPage, NotebookPageVersion, User
from app.modules.learning import events

COVERS = ("forest", "midnight", "burgundy", "ocean", "amber", "slate", "lavender", "terracotta")
UNLOCK_MINUTES = 30
MAX_ATTEMPTS, WINDOW = 5, 300
_attempts: dict[tuple[int, int], list[float]] = {}


class LockedError(PermissionError):
    pass


# ------------------------------------------------------------------ lock
def _throttle(user_id: int, notebook_id: int) -> None:
    now = time.monotonic()
    hits = [t for t in _attempts.get((user_id, notebook_id), []) if now - t < WINDOW]
    if len(hits) >= MAX_ATTEMPTS:
        raise LockedError("Too many wrong passwords. Try again in a few minutes.")
    _attempts[(user_id, notebook_id)] = hits


def _fail(user_id: int, notebook_id: int) -> None:
    _attempts.setdefault((user_id, notebook_id), []).append(time.monotonic())


def unlock(user: User, nb: Notebook, password: str) -> dict[str, Any]:
    if not nb.lock_hash:
        return {"token": None, "expires_in": 0}
    _throttle(user.id, nb.id)
    if not verify_password(password, nb.lock_hash):
        _fail(user.id, nb.id)
        raise LockedError("Incorrect password.")
    _attempts.pop((user.id, nb.id), None)
    token, exp = create_access_token(user.id, {"type": "notebook", "nbk": nb.id}, expires_minutes=UNLOCK_MINUTES)
    return {"token": token, "expires_in": UNLOCK_MINUTES * 60, "expires_at": exp.isoformat()}


def check_access(user: User, nb: Notebook, token: str | None) -> None:
    """Raise LockedError unless the notebook is open, or the unlock token is valid for THIS user and notebook."""
    if not nb.lock_hash:
        return
    if not token:
        raise LockedError("This notebook is locked.")
    try:
        c = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM], options={"require": ["exp", "sub"]})
    except jwt.PyJWTError as exc:
        raise LockedError("Unlock expired. Enter the password again.") from exc
    if c.get("type") != "notebook" or c.get("nbk") != nb.id or str(c.get("sub")) != str(user.id):
        raise LockedError("This notebook is locked.")


def set_lock(user: User, nb: Notebook, new_password: str | None, current_password: str | None) -> None:
    if nb.lock_hash:
        _throttle(user.id, nb.id)
        if not current_password or not verify_password(current_password, nb.lock_hash):
            _fail(user.id, nb.id)
            raise LockedError("Current password is incorrect.")
    if new_password:
        if len(new_password) < 6:
            raise ValueError("Use at least 6 characters for a notebook password.")
        nb.lock_hash = hash_password(new_password)
    else:
        nb.lock_hash = None


# ------------------------------------------------------------------ notebooks
def get_notebook(db: Session, user: User, notebook_id: int) -> Notebook:
    nb = db.scalar(select(Notebook).where(Notebook.id == notebook_id, Notebook.user_id == user.id))
    if nb is None:
        raise LookupError("Notebook not found")
    return nb


def notebook_out(db: Session, nb: Notebook) -> dict[str, Any]:
    pages = db.scalar(select(func.count()).select_from(NotebookPage).where(NotebookPage.notebook_id == nb.id)) or 0
    locked = bool(nb.lock_hash)
    return {"id": nb.id, "title": nb.title, "cover_style": nb.cover_style, "locked": locked, "pages": pages, "folder": nb.folder,
            "description": None if locked else nb.description, "tags": [] if locked else nb.tags, "updated_at": nb.updated_at.isoformat() if nb.updated_at else None}


def create_notebook(db: Session, user: User, title: str, cover: str, description: str | None, folder: str | None, tags: list[str], password: str | None, plan_id: int | None = None) -> Notebook:
    nb = Notebook(user_id=user.id, title=title.strip()[:160], cover_style=cover if cover in COVERS else "forest", description=description, folder=folder, tags=tags[:10], plan_id=plan_id)
    if password:
        if len(password) < 6:
            raise ValueError("Use at least 6 characters for a notebook password.")
        nb.lock_hash = hash_password(password)
    db.add(nb)
    db.flush()
    db.add(NotebookChapter(notebook_id=nb.id, title="General", position=0))
    db.add(NotebookPage(notebook_id=nb.id, page_no=1, title="Welcome", content=f"# {nb.title}\n\nThis is your first page. Write anything, or save AI notes and video summaries here."))
    db.flush()  # the Welcome page must exist before add_page numbers the next one
    events.log(db, user.id, "notebook_created", "notebook", nb.id)
    return nb


# ------------------------------------------------------------------ index and pages
def index(db: Session, nb: Notebook) -> dict[str, Any]:
    chapters = list(db.scalars(select(NotebookChapter).where(NotebookChapter.notebook_id == nb.id).order_by(NotebookChapter.position)))
    pages = list(db.scalars(select(NotebookPage).where(NotebookPage.notebook_id == nb.id).order_by(NotebookPage.page_no)))
    return {
        "notebook": {"id": nb.id, "title": nb.title, "cover_style": nb.cover_style, "locked": bool(nb.lock_hash), "description": nb.description, "tags": nb.tags},
        "chapters": [{"id": c.id, "title": c.title, "position": c.position} for c in chapters],
        "pages": [{"id": p.id, "page_no": p.page_no, "title": p.title, "chapter_id": p.chapter_id, "bookmarked": p.bookmarked, "tags": p.tags, "source_type": p.source_type, "updated_at": p.updated_at.isoformat() if p.updated_at else None} for p in pages],
    }


def page_out(p: NotebookPage) -> dict[str, Any]:
    return {"id": p.id, "notebook_id": p.notebook_id, "page_no": p.page_no, "title": p.title, "content": p.content, "chapter_id": p.chapter_id, "tags": p.tags, "bookmarked": p.bookmarked,
            "source_type": p.source_type, "source_ref": p.source_ref, "task_id": p.task_id, "updated_at": p.updated_at.isoformat() if p.updated_at else None}


def get_page(db: Session, nb: Notebook, page_no: int) -> NotebookPage:
    p = db.scalar(select(NotebookPage).where(NotebookPage.notebook_id == nb.id, NotebookPage.page_no == page_no))
    if p is None:
        raise LookupError("Page not found")
    return p


def add_page(db: Session, nb: Notebook, title: str = "Untitled page", content: str = "", chapter_id: int | None = None, source_type: str = "manual", source_ref: int | None = None, task_id: int | None = None, tags: list[str] | None = None) -> NotebookPage:
    nxt = (db.scalar(select(func.max(NotebookPage.page_no)).where(NotebookPage.notebook_id == nb.id)) or 0) + 1
    if chapter_id and db.scalar(select(NotebookChapter.id).where(NotebookChapter.id == chapter_id, NotebookChapter.notebook_id == nb.id)) is None:
        chapter_id = None
    p = NotebookPage(notebook_id=nb.id, page_no=nxt, title=(title or "Untitled page")[:200], content=content, chapter_id=chapter_id, source_type=source_type, source_ref=source_ref, task_id=task_id, tags=tags or [])
    db.add(p)
    db.flush()
    return p


def update_page(db: Session, p: NotebookPage, data: dict[str, Any], snapshot: bool = False) -> NotebookPage:
    changed = ("content" in data and data["content"] != p.content) or ("title" in data and data["title"] != p.title)
    if changed:
        latest = db.scalar(select(NotebookPageVersion).where(NotebookPageVersion.page_id == p.id).order_by(NotebookPageVersion.id.desc()).limit(1))
        stale = latest is None or (dt.datetime.now(dt.timezone.utc) - latest.saved_at).total_seconds() > 120
        if snapshot or stale:
            db.add(NotebookPageVersion(page_id=p.id, title=p.title, content=p.content))  # the state BEFORE this edit
    for k in ("title", "content", "chapter_id", "tags", "bookmarked", "task_id"):
        if k in data and data[k] is not None or (k in ("chapter_id", "task_id") and k in data):
            setattr(p, k, data[k] if k != "title" else (data[k] or "Untitled page")[:200])
    db.flush()
    return p


def delete_page(db: Session, p: NotebookPage) -> None:
    nb_id, no = p.notebook_id, p.page_no
    db.delete(p)
    db.flush()
    for q in db.scalars(select(NotebookPage).where(NotebookPage.notebook_id == nb_id, NotebookPage.page_no > no).order_by(NotebookPage.page_no)):
        q.page_no -= 1  # keep numbering contiguous
        db.flush()


def search(db: Session, nb: Notebook, q: str) -> list[dict[str, Any]]:
    like = f"%{q.strip()}%"
    rows = db.scalars(select(NotebookPage).where(NotebookPage.notebook_id == nb.id, or_(NotebookPage.title.ilike(like), NotebookPage.content.ilike(like))).order_by(NotebookPage.page_no).limit(30))
    out = []
    for p in rows:
        i = p.content.lower().find(q.lower().strip())
        snip = p.content[max(0, i - 40): i + 90].replace("\n", " ") if i >= 0 else p.content[:100].replace("\n", " ")
        out.append({"page_no": p.page_no, "title": p.title, "snippet": snip})
    return out


# ------------------------------------------------------------------ content imports
def material_to_markdown(m: dict[str, Any]) -> str:
    out = [f"# {m.get('title', 'Notes')}", "", m.get("summary", "")]

    def sections(title: str, items: list[dict[str, str]]) -> None:
        if items:
            out.extend(["", f"## {title}"])
            for it in items:
                out.extend([f"### {it['heading']}", it["body"]])

    def bullets(title: str, items: list[str]) -> None:
        if items:
            out.extend(["", f"## {title}", *[f"- {i}" for i in items]])

    sections("Definitions", m.get("definitions", []))
    sections("Explanation", m.get("explanation", []))
    sections("Examples", m.get("examples", []))
    for c in m.get("code_snippets", []):
        out.extend(["", f"### {c.get('title') or 'Code'}", f"```{c.get('language', '')}", c["code"], "```", c.get("explanation", "")])
    sections("Formulas", m.get("formulas", []))
    bullets("Real-world applications", m.get("real_world_applications", []))
    bullets("Common mistakes", m.get("common_mistakes", []))
    bullets("Interview relevance", m.get("interview_relevance", []))
    if m.get("practice_problems"):
        out.extend(["", "## Practice problems"])
        for i, p in enumerate(m["practice_problems"], 1):
            out.extend([f"{i}. {p['question']}", f"   - Hint: {p.get('hint', '')}", f"   - Answer: {p.get('answer', '')}"])
    bullets("Key takeaways", m.get("key_takeaways", []))
    if m.get("revision_summary"):
        out.extend(["", "## Revision summary", m["revision_summary"]])
    return "\n".join(out)


def video_to_markdown(title: str | None, url: str, s: dict[str, Any]) -> str:
    def ts(sec: int) -> str:
        return f"{sec // 60:02d}:{sec % 60:02d}"

    out = [f"# {title or 'Video notes'}", f"Source: {url}", ""]
    if s.get("level") or s.get("topics"):
        out.append("**Level:** " + (s.get("level") or "n/a") + ("  |  **Topics:** " + ", ".join(s["topics"]) if s.get("topics") else ""))
        out.append("")
    out.extend([s.get("overview", ""), ""])
    if s.get("prerequisites"):
        out.extend(["## Prerequisites", *[f"- {p}" for p in s["prerequisites"]], ""])
    if s.get("concepts"):
        out.append("## Concepts to learn")
        for c in s["concepts"]:
            stamp = f" [{ts(int(c['timestamp_seconds']))}]" if c.get("timestamp_seconds") is not None else ""
            out.extend([f"### {c['name']}{stamp}", c["explanation"], *([f"*Why it matters:* {c['why_it_matters']}"] if c.get("why_it_matters") else []), ""])
    if s.get("terminology"):
        out.append("## Terminology")
        out.extend(f"- **{t['term']}**: {t['definition']}" for t in s["terminology"])
        out.append("")
    if s.get("applications"):
        out.append("## Where it is applied")
        out.extend(f"- **{a['area']}**: {a['description']}" for a in s["applications"])
        out.append("")
    if s.get("tools_mentioned"):
        out.extend(["## Tools mentioned", ", ".join(s["tools_mentioned"]), ""])
    out.append("## Chapters")
    for c in s.get("chapters", []):
        out.extend([f"### [{ts(int(c.get('start_seconds', 0)))}] {c['title']}", c["summary"], *[f"- {k}" for k in c.get("key_points", [])], ""])
    for title_, key in (("Examples", "examples"), ("Takeaways", "takeaways")):
        if s.get(key):
            out.extend([f"## {title_}", *[f"- {i}" for i in s[key]], ""])
    if s.get("flashcards"):
        out.extend(["## Flashcards", *[f"- **{f['front']}**: {f['back']}" for f in s["flashcards"]]])
    return "\n".join(out)


def pages_from_upload(path: Path, ext: str, max_chars: int = 5000) -> list[tuple[str, str]]:
    """Extract text from PDF/DOCX/TXT and split into page-sized chunks."""
    from app.modules.resume.extract import extract_text

    ext = ext.lower()
    if ext == ".txt":
        text = path.read_text(encoding="utf-8", errors="replace").strip()
        if not text:
            raise ValueError("The file is empty.")
    elif ext in (".pdf", ".docx"):
        text = extract_text(path, ext)
    else:
        raise ValueError("Only PDF, DOCX and TXT files are supported.")
    chunks, cur = [], ""
    for para in text.split("\n\n"):
        if len(cur) + len(para) > max_chars and cur:
            chunks.append(cur.strip())
            cur = ""
        cur += para + "\n\n"
    if cur.strip():
        chunks.append(cur.strip())
    return [(f"{path.stem[:60]} (part {i})" if len(chunks) > 1 else path.stem[:80], c) for i, c in enumerate(chunks[:40], 1)]


# ------------------------------------------------------------------ YouTube notes land in My Notes automatically
YOUTUBE_NOTEBOOK = "YouTube Notes"
_STAMP = re.compile(r"\[((?:\d{1,2}:)?\d{1,2}:\d{2})\]")


def youtube_notebook(db: Session, user: User) -> Notebook:
    """The student's own unlocked 'YouTube Notes' notebook, created the first time it is needed."""
    nb = db.scalar(select(Notebook).where(Notebook.user_id == user.id, Notebook.title == YOUTUBE_NOTEBOOK, Notebook.lock_hash.is_(None)).order_by(Notebook.id))
    if nb is not None:
        return nb
    return create_notebook(db, user, YOUTUBE_NOTEBOOK, "ocean", "Summaries and your own notes from the videos you studied", "Videos", ["youtube"], None)


def _find_page(db: Session, nb: Notebook, source_type: str, source_ref: int) -> NotebookPage | None:
    return db.scalar(select(NotebookPage).where(NotebookPage.notebook_id == nb.id, NotebookPage.source_type == source_type, NotebookPage.source_ref == source_ref))


def sync_video_summary(db: Session, user: User, y: Any) -> NotebookPage | None:
    """Put a summarised video's study notes in My Notes once. An existing page is never overwritten, because the student may have edited it."""
    if not y.summary:
        return None
    nb = youtube_notebook(db, user)
    page = _find_page(db, nb, "youtube", y.id)
    if page is not None:
        return page
    return add_page(db, nb, y.title or "Video notes", video_to_markdown(y.title, y.url, y.summary), None, "youtube", y.id, None, ["video summary"])


def _link_stamps(notes: str, url: str) -> str:
    def repl(m: re.Match[str]) -> str:
        parts = [int(x) for x in m.group(1).split(":")]
        sec = parts[0] * 3600 + parts[1] * 60 + parts[2] if len(parts) == 3 else parts[0] * 60 + parts[1]
        return f"[{m.group(1)}]({url}{'&' if '?' in url else '?'}t={sec}s)"
    return _STAMP.sub(repl, notes)


def save_video_notes(db: Session, user: User, y: Any, notes: str) -> NotebookPage | None:
    """The student's own notes beside a video: one page per video, updated as they type. [mm:ss] markers become links."""
    notes = (notes or "").strip()
    nb = youtube_notebook(db, user)
    page = _find_page(db, nb, "video_notes", y.id)
    if not notes and page is None:
        return None
    title = f"My notes: {(y.title or 'Video')[:170]}"
    content = f"# {title}\n\nVideo: {y.url}\n\n{_link_stamps(notes, y.url)}\n" if notes else (page.content if page else "")
    if page is None:
        return add_page(db, nb, title, content, None, "video_notes", y.id, None, ["video notes"])
    if notes:
        update_page(db, page, {"title": title, "content": content})
    return page
