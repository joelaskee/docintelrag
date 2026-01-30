"""Documents router."""
from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.document import Document, DocumentStatus, DocumentType
from app.models.extraction import ExtractedField, DocumentLine, FieldEvent, FieldEventType
from app.models.user import User, UserRole
from app.routers.auth import get_current_user
from app.schemas.document import DocumentRead, DocumentListItem, DocumentUpdate
from app.schemas.extraction import ExtractedFieldRead, ExtractedFieldUpdate, DocumentLineRead

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=List[DocumentListItem])
async def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: DocumentStatus | None = None,
    doc_type: DocumentType | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List documents for current tenant."""
    query = db.query(Document).filter(Document.tenant_id == current_user.tenant_id)
    
    if status:
        query = query.filter(Document.status == status)
    if doc_type:
        query = query.filter(Document.doc_type == doc_type)
    
    query = query.order_by(Document.created_at.desc())
    return query.offset(skip).limit(limit).all()


@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get document by ID."""
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.tenant_id == current_user.tenant_id
    ).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.patch("/{document_id}", response_model=DocumentRead)
async def update_document(
    document_id: UUID,
    update: DocumentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update document (e.g., override type)."""
    if current_user.role == UserRole.MANAGER:
        raise HTTPException(status_code=403, detail="Managers cannot modify documents")
    
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.tenant_id == current_user.tenant_id
    ).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(doc, field, value)
    
    db.commit()
    db.refresh(doc)
    return doc


@router.get("/{document_id}/fields", response_model=List[ExtractedFieldRead])
async def get_document_fields(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get extracted fields for a document."""
    # Verify document belongs to tenant
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.tenant_id == current_user.tenant_id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return db.query(ExtractedField).filter(
        ExtractedField.document_id == document_id
    ).all()


@router.patch("/{document_id}/fields/{field_id}", response_model=ExtractedFieldRead)
async def update_field(
    document_id: UUID,
    field_id: UUID,
    update: ExtractedFieldUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update extracted field with audit trail."""
    if current_user.role == UserRole.MANAGER:
        raise HTTPException(status_code=403, detail="Managers cannot modify fields")
    
    # Verify document belongs to tenant
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.tenant_id == current_user.tenant_id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    field = db.query(ExtractedField).filter(
        ExtractedField.id == field_id,
        ExtractedField.document_id == document_id
    ).first()
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    
    # Create audit event
    old_value = field.normalized_value or field.raw_value
    new_value = update.normalized_value or update.raw_value
    
    if old_value != new_value:
        event = FieldEvent(
            field_id=field_id,
            user_id=current_user.id,
            event_type=FieldEventType.UPDATED,
            old_value=old_value,
            new_value=new_value,
            comment=update.comment
        )
        db.add(event)
    
    # Update field
    if update.raw_value is not None:
        field.raw_value = update.raw_value
    if update.normalized_value is not None:
        field.normalized_value = update.normalized_value
    
    db.commit()
    db.refresh(field)
    return field


@router.get("/{document_id}/lines", response_model=List[DocumentLineRead])
async def get_document_lines(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get line items for a document."""
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.tenant_id == current_user.tenant_id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return db.query(DocumentLine).filter(
        DocumentLine.document_id == document_id
    ).order_by(DocumentLine.line_number).all()


@router.get("/{document_id}/pdf")
async def get_document_pdf(
    document_id: UUID,
    token: str | None = Query(None, description="Auth token for iframe access"),
    db: Session = Depends(get_db)
):
    """Get PDF file for document viewer. Accepts token via query param for iframe embedding."""
    from fastapi.responses import Response
    from jose import JWTError, jwt
    from app.config import get_settings
    import os
    
    settings = get_settings()
    
    # Get token from query param
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        tenant_id = UUID(payload.get("tenant_id"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.tenant_id == tenant_id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Check file exists
    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="PDF file not found on disk")
    
    # Read file and return with inline disposition for browser preview
    with open(doc.file_path, "rb") as f:
        content = f.read()
    
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{doc.filename}"',
            "Content-Length": str(len(content))
        }
    )

