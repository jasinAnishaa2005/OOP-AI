import logging
import smtplib
from email.message import EmailMessage
from typing import Protocol

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


class EmailSender(Protocol):
    def send(self, to: str, subject: str, body: str) -> None: ...


class SmtpEmailSender:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def send(self, to: str, subject: str, body: str) -> None:
        s = self._settings
        message = EmailMessage()
        message["From"] = s.smtp_from
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)
        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=10) as smtp:
            if s.smtp_use_tls:
                smtp.starttls()
            if s.smtp_username and s.smtp_password:
                smtp.login(s.smtp_username, s.smtp_password)
            smtp.send_message(message)


class ConsoleEmailSender:
    """Development-only sender: prints emails to the server console instead of delivering them."""

    def send(self, to: str, subject: str, body: str) -> None:
        logger.warning("[dev email] to=%s subject=%s\n%s", to, subject, body)


class DisabledEmailSender:
    def send(self, to: str, subject: str, body: str) -> None:
        logger.error("Email delivery is not configured (set SMTP_HOST and SMTP_FROM); message to %s dropped", to)


def get_email_sender() -> EmailSender:
    settings = get_settings()
    if settings.smtp_configured:
        return SmtpEmailSender(settings)
    if settings.environment == "development":
        return ConsoleEmailSender()
    return DisabledEmailSender()
