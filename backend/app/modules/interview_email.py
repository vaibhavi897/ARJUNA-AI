"""The short interview summary emailed to the student once a session ends.

Content comes only from the stored report — nothing is invented. When a report
could not be produced, the email says so plainly rather than inventing a score.

The recording is linked, never attached: a 40-minute capture runs to a few
hundred megabytes, far past what mail servers accept. The link points at the
report page, which requires signing in, rather than at a signed storage URL,
so the recording is never reachable straight from an inbox.
"""

from __future__ import annotations

import html
from typing import Any

from app.core.config import settings
from app.core.logging_config import get_logger
from app.models import InterviewSession, User
from app.modules import mailer
from app.modules import interview_recording as rec

logger = get_logger(__name__)

def _report_url(session: InterviewSession) -> str:
    base = (settings.FRONTEND_URL or "").rstrip("/")
    return f"{base}/app/interview-arena?session={session.id}" if base else ""



def _duration(seconds: int | None) -> str:
    if not seconds:
        return ""
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes} min {secs}s" if minutes else f"{secs}s"


def build(session: InterviewSession, user: User) -> tuple[str, str, str]:
    """Return (subject, plain text, html) for this session."""
    report = session.report or {}
    name = (getattr(user, "full_name", None) or getattr(user, "username", None) or "there").split(" ")[0]
    recording = rec.summary(session)
    url = _report_url(session)

    # Deliberately score-only: the detail, the feedback and the transcript stay
    # behind the sign-in on the report page rather than sitting in an inbox.
    if not report.get("sufficient_data"):
        subject = f"Your {session.domain} practice interview is complete"
        headline = "There was not enough attempted data for a reliable score, so no score was produced."
        score_line = ""
    else:
        score = report.get("overall_score")
        subject = f"Your {session.domain} interview score — {score}/100" if isinstance(score, (int, float)) else f"Your {session.domain} interview is complete"
        headline = f"Based on {report.get('attempted_count') or 0} attempted response(s). Ending early is not penalised."
        score_line = f"{score}/100" if isinstance(score, (int, float)) else ""

    # ---------------------------------------------------------------- text
    lines = [f"Hi {name},", "", f"Your practice interview in {session.domain} is complete.", ""]
    if score_line:
        lines += [f"Overall score: {score_line}"]
    lines += [headline, ""]
    if recording["available"]:
        bits = [b for b in [_duration(recording["seconds"]), "kept for " + str(settings.RECORDING_RETENTION_DAYS) + " days"] if b]
        lines += [f"Your recording is saved ({', '.join(bits)}) and can be played on the report page.", ""]
    if url:
        lines += [f"Full report: {url}", ""]
    lines += ["The full breakdown, question-by-question feedback and transcript are on the report page.", "", "— Arjuna AI"]
    text = "\n".join(lines)

    # ---------------------------------------------------------------- html
    score_block = (
        f"<div style='font:800 34px/1 system-ui,sans-serif;color:#0C3326'>{html.escape(score_line)}</div>"
        if score_line
        else ""
    )
    rec_block = ""
    if recording["available"]:
        bits = ", ".join(b for b in [_duration(recording["seconds"]), f"kept for {settings.RECORDING_RETENTION_DAYS} days"] if b)
        rec_block = (
            "<p style='margin:16px 0 0;padding:12px 14px;background:#F5FAF6;border-radius:10px;"
            "font:14px/1.6 system-ui,sans-serif;color:#2C463A'>"
            f"🎥 Your interview recording is saved ({html.escape(bits)}). Sign in to play it on the report page.</p>"
        )
    button = (
        f"<p style='margin:22px 0 0'><a href='{html.escape(url)}' "
        "style='display:inline-block;background:#187C4F;color:#fff;text-decoration:none;"
        "padding:11px 20px;border-radius:10px;font:600 14px system-ui,sans-serif'>View the full report</a></p>"
        if url
        else ""
    )

    body = f"""<div style="max-width:560px;margin:0 auto;padding:24px;font:15px/1.6 system-ui,sans-serif;color:#2C463A">
  <p style="margin:0 0 4px;font:700 13px system-ui,sans-serif;color:#187C4F;letter-spacing:.08em;text-transform:uppercase">Arjuna AI</p>
  <h1 style="margin:0 0 12px;font:800 22px system-ui,sans-serif;color:#0C3326">{html.escape(session.domain)} practice interview</h1>
  <p style="margin:0 0 14px">Hi {html.escape(name)}, your interview is complete.</p>
  {score_block}
  <p style="margin:6px 0 0;color:#5F736A;font-size:13px">{html.escape(headline)}</p>
  {rec_block}
  {button}
  <p style="margin:18px 0 0;color:#5F736A;font-size:13px">The full breakdown, question-by-question feedback and transcript are on the report page.</p>
  <p style="margin:26px 0 0;color:#7D8F86;font-size:12px">You are receiving this because you completed a practice interview in Arjuna AI.</p>
</div>"""

    return subject, text, body


def prepare(session: InterviewSession, user: User) -> dict[str, str] | None:
    """Render the email while the ORM objects are still attached to a session.

    Background tasks run after the request's database session is closed, so the
    message is built here and only plain strings are handed on.
    """
    if not mailer.is_configured():
        return None
    to = (getattr(user, "email", "") or "").strip() or (settings.ALERT_EMAIL_TO or "").strip()
    if not to or "@" not in to:
        return None
    try:
        subject, text, body = build(session, user)
    except Exception as exc:  # never let the report fail over an email
        logger.warning("Could not build interview email for session %s: %s", session.id, exc)
        return None
    return {"to": to, "subject": subject, "text": text, "html": body}


def deliver(message: dict[str, str] | None) -> bool:
    """Send a message produced by :func:`prepare`. Safe to run in the background."""
    if not message:
        return False
    try:
        return mailer.send(
            message["to"], message["subject"], message["text"], message["html"], bcc=settings.ALERT_EMAIL_TO
        )
    except Exception as exc:
        logger.warning("Could not send interview email: %s", exc)
        return False


def send_for_session(session: InterviewSession, user: User) -> bool:
    """Convenience for callers that are still inside the request."""
    return deliver(prepare(session, user))
