"""Document schemas."""
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.models.document import DocumentType, DocumentStatus


class DocumentCreate(BaseModel):
    """Create document (internal use, after file upload)."""
    filename: str
    file_path: str
    file_hash: str
    file_size_bytes: int


class DocumentListItem(BaseModel):
    """Document in list view."""
    id: UUID
    filename: str
    status: DocumentStatus
    doc_type: DocumentType | None = None
    doc_type_confidence: float | None = None
    doc_number: str | None = None
    doc_date: datetime | None = None
    created_at: datetime
    warnings: list[str] = []
    
    model_config = ConfigDict(from_attributes=True)


class DocumentPageRead(BaseModel):
    """Document page response."""
    id: UUID
    page_number: int
    text_content: str | None = None
    ocr_confidence: float | None = None
    
    model_config = ConfigDict(from_attributes=True)


class DocumentRead(BaseModel):
    """Full document response."""
    id: UUID
    tenant_id: UUID
    filename: str
    file_hash: str
    file_size_bytes: int
    status: DocumentStatus
    is_scanned: bool | None = None
    ocr_quality: float | None = None
    doc_type: DocumentType | None = None
    doc_type_confidence: float | None = None
    doc_type_override: DocumentType | None = None
    raw_text: str | None = None
    warnings: list[str] = []
    error_message: str | None = None
    doc_number: str | None = None
    doc_date: datetime | None = None
    created_at: datetime
    processed_at: datetime | None = None
    pages: list[DocumentPageRead] = []
    
    model_config = ConfigDict(from_attributes=True)


class DocumentUpdate(BaseModel):
    """Update document request."""
    doc_type_override: DocumentType | None = None
    doc_number: str | None = None
    doc_date: datetime | None = None
    status: DocumentStatus | None = None


class JobStatus(BaseModel):
    """Ingestion job status."""
    job_id: str
    status: str  # queued, running, completed, failed
    progress: int = 0
    total: int = 0
    message: str | None = None
    documents_created: list[UUID] = []
