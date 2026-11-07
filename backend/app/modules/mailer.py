"""Outgoing email over SMTP.

Optional everywhere: when ``EMAIL_ALERTS_ENABLED`` is false or the SMTP settings
are missing, :func:`send` returns False and the caller carries on. Sending is
never allowed to break the request that triggered it.

The credentials live in the backend environment only.
"""

from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

TIMEOUT = 20


def is_configured() -> bool:
    return bool(
        settings.EMAIL_ALERTS_ENABLED
        and settings.SMTP_HOST
        and settings.SMTP_USERNAME
        and settings.SMTP_PASSWORD
        and (settings.SMTP_FROM or settings.SMTP_USERNAME)
    )


def _sender() -> str:
    return settings.SMTP_FROM or settings.SMTP_USERNAME or ""


def send(
    to: str,
    subject: str,
    text_body: str,
    html_body: str | None = None,
    *,
    bcc: str | None = None,
    from_name: str = "Arjuna AI",
) -> bool:
    """Send one message. Returns False instead of raising when it cannot."""
    if not is_configured():
        logger.info("Email not sent (not configured): %s", subject)
        return False
    if not to or "@" not in to:
        logger.warning("Email not sent: invalid recipient")
        return False

    message = EmailMessage()
    message["From"] = formataddr((from_name, _sender()))
    message["To"] = to
    message["Subject"] = subject
    message.set_content(text_body)
    if html_body:
        message.add_alternative(html_body, subtype="html")

    recipients = [to]
    if bcc and "@" in bcc and bcc.lower() != to.lower():
        recipients.append(bcc)

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(settings.SMTP_HOST or "", settings.SMTP_PORT, timeout=TIMEOUT) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(settings.SMTP_USERNAME or "", settings.SMTP_PASSWORD or "")
            server.send_message(message, from_addr=_sender(), to_addrs=recipients)
    except (smtplib.SMTPException, OSError) as exc:
        logger.warning("Could not send email '%s': %s: %s", subject, type(exc).__name__, exc)
        return False

    logger.info("Sent email '%s' to %s", subject, to)
    return True
