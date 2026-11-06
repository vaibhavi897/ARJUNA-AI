"""Dynamic Resume Builder API. JWT-protected and scoped to the caller."""

from __future__ import annotations

import functools
import re
from typing import Any

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.routes.careerverse import _rate_limit
from app.core.logging_config import get_logger
from app.models import ResumeVersion
from app.modules.auth.dependencies import CurrentUser, DbSession
from app.modules.careerverse import gemini_service
from app.modules.resume_builder import pool as P, render_docx, render_pdf, service

router = APIRouter(prefix="/resume-builder", tags=["resume-builder"])
logger = get_logger(__name__)


def _guard(fn):  # noqa: ANN001, ANN202
    @functools.wraps(fn)
    def wrapper(*a, **kw):  # noqa: ANN002, ANN003
        try:
            return fn(*a, **kw)
        except LookupError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    return wrapper


class GenerateIn(BaseModel):
    job_title: str = Field(min_length=2, max_length=160)
    company: str | None = Field(default=None, max_length=160)
    job_description: str | None = Field(default=None, max_length=12000)


class ContentIn(BaseModel):
    content: dict[str, Any]
    title: str | None = Field(default=None, max_length=200)


class SwapIn(BaseModel):
    add_ref: str = Field(max_length=40)
    remove_ref: str | None = Field(default=None, max_length=40)


def _out(v: ResumeVersion, full: bool = True) -> dict[str, Any]:
    base = {"id": v.id, "title": v.title, "job_title": v.job_title, "company": v.company, "role_type": v.role_type, "edited": v.edited,
            "created_at": v.created_at.isoformat() if v.created_at else None, "updated_at": v.updated_at.isoformat() if v.updated_at else None}
    if not full:
        return base
    return {**base, "job_description": v.job_description, "analysis": v.analysis, "content": v.content, "selection": v.selection, "fit": service.fit_info(v.content),
            "ai_available": gemini_service.is_enabled()}


@router.get("/versions")
def list_versions(user: CurrentUser, db: DbSession) -> list[dict[str, Any]]:
    rows = db.scalars(select(ResumeVersion).where(ResumeVersion.user_id == user.id).order_by(ResumeVersion.updated_at.desc()).limit(100))
    return [_out(v, False) for v in rows]


@router.get("/profile-check")
def profile_check(user: CurrentUser, db: DbSession) -> dict[str, Any]:
    pl = P.load(db, user)
    counts: dict[str, int] = {}
    for i in pl.items:
        counts[i.kind] = counts.get(i.kind, 0) + 1
    return {"ready": pl.profile_ok, "education": len(pl.education), "skills": len(pl.skills), "counts": counts, "ai_available": gemini_service.is_enabled()}


@router.post("/generate", status_code=status.HTTP_201_CREATED)
@_guard
def generate(body: GenerateIn, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    _rate_limit(user.id, "resume_generate", limit=6)
    v = service.create_version(db, user, body.job_title, body.company, body.job_description)
    db.commit()
    return _out(v)


@router.get("/versions/{vid}")
@_guard
def get_version(vid: int, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    return _out(service.get_version(db, user, vid))


@router.put("/versions/{vid}")
@_guard
def save_version(vid: int, body: ContentIn, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    v = service.get_version(db, user, vid)
    v.content = service.sanitize(body.content)
    if body.title:
        v.title = re.sub(r"[\x00-\x1f]", "", body.title).strip()[:200] or v.title
    v.edited = True
    db.commit()
    return _out(v)


@router.post("/fit")
def check_fit(body: ContentIn, user: CurrentUser) -> dict[str, Any]:
    return service.fit_info(service.sanitize(body.content))


@router.post("/versions/{vid}/regenerate")
@_guard
def regenerate(vid: int, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    _rate_limit(user.id, "resume_generate", limit=6)
    v = service.regenerate(db, user, service.get_version(db, user, vid))
    db.commit()
    return _out(v)


@router.get("/versions/{vid}/candidates")
@_guard
def candidates(vid: int, user: CurrentUser, db: DbSession) -> list[dict[str, Any]]:
    return service.candidates(db, user, service.get_version(db, user, vid))


@router.post("/versions/{vid}/swap")
@_guard
def swap(vid: int, body: SwapIn, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    _rate_limit(user.id, "resume_generate", limit=12)
    v = service.swap(db, user, service.get_version(db, user, vid), body.remove_ref, body.add_ref)
    db.commit()
    return _out(v)


@router.delete("/versions/{vid}", status_code=status.HTTP_204_NO_CONTENT)
@_guard
def delete_version(vid: int, user: CurrentUser, db: DbSession) -> Response:
    db.delete(service.get_version(db, user, vid))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _filename(v: ResumeVersion, ext: str) -> str:
    base = re.sub(r"[^A-Za-z0-9]+", "_", f"{v.content.get('header', {}).get('name', 'Resume')}_{v.job_title}").strip("_")[:80] or "Resume"
    return f"{base}.{ext}"


@router.get("/versions/{vid}/pdf")
@_guard
def download_pdf(vid: int, user: CurrentUser, db: DbSession, inline: bool = False) -> Response:
    v = service.get_version(db, user, vid)
    try:
        data = render_pdf.render_pdf(v.content, v.title)
    except render_pdf.DoesNotFit as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    disp = "inline" if inline else "attachment"
    return Response(data, media_type="application/pdf", headers={"Content-Disposition": f'{disp}; filename="{_filename(v, "pdf")}"', "Cache-Control": "no-store"})


@router.post("/preview")
def preview_pdf(body: ContentIn, user: CurrentUser) -> Response:
    """Render unsaved editor content so the preview always matches what will export."""
    _rate_limit(user.id, "resume_preview", limit=60)
    try:
        data = render_pdf.render_pdf(service.sanitize(body.content), "Resume preview")
    except render_pdf.DoesNotFit as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    return Response(data, media_type="application/pdf", headers={"Content-Disposition": 'inline; filename="preview.pdf"', "Cache-Control": "no-store"})


@router.get("/versions/{vid}/docx")
@_guard
def download_docx(vid: int, user: CurrentUser, db: DbSession) -> Response:
    v = service.get_version(db, user, vid)
    data = render_docx.render_docx(v.content)
    return Response(data, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={"Content-Disposition": f'attachment; filename="{_filename(v, "docx")}"', "Cache-Control": "no-store"})
