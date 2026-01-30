"""Extraction models: fields, lines, and field events for audit."""
import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Float, Text
from sqlalchemy import Enum as SQLEnum, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.database import Base


class ExtractedField(Base):
    """Extracted field from a document with evidence."""
    
    __tablename__ = "extracted_fields"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    
    field_name = Column(String(100), nullable=False)
    raw_value = Column(Text, nullable=True)
    normalized_value = Column(Text, nullable=True)
    confidence = Column(Float, nullable=False, default=0.0)
    
    # Evidence
    page = Column(Integer, nullable=True)
    bbox = Column(JSON, nullable=True)  # {"x": 0, "y": 0, "w": 100, "h": 20}
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    document = relationship("Document", back_populates="fields")
    events = relationship("FieldEvent", back_populates="field", cascade="all, delete-orphan")


class DocumentLine(Base):
    """Line item from a document (e.g., order line, invoice line)."""
    
    __tablename__ = "document_lines"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    
    line_number = Column(Integer, nullable=False)
    item_code = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    quantity = Column(Float, nullable=True)
    unit = Column(String(20), nullable=True)
    unit_price = Column(Float, nullable=True)
    total_price = Column(Float, nullable=True)
    
    confidence = Column(Float, nullable=False, default=0.0)
    page = Column(Integer, nullable=True)
    bbox = Column(JSON, nullable=True)
    
    # Embedding for semantic search
    embedding = Column(Vector(768), nullable=True)  # nomic-embed-text dimension
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    document = relationship("Document", back_populates="lines")


class FieldEventType(str, Enum):
    """Type of field modification event."""
    CREATED = "created"
    UPDATED = "updated"
    VALIDATED = "validated"


class FieldEvent(Base):
    """Audit trail for field modifications (human-in-the-loop)."""
    
    __tablename__ = "field_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    field_id = Column(UUID(as_uuid=True), ForeignKey("extracted_fields.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    event_type = Column(SQLEnum(FieldEventType), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    comment = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    field = relationship("ExtractedField", back_populates="events")
    user = relationship("User", back_populates="field_events")
