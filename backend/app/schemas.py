from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from .models import DocumentStatus, Plan, SignerStatus


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=6)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    plan: Plan
    created_at: datetime

    class Config:
        from_attributes = True


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class SignerCreate(BaseModel):
    name: str
    email: EmailStr


class SignerOut(BaseModel):
    id: int
    name: str
    email: str
    status: SignerStatus
    order_index: int
    signed_at: datetime | None
    reminder_count: int

    class Config:
        from_attributes = True


class FieldCreate(BaseModel):
    signer_id: int
    page_number: int
    x: float
    y: float
    width: float
    height: float


class FieldOut(BaseModel):
    id: int
    signer_id: int
    page_number: int
    x: float
    y: float
    width: float
    height: float

    class Config:
        from_attributes = True


class FieldsReplaceRequest(BaseModel):
    fields: list[FieldCreate]


class DocumentOut(BaseModel):
    id: int
    title: str
    original_filename: str
    status: DocumentStatus
    created_at: datetime
    sent_at: datetime | None
    completed_at: datetime | None
    final_hash: str | None
    signers: list[SignerOut] = []
    fields: list[FieldOut] = []

    class Config:
        from_attributes = True


class DocumentSummaryOut(BaseModel):
    id: int
    title: str
    original_filename: str
    status: DocumentStatus
    created_at: datetime
    sent_at: datetime | None
    completed_at: datetime | None
    signers: list[SignerOut] = []

    class Config:
        from_attributes = True


class SendRequest(BaseModel):
    signers: list[SignerCreate]


class PublicFieldOut(BaseModel):
    id: int
    page_number: int
    x: float
    y: float
    width: float
    height: float

    class Config:
        from_attributes = True


class PublicSignerView(BaseModel):
    document_title: str
    signer_name: str
    signer_status: SignerStatus
    total_pages: int
    fields: list[PublicFieldOut]
    other_signers_pending: list[str]


class SubmitSignatureRequest(BaseModel):
    signature_image: str  # base64-encoded PNG data URL
    typed_name: str


class PlanUpdate(BaseModel):
    plan: Plan


class AuditLogOut(BaseModel):
    event: str
    ip_address: str | None
    user_agent: str | None
    detail: str | None
    created_at: datetime

    class Config:
        from_attributes = True
