"""Outbound email.

Backends:

* ``smtp``    - real delivery via SMTP (STARTTLS supported). Required in staging/prod.
* ``console`` - development: logs that an email was sent. Links contain secrets
  (reset/verification tokens), so the body is **not** logged; developers use Mailpit
  via the SMTP backend when they need the content.
* :class:`MemoryEmailSender` - tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import Protocol

import aiosmtplib
import structlog

from serptank.core.config import Settings

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class OutgoingEmail:
    to: str
    subject: str
    text: str
    html: str | None = None


class EmailSender(Protocol):
    async def send(self, message: OutgoingEmail) -> None: ...


class ConsoleEmailSender:
    async def send(self, message: OutgoingEmail) -> None:
        logger.info("email_sent_console", to=message.to, subject=message.subject)


@dataclass
class MemoryEmailSender:
    outbox: list[OutgoingEmail] = field(default_factory=list)

    async def send(self, message: OutgoingEmail) -> None:
        self.outbox.append(message)


class SmtpEmailSender:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def send(self, message: OutgoingEmail) -> None:
        msg = EmailMessage()
        msg["From"] = self._settings.email_from
        msg["To"] = message.to
        msg["Subject"] = message.subject
        msg.set_content(message.text)
        if message.html:
            msg.add_alternative(message.html, subtype="html")
        password = self._settings.smtp_password.get_secret_value()
        await aiosmtplib.send(
            msg,
            hostname=self._settings.smtp_host,
            port=self._settings.smtp_port,
            username=self._settings.smtp_username or None,
            password=password or None,
            start_tls=self._settings.smtp_starttls,
            timeout=15,
        )
        logger.info("email_sent", to=message.to, subject=message.subject)


def create_email_sender(settings: Settings) -> EmailSender:
    if settings.email_backend == "smtp":
        return SmtpEmailSender(settings)
    return ConsoleEmailSender()
