"""Reconciliation service for order/delivery matching queries."""
import logging
from uuid import UUID
from typing import List, Dict, Any

from sqlalchemy.orm import Session

from app.models.document import Document, DocumentType

logger = logging.getLogger(__name__)


class ReconciliationService:
    """Service for reconciling orders with deliveries (DDT/PO matching)."""
    
    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id
    
    def _get_documents_by_type(self, doc_type: str) -> List[Document]:
        """Get all documents of a specific type."""
        return self.db.query(Document).filter(
            Document.tenant_id == self.tenant_id,
            Document.doc_type == doc_type
        ).all()
    
    def _analyze_completeness(self) -> Dict[str, Any]:
        """Analyze if orders are complete based on DDT/PO matching."""
        orders = self._get_documents_by_type("po")
        ddts = self._get_documents_by_type("ddt")
        invoices = self._get_documents_by_type("fattura")
        
        analysis = {
            "total_orders": len(orders),
            "total_ddts": len(ddts),
            "total_invoices": len(invoices),
            "documents": []
        }
        
        for doc in orders + ddts + invoices:
            doc_type_str = doc.doc_type.value if hasattr(doc.doc_type, 'value') else doc.doc_type
            analysis["documents"].append({
                "id": str(doc.id),
                "filename": doc.filename,
                "type": doc_type_str,
                "number": doc.doc_number,
                "date": doc.doc_date.strftime('%d/%m/%Y') if doc.doc_date else None
            })
        
        return analysis
    
    def answer_query(self, question: str) -> Dict[str, Any]:
        """Answer a reconciliation-related question."""
        analysis = self._analyze_completeness()
        
        question_lower = question.lower()
        
        # Build contextual answer
        if "arrivata" in question_lower or "consegna" in question_lower or "merce" in question_lower:
            if analysis["total_ddts"] > 0:
                ddt_list = [d for d in analysis["documents"] if d["type"] == "ddt"]
                answer = f"Ho trovato {len(ddt_list)} DDT (Documenti di Trasporto):\n"
                for d in ddt_list:
                    answer += f"\n• {d['filename']}"
                    if d['number']:
                        answer += f" - N° {d['number']}"
                    if d['date']:
                        answer += f" del {d['date']}"
                
                answer += "\n\nPer verificare se la merce corrisponde all'ordine, confronta le righe articolo nei documenti."
            else:
                answer = "Non ho trovato DDT caricati nel sistema. Per verificare le consegne, carica i documenti di trasporto."
            
            citations = [
                {"document_id": d["id"], "filename": d["filename"], "page": 1, "snippet": None}
                for d in analysis["documents"] if d["type"] == "ddt"
            ]
            
        elif "fattura" in question_lower or "totale" in question_lower:
            invoices = [d for d in analysis["documents"] if d["type"] == "fattura"]
            if invoices:
                answer = f"Ho trovato {len(invoices)} fatture:\n"
                for inv in invoices:
                    answer += f"\n• {inv['filename']}"
                    if inv['number']:
                        answer += f" - N° {inv['number']}"
                    if inv['date']:
                        answer += f" del {inv['date']}"
            else:
                answer = "Non ho trovato fatture caricate nel sistema."
            
            citations = [
                {"document_id": d["id"], "filename": d["filename"], "page": 1, "snippet": None}
                for d in invoices
            ]
            
        elif "ordine" in question_lower or "po" in question_lower:
            orders = [d for d in analysis["documents"] if d["type"] == "po"]
            if orders:
                answer = f"Ho trovato {len(orders)} ordini/PO:\n"
                for o in orders:
                    answer += f"\n• {o['filename']}"
                    if o['number']:
                        answer += f" - N° {o['number']}"
                    if o['date']:
                        answer += f" del {o['date']}"
            else:
                answer = "Non ho trovato ordini caricati nel sistema."
            
            citations = [
                {"document_id": d["id"], "filename": d["filename"], "page": 1, "snippet": None}
                for d in orders
            ]
            
        else:
            # Generic summary
            answer = f"""Riepilogo documenti:
• {analysis['total_orders']} Ordini/PO
• {analysis['total_ddts']} DDT
• {analysis['total_invoices']} Fatture

Posso aiutarti a verificare:
- Se la merce dell'ordine è arrivata (confronto PO vs DDT)
- Il totale delle fatture
- Quali DDT mancano per gli ordini aperti"""
            
            citations = [
                {"document_id": d["id"], "filename": d["filename"], "page": 1, "snippet": None}
                for d in analysis["documents"][:3]
            ]
        
        return {
            "answer": answer,
            "citations": citations
        }
