"""Outgoing email: `send`, with two backends chosen by MAIL_BACKEND.

- "console" (the default): nothing leaves the machine. Each message is
  logged and kept in `outbox` (the last few), for development and tests.
- "smtp": sent through SMTP_HOST with STARTTLS and SMTP_USERNAME /
  SMTP_PASSWORD. Amazon SES's SMTP endpoint (the server is already on AWS)
  or a mailbox's app password both work; the sender in MAIL_FROM must be an
  address that service lets you send from.

Plain text only: a confirmation link reads the same in every mail client,
and there is no HTML to escape.
"""
from __future__ import annotations

import logging
import smtplib
import ssl
from collections import deque
from email.message import EmailMessage

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# The console backend's last messages, newest last.
outbox: deque[EmailMessage] = deque(maxlen=20)


class MailError(Exception):
    """The message couldn't be handed to the mail server."""


def send(to: str, subject: str, text: str) -> None:
    s = get_settings()
    msg = EmailMessage()
    msg["From"] = s.mail_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text)
    if s.mail_backend != "smtp":
        outbox.append(msg)
        logger.info("Mail not sent (MAIL_BACKEND=%s) to %s: %s\n%s", s.mail_backend, to, subject, text)
        return
    if not s.smtp_host:
        raise MailError("MAIL_BACKEND=smtp needs SMTP_HOST.")
    try:
        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=20) as smtp:
            if s.smtp_starttls:
                smtp.starttls(context=ssl.create_default_context())
            if s.smtp_username:
                smtp.login(s.smtp_username, s.smtp_password or "")
            smtp.send_message(msg)
    except (OSError, smtplib.SMTPException) as exc:
        # The address only, never the body: it holds a sign-in-grade link.
        logger.error("Mail to %s failed: %s", to, exc)
        raise MailError(str(exc)) from exc
