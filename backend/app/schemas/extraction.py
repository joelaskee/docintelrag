"""Extraction schemas."""
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.models.extraction import FieldEventType


class ExtractedFieldRead(BaseModel):
    """Extracted field response."""
    id: UUID
    document_id: UUID
    field_name: str
    raw_value: str | None = None
    normalized_value: str | None = None
    confidence: float
    page: int | None = None
    bbox: dict | None = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ExtractedFieldUpdate(BaseModel):
    """Update extracted field request."""
    raw_value: str | None = None
    normalized_value: str | None = None
    comment: str | None = None  # For audit trail


class DocumentLineRead(BaseModel):
    """Document line item response."""
    id: UUID
    document_id: UUID
    line_number: int
    item_code: str | None = None
    description: str | None = None
    quantity: float | None = None
    unit: str | None = None
    unit_price: float | None = None
    total_price: float | None = None
    confidence: float
    page: int | None = None
    bbox: dict | None = None
    
    model_config = ConfigDict(from_attributes=True)


class FieldEventCreate(BaseModel):
    """Create field event request."""
    event_type: FieldEventType
    old_value: str | None = None
    new_value: str | None = None
    comment: str | None = None


class FieldEventRead(BaseModel):
    """Field event response (audit trail)."""
    id: UUID
    field_id: UUID
    user_id: UUID
    event_type: FieldEventType
    old_value: str | None = None
    new_value: str | None = None
    comment: str | None = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
