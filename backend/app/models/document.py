"""Document and page models."""
import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Float, Text, Boolean
from sqlalchemy import Enum as SQLEnum, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class DocumentType(str, Enum):
    """Document classification types."""
    PO = "po"  # Purchase Order / Ordine
    DDT = "ddt"  # Documento di Trasporto / Bolla
    FATTURA = "fattura"  # Invoice
    PREVENTIVO = "preventivo"  # Quote / Estimate
    ALTRO = "altro"  # Other / Unclassified


class DocumentStatus(str, Enum):
    """Document processing status."""
    QUEUED = "queued"
    PROCESSING = "processing"
    EXTRACTED = "extracted"
    VALIDATED = "validated"
    FAILED = "failed"


class Document(Base):
    """Document record with metadata and processing status."""
    
    __tablename__ = "documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # File info
    filename = Column(String(512), nullable=False)
    file_path = Column(String(1024), nullable=False)
    file_hash = Column(String(64), nullable=False)  # SHA-256
    file_size_bytes = Column(Integer, nullable=False)
    
    # Processing
    status = Column(String(20), nullable=False, default='queued')
    is_scanned = Column(Boolean, nullable=True)  # None = not determined yet
    ocr_quality = Column(Float, nullable=True)  # 0-1 confidence
    
    # Classification
    doc_type = Column(String(20), nullable=True)  # po, ddt, fattura, preventivo, altro
    doc_type_confidence = Column(Float, nullable=True)
    doc_type_override = Column(String(20), nullable=True)  # Human override
    
    # Extracted text
    raw_text = Column(Text, nullable=True)
    
    # Warnings/errors
    warnings = Column(JSON, nullable=False, default=list)
    error_message = Column(Text, nullable=True)
    
    # Metadata - key extracted fields for quick access
    doc_number = Column(String(100), nullable=True)
    doc_date = Column(DateTime, nullable=True)
    fornitore = Column(String(255), nullable=True)  # Supplier/vendor name (destinatario for DDT)
    emittente = Column(String(255), nullable=True)  # Issuing company (who created the document)
    totale = Column(Float, nullable=True)  # Total amount
    
    # Type-specific fields
    vettore = Column(String(255), nullable=True)  # DDT: carrier/transporter
    causale_trasporto = Column(String(100), nullable=True)  # DDT: transport reason
    scadenza_pagamento = Column(DateTime, nullable=True)  # Fattura: payment due date
    modalita_pagamento = Column(String(100), nullable=True)  # Fattura: payment method
    imponibile = Column(Float, nullable=True)  # Fattura: taxable amount
    aliquota_iva = Column(Float, nullable=True)  # Fattura: VAT rate %
    importo_iva = Column(Float, nullable=True)  # Fattura: VAT amount
    validita_offerta = Column(DateTime, nullable=True)  # Preventivo: offer validity
    data_consegna = Column(DateTime, nullable=True)  # Ordine: requested delivery date
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="documents")
    pages = relationship("DocumentPage", back_populates="document", cascade="all, delete-orphan")
    fields = relationship("ExtractedField", back_populates="document", cascade="all, delete-orphan")
    lines = relationship("DocumentLine", back_populates="document", cascade="all, delete-orphan")


class DocumentPage(Base):
    """Individual page within a document."""
    
    __tablename__ = "document_pages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    
    page_number = Column(Integer, nullable=False)
    text_content = Column(Text, nullable=True)
    ocr_confidence = Column(Float, nullable=True)
    
    # Relationships
    document = relationship("Document", back_populates="pages")
