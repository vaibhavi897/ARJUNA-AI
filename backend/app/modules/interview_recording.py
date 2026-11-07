"""Interview recordings: buffer chunks on the server, then store in Supabase.

Why chunks:
    the browser streams ~5 second pieces while the interview runs, so a closed
    tab or a crashed laptop loses seconds rather than the whole session. The
    pieces are appended to one temporary file on the backend and uploaded as a
    single WebM when the interview ends.

Privacy:
    recordings are only made when the student consented to media, the bucket is
    private, playback goes through a short-lived signed URL, and every recording
    carries an expiry date after which the cleanup removes it.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging_config import get_logger
from app.models import InterviewSession
from app.modules import supabase_storage as store

logger = get_logger(__name__)

TMP_DIR = Path(settings.UPLOAD_DIR) / "interview_tmp"
ALLOWED_MIME = {"video/webm", "audio/webm", "video/mp4", "audio/mp4"}


class RecordingError(RuntimeError):
    """Message is safe to show the user."""


def is_enabled() -> bool:
    """Recording is offered only when there is somewhere to put it."""
    return store.is_configured()


def max_bytes() -> int:
    return settings.RECORDING_MAX_MB * 1024 * 1024


def _tmp_path(session_id: int) -> Path:
    return TMP_DIR / f"session_{session_id}.webm"


def _object_path(session: InterviewSession) -> str:
    return f"user_{session.user_id}/session_{session.id}.webm"


def append_chunk(session: InterviewSession, data: bytes) -> int:
    """Append one recorded chunk. Returns the size buffered so far."""
    if not data:
        return current_size(session)
    path = _tmp_path(session.id)
    try:
        TMP_DIR.mkdir(parents=True, exist_ok=True)
        size = path.stat().st_size if path.exists() else 0
        if size + len(data) > max_bytes():
            raise RecordingError(f"This recording has reached the {settings.RECORDING_MAX_MB} MB limit.")
        with path.open("ab") as fh:
            fh.write(data)
        return size + len(data)
    except OSError as exc:
        logger.warning("Could not buffer recording chunk for session %s: %s", session.id, exc)
        raise RecordingError("The recording could not be saved on the server.") from exc


def current_size(session: InterviewSession) -> int:
    path = _tmp_path(session.id)
    try:
        return path.stat().st_size if path.exists() else 0
    except OSError:
        return 0


def discard(session: InterviewSession) -> None:
    """Drop the buffered chunks without storing them."""
    try:
        _tmp_path(session.id).unlink(missing_ok=True)
    except OSError:
        pass


def finalise(db: Session, session: InterviewSession, seconds: int | None = None) -> dict[str, object]:
    """Upload the buffered recording and record it against the session."""
    if not is_enabled():
        raise RecordingError("Recording storage is not configured on this server.")

    path = _tmp_path(session.id)
    if not path.exists() or path.stat().st_size == 0:
        raise RecordingError("No recording was captured for this interview.")

    data = path.read_bytes()
    if len(data) > max_bytes():
        discard(session)
        raise RecordingError(f"That recording is larger than the {settings.RECORDING_MAX_MB} MB limit.")

    object_path = _object_path(session)
    try:
        store.upload(object_path, data, "video/webm")
    except store.StorageUnavailable as exc:
        # keep the buffered file so the upload can be retried
        raise RecordingError(str(exc)) from exc

    expires = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=settings.RECORDING_RETENTION_DAYS)
    session.recording_path = object_path
    session.recording_mime = "video/webm"
    session.recording_bytes = len(data)
    session.recording_seconds = int(seconds) if seconds and seconds > 0 else None
    session.recording_expires_at = expires.isoformat()
    db.commit()

    discard(session)
    logger.info("Stored interview recording for session %s (%.1f MB)", session.id, len(data) / 1024 / 1024)
    return summary(session)


def _expired(session: InterviewSession) -> bool:
    if not session.recording_expires_at:
        return False
    try:
        return dt.datetime.fromisoformat(session.recording_expires_at) <= dt.datetime.now(dt.timezone.utc)
    except ValueError:
        return False


def summary(session: InterviewSession) -> dict[str, object]:
    """Small, safe description of the recording for the report screen."""
    has = bool(session.recording_path) and not _expired(session)
    return {
        "available": has,
        "bytes": session.recording_bytes if has else None,
        "seconds": session.recording_seconds if has else None,
        "mime": session.recording_mime if has else None,
        "expires_at": session.recording_expires_at if has else None,
    }


def playback_url(session: InterviewSession) -> str:
    if not session.recording_path:
        raise RecordingError("There is no recording for this interview.")
    if _expired(session):
        raise RecordingError("This recording has passed its retention period and was removed.")
    try:
        return store.signed_url(session.recording_path)
    except store.StorageUnavailable as exc:
        raise RecordingError(str(exc)) from exc


def remove(db: Session, session: InterviewSession) -> None:
    """Delete the stored recording and forget it on the session."""
    if session.recording_path:
        store.delete(session.recording_path)
    session.recording_path = None
    session.recording_mime = None
    session.recording_bytes = None
    session.recording_seconds = None
    session.recording_expires_at = None
    db.commit()
    discard(session)


def purge_expired(db: Session) -> dict[str, int]:
    """Delete every recording past its retention date. Safe to run repeatedly."""
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    rows = list(
        db.scalars(
            select(InterviewSession).where(
                InterviewSession.recording_path.is_not(None),
                InterviewSession.recording_expires_at.is_not(None),
                InterviewSession.recording_expires_at <= now,
            )
        )
    )
    removed = 0
    for s in rows:
        try:
            remove(db, s)
            removed += 1
        except Exception as exc:  # one bad row must not stop the sweep
            logger.warning("Could not purge recording for session %s: %s", s.id, exc)
            db.rollback()
    return {"checked": len(rows), "removed": removed}
