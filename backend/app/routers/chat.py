"""Chat router for RAG chatbot."""
from uuid import UUID
from typing import List
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.routers.auth import get_current_user

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatMessage(BaseModel):
    """Chat message."""
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    """Chat request."""
    message: str
    history: List[ChatMessage] = []


class Citation(BaseModel):
    """Document citation in response."""
    document_id: UUID
    filename: str
    page: int | None = None
    snippet: str | None = None


class ChatResponse(BaseModel):
    """Chat response with citations."""
    message: str
    citations: List[Citation] = []
    used_reconciliation: bool = False


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Chat with documents using RAG.
    
    Routes to reconciliation engine for order/delivery questions,
    otherwise uses standard RAG retrieval.
    """
    from app.services.rag import RAGService
    from app.services.reconciliation import ReconciliationService
    
    # Detect if this is a reconciliation question
    reconciliation_keywords = [
        "arrivata", "consegnato", "merce", "ordine", "ddt",
        "completo", "parziale", "mancante", "consegna"
    ]
    
    message_lower = request.message.lower()
    is_reconciliation = any(kw in message_lower for kw in reconciliation_keywords)
    
    if is_reconciliation:
        # Use reconciliation engine
        recon_service = ReconciliationService(db, current_user.tenant_id)
        result = recon_service.answer_query(request.message)
        return ChatResponse(
            message=result["answer"],
            citations=result.get("citations", []),
            used_reconciliation=True
        )
    else:
        # Use standard RAG
        rag_service = RAGService(db, current_user.tenant_id)
        result = rag_service.query(request.message, history=request.history)
        return ChatResponse(
            message=result["answer"],
            citations=result.get("citations", []),
            used_reconciliation=False
        )


@router.get("/history")
async def get_chat_history(
    current_user: User = Depends(get_current_user)
):
    """Get chat history for current user (placeholder)."""
    # TODO: Implement chat history storage
    return {"history": []}
