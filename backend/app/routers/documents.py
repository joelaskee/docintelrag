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


@router.get("/{document_id}/pages/{page_num}/preview")
async def get_page_preview(
    document_id: UUID,
    page_num: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get page preview image as base64 JPEG for rotation modal."""
    from fastapi.responses import Response
    from app.services.extraction import get_page_as_image
    from app.models.document import DocumentPage
    import io
    
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.tenant_id == current_user.tenant_id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get page rotation if exists
    page = db.query(DocumentPage).filter(
        DocumentPage.document_id == document_id,
        DocumentPage.page_number == page_num
    ).first()
    
    rotation = page.rotation_angle if page else 0
    
    # Render page as image
    try:
        image = get_page_as_image(doc.file_path, page_num, dpi=150)
        if rotation:
            image = image.rotate(-rotation, expand=True)  # Negative for clockwise
        
        # Convert to JPEG
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=85)
        buffer.seek(0)
        
        return Response(
            content=buffer.read(),
            media_type="image/jpeg"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to render page: {str(e)}")


@router.patch("/{document_id}/pages/{page_num}/rotation")
async def set_page_rotation(
    document_id: UUID,
    page_num: int,
    rotation: int = Query(..., description="Rotation angle: 0, 90, 180, or 270"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Set rotation angle for a page."""
    from app.models.document import DocumentPage
    
    if rotation not in (0, 90, 180, 270):
        raise HTTPException(status_code=400, detail="Rotation must be 0, 90, 180, or 270")
    
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.tenant_id == current_user.tenant_id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get or create page record
    page = db.query(DocumentPage).filter(
        DocumentPage.document_id == document_id,
        DocumentPage.page_number == page_num
    ).first()
    
    if page:
        page.rotation_angle = rotation
    else:
        # Create page record if doesn't exist
        page = DocumentPage(
            document_id=document_id,
            page_number=page_num,
            rotation_angle=rotation
        )
        db.add(page)
    
    db.commit()
    return {"message": f"Page {page_num} rotation set to {rotation}°", "rotation": rotation}


@router.post("/{document_id}/confirm-rotation")
async def confirm_rotation(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Confirm rotations and resume document processing."""
    from app.workers.tasks import process_document_after_rotation
    
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.tenant_id == current_user.tenant_id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if doc.status != DocumentStatus.NEEDS_ROTATION.value:
        raise HTTPException(
            status_code=400, 
            detail=f"Document status is '{doc.status}', not 'needs_rotation'"
        )
    
    # Reset to processing and queue the task
    doc.status = DocumentStatus.PROCESSING.value
    db.commit()
    
    # Queue task for processing with rotations applied
    process_document_after_rotation.delay(str(document_id))
    
    return {"message": f"Document {doc.filename} queued for processing with rotations applied"}


@router.get("/{document_id}/page-count")
async def get_page_count(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get total page count for a document."""
    import fitz
    
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.tenant_id == current_user.tenant_id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    try:
        pdf = fitz.open(doc.file_path)
        page_count = len(pdf)
        pdf.close()
        return {"page_count": page_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read PDF: {str(e)}")


@router.delete("/{document_id}")
async def delete_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a document and all related data."""
    import os
    from app.models.document import DocumentPage
    
    if current_user.role == UserRole.MANAGER:
        raise HTTPException(status_code=403, detail="Managers cannot delete documents")
    
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.tenant_id == current_user.tenant_id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    file_path = doc.file_path
    filename = doc.filename
    
    # Delete related data
    db.query(FieldEvent).filter(
        FieldEvent.field_id.in_(
            db.query(ExtractedField.id).filter(ExtractedField.document_id == document_id)
        )
    ).delete(synchronize_session=False)
    db.query(ExtractedField).filter(ExtractedField.document_id == document_id).delete()
    db.query(DocumentLine).filter(DocumentLine.document_id == document_id).delete()
    db.query(DocumentPage).filter(DocumentPage.document_id == document_id).delete()
    db.delete(doc)
    db.commit()
    
    # Delete file from disk
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            pass  # File deletion is not critical
    
    return {"message": f"Document '{filename}' deleted successfully"}


@router.post("/{document_id}/reprocess")
async def reprocess_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reprocess a document (re-run OCR and extraction)."""
    from app.models.document import DocumentPage
    from app.workers.tasks import process_document
    
    if current_user.role == UserRole.MANAGER:
        raise HTTPException(status_code=403, detail="Managers cannot reprocess documents")
    
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.tenant_id == current_user.tenant_id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Clear previous extraction data
    db.query(FieldEvent).filter(
        FieldEvent.field_id.in_(
            db.query(ExtractedField.id).filter(ExtractedField.document_id == document_id)
        )
    ).delete(synchronize_session=False)
    db.query(ExtractedField).filter(ExtractedField.document_id == document_id).delete()
    db.query(DocumentLine).filter(DocumentLine.document_id == document_id).delete()
    db.query(DocumentPage).filter(DocumentPage.document_id == document_id).delete()
    
    # Reset document status
    doc.status = DocumentStatus.QUEUED.value
    doc.raw_text = None
    doc.ocr_quality = None
    doc.doc_type = None
    doc.doc_type_confidence = None
    doc.error_message = None
    doc.warnings = []
    
    db.commit()
    
    # Queue for processing
    process_document.delay(str(document_id))
    
    return {"message": f"Document '{doc.filename}' queued for reprocessing"}


@router.post("/{document_id}/stop-processing")
async def stop_processing(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Stop processing a document and mark it as failed."""
    if current_user.role == UserRole.MANAGER:
        raise HTTPException(status_code=403, detail="Managers cannot stop document processing")
    
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.tenant_id == current_user.tenant_id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Set to failed with message
    doc.status = DocumentStatus.FAILED.value
    doc.error_message = "Processing stopped manually by user"
    
    db.commit()
    
    return {"message": f"Document '{doc.filename}' processing stopped"}
