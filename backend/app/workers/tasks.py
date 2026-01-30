"""Celery tasks for async document processing."""
import logging
from datetime import datetime

from app.workers.celery_app import celery_app
from app.database import SessionLocal
from app.models.document import Document, DocumentPage, DocumentStatus
from app.models.extraction import ExtractedField, DocumentLine
from app.services.extraction import extract_text_from_pdf
from app.services.ocr import run_ocr
from app.services.classification import classify_document
from app.services.metatag import extract_fields

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def process_document(self, document_id: str):
    """
    Main document processing pipeline.
    
    Steps:
    1. Extract text (native PDF)
    2. If scanned, run OCR
    3. Classify document type
    4. Extract structured fields
    5. Update document status
    """
    db = SessionLocal()
    
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        
        if not doc:
            logger.error(f"Document {document_id} not found")
            return {"status": "error", "message": "Document not found"}
        
        # Update status to processing
        doc.status = DocumentStatus.PROCESSING
        db.commit()
        
        logger.info(f"Processing document: {doc.filename}")
        
        # Step 1: Extract text
        extraction = extract_text_from_pdf(doc.file_path)
        
        doc.is_scanned = extraction.is_scanned
        doc.raw_text = extraction.raw_text
        doc.warnings = extraction.warnings
        
        # Save pages
        for page in extraction.pages:
            db_page = DocumentPage(
                document_id=doc.id,
                page_number=page.page_number,
                text_content=page.text
            )
            db.add(db_page)
        
        # Step 2: OCR if needed
        if extraction.is_scanned:
            logger.info(f"Running OCR for scanned document: {doc.filename}")
            
            ocr_result = run_ocr(doc.file_path)
            
            doc.ocr_quality = ocr_result.avg_confidence
            doc.warnings = doc.warnings + ocr_result.warnings
            
            # Update page text with OCR results
            for ocr_page in ocr_result.pages:
                db_page = db.query(DocumentPage).filter(
                    DocumentPage.document_id == doc.id,
                    DocumentPage.page_number == ocr_page.page_number
                ).first()
                
                if db_page:
                    db_page.text_content = ocr_page.text
                    db_page.ocr_confidence = ocr_page.confidence
            
            # Update raw_text with OCR
            doc.raw_text = "\n\n".join(p.text for p in ocr_result.pages)
        
        db.commit()
        
        # Step 3: Classify document (with filename for hints)
        import asyncio
        classification = asyncio.get_event_loop().run_until_complete(
            classify_document(doc.raw_text or "", filename=doc.filename)
        )
        
        doc.doc_type = classification.doc_type
        doc.doc_type_confidence = classification.confidence
        
        db.commit()
        
        # Step 4: Extract fields (with doc_type for semantic context)
        page_texts = [p.text for p in extraction.pages]
        doc_type_str = doc.doc_type if doc.doc_type else "unknown"
        field_result = asyncio.get_event_loop().run_until_complete(
            extract_fields(doc.raw_text or "", page_texts, doc_type=doc_type_str)
        )
        
        # Clear old extracted fields and lines to prevent duplicates on reprocess
        db.query(ExtractedField).filter(ExtractedField.document_id == doc.id).delete()
        db.query(DocumentLine).filter(DocumentLine.document_id == doc.id).delete()
        
        for field in field_result.fields:
            db_field = ExtractedField(
                document_id=doc.id,
                field_name=field.field_name,
                raw_value=field.raw_value,
                normalized_value=field.normalized_value,
                confidence=field.confidence,
                page=field.page
            )
            db.add(db_field)
            
            # Update doc metadata for key fields
            if field.field_name == "numero_documento":
                doc.doc_number = field.normalized_value
            elif field.field_name == "data_documento":
                try:
                    doc.doc_date = datetime.fromisoformat(field.normalized_value)
                except (ValueError, TypeError):
                    pass
            elif field.field_name == "fornitore":
                doc.fornitore = field.normalized_value
            elif field.field_name == "emittente":
                doc.emittente = field.normalized_value
            elif field.field_name == "totale":
                try:
                    doc.totale = float(field.normalized_value)
                except (ValueError, TypeError):
                    pass
            # Type-specific fields
            elif field.field_name == "vettore":
                doc.vettore = field.normalized_value
            elif field.field_name == "causale_trasporto":
                doc.causale_trasporto = field.normalized_value
            elif field.field_name == "scadenza_pagamento":
                try:
                    doc.scadenza_pagamento = datetime.fromisoformat(field.normalized_value)
                except (ValueError, TypeError):
                    pass
            elif field.field_name == "modalita_pagamento":
                doc.modalita_pagamento = field.normalized_value
            elif field.field_name == "imponibile":
                try:
                    doc.imponibile = float(field.normalized_value)
                except (ValueError, TypeError):
                    pass
            elif field.field_name == "aliquota_iva":
                try:
                    doc.aliquota_iva = float(field.normalized_value)
                except (ValueError, TypeError):
                    pass
            elif field.field_name == "importo_iva":
                try:
                    doc.importo_iva = float(field.normalized_value)
                except (ValueError, TypeError):
                    pass
            elif field.field_name == "validita_offerta":
                try:
                    doc.validita_offerta = datetime.fromisoformat(field.normalized_value)
                except (ValueError, TypeError):
                    pass
            elif field.field_name == "data_consegna":
                try:
                    doc.data_consegna = datetime.fromisoformat(field.normalized_value)
                except (ValueError, TypeError):
                    pass
        
        for line in field_result.lines:
            db_line = DocumentLine(
                document_id=doc.id,
                line_number=line["line_number"],
                item_code=line.get("item_code"),
                description=line.get("description"),
                quantity=line.get("quantity"),
                unit=line.get("unit"),
                unit_price=line.get("unit_price"),
                confidence=line.get("confidence", 0.5)
            )
            db.add(db_line)
        
        doc.warnings = doc.warnings + field_result.warnings
        
        # Step 5: Update status
        doc.status = DocumentStatus.EXTRACTED
        doc.processed_at = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"Successfully processed document: {doc.filename}")
        
        return {
            "status": "success",
            "document_id": str(doc.id),
            "doc_type": doc.doc_type.value if hasattr(doc.doc_type, "value") else doc.doc_type,
            "fields_extracted": len(field_result.fields),
            "lines_extracted": len(field_result.lines)
        }
        
    except Exception as e:
        logger.exception(f"Error processing document {document_id}: {e}")
        
        # Update status to failed
        if doc:
            doc.status = DocumentStatus.FAILED
            doc.error_message = str(e)
            db.commit()
        
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))
        
    finally:
        db.close()


@celery_app.task
def generate_embeddings(document_id: str):
    """Generate embeddings for document lines (for RAG)."""
    import asyncio
    import httpx
    
    from app.config import get_settings
    settings = get_settings()
    
    db = SessionLocal()
    
    try:
        lines = db.query(DocumentLine).filter(
            DocumentLine.document_id == document_id,
            DocumentLine.embedding.is_(None)
        ).all()
        
        async def embed_line(line: DocumentLine):
            text = f"{line.item_code or ''} {line.description or ''}"
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{settings.ollama_base_url}/api/embeddings",
                    json={"model": settings.ollama_embed_model, "prompt": text}
                )
                
                if response.status_code == 200:
                    embedding = response.json().get("embedding")
                    if embedding:
                        line.embedding = embedding
        
        loop = asyncio.get_event_loop()
        for line in lines:
            loop.run_until_complete(embed_line(line))
        
        db.commit()
        
        return {"status": "success", "lines_embedded": len(lines)}
        
    finally:
        db.close()
