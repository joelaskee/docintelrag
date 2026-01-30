"""PDF text extraction service."""
import logging
from pathlib import Path
from dataclasses import dataclass

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


@dataclass
class PageContent:
    """Extracted content from a single page."""
    page_number: int
    text: str
    has_text_layer: bool
    image_count: int


@dataclass
class ExtractionResult:
    """Result of PDF text extraction."""
    raw_text: str
    pages: list[PageContent]
    is_scanned: bool
    total_pages: int
    warnings: list[str]


def extract_text_from_pdf(file_path: str | Path) -> ExtractionResult:
    """
    Extract text from a PDF file.
    
    Determines if PDF is native (has text layer) or scanned (needs OCR).
    For native PDFs, extracts text directly.
    For scanned PDFs, marks for OCR processing.
    """
    file_path = Path(file_path)
    pages: list[PageContent] = []
    warnings: list[str] = []
    all_text: list[str] = []
    
    pages_with_text = 0
    pages_with_images = 0
    
    try:
        doc = fitz.open(file_path)
        total_pages = len(doc)
        
        for page_num in range(total_pages):
            page = doc[page_num]
            
            # Extract text
            text = page.get_text("text").strip()
            
            # Count images
            image_list = page.get_images(full=True)
            image_count = len(image_list)
            
            has_text = len(text) > 20  # Minimal threshold
            
            if has_text:
                pages_with_text += 1
            if image_count > 0:
                pages_with_images += 1
            
            pages.append(PageContent(
                page_number=page_num + 1,
                text=text,
                has_text_layer=has_text,
                image_count=image_count
            ))
            all_text.append(text)
        
        doc.close()
        
        # Determine if scanned
        # If less than 50% of pages have text and most have images, likely scanned
        text_ratio = pages_with_text / total_pages if total_pages > 0 else 0
        is_scanned = text_ratio < 0.5 and pages_with_images >= total_pages * 0.7
        
        if is_scanned:
            warnings.append("Document appears to be scanned (minimal text layer)")
        
        return ExtractionResult(
            raw_text="\n\n".join(all_text),
            pages=pages,
            is_scanned=is_scanned,
            total_pages=total_pages,
            warnings=warnings
        )
        
    except Exception as e:
        logger.error(f"Error extracting text from {file_path}: {e}")
        return ExtractionResult(
            raw_text="",
            pages=[],
            is_scanned=True,  # Assume needs OCR if extraction fails
            total_pages=0,
            warnings=[f"Extraction error: {str(e)}"]
        )


def get_page_as_image(file_path: str | Path, page_number: int, dpi: int = 300):
    """Render a PDF page as an image for OCR."""
    from PIL import Image
    import io
    
    doc = fitz.open(file_path)
    page = doc[page_number - 1]  # 0-indexed
    
    # Render at specified DPI
    zoom = dpi / 72  # 72 is the default DPI
    matrix = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=matrix)
    
    # Convert to PIL Image
    img_data = pix.tobytes("png")
    image = Image.open(io.BytesIO(img_data))
    
    doc.close()
    return image
