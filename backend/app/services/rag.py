"""RAG service for document retrieval and question answering.

This service searches documents based on the query and only returns
information that is ACTUALLY present in the documents.
"""
import logging
import re
from uuid import UUID
from typing import List, Dict, Any, Optional

import httpx
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.document import Document
from app.models.extraction import ExtractedField
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class RAGService:
    """RAG service that searches documents and answers based on actual content."""
    
    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id
    
    def _search_documents(self, query: str) -> List[tuple[Document, float, str]]:
        """
        Search documents by text content and metadata.
        Returns: List of (document, relevance_score, matched_snippet)
        """
        query_lower = query.lower()
        
        # Extract potential entity names for search
        # Common patterns: "documenti di X", "fatture di X", "X SRL", "X spa"
        entity_patterns = [
            r"(?:documenti|fatture|ordini|ddt|preventivi)\s+(?:di|per|da)\s+([A-Za-zÀ-ÿ\s]+?)(?:\s|$|\?)",
            r"([A-Za-zÀ-ÿ]+\s+(?:srl|spa|snc|sas|s\.r\.l\.|s\.p\.a\.))",
            r"fornitore\s+([A-Za-zÀ-ÿ\s]+?)(?:\s|$|\?)",
        ]
        
        search_terms = [query_lower]
        for pattern in entity_patterns:
            matches = re.findall(pattern, query_lower, re.IGNORECASE)
            search_terms.extend([m.strip().lower() for m in matches if m.strip()])
        
        # Get all documents
        all_docs = self.db.query(Document).filter(
            Document.tenant_id == self.tenant_id
        ).all()
        
        results = []
        
        for doc in all_docs:
            score = 0.0
            snippets = []
            
            # Search in raw text
            raw_text = (doc.raw_text or "").lower()
            
            for term in search_terms:
                if len(term) < 3:
                    continue
                    
                if term in raw_text:
                    # Find snippet around the match
                    idx = raw_text.find(term)
                    start = max(0, idx - 50)
                    end = min(len(raw_text), idx + len(term) + 100)
                    snippet = raw_text[start:end].replace("\n", " ")
                    snippets.append(f"...{snippet}...")
                    score += 3.0
            
            # Search in metadata
            if doc.fornitore and any(t in doc.fornitore.lower() for t in search_terms):
                score += 5.0
                snippets.append(f"Destinatario: {doc.fornitore}")
            
            if doc.emittente and any(t in doc.emittente.lower() for t in search_terms):
                score += 5.0
                snippets.append(f"Emittente: {doc.emittente}")
            
            if doc.doc_number and any(t in doc.doc_number.lower() for t in search_terms):
                score += 4.0
                snippets.append(f"Numero: {doc.doc_number}")
            
            # Search in extracted fields
            fields = self.db.query(ExtractedField).filter(
                ExtractedField.document_id == doc.id
            ).all()
            
            for field in fields:
                value = (field.normalized_value or field.raw_value or "").lower()
                for term in search_terms:
                    if term in value:
                        score += 2.0
                        snippets.append(f"{field.field_name}: {value}")
            
            if score > 0:
                results.append((doc, score, " | ".join(snippets[:3])))
        
        # Sort by score
        results.sort(key=lambda x: x[1], reverse=True)
        return results
    
    def _get_document_summary(self, doc: Document) -> str:
        """Get a summary of document info for context."""
        parts = [f"📄 {doc.filename}"]
        
        if doc.doc_type:
            type_names = {
                "fattura": "Fattura",
                "ddt": "DDT",
                "po": "Ordine",
                "preventivo": "Preventivo",
                "altro": "Altro"
            }
            parts.append(f"Tipo: {type_names.get(doc.doc_type, doc.doc_type)}")
        
        if doc.emittente:
            parts.append(f"Emittente: {doc.emittente}")
        
        if doc.fornitore:
            parts.append(f"Destinatario: {doc.fornitore}")
        
        if doc.doc_number:
            parts.append(f"N°: {doc.doc_number}")
        
        if doc.doc_date:
            parts.append(f"Data: {doc.doc_date.strftime('%d/%m/%Y')}")
        
        if doc.totale:
            parts.append(f"Totale: €{doc.totale:.2f}")
        
        # Type-specific fields
        if doc.vettore:
            parts.append(f"Vettore: {doc.vettore}")
        if doc.causale_trasporto:
            parts.append(f"Causale: {doc.causale_trasporto}")
        if doc.modalita_pagamento:
            parts.append(f"Pagamento: {doc.modalita_pagamento}")
        if doc.scadenza_pagamento:
            parts.append(f"Scadenza: {doc.scadenza_pagamento.strftime('%d/%m/%Y')}")
        
        return " | ".join(parts)
    
    def _format_search_results(self, results: List[tuple[Document, float, str]]) -> str:
        """Format search results for the LLM context."""
        if not results:
            return "NESSUN DOCUMENTO TROVATO per questa ricerca."
        
        context_parts = []
        for doc, score, snippet in results[:5]:  # Top 5
            summary = self._get_document_summary(doc)
            
            # Include relevant text snippet
            text_preview = ""
            if doc.raw_text:
                text_preview = doc.raw_text[:1500]
            
            context_parts.append(f"""
--- DOCUMENTO ---
{summary}
Rilevanza: {score:.1f}
Testo trovato: {snippet}

Contenuto:
{text_preview}
""")
        
        return "\n".join(context_parts)
    
    def query(self, question: str, history: List[Dict] = None) -> Dict[str, Any]:
        """
        Answer a question by searching documents first.
        
        IMPORTANT: Only includes documents that actually match the query.
        Does not hallucinate or return unrelated documents.
        """
        # First, search for relevant documents
        search_results = self._search_documents(question)
        
        # Format context with only matching documents
        if search_results:
            context = self._format_search_results(search_results)
            matched_docs = [r[0] for r in search_results]
        else:
            # If no matches, provide general overview
            all_docs = self.db.query(Document).filter(
                Document.tenant_id == self.tenant_id
            ).all()
            
            context = "NESSUN DOCUMENTO trovato per la ricerca specifica.\n\nDocumenti disponibili:\n"
            for doc in all_docs:
                context += f"- {self._get_document_summary(doc)}\n"
            matched_docs = []
        
        # Format history
        history_text = ""
        if history:
            history_text = "CRONOLOGIA CHAT RECENTE:\n"
            for msg in history[-5:]: # Last 5 messages
                role = "User" if msg.get("role") == "user" else "Assistant"
                content = msg.get("content", "").replace("\n", " ")
                history_text += f"{role}: {content}\n"
            history_text += "\n"
        
        from datetime import datetime
        today_str = datetime.now().strftime('%d/%m/%Y')

        prompt = f"""Sei un assistente AI per l'analisi di documenti aziendali.
OGGI è: {today_str}

REGOLE FONDAMENTALI:
1. Rispondi SOLO basandoti sui documenti forniti sotto e sulla cronologia chat.
2. Se un documento NON contiene l'informazione cercata, NON includerlo nella risposta.
3. Se non trovi l'informazione, dì chiaramente "Non ho trovato documenti che contengono...".
4. NON inventare informazioni o connessioni tra documenti.
5. Cita SOLO i documenti che effettivamente contengono le informazioni richieste.
6. Usa la cronologia per capire il contesto (es. "di chi parliamo" se l'utente dice "e le sue fatture?").
7. Se l'utente chiede informazioni relative al tempo (es. "questo mese"), usa la data di oggi per orientarti.

{history_text}RISULTATI RICERCA:
{context}

DOMANDA: {question}

Rispondi in modo preciso e onesto. Se non trovi informazioni rilevanti, dillo chiaramente."""

        try:
            with httpx.Client(timeout=60) as client:
                response = client.post(
                    f"{settings.ollama_base_url}/api/generate",
                    json={
                        "model": settings.ollama_chat_model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.1}  # Low temperature for factual
                    }
                )
                
                if response.status_code == 200:
                    answer = response.json().get("response", "")
                    
                    # Only cite documents that were actually found
                    citations = []
                    for doc in matched_docs:
                        # Verify document is mentioned in answer or was searched
                        if doc.filename.lower() in answer.lower() or len(matched_docs) == 1:
                            citations.append({
                                "document_id": str(doc.id),
                                "filename": doc.filename,
                                "page": 1,
                                "snippet": None
                            })
                    
                    return {
                        "answer": answer.strip(),
                        "citations": citations[:3]  # Max 3 citations
                    }
                else:
                    logger.error(f"Ollama error: {response.status_code}")
                    return {
                        "answer": "Errore nel processare la richiesta.",
                        "citations": []
                    }
                    
        except Exception as e:
            logger.error(f"RAG query error: {e}")
            return {
                "answer": f"Errore: {str(e)}",
                "citations": []
            }
