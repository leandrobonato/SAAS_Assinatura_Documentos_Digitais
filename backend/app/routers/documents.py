from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session, selectinload

from .. import models, pdf_utils, schemas, storage
from ..config import settings
from ..database import get_db
from ..deps import get_current_user
from ..email_utils import send_email

router = APIRouter(prefix="/documents", tags=["documents"])


def _get_owned_document(document_id: int, user: models.User, db: Session) -> models.Document:
    document = (
        db.query(models.Document)
        .options(selectinload(models.Document.signers), selectinload(models.Document.fields))
        .filter(models.Document.id == document_id)
        .first()
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    if document.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Você não tem acesso a este documento")
    return document


@router.post("", response_model=schemas.DocumentOut, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if file.content_type != "application/pdf" and not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Apenas arquivos PDF são aceitos")

    data = await file.read()
    if not data.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Arquivo não é um PDF válido")

    try:
        pdf_utils.get_page_count(data)
    except Exception:
        raise HTTPException(status_code=400, detail="Não foi possível ler o PDF enviado")

    document = models.Document(
        owner_id=current_user.id,
        title=title,
        original_filename=file.filename,
        storage_key_original="",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    key = f"documents/{document.id}/original.pdf"
    storage.put_object(key, data)
    document.storage_key_original = key
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


@router.get("", response_model=list[schemas.DocumentSummaryOut])
def list_documents(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(models.Document)
        .options(selectinload(models.Document.signers))
        .filter(models.Document.owner_id == current_user.id)
        .order_by(models.Document.created_at.desc())
        .all()
    )


@router.get("/{document_id}", response_model=schemas.DocumentOut)
def get_document(document_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _get_owned_document(document_id, current_user, db)


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    document = _get_owned_document(document_id, current_user, db)
    if document.status != models.DocumentStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Apenas documentos em rascunho podem ser excluídos")
    storage.delete_object(document.storage_key_original)
    db.delete(document)
    db.commit()
    return Response(status_code=204)


@router.get("/{document_id}/original.pdf")
def download_original(document_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    document = _get_owned_document(document_id, current_user, db)
    data = storage.get_object(document.storage_key_original)
    return Response(content=data, media_type="application/pdf")


@router.get("/{document_id}/final.pdf")
def download_final(document_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    document = _get_owned_document(document_id, current_user, db)
    if document.status != models.DocumentStatus.COMPLETED or not document.storage_key_final:
        raise HTTPException(status_code=400, detail="Documento ainda não foi concluído")
    data = storage.get_object(document.storage_key_final)
    return Response(content=data, media_type="application/pdf")


@router.get("/{document_id}/audit", response_model=list[schemas.AuditLogOut])
def get_audit_trail(document_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    document = _get_owned_document(document_id, current_user, db)
    return (
        db.query(models.AuditLog)
        .filter(models.AuditLog.document_id == document.id)
        .order_by(models.AuditLog.created_at.asc())
        .all()
    )


@router.post("/{document_id}/signers", response_model=schemas.SignerOut, status_code=201)
def add_signer(
    document_id: int,
    payload: schemas.SignerCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = _get_owned_document(document_id, current_user, db)
    if document.status != models.DocumentStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Só é possível adicionar signatários em documentos em rascunho")

    signer = models.Signer(
        document_id=document.id,
        name=payload.name,
        email=payload.email,
        order_index=len(document.signers),
    )
    db.add(signer)
    db.commit()
    db.refresh(signer)
    return signer


@router.delete("/{document_id}/signers/{signer_id}", status_code=204)
def remove_signer(
    document_id: int,
    signer_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = _get_owned_document(document_id, current_user, db)
    if document.status != models.DocumentStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Só é possível remover signatários em documentos em rascunho")
    signer = next((s for s in document.signers if s.id == signer_id), None)
    if signer is None:
        raise HTTPException(status_code=404, detail="Signatário não encontrado")
    db.delete(signer)
    db.commit()
    return Response(status_code=204)


@router.put("/{document_id}/fields", response_model=list[schemas.FieldOut])
def replace_fields(
    document_id: int,
    payload: schemas.FieldsReplaceRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = _get_owned_document(document_id, current_user, db)
    if document.status != models.DocumentStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Só é possível editar campos em documentos em rascunho")

    valid_signer_ids = {s.id for s in document.signers}
    for f in payload.fields:
        if f.signer_id not in valid_signer_ids:
            raise HTTPException(status_code=400, detail=f"signer_id {f.signer_id} não pertence a este documento")

    db.query(models.SignatureField).filter(models.SignatureField.document_id == document.id).delete()
    new_fields = [
        models.SignatureField(
            document_id=document.id,
            signer_id=f.signer_id,
            page_number=f.page_number,
            x=f.x, y=f.y, width=f.width, height=f.height,
        )
        for f in payload.fields
    ]
    db.add_all(new_fields)
    db.commit()

    return (
        db.query(models.SignatureField)
        .filter(models.SignatureField.document_id == document.id)
        .all()
    )


def _month_start(now: datetime) -> datetime:
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


@router.post("/{document_id}/send", response_model=schemas.DocumentOut)
def send_document(
    document_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = _get_owned_document(document_id, current_user, db)
    if document.status != models.DocumentStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Documento já foi enviado")
    if not document.signers:
        raise HTTPException(status_code=400, detail="Adicione ao menos um signatário antes de enviar")

    fields_by_signer: dict[int, int] = {}
    for f in document.fields:
        fields_by_signer[f.signer_id] = fields_by_signer.get(f.signer_id, 0) + 1
    missing = [s.name for s in document.signers if fields_by_signer.get(s.id, 0) == 0]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Defina ao menos um campo de assinatura para: {', '.join(missing)}",
        )

    if current_user.plan == models.Plan.FREE:
        if len(document.signers) > settings.free_plan_max_signers:
            raise HTTPException(
                status_code=402,
                detail=(
                    f"Plano gratuito permite no máximo {settings.free_plan_max_signers} "
                    "signatário por documento. Faça upgrade para o plano Pro para envio em lote."
                ),
            )
        month_start = _month_start(datetime.utcnow())
        sent_this_month = (
            db.query(models.Document)
            .filter(models.Document.owner_id == current_user.id)
            .filter(models.Document.sent_at.isnot(None))
            .filter(models.Document.sent_at >= month_start)
            .count()
        )
        if sent_this_month >= settings.free_plan_monthly_limit:
            raise HTTPException(
                status_code=402,
                detail=(
                    f"Limite mensal do plano gratuito atingido "
                    f"({settings.free_plan_monthly_limit} envios/mês). Faça upgrade para o plano Pro."
                ),
            )

    original_data = storage.get_object(document.storage_key_original)
    working_key = f"documents/{document.id}/working.pdf"
    storage.put_object(working_key, original_data)
    document.storage_key_working = working_key
    document.status = models.DocumentStatus.SENT
    document.sent_at = datetime.utcnow()
    db.add(document)

    for signer in document.signers:
        link = f"{settings.frontend_base_url}/assinar/{signer.token}"
        send_email(
            to=signer.email,
            subject=f"Documento para assinatura: {document.title}",
            body=(
                f"Olá {signer.name},\n\n"
                f"{current_user.name} enviou o documento \"{document.title}\" para sua assinatura.\n"
                f"Acesse o link para revisar e assinar: {link}\n\nDocuFlow"
            ),
        )
        db.add(models.AuditLog(
            document_id=document.id,
            signer_id=signer.id,
            event="sent",
            detail=f"Convite de assinatura enviado para {signer.email}",
        ))

    db.commit()
    db.refresh(document)
    return document
