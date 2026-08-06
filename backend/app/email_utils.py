"""Email delivery.

If SMTP credentials are configured (.env), sends real email. Otherwise falls
back to writing an .eml-like file under storage/emails/ and printing to the
console -- lets the whole signing flow be demoed end-to-end without any real
mailbox, matching how the other mock-backed portfolio pieces work.
"""

import smtplib
from datetime import datetime
from email.message import EmailMessage

from .config import settings


def send_email(to: str, subject: str, body: str) -> None:
    if settings.smtp_host and settings.smtp_user and settings.smtp_password:
        _send_real(to, subject, body)
    else:
        _send_mock(to, subject, body)


def _send_real(to: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)


def _send_mock(to: str, subject: str, body: str) -> None:
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    safe_to = to.replace("@", "_at_").replace(".", "_")
    filename = settings.storage_dir / "emails" / f"{timestamp}_{safe_to}.eml"
    content = f"To: {to}\nSubject: {subject}\nDate: {datetime.utcnow().isoformat()}\n\n{body}\n"
    filename.write_text(content, encoding="utf-8")
    print(f"[DocuFlow] (email simulado, SMTP não configurado) -> {to} | {subject} | salvo em {filename}")
