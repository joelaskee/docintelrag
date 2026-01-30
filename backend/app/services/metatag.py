"""Meta-tagging service for structured field extraction with semantic understanding."""
import re
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class ExtractedFieldResult:
    """Single extracted field with evidence."""
    field_name: str
    raw_value: str | None
    normalized_value: str | None
    confidence: float
    page: int | None = None
    evidence_text: str | None = None


@dataclass
class ExtractionOutput:
    """Full extraction output for a document."""
    fields: list[ExtractedFieldResult]
    lines: list[dict]
    warnings: list[str]


def normalize_date(date_str: str) -> str | None:
    """Normalize date string to ISO format."""
    if not date_str:
        return None
        
    formats = [
        "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
        "%d/%m/%y", "%d-%m-%y", "%d.%m.%y",
        "%Y-%m-%d",  # Already ISO
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            if dt.year < 100:
                dt = dt.replace(year=dt.year + 2000)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return date_str


def normalize_amount(amount_str: str) -> str | None:
    """
    Normalize monetary amount.
    
    Handles both formats:
    - Italian: 1.234,56 (dot as thousands sep, comma as decimal)
    - Standard: 1234.56 (dot as decimal)
    """
    if not amount_str:
        return None
    
    # Remove currency symbols and whitespace
    cleaned = re.sub(r'[€$\s]', '', str(amount_str))
    
    if not cleaned:
        return None
    
    # Detect format: if both . and , are present, determine which is decimal
    has_dot = '.' in cleaned
    has_comma = ',' in cleaned
    
    if has_comma and has_dot:
        # Both present: comma after dot = Italian (1.234,56)
        dot_pos = cleaned.rfind('.')
        comma_pos = cleaned.rfind(',')
        if comma_pos > dot_pos:
            # Italian format: 1.234,56
            cleaned = cleaned.replace('.', '').replace(',', '.')
        else:
            # English format with comma as thousands: 1,234.56
            cleaned = cleaned.replace(',', '')
    elif has_comma:
        # Only comma: check if it's decimal (X,XX) or thousands (X,XXX)
        parts = cleaned.split(',')
        if len(parts) == 2 and len(parts[1]) <= 2:
            # Decimal comma: 123,45
            cleaned = cleaned.replace(',', '.')
        else:
            # Thousands comma: 1,234
            cleaned = cleaned.replace(',', '')
    # If only dot: it's either decimal (123.45) or Italian thousands (1.234)
    elif has_dot:
        parts = cleaned.split('.')
        if len(parts) == 2 and len(parts[1]) == 2:
            # Decimal dot: 123.45 - keep as is
            pass
        elif len(parts) == 2 and len(parts[1]) == 3:
            # Italian thousands without decimals: 1.234 = 1234
            cleaned = cleaned.replace('.', '')
        # Otherwise keep as is (assume decimal)
    
    try:
        value = float(cleaned)
        return f"{value:.2f}"
    except ValueError:
        return amount_str



def validate_partita_iva(value: str) -> str | None:
    """Validate Italian Partita IVA (11 digits) or Codice Fiscale (16 chars)."""
    if not value:
        return None
    cleaned = re.sub(r'[^A-Z0-9]', '', value.upper().strip())
    
    # Valid if 11 digits (P.IVA) or 16 alphanumeric (CF)
    if len(cleaned) == 11 and cleaned.isdigit():
        return cleaned
    elif len(cleaned) == 16:
        return cleaned
    return None


def validate_doc_number(value: str) -> str | None:
    """Validate document number - must contain at least one digit and be reasonable length."""
    if not value:
        return None
    
    cleaned = value.strip()
    
    # Must contain at least one digit to be a document number
    if not re.search(r'\d', cleaned):
        return None
    
    # Remove excessive whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # Should be reasonably short (document numbers are typically < 25 chars)
    if len(cleaned) < 2 or len(cleaned) > 25:
        return None
    
    return cleaned.upper()


async def extract_with_llm_semantic(text: str, doc_type: str) -> dict:
    """
    Use LLM to semantically interpret the document and extract structured data.
    
    This is the PRIMARY extraction method - it understands context and meaning,
    not just patterns.
    """
    
    doc_type_desc = {
        "fattura": "Fattura (invoice)",
        "ddt": "Documento di Trasporto / Bolla (delivery note)",
        "po": "Ordine di Acquisto (purchase order)",
        "unknown": "documento non classificato"
    }.get(doc_type, "documento")
    
    # Build type-specific fields section
    type_specific_rules = ""
    type_specific_json = ""
    
    if doc_type == "ddt":
        type_specific_rules = """
7. "vettore": Nome del corriere/trasportatore (es: TNT, Bartolini, DHL). Cerca "VETTORE", "CORRIERE", "TRASPORTATORE".
8. "causale_trasporto": Motivo del trasporto. Cerca "CAUSALE", "CAUSALE DEL TRASPORTO". Valori tipici: "Vendita", "Conto Visione", "Reso", "Omaggio".
"""
        type_specific_json = '"vettore": "...", "causale_trasporto": "...",'
        
    elif doc_type == "fattura":
        type_specific_rules = """
7. "imponibile": Totale imponibile (senza IVA). Cerca "IMPONIBILE", "TOTALE IMPONIBILE".
8. "aliquota_iva": Percentuale IVA (es: 22, 10, 4). Solo il numero.
9. "importo_iva": Importo IVA in euro.
10. "scadenza_pagamento": Data scadenza pagamento. Formato YYYY-MM-DD.
11. "modalita_pagamento": Metodo di pagamento. Cerca "PAGAMENTO", "MODALITÀ PAGAMENTO". Es: "Bonifico Bancario", "Rimessa Diretta", "RiBa 30gg".
"""
        type_specific_json = '"imponibile": 100.00, "aliquota_iva": 22, "importo_iva": 22.00, "scadenza_pagamento": "YYYY-MM-DD", "modalita_pagamento": "...",'
        
    elif doc_type == "preventivo":
        type_specific_rules = """
7. "validita_offerta": Data o giorni di validità dell'offerta. Se è una data, formattare come YYYY-MM-DD. Se sono giorni (es: "30 giorni"), restituire "30 giorni".
8. "condizioni": Eventuali condizioni o note importanti dell'offerta.
"""
        type_specific_json = '"validita_offerta": "...", "condizioni": "...",'
        
    elif doc_type == "po":
        type_specific_rules = """
7. "data_consegna": Data di consegna richiesta. Formato YYYY-MM-DD.
8. "indirizzo_consegna": Indirizzo dove consegnare la merce.
"""
        type_specific_json = '"data_consegna": "YYYY-MM-DD", "indirizzo_consegna": "...",'
    
    prompt = f"""Sei un esperto estrattore di dati da documenti aziendali italiani.
Analizza questo {doc_type_desc} ed estrai SOLO i dati effettivamente presenti.

REGOLE IMPORTANTI:
1. "numero_documento": Cerca esplicitamente "Fattura N.", "DDT N.", "Ordine N.", "Nr.", "N°". 
   DEVE essere un codice/numero breve (es: "2024/001", "FT-123", "A00001"). 
   NON mettere indirizzi, nomi o descrizioni come numero documento.
   Se non trovi un numero documento chiaro, metti null.

2. "data_documento": La data del documento (es: data fattura, data DDT). 
   Formato: DD/MM/YYYY o simile. Converti in YYYY-MM-DD.

3. "partita_iva": P.IVA (11 cifre) o Codice Fiscale (16 caratteri). 
   Cerca "P.IVA", "Partita IVA", "C.F.". Solo numeri/lettere.

4. "emittente": L'azienda che HA EMESSO il documento (chi lo ha creato/inviato).
   Di solito è in alto a sinistra, con logo, indirizzo completo, P.IVA, telefono.
   Solo il nome dell'azienda, non l'indirizzo.

5. "destinatario": L'azienda a cui è destinato il documento (chi lo riceve).
   Di solito sotto "DESTINATARIO", "SPETT.LE", "Cliente".
   Solo il nome dell'azienda, non l'indirizzo.

6. "totale": Importo totale finale. Solo numeri e decimali.
{type_specific_rules}
RIGHE ARTICOLO:
"righe_articolo": Array di oggetti con: codice, descrizione, quantita, prezzo_unitario.
   - Le colonne tipiche sono: CODICE | DESCRIZIONE | UM | QUANTITA | PREZZO | SCONTO | IMPORTO
   - ATTENZIONE: Il valore dopo "N" o "PZ" è la QUANTITA.
   - OGNI RIGA ha la SUA quantità. Non copiare valori.

IMPORTANTE: Se un campo non è chiaramente identificabile, usa null.

Rispondi SOLO con JSON valido:

{{
  "numero_documento": "...", 
  "data_documento": "YYYY-MM-DD",
  "partita_iva": "...",
  "emittente": "...",
  "destinatario": "...",
  "totale": "1234.56",
  {type_specific_json}
  "righe_articolo": [
    {{"codice": "...", "descrizione": "...", "quantita": 5.0, "prezzo_unitario": 99.00}}
  ]
}}

TESTO DEL DOCUMENTO:
---
{text[:6000]}
---

JSON:"""

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{settings.ollama_base_url}/api/generate",
                json={
                    "model": settings.ollama_chat_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Low temperature for consistency
                        "num_predict": 1000
                    }
                }
            )
            
            if response.status_code != 200:
                logger.error(f"LLM extraction failed: {response.status_code}")
                return {}
            
            result = response.json()
            answer = result.get("response", "")
            
            # Extract JSON from response
            # Try to find JSON block
            json_match = re.search(r'\{.*\}', answer, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                    logger.info(f"LLM extraction successful: {list(data.keys())}")
                    return data
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse LLM JSON: {e}")
                    logger.debug(f"Raw response: {answer[:500]}")
            else:
                logger.error("No JSON found in LLM response")
                logger.debug(f"Raw response: {answer[:500]}")
                    
    except Exception as e:
        logger.error(f"LLM extraction error: {e}")
    
    return {}


def extract_by_rules_fallback(text: str) -> list[ExtractedFieldResult]:
    """
    Fallback regex extraction for when LLM is unavailable.
    Only extracts high-confidence patterns with semantic validation.
    """
    results = []
    text_lower = text.lower()
    
    # P.IVA - very specific pattern
    piva_match = re.search(r'(?:p\.?\s*iva|partita\s*iva)[:\s]*(\d{11})', text_lower)
    if piva_match:
        results.append(ExtractedFieldResult(
            field_name="partita_iva",
            raw_value=piva_match.group(1),
            normalized_value=piva_match.group(1),
            confidence=0.85,
            evidence_text=piva_match.group(0)
        ))
    
    # Date - look for explicit document date labels
    date_match = re.search(
        r'(?:data\s*(?:fattura|documento|ddt|ordine)?)[:\s]*(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})',
        text_lower
    )
    if date_match:
        normalized = normalize_date(date_match.group(1))
        results.append(ExtractedFieldResult(
            field_name="data_documento",
            raw_value=date_match.group(1),
            normalized_value=normalized,
            confidence=0.7,
            evidence_text=date_match.group(0)
        ))
    
    # Document number - look for explicit labels, must contain digits
    doc_num_match = re.search(
        r'(?:fattura|ddt|ordine|bolla)\s*(?:n[°.:\s]|nr\.?\s*)([A-Z0-9/-]{2,20})',
        text_lower, re.IGNORECASE
    )
    if doc_num_match:
        value = doc_num_match.group(1)
        if validate_doc_number(value):
            results.append(ExtractedFieldResult(
                field_name="numero_documento",
                raw_value=value,
                normalized_value=validate_doc_number(value),
                confidence=0.6,
                evidence_text=doc_num_match.group(0)
            ))
    
    return results


async def extract_fields(text: str, page_texts: list[str] | None = None, doc_type: str = "unknown") -> ExtractionOutput:
    """
    Extract structured fields from document text.
    
    Primary method: LLM-based semantic extraction
    Fallback: Rule-based for specific high-confidence patterns
    """
    warnings = []
    fields = []
    lines = []
    
    # Primary: LLM semantic extraction
    llm_data = await extract_with_llm_semantic(text, doc_type)
    
    if llm_data:
        # Process LLM results with validation
        
        # Numero documento - validate
        if llm_data.get("numero_documento"):
            num = str(llm_data["numero_documento"])
            validated = validate_doc_number(num)
            if validated:
                fields.append(ExtractedFieldResult(
                    field_name="numero_documento",
                    raw_value=num,
                    normalized_value=validated,
                    confidence=0.85,
                    evidence_text="LLM semantic extraction"
                ))
            else:
                warnings.append(f"Numero documento '{num}' non valido (deve contenere cifre)")
        
        # Data documento
        if llm_data.get("data_documento"):
            date_val = str(llm_data["data_documento"])
            normalized = normalize_date(date_val)
            fields.append(ExtractedFieldResult(
                field_name="data_documento",
                raw_value=date_val,
                normalized_value=normalized or date_val,
                confidence=0.85,
                evidence_text="LLM semantic extraction"
            ))
        
        # Partita IVA - validate
        if llm_data.get("partita_iva"):
            piva = str(llm_data["partita_iva"])
            validated = validate_partita_iva(piva)
            if validated:
                fields.append(ExtractedFieldResult(
                    field_name="partita_iva",
                    raw_value=piva,
                    normalized_value=validated,
                    confidence=0.85,
                    evidence_text="LLM semantic extraction"
                ))
        
        # Emittente (who issued the document)
        if llm_data.get("emittente"):
            emittente = str(llm_data["emittente"]).strip()
            if len(emittente) > 2:
                fields.append(ExtractedFieldResult(
                    field_name="emittente",
                    raw_value=emittente,
                    normalized_value=emittente.title(),
                    confidence=0.85,
                    evidence_text="LLM semantic extraction"
                ))
        
        # Destinatario (who receives the document) - stored in fornitore for compatibility
        if llm_data.get("destinatario"):
            destinatario = str(llm_data["destinatario"]).strip()
            if len(destinatario) > 2:
                fields.append(ExtractedFieldResult(
                    field_name="fornitore",  # Keep using fornitore column for destinatario
                    raw_value=destinatario,
                    normalized_value=destinatario.title(),
                    confidence=0.75,
                    evidence_text="LLM semantic extraction"
                ))
        
        # Totale
        if llm_data.get("totale"):
            totale = str(llm_data["totale"])
            normalized = normalize_amount(totale)
            if normalized:
                fields.append(ExtractedFieldResult(
                    field_name="totale",
                    raw_value=totale,
                    normalized_value=normalized,
                    confidence=0.8,
                    evidence_text="LLM semantic extraction"
                ))
        
        # Type-specific fields
        
        # DDT fields
        if llm_data.get("vettore"):
            fields.append(ExtractedFieldResult(
                field_name="vettore",
                raw_value=str(llm_data["vettore"]),
                normalized_value=str(llm_data["vettore"]).strip(),
                confidence=0.75,
                evidence_text="LLM type-specific extraction"
            ))
        
        if llm_data.get("causale_trasporto"):
            fields.append(ExtractedFieldResult(
                field_name="causale_trasporto",
                raw_value=str(llm_data["causale_trasporto"]),
                normalized_value=str(llm_data["causale_trasporto"]).strip(),
                confidence=0.75,
                evidence_text="LLM type-specific extraction"
            ))
        
        # Fattura fields
        if llm_data.get("imponibile"):
            val = str(llm_data["imponibile"])
            normalized = normalize_amount(val)
            if normalized:
                fields.append(ExtractedFieldResult(
                    field_name="imponibile",
                    raw_value=val,
                    normalized_value=normalized,
                    confidence=0.75,
                    evidence_text="LLM type-specific extraction"
                ))
        
        if llm_data.get("aliquota_iva"):
            fields.append(ExtractedFieldResult(
                field_name="aliquota_iva",
                raw_value=str(llm_data["aliquota_iva"]),
                normalized_value=str(llm_data["aliquota_iva"]),
                confidence=0.75,
                evidence_text="LLM type-specific extraction"
            ))
        
        if llm_data.get("importo_iva"):
            val = str(llm_data["importo_iva"])
            normalized = normalize_amount(val)
            if normalized:
                fields.append(ExtractedFieldResult(
                    field_name="importo_iva",
                    raw_value=val,
                    normalized_value=normalized,
                    confidence=0.75,
                    evidence_text="LLM type-specific extraction"
                ))
        
        if llm_data.get("scadenza_pagamento"):
            fields.append(ExtractedFieldResult(
                field_name="scadenza_pagamento",
                raw_value=str(llm_data["scadenza_pagamento"]),
                normalized_value=str(llm_data["scadenza_pagamento"]).strip(),
                confidence=0.75,
                evidence_text="LLM type-specific extraction"
            ))
        
        if llm_data.get("modalita_pagamento"):
            fields.append(ExtractedFieldResult(
                field_name="modalita_pagamento",
                raw_value=str(llm_data["modalita_pagamento"]),
                normalized_value=str(llm_data["modalita_pagamento"]).strip(),
                confidence=0.75,
                evidence_text="LLM type-specific extraction"
            ))
        
        # Preventivo fields
        if llm_data.get("validita_offerta"):
            fields.append(ExtractedFieldResult(
                field_name="validita_offerta",
                raw_value=str(llm_data["validita_offerta"]),
                normalized_value=str(llm_data["validita_offerta"]).strip(),
                confidence=0.70,
                evidence_text="LLM type-specific extraction"
            ))
        
        # Ordine (PO) fields
        if llm_data.get("data_consegna"):
            fields.append(ExtractedFieldResult(
                field_name="data_consegna",
                raw_value=str(llm_data["data_consegna"]),
                normalized_value=str(llm_data["data_consegna"]).strip(),
                confidence=0.75,
                evidence_text="LLM type-specific extraction"
            ))
        
        # Line items
        if llm_data.get("righe_articolo") and isinstance(llm_data["righe_articolo"], list):
            for i, item in enumerate(llm_data["righe_articolo"], 1):
                if isinstance(item, dict):
                    lines.append({
                        "line_number": i,
                        "item_code": item.get("codice"),
                        "description": item.get("descrizione"),
                        "quantity": item.get("quantita"),
                        "unit": item.get("unita"),
                        "unit_price": item.get("prezzo_unitario"),
                        "confidence": 0.75
                    })
    
    else:
        warnings.append("LLM extraction failed, using fallback rules")
        # Fallback to rules
        fields = extract_by_rules_fallback(text)
    
    # Check for missing required fields
    extracted_names = {f.field_name for f in fields}
    required = {"numero_documento", "data_documento"}
    missing = required - extracted_names
    
    if missing:
        warnings.append(f"Campi non estratti: {', '.join(missing)}")
    
    if not lines:
        warnings.append("Nessuna riga articolo rilevata")
    
    return ExtractionOutput(
        fields=fields,
        lines=lines,
        warnings=warnings
    )
