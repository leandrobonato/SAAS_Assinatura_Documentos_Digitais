from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session, selectinload

from .. import models, pdf_utils, schemas, storage
from ..config import settings
from ..database import get_db
from ..email_utils import send_email

router = APIRouter(prefix="/public/sign", tags=["signing"])


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "desconhecido"


def _get_signer_or_404(token: str, db: Session) -> models.Signer:
    signer = (
        db.query(models.Signer)
        .options(selectinload(models.Signer.document).selectinload(models.Document.signers))
        .filter(models.Signer.token == token)
        .first()
    )
    if signer is None:
        raise HTTPException(status_code=404, detail="Link de assinatura inválido")
    return signer


@router.get("/{token}", response_model=schemas.PublicSignerView)
def get_signing_view(token: str, request: Request, db: Session = Depends(get_db)):
    signer = _get_signer_or_404(token, db)
    document = signer.document

    if signer.status == models.SignerStatus.PENDING:
        signer.status = models.SignerStatus.VIEWED
        db.add(signer)
        db.add(models.AuditLog(
            document_id=document.id,
            signer_id=signer.id,
            event="viewed",
            ip_address=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        ))
        db.commit()

    data = storage.get_object(document.storage_key_working or document.storage_key_original)
    total_pages = pdf_utils.get_page_count(data)

    own_fields = [f for f in document.fields if f.signer_id == signer.id]
    other_pending = [s.name for s in document.signers if s.id != signer.id and s.status != models.SignerStatus.SIGNED]

    return schemas.PublicSignerView(
        document_title=document.title,
        signer_name=signer.name,
        signer_status=signer.status,
        total_pages=total_pages,
        fields=own_fields,
        other_signers_pending=other_pending,
    )


@router.get("/{token}/document.pdf")
def get_signing_document(token: str, db: Session = Depends(get_db)):
    signer = _get_signer_or_404(token, db)
    document = signer.document
    data = storage.get_object(document.storage_key_working or document.storage_key_original)
    return Response(content=data, media_type="application/pdf")


@router.post("/{token}", response_model=schemas.DocumentSummaryOut)
def submit_signature(
    token: str,
    payload: schemas.SubmitSignatureRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    signer = _get_signer_or_404(token, db)
    document = signer.document

    if signer.status == models.SignerStatus.SIGNED:
        raise HTTPException(status_code=400, detail="Este documento já foi assinado por você")
    if document.status != models.DocumentStatus.SENT:
        raise HTTPException(status_code=400, detail="Este documento não está disponível para assinatura")
    if not payload.typed_name.strip():
        raise HTTPException(status_code=400, detail="Informe seu nome completo para confirmar a assinatura")

    own_fields = [
        {"page_number": f.page_number, "x": f.x, "y": f.y, "width": f.width, "height": f.height}
        for f in document.fields if f.signer_id == signer.id
    ]
    if not own_fields:
        raise HTTPException(status_code=400, detail="Nenhum campo de assinatura definido para este signatário")

    try:
        signature_png = pdf_utils.decode_signature_image(payload.signature_image)
    except Exception:
        raise HTTPException(status_code=400, detail="Imagem de assinatura inválida")

    now = datetime.utcnow()
    ip_address = _client_ip(request)
    user_agent = request.headers.get("user-agent")

    working_data = storage.get_object(document.storage_key_working or document.storage_key_original)
    label = f"Assinado por {payload.typed_name} em {now.strftime('%d/%m/%Y %H:%M UTC')}"
    updated = pdf_utils.apply_signature(working_data, own_fields, signature_png, label)
    storage.put_object(document.storage_key_working, updated)

    signer.status = models.SignerStatus.SIGNED
    signer.signed_at = now
    signer.ip_address = ip_address
    signer.user_agent = user_agent
    db.add(signer)
    db.add(models.AuditLog(
        document_id=document.id,
        signer_id=signer.id,
        event="signed",
        ip_address=ip_address,
        user_agent=user_agent,
        detail=f"Assinado como \"{payload.typed_name}\"",
    ))
    db.commit()
    db.refresh(document)

    all_signed = all(s.status == models.SignerStatus.SIGNED for s in document.signers)
    if all_signed:
        _finalize_document(document, db)

    db.commit()
    db.refresh(document)
    return document


def _finalize_document(document: models.Document, db: Session) -> None:
    original_data = storage.get_object(document.storage_key_original)
    original_hash = pdf_utils.compute_sha256(original_data)

    signers_info = [
        {
            "name": s.name,
            "email": s.email,
            "signed_at": s.signed_at.strftime("%d/%m/%Y %H:%M:%S") if s.signed_at else "N/D",
            "ip_address": s.ip_address,
            "user_agent": s.user_agent,
        }
        for s in document.signers
    ]
    certificate = pdf_utils.generate_certificate_page(document.title, original_hash, signers_info)

    working_data = storage.get_object(document.storage_key_working)
    final_data = pdf_utils.append_pages(working_data, certificate)
    final_hash = pdf_utils.compute_sha256(final_data)

    final_key = f"documents/{document.id}/final.pdf"
    storage.put_object(final_key, final_data)

    document.storage_key_final = final_key
    document.final_hash = final_hash
    document.status = models.DocumentStatus.COMPLETED
    document.completed_at = datetime.utcnow()
    db.add(document)
    db.add(models.AuditLog(
        document_id=document.id,
        event="completed",
        detail=f"Documento concluído. Hash SHA-256 final: {final_hash}",
    ))

    recipients = {s.email: s.name for s in document.signers}
    recipients[document.owner.email] = document.owner.name
    for email, name in recipients.items():
        send_email(
            to=email,
            subject=f"Documento concluído: {document.title}",
            body=(
                f"Olá {name},\n\n"
                f"Todas as partes assinaram o documento \"{document.title}\".\n"
                f"Hash SHA-256 do arquivo final: {final_hash}\n\nDocuFlow"
            ),
        )
