"""Document classification service with improved rules."""
import logging
import re
from dataclasses import dataclass
from typing import Optional

import httpx

from app.config import get_settings
from app.models.document import DocumentType

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class ClassificationResult:
    """Document classification result."""
    doc_type: str  # Using string for flexibility
    confidence: float
    method: str  # "rules" or "llm"
    evidence: list[str]  # Keywords or phrases that led to classification


# Classification rules with priorities
# Higher priority = checked first, and if matched strongly, stops further checks
CLASSIFICATION_RULES = {
    # PREVENTIVO - check first because it's often mistaken for fattura
    "preventivo": {
        "priority": 1,
        "keywords": [
            "preventivo", "offerta", "quotazione", "proposta commerciale",
            "quote", "proposal", "estimate", "stima", "offerta commerciale",
            "ns. offerta", "nostra offerta"
        ],
        "patterns": [
            r"preventivo\s*n[°.:\s]*\d*",
            r"offerta\s*n[°.:\s]*\d*",
            r"quotazione",
            r"proposta\s*commerciale",
            r"validità\s*(?:offerta|preventivo)",  # "validità offerta: 30 giorni"
            r"condizioni\s*di\s*offerta",
        ],
        "negative_keywords": []  # Keywords that reduce score
    },
    # DDT - very specific structure
    "ddt": {
        "priority": 2,
        "keywords": [
            "documento di trasporto", "ddt", "bolla di accompagnamento",
            "delivery note", "packing list", "bolla"
        ],
        "patterns": [
            r"d\.?d\.?t\.?\s*n[°.:\s]*\d+",
            r"bolla\s*n[°.:\s]*\d+",
            r"documento\s*di\s*trasporto",
            r"doc\\.?\s*di\s*trasporto",
            r"destinatario\s*:.+destinazione",  # Typical DDT layout
            r"causale\s*trasporto",
            r"vettore",
            r"inizio\s*trasporto",
        ],
        "negative_keywords": ["fattura", "preventivo", "ordine"]
    },
    # FATTURA - invoices have specific legal requirements
    "fattura": {
        "priority": 3,
        "keywords": [
            "fattura", "invoice", "fattura elettronica", 
            "nota di credito", "ricevuta fiscale", "parcella"
        ],
        "patterns": [
            r"fattura\s*n[°.:\s]*[A-Z0-9/-]+",
            r"invoice\s*n[°.:\s]*\d+",
            r"fattura\s*elettronica",
            r"codice\s*destinatario",  # SDI code
            r"split\s*payment",
            r"regime\s*iva",
            r"esigibilità\s*iva",
            r"bollo\s*virtuale",
        ],
        "negative_keywords": ["preventivo", "offerta", "proposta"]
    },
    # PO - Purchase Order
    "po": {
        "priority": 4,
        "keywords": [
            "ordine", "order", "ordine d'acquisto", "purchase order",
            "ordine di acquisto", "conferma ordine", "o.d.a.", "oda"
        ],
        "patterns": [
            r"ordine\s*n[°.:\s]*\d+",
            r"order\s*n[°.:\s]*\d+",
            r"vs\.?\s*ordine",
            r"conferma\s*d'ordine",
            r"rif\.\s*ordine",
        ],
        "negative_keywords": ["fattura", "ddt", "preventivo"]
    }
}


def classify_by_rules(text: str, filename: str = "") -> ClassificationResult | None:
    """Classify document using rule-based keywords and patterns."""
    text_lower = text.lower()
    filename_lower = filename.lower()
    
    # Check filename hints first
    filename_hints = {
        "preventivo": ["preventivo", "offerta", "quote", "quotazione"],
        "ddt": ["ddt", "trasporto", "bolla", "delivery"],
        "fattura": ["fattura", "invoice", "fatt"],
        "po": ["ordine", "order", "po_", "oda"]
    }
    
    filename_match = None
    for doc_type, hints in filename_hints.items():
        for hint in hints:
            if hint in filename_lower:
                filename_match = doc_type
                break
        if filename_match:
            break
    
    scores: dict[str, tuple[float, list[str]]] = {}
    
    # Sort rules by priority
    sorted_rules = sorted(CLASSIFICATION_RULES.items(), key=lambda x: x[1]["priority"])
    
    for doc_type, rules in sorted_rules:
        score = 0.0
        evidence = []
        
        # Filename bonus
        if filename_match == doc_type:
            score += 3.0
            evidence.append(f"filename hint: {filename_lower}")
        
        # Check keywords
        for keyword in rules["keywords"]:
            if keyword in text_lower:
                score += 1.0
                evidence.append(f"keyword: {keyword}")
        
        # Check patterns (more specific = higher score)
        for pattern in rules["patterns"]:
            matches = re.findall(pattern, text_lower)
            if matches:
                score += 2.5
                evidence.append(f"pattern: {matches[0][:30]}")
        
        # Negative keywords reduce score
        for neg_kw in rules.get("negative_keywords", []):
            if neg_kw in text_lower:
                score -= 0.5
        
        if score > 0:
            scores[doc_type] = (score, evidence)
    
    if not scores:
        return None
    
    # Get highest scoring type
    best_type = max(scores.keys(), key=lambda t: scores[t][0])
    best_score, best_evidence = scores[best_type]
    
    # Calculate confidence
    confidence = min(best_score / 10.0, 0.95)  # Normalize to 0-0.95
    
    # Check for ambiguity
    sorted_scores = sorted(scores.items(), key=lambda x: x[1][0], reverse=True)
    if len(sorted_scores) > 1:
        second_type, (second_score, _) = sorted_scores[1]
        if second_score >= best_score * 0.8:  # Within 20%
            confidence *= 0.7
            best_evidence.append(f"ambiguous with: {second_type}")
    
    return ClassificationResult(
        doc_type=best_type,
        confidence=confidence,
        method="rules",
        evidence=best_evidence[:5]
    )


async def classify_by_llm(text: str, filename: str = "") -> ClassificationResult | None:
    """Classify document using LLM with better prompting."""
    prompt = f"""Sei un esperto classificatore di documenti aziendali italiani.

Classifica questo documento in UNA delle seguenti categorie:

1. PREVENTIVO - Offerta commerciale, quotazione, proposta di vendita (NON ancora accettata/pagata)
   Caratteristiche: "Preventivo", "Offerta", "Quotazione", "Proposta", validità temporale

2. DDT - Documento di Trasporto / Bolla di accompagnamento
   Caratteristiche: "DDT", "Documento di trasporto", destinatario, vettore, causale trasporto

3. FATTURA - Documento fiscale che richiede pagamento (già consegnato/prestato)
   Caratteristiche: "Fattura n.", P.IVA, codice SDI, riferimenti fiscali, scadenza pagamento

4. PO - Ordine d'acquisto (richiesta di fornitura dal cliente)
   Caratteristiche: "Ordine n.", "Conferma ordine", data consegna richiesta

5. ALTRO - Se non rientra chiaramente in nessuna delle precedenti

ATTENZIONE: Un PREVENTIVO non è una FATTURA! Il preventivo è una PROPOSTA, la fattura è una RICHIESTA DI PAGAMENTO.

Nome file: {filename}

Testo del documento (primi 3000 caratteri):
---
{text[:3000]}
---

Rispondi SOLO con una riga nel formato:
CATEGORIA: [motivazione breve]

Esempio: PREVENTIVO: contiene "Offerta n." e condizioni di validità"""

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{settings.ollama_base_url}/api/generate",
                json={
                    "model": settings.ollama_chat_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1}
                }
            )
            
            if response.status_code != 200:
                logger.warning(f"Ollama returned {response.status_code}")
                return None
            
            result = response.json()
            answer = result.get("response", "").strip().upper()
            
            # Parse response
            if "PREVENTIVO" in answer:
                doc_type = "preventivo"
            elif "DDT" in answer or "TRASPORTO" in answer or "BOLLA" in answer:
                doc_type = "ddt"
            elif "FATTURA" in answer or "INVOICE" in answer:
                doc_type = "fattura"
            elif "PO" in answer or "ORDINE" in answer:
                doc_type = "po"
            else:
                doc_type = "altro"
            
            return ClassificationResult(
                doc_type=doc_type,
                confidence=0.8,
                method="llm",
                evidence=[answer[:100]]
            )
            
    except Exception as e:
        logger.error(f"LLM classification error: {e}")
        return None


async def classify_document(text: str, filename: str = "") -> ClassificationResult:
    """
    Classify document using hybrid approach.
    
    1. Try rule-based classification first (uses filename + content)
    2. If ambiguous or low confidence, try LLM
    3. If both agree, boost confidence
    """
    # Try rules first
    rules_result = classify_by_rules(text, filename)
    
    if rules_result and rules_result.confidence >= 0.7:
        logger.info(f"Classification by rules: {rules_result.doc_type} ({rules_result.confidence:.2f})")
        return rules_result
    
    # Try LLM for low confidence or no match
    llm_result = await classify_by_llm(text, filename)
    
    if llm_result:
        logger.info(f"Classification by LLM: {llm_result.doc_type} ({llm_result.confidence:.2f})")
        
        # If both agree, boost confidence
        if rules_result and rules_result.doc_type == llm_result.doc_type:
            return ClassificationResult(
                doc_type=llm_result.doc_type,
                confidence=min(rules_result.confidence + 0.2, 0.98),
                method="hybrid",
                evidence=rules_result.evidence + llm_result.evidence
            )
        return llm_result
    
    # Fallback to rules result or ALTRO
    if rules_result:
        return rules_result
    
    return ClassificationResult(
        doc_type="altro",
        confidence=0.5,
        method="fallback",
        evidence=["No classification match found"]
    )
