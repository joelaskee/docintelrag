"""Ingestion router for document upload and folder processing."""
import hashlib
import os
import shutil
from pathlib import Path
from uuid import UUID, uuid4
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.document import Document, DocumentStatus
from app.models.user import User, UserRole
from app.routers.auth import get_current_user, require_role
from app.schemas.document import DocumentListItem, JobStatus

router = APIRouter(prefix="/ingestion", tags=["ingestion"])
settings = get_settings()

# In-memory job tracking (would use Redis in production)
_jobs: dict[str, JobStatus] = {}

UPLOAD_DIR = Path("/app/uploads")


def get_file_hash(file_path: Path) -> str:
    """Calculate SHA-256 hash of file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def is_path_allowed(path: str) -> bool:
    """Check if path is in allowed list (prevent path traversal)."""
    if not settings.allowed_upload_paths:
        return False
    
    resolved = Path(path).resolve()
    for allowed in settings.allowed_upload_paths:
        allowed_resolved = Path(allowed).resolve()
        try:
            resolved.relative_to(allowed_resolved)
            return True
        except ValueError:
            continue
    return False


@router.post("/upload", response_model=JobStatus)
async def upload_files(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.OPERATORE)),
    db: Session = Depends(get_db)
):
    """Upload multiple PDF files for processing."""
    job_id = str(uuid4())
    job = JobStatus(
        job_id=job_id,
        status="running",
        total=len(files),
        progress=0
    )
    _jobs[job_id] = job
    
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    tenant_dir = UPLOAD_DIR / str(current_user.tenant_id)
    tenant_dir.mkdir(exist_ok=True)
    
    documents_created = []
    
    for i, file in enumerate(files):
        filename = file.filename.lower()
        is_pdf = filename.endswith(".pdf")
        is_image = filename.endswith((".jpg", ".jpeg", ".png"))
        
        if not (is_pdf or is_image):
            job.message = f"Skipped unsupported file: {file.filename}"
            continue
        
        # Save file
        file_id = uuid4()
        file_path = tenant_dir / f"{file_id}.pdf" # Always save as PDF
        
        try:
            if is_image:
                from PIL import Image
                # Reset file pointer
                file.file.seek(0)
                img = Image.open(file.file)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                img.save(file_path, "PDF", resolution=150.0)
                size = file_path.stat().st_size
            else:
                # Is PDF
                file.file.seek(0, 2)
                size = file.file.tell()
                file.file.seek(0)
                
                if size > settings.max_file_size_mb * 1024 * 1024:
                    job.message = f"File too large: {file.filename}"
                    continue
                    
                with open(file_path, "wb") as f:
                    shutil.copyfileobj(file.file, f)
        except Exception as e:
            job.message = f"Error processing {file.filename}: {e}"
            continue
        
        file_hash = get_file_hash(file_path)
        
        # Check for duplicates
        existing = db.query(Document).filter(
            Document.tenant_id == current_user.tenant_id,
            Document.file_hash == file_hash
        ).first()
        
        if existing:
            os.remove(file_path)
            job.message = f"Duplicate skipped: {file.filename}"
            continue
        
        # Create document record
        doc = Document(
            id=file_id,
            tenant_id=current_user.tenant_id,
            filename=file.filename, # Keep original filename for reference? Or change extension? Best to keep orig.
            file_path=str(file_path),
            file_hash=file_hash,
            file_size_bytes=size,
            status=DocumentStatus.QUEUED
        )
        db.add(doc)
        documents_created.append(doc.id)
        
        job.progress = i + 1
    
    db.commit()
    
    job.status = "completed"
    job.documents_created = documents_created
    job.message = f"Created {len(documents_created)} documents"
    
    # Trigger async processing via Celery
    from app.workers.tasks import process_document
    for doc_id in documents_created:
        process_document.delay(str(doc_id))
    
    return job


@router.post("/folder", response_model=JobStatus)
async def ingest_folder(
    folder_path: str = Form(...),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.OPERATORE)),
    db: Session = Depends(get_db)
):
    """Ingest documents from a server folder path."""
    if not is_path_allowed(folder_path):
        raise HTTPException(
            status_code=403,
            detail="Folder path not in allowed list"
        )
    
    folder = Path(folder_path)
    if not folder.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")
    
    pdf_files = list(folder.rglob("*.pdf")) + list(folder.rglob("*.PDF"))
    
    job_id = str(uuid4())
    job = JobStatus(
        job_id=job_id,
        status="running",
        total=len(pdf_files),
        progress=0
    )
    _jobs[job_id] = job
    
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    tenant_dir = UPLOAD_DIR / str(current_user.tenant_id)
    tenant_dir.mkdir(exist_ok=True)
    
    documents_created = []
    
    for i, pdf_path in enumerate(pdf_files):
        size = pdf_path.stat().st_size
        if size > settings.max_file_size_mb * 1024 * 1024:
            continue
        
        file_hash = get_file_hash(pdf_path)
        
        # Check for duplicates
        existing = db.query(Document).filter(
            Document.tenant_id == current_user.tenant_id,
            Document.file_hash == file_hash
        ).first()
        
        if existing:
            continue
        
        # Copy file to upload dir
        file_id = uuid4()
        dest_path = tenant_dir / f"{file_id}.pdf"
        shutil.copy2(pdf_path, dest_path)
        
        # Create document record
        doc = Document(
            id=file_id,
            tenant_id=current_user.tenant_id,
            filename=pdf_path.name,
            file_path=str(dest_path),
            file_hash=file_hash,
            file_size_bytes=size,
            status=DocumentStatus.QUEUED
        )
        db.add(doc)
        documents_created.append(doc.id)
        
        job.progress = i + 1
    
    db.commit()
    
    job.status = "completed"
    job.documents_created = documents_created
    job.message = f"Created {len(documents_created)} documents from folder"
    
    # Trigger async processing
    from app.workers.tasks import process_document
    for doc_id in documents_created:
        process_document.delay(str(doc_id))
    
    return job


@router.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get ingestion job status."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/reprocess/{document_id}")
async def reprocess_document(
    document_id: UUID,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.OPERATORE)),
    db: Session = Depends(get_db)
):
    """Re-process a document with updated extraction logic."""
    from app.models.extraction import ExtractedField, DocumentLine
    
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.tenant_id == current_user.tenant_id
    ).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete existing fields and lines
    db.query(ExtractedField).filter(ExtractedField.document_id == document_id).delete()
    db.query(DocumentLine).filter(DocumentLine.document_id == document_id).delete()
    
    # Reset document metadata
    doc.doc_number = None
    doc.doc_date = None
    doc.status = DocumentStatus.QUEUED
    
    db.commit()
    
    # Trigger reprocessing
    from app.workers.tasks import process_document
    process_document.delay(str(document_id))
    
    return {"message": f"Document {doc.filename} queued for reprocessing", "document_id": str(document_id)}
