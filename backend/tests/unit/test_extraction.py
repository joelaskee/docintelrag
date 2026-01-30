"""Tests for PDF extraction service."""
import pytest
from pathlib import Path


class TestExtraction:
    """Test PDF text extraction."""
    
    def test_extraction_result_dataclass(self):
        """Test ExtractionResult dataclass."""
        from app.services.extraction import ExtractionResult, PageContent
        
        result = ExtractionResult(
            raw_text="Test content",
            pages=[PageContent(page_number=1, text="Test", has_text_layer=True, image_count=0)],
            is_scanned=False,
            total_pages=1,
            warnings=[]
        )
        
        assert result.raw_text == "Test content"
        assert len(result.pages) == 1
        assert result.is_scanned is False
    
    def test_page_content_dataclass(self):
        """Test PageContent dataclass."""
        from app.services.extraction import PageContent
        
        page = PageContent(
            page_number=1,
            text="Sample text",
            has_text_layer=True,
            image_count=2
        )
        
        assert page.page_number == 1
        assert page.text == "Sample text"
        assert page.has_text_layer is True
        assert page.image_count == 2
