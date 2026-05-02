import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models import DocumentStatus


class DocumentUploadResponse(BaseModel):
    document_id: uuid.UUID
    filename: str
    status: DocumentStatus


class DocumentStatusResponse(BaseModel):
    document_id: uuid.UUID
    filename: str
    status: DocumentStatus
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)


class Citation(BaseModel):
    chunk_id: uuid.UUID
    page_number: int
    score: float
    text: str


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation]
    cached: bool = False
