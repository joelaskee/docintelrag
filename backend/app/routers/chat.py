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


from app.models.chat import ChatSession, ChatMessage as DBChatMessage

class ChatRequest(BaseModel):
    """Chat request."""
    message: str
    session_id: UUID | None = None
    # 'history' field removed/ignored as we use DB persistence

class Citation(BaseModel):
    """Document citation in response."""
    document_id: UUID
    filename: str
    page: int | None = None
    snippet: str | None = None

class ChatResponse(BaseModel):
    """Chat response with citations."""
    message: str
    session_id: UUID
    citations: List[Citation] = []
    used_reconciliation: bool = False


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Chat with documents using RAG + BI + Reconciliation.
    Persists history and uses it for context.
    """
    from app.services.rag import RAGService
    from app.services.reconciliation import ReconciliationService
    from app.services.bi import bi_service
    
    # 1. Session Management
    session = None
    if request.session_id:
        session = db.query(ChatSession).filter(
            ChatSession.id == request.session_id,
            ChatSession.tenant_id == current_user.tenant_id
        ).first()
    
    if not session:
        # Create new session
        title = request.message[:50] + "..." if len(request.message) > 50 else request.message
        session = ChatSession(
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            title=title
        )
        db.add(session)
        db.commit()
    
    # 2. Save User Message
    user_msg = DBChatMessage(
        session_id=session.id,
        role="user",
        content=request.message
    )
    db.add(user_msg)
    db.commit()
    
    # 3. Retrieve Context (Last 10 messages)
    history_msgs = db.query(DBChatMessage).filter(
        DBChatMessage.session_id == session.id
    ).order_by(DBChatMessage.created_at.desc()).limit(11).all() # +1 includes current
    
    # Convert to format expected by services (chronological order)
    # Exclude the current message we just added to avoid duplication if service adds it
    # Actually RAGService expects "history" as previous context.
    history_dicts = []
    for msg in reversed(history_msgs):
        if msg.id != user_msg.id: # Exclude current
            history_dicts.append({"role": msg.role, "content": msg.content})

    message_lower = request.message.lower()
    
    # 4. Route Logic
    response_text = ""
    citations = []
    used_recon = False
    
    # A. Reconciliation
    reconciliation_keywords = [
        "arrivata", "consegnato", "merce", "ordine", "ddt",
        "completo", "parziale", "mancante", "consegna"
    ]
    is_reconciliation = any(kw in message_lower for kw in reconciliation_keywords)
    
    # B. BI / Analytics
    bi_keywords = [
        "quanto ho speso", "spesa totale", "totale fatture", 
        "somma", "media", "quanti", "quante", 
        "classifica", "top 5", "top 3", "top 10", "fornitori principali",
        "andamento", "statistiche", "report", "riepilogo",
        "a quanto ammonta", "totale", "complessivo"
    ]
    is_bi = any(kw in message_lower for kw in bi_keywords)

    if is_reconciliation:
        recon_service = ReconciliationService(db, current_user.tenant_id)
        result = recon_service.answer_query(request.message)
        response_text = result["answer"]
        citations = [Citation(**c) for c in result.get("citations", [])]
        used_recon = True
        
    elif is_bi:
        bi_result = bi_service.process_query(request.message)
        if bi_result.get("sql") and bi_result.get("data"):
            response_text = bi_result["answer"]
            used_recon = False
        else:
            # Fallback to RAG if BI fails
            rag_service = RAGService(db, current_user.tenant_id)
            result = rag_service.query(request.message, history=history_dicts)
            response_text = result["answer"]
            citations = [Citation(**c) for c in result.get("citations", [])]

    else:
        # Standard RAG
        rag_service = RAGService(db, current_user.tenant_id)
        result = rag_service.query(request.message, history=history_dicts)
        response_text = result["answer"]
        citations = [Citation(**c) for c in result.get("citations", [])]

    # 5. Save Assistant Response
    asst_msg = DBChatMessage(
        session_id=session.id,
        role="assistant",
        content=response_text,
        metadata_={
            "citations": [c.model_dump() for c in citations], # Pydantic v2 uses model_dump
            "used_reconciliation": used_recon
        }
    )
    db.add(asst_msg)
    db.commit()
    
    return ChatResponse(
        message=response_text,
        session_id=session.id,
        citations=citations,
        used_reconciliation=used_recon
    )


@router.get("/sessions")
async def get_chat_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's chat sessions."""
    sessions = db.query(ChatSession).filter(
        ChatSession.user_id == current_user.id,
        ChatSession.tenant_id == current_user.tenant_id
    ).order_by(ChatSession.updated_at.desc()).all()
    
    return [{"id": s.id, "title": s.title, "date": s.updated_at} for s in sessions]


@router.get("/sessions/{session_id}")
async def get_chat_messages(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get messages for a specific session."""
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    messages = db.query(DBChatMessage).filter(
        DBChatMessage.session_id == session.id
    ).order_by(DBChatMessage.created_at.asc()).all()
    
    return [{
        "role": m.role, 
        "content": m.content, 
        "created_at": m.created_at,
        "citations": (m.metadata_ or {}).get("citations", []),
        "used_reconciliation": (m.metadata_ or {}).get("used_reconciliation", False)
    } for m in messages]
