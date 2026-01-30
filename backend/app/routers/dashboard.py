"""Dashboard router for BI widgets and KPIs."""
from datetime import datetime, timedelta
from uuid import UUID
from typing import List, Optional
from pydantic import BaseModel

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.document import Document, DocumentStatus, DocumentType
from app.models.user import User
from app.routers.auth import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class KPICard(BaseModel):
    """KPI card data."""
    name: str
    value: int | float
    unit: str = ""
    trend: float | None = None  # Percentage change


class DocumentsByType(BaseModel):
    """Documents grouped by type."""
    doc_type: str
    count: int


class DocumentsByStatus(BaseModel):
    """Documents grouped by status."""
    status: str
    count: int


class DashboardData(BaseModel):
    """Full dashboard response."""
    kpis: List[KPICard]
    by_type: List[DocumentsByType]
    by_status: List[DocumentsByStatus]
    recent_documents: List[dict]


@router.get("", response_model=DashboardData)
async def get_dashboard(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get dashboard data for current tenant."""
    tenant_id = current_user.tenant_id
    since = datetime.utcnow() - timedelta(days=days)
    
    # Total documents
    total_docs = db.query(func.count(Document.id)).filter(
        Document.tenant_id == tenant_id
    ).scalar()
    
    # Documents this period
    period_docs = db.query(func.count(Document.id)).filter(
        Document.tenant_id == tenant_id,
        Document.created_at >= since
    ).scalar()
    
    # Validated documents
    validated_docs = db.query(func.count(Document.id)).filter(
        Document.tenant_id == tenant_id,
        Document.status == DocumentStatus.VALIDATED
    ).scalar()
    
    # Failed documents
    failed_docs = db.query(func.count(Document.id)).filter(
        Document.tenant_id == tenant_id,
        Document.status == DocumentStatus.FAILED
    ).scalar()
    
    kpis = [
        KPICard(name="Total Documents", value=total_docs),
        KPICard(name=f"Documents ({days}d)", value=period_docs),
        KPICard(name="Validated", value=validated_docs),
        KPICard(name="Failed", value=failed_docs),
    ]
    
    # By type
    by_type_query = db.query(
        Document.doc_type, func.count(Document.id)
    ).filter(
        Document.tenant_id == tenant_id,
        Document.doc_type.isnot(None)
    ).group_by(Document.doc_type).all()
    
    by_type = [
        DocumentsByType(doc_type=t.value if hasattr(t, 'value') else (t or "unknown"), count=c)
        for t, c in by_type_query
    ]
    
    # By status
    by_status_query = db.query(
        Document.status, func.count(Document.id)
    ).filter(
        Document.tenant_id == tenant_id
    ).group_by(Document.status).all()
    
    by_status = [
        DocumentsByStatus(status=s.value if hasattr(s, 'value') else s, count=c)
        for s, c in by_status_query
    ]
    
    # Recent documents
    recent = db.query(Document).filter(
        Document.tenant_id == tenant_id
    ).order_by(Document.created_at.desc()).limit(10).all()
    
    recent_docs = [
        {
            "id": str(d.id),
            "filename": d.filename,
            "status": d.status.value if hasattr(d.status, 'value') else d.status,
            "doc_type": (d.doc_type.value if hasattr(d.doc_type, 'value') else d.doc_type) if d.doc_type else None,
            "created_at": d.created_at.isoformat()
        }
        for d in recent
    ]
    
    return DashboardData(
        kpis=kpis,
        by_type=by_type,
        by_status=by_status,
        recent_documents=recent_docs
    )


@router.get("/export")
async def export_data(
    format: str = Query("csv", pattern="^(csv|parquet)$"),
    doc_type: Optional[DocumentType] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export document data as CSV or Parquet."""
    from fastapi.responses import StreamingResponse
    import csv
    import io
    
    query = db.query(Document).filter(Document.tenant_id == current_user.tenant_id)
    if doc_type:
        query = query.filter(Document.doc_type == doc_type)
    
    documents = query.all()
    
    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "filename", "doc_type", "doc_number", "doc_date", "status", "created_at"])
        
        for doc in documents:
            writer.writerow([
                str(doc.id),
                doc.filename,
                doc.doc_type.value if doc.doc_type else "",
                doc.doc_number or "",
                doc.doc_date.isoformat() if doc.doc_date else "",
                doc.status.value,
                doc.created_at.isoformat()
            ])
        
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=documents.csv"}
        )
    else:
        # Parquet export (requires pyarrow)
        raise HTTPException(status_code=501, detail="Parquet export not yet implemented")
