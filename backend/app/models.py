import enum
import secrets
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Plan(str, enum.Enum):
    FREE = "free"
    PRO = "pro"


class DocumentStatus(str, enum.Enum):
    DRAFT = "draft"
    SENT = "sent"
    COMPLETED = "completed"


class SignerStatus(str, enum.Enum):
    PENDING = "pending"
    VIEWED = "viewed"
    SIGNED = "signed"


def _now() -> datetime:
    return datetime.utcnow()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    plan: Mapped[Plan] = mapped_column(Enum(Plan), default=Plan.FREE)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    documents: Mapped[list["Document"]] = relationship(back_populates="owner", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(255))
    original_filename: Mapped[str] = mapped_column(String(255))
    status: Mapped[DocumentStatus] = mapped_column(Enum(DocumentStatus), default=DocumentStatus.DRAFT)

    storage_key_original: Mapped[str] = mapped_column(String(500))
    storage_key_working: Mapped[str | None] = mapped_column(String(500), nullable=True)
    storage_key_final: Mapped[str | None] = mapped_column(String(500), nullable=True)
    final_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    owner: Mapped["User"] = relationship(back_populates="documents")
    signers: Mapped[list["Signer"]] = relationship(back_populates="document", cascade="all, delete-orphan", order_by="Signer.order_index")
    fields: Mapped[list["SignatureField"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class Signer(Base):
    __tablename__ = "signers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"))
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255))
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    token: Mapped[str] = mapped_column(String(64), unique=True, default=lambda: secrets.token_urlsafe(32))
    status: Mapped[SignerStatus] = mapped_column(Enum(SignerStatus), default=SignerStatus.PENDING)

    signed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)

    reminder_sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reminder_count: Mapped[int] = mapped_column(Integer, default=0)

    document: Mapped["Document"] = relationship(back_populates="signers")
    fields: Mapped[list["SignatureField"]] = relationship(back_populates="signer", cascade="all, delete-orphan")


class SignatureField(Base):
    __tablename__ = "signature_fields"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"))
    signer_id: Mapped[int] = mapped_column(ForeignKey("signers.id"))
    page_number: Mapped[int] = mapped_column(Integer, default=0)

    # relative coordinates (0-1) so the frontend can render at any zoom level
    x: Mapped[float] = mapped_column(Float)
    y: Mapped[float] = mapped_column(Float)
    width: Mapped[float] = mapped_column(Float)
    height: Mapped[float] = mapped_column(Float)

    document: Mapped["Document"] = relationship(back_populates="fields")
    signer: Mapped["Signer"] = relationship(back_populates="fields")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"))
    signer_id: Mapped[int | None] = mapped_column(ForeignKey("signers.id"), nullable=True)
    event: Mapped[str] = mapped_column(String(50))
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    document: Mapped["Document"] = relationship(back_populates="audit_logs")
