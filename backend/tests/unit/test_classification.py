"""Tests for document classification."""
import pytest


class TestClassification:
    """Test document classification service."""
    
    def test_classify_by_rules_ordine(self):
        """Test rule-based classification for PO."""
        from app.services.classification import classify_by_rules
        from app.models.document import DocumentType
        
        text = "ORDINE DI ACQUISTO N. 12345 del 01/01/2024"
        result = classify_by_rules(text)
        
        assert result is not None
        assert result.doc_type == DocumentType.PO
        assert result.confidence > 0  # Just verify confidence is positive
        assert result.method == "rules"
    
    def test_classify_by_rules_ddt(self):
        """Test rule-based classification for DDT."""
        from app.services.classification import classify_by_rules
        from app.models.document import DocumentType
        
        text = "DOCUMENTO DI TRASPORTO DDT N. 789/2024"
        result = classify_by_rules(text)
        
        assert result is not None
        assert result.doc_type == DocumentType.DDT
        assert result.confidence > 0  # Just verify confidence is positive
    
    def test_classify_by_rules_fattura(self):
        """Test rule-based classification for invoice."""
        from app.services.classification import classify_by_rules
        from app.models.document import DocumentType
        
        text = "FATTURA ELETTRONICA N. 2024/00123 del 15/03/2024"
        result = classify_by_rules(text)
        
        assert result is not None
        assert result.doc_type == DocumentType.FATTURA
        assert result.confidence > 0  # Just verify confidence is positive
    
    def test_classify_by_rules_no_match(self):
        """Test classification when no patterns match."""
        from app.services.classification import classify_by_rules
        
        text = "This is just some random text with no document keywords"
        result = classify_by_rules(text)
        
        assert result is None
    
    def test_classification_result_dataclass(self):
        """Test ClassificationResult dataclass."""
        from app.services.classification import ClassificationResult
        from app.models.document import DocumentType
        
        result = ClassificationResult(
            doc_type=DocumentType.PO,
            confidence=0.85,
            method="rules",
            evidence=["keyword: ordine"]
        )
        
        assert result.doc_type == DocumentType.PO
        assert result.confidence == 0.85
        assert result.method == "rules"
        assert len(result.evidence) == 1
