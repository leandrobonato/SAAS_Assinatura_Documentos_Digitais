"""Automatic renewal reminders -- the paid-plan differentiator.

Free-plan documents are never swept here: reminders are a Pro feature per
the product spec (free plan = 5 signatures/month, Pro = batch sending +
automatic reminders for signers who haven't signed yet).
"""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from . import models
from .config import settings
from .email_utils import send_email


def run_reminder_sweep(db: Session) -> int:
    now = datetime.utcnow()
    threshold = timedelta(days=settings.reminder_after_days)
    min_interval = timedelta(days=settings.reminder_min_interval_days)

    sent_count = 0
    documents = (
        db.query(models.Document)
        .join(models.User, models.Document.owner_id == models.User.id)
        .filter(models.Document.status == models.DocumentStatus.SENT)
        .filter(models.User.plan == models.Plan.PRO)
        .all()
    )

    for document in documents:
        if not document.sent_at:
            continue
        if now - document.sent_at < threshold:
            continue

        for signer in document.signers:
            if signer.status != models.SignerStatus.PENDING:
                continue
            last_notice = signer.reminder_sent_at or document.sent_at
            if now - last_notice < min_interval:
                continue

            link = f"{settings.frontend_base_url}/assinar/{signer.token}"
            send_email(
                to=signer.email,
                subject=f"Lembrete: assinatura pendente — {document.title}",
                body=(
                    f"Olá {signer.name},\n\n"
                    f"O documento \"{document.title}\" ainda aguarda sua assinatura.\n"
                    f"Assine aqui: {link}\n\nDocuFlow"
                ),
            )
            signer.reminder_sent_at = now
            signer.reminder_count += 1
            db.add(models.AuditLog(
                document_id=document.id,
                signer_id=signer.id,
                event="reminder_sent",
                detail=f"Lembrete #{signer.reminder_count} enviado para {signer.email}",
            ))
            sent_count += 1

    db.commit()
    return sent_count
