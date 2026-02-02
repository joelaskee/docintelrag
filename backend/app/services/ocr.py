"""OCR service using hybrid Tesseract + DeepSeek-OCR (VLM)."""
import logging
from pathlib import Path
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
import base64
from io import BytesIO
import httpx
import re

import pytesseract
from PIL import Image, ImageEnhance, ImageOps

from app.config import get_settings
from app.services.extraction import get_page_as_image

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class OCRPageResult:
    """OCR result for a single page."""
    page_number: int
    text: str
    confidence: float  # 0-1
    words_with_bbox: list[dict]  # [{"text": "...", "bbox": {...}, "conf": 0.9}]


@dataclass  
class OCRResult:
    """Full OCR result for a document."""
    pages: list[OCRPageResult]
    avg_confidence: float
    warnings: list[str]
    success: bool


def preprocess_image(image: Image.Image) -> Image.Image:
    """
    Preprocess image for better OCR quality.
    """
    # 1. Convert to grayscale
    if image.mode != 'L':
        image = image.convert('L')
    
    # 2. Upscale if resolution is low (width < 2000px)
    w, h = image.size
    if w < 2000:
        factor = 2000 / w
        new_size = (int(w * factor), int(h * factor))
        image = image.resize(new_size, resample=Image.LANCZOS)
    
    # 3. Enhance Sharpness
    enhancer = ImageEnhance.Sharpness(image)
    image = enhancer.enhance(2.0)
    
    # 4. Enhance Contrast
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(1.5)
    
    # 5. Thresholding
    threshold = 128
    image = image.point(lambda p: 255 if p > threshold else 0)
    
    return image


def ocr_with_deepseek(image: Image.Image) -> str | None:
    """
    Run OCR using DeepSeek-OCR via Ollama HTTP API.
    Uses base64 encoded image sent to the /api/generate endpoint.
    """
    try:
        # Resize image if too large to prevent timeouts
        # Limit max dimension to 2000px (sufficient for text)
        w, h = image.size
        max_dim = 2000
        if w > max_dim or h > max_dim:
            ratio = min(max_dim / w, max_dim / h)
            new_size = (int(w * ratio), int(h * ratio))
            image = image.resize(new_size, resample=Image.LANCZOS)
            logger.info(f"Resized image for DeepSeek to {new_size}")

        # Convert image to base64
        buffered = BytesIO()
        image.save(buffered, format="JPEG", quality=85)
        img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        logger.info(f"Calling DeepSeek-OCR via HTTP API...")
        
        # Call Ollama API with image
        with httpx.Client(timeout=300) as client:
            response = client.post(
                f"{settings.ollama_base_url}/api/generate",
                json={
                    "model": "deepseek-ocr:latest",
                    "prompt": "Extract all the text in this image. Return only the extracted text, nothing else.",
                    "images": [img_base64],
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                text = result.get("response", "").strip()
                logger.info(f"DeepSeek-OCR API successful, extracted {len(text)} chars")
                return text
            else:
                logger.error(f"DeepSeek-OCR API failed: {response.status_code} - {response.text}")
                return None
                
    except Exception as e:
        logger.error(f"DeepSeek-OCR error: {e}")
        return None


def ocr_page(file_path: Path, page_number: int, dpi: int = 400) -> OCRPageResult:
    """Run OCR on a single page."""
    import fitz  # PyMuPDF
    
    try:
        # 1. Check for Native Text (smart mode)
        # Verify if page has extractable text directly
        doc = fitz.open(file_path)
        page = doc.load_page(page_number - 1) # 0-indexed
        text = page.get_text()
        doc.close()
        
        # Heuristic: If > 50 chars of text found, assume native PDF
        if len(text.strip()) > 50:
            logger.info(f"Page {page_number} detected as NATIVE PDF. Extracting text directly.")
            return OCRPageResult(
                page_number=page_number,
                text=text,
                confidence=1.0,
                words_with_bbox=[] # Can implement get_text("words") if needed later
            )
            
        # 2. If not native, proceed with OCR (Scanned)
        logger.info(f"Page {page_number} detected as SCANNED. Running OCR analysis.")
        
        # Render page to image - use LOWER DPI for DeepSeek to avoid bloated images
        # 150 DPI is sufficient for OCR and much faster to process
        deepseek_dpi = 150
        image_for_deepseek = get_page_as_image(file_path, page_number, deepseek_dpi)
        
        # For Tesseract, we still need higher DPI for preprocessing
        image = get_page_as_image(file_path, page_number, dpi)
        
        # Preprocess for Tesseract
        processed = preprocess_image(image)
        
        # Run Tesseract first (fast)
        custom_config = r'--oem 1 --psm 3'
        data = pytesseract.image_to_data(
            processed,
            lang='ita+eng',
            output_type=pytesseract.Output.DICT,
            config=custom_config
        )
        
        # Calculate confidence
        valid_confs = [int(c) for c in data['conf'] if int(c) >= 0]
        avg_conf = sum(valid_confs) / len(valid_confs) if valid_confs else 0.0
        
        # Extract meaningful words (len > 2, alpha)
        meaningful_words = [w for w in data['text'] if len(w.strip()) > 3 and w.strip().isalnum()]
        
        # Heuristic: If confidence < 75 OR very few meaningful words (< 10), use DeepSeek
        use_deepseek = avg_conf < 75.0 or len(meaningful_words) < 10
        
        # If document looks "scanned" effectively (low quality), force DeepSeek
        if use_deepseek:
            logger.warning(f"Page {page_number} quality poor (Conf: {avg_conf:.1f}%, Words: {len(meaningful_words)}). Trying DeepSeek-OCR.")
            
            # Pass the LOWER DPI image to DeepSeek (already resized in ocr_with_deepseek if needed)
            deepseek_text = ocr_with_deepseek(image_for_deepseek)
            
            if deepseek_text and len(deepseek_text) > 50:
                # Use DeepSeek result
                return OCRPageResult(
                    page_number=page_number,
                    text=deepseek_text,
                    confidence=0.9, # Trust DeepSeek
                    words_with_bbox=[] # No bboxes from DeepSeek
                )
            else:
                # Try rotating image 180° (document might be upside-down)
                logger.warning("DeepSeek returned empty, trying 180° rotation...")
                rotated_image = image_for_deepseek.rotate(180)
                deepseek_text_rotated = ocr_with_deepseek(rotated_image)
                
                if deepseek_text_rotated and len(deepseek_text_rotated) > 50:
                    logger.info(f"Page {page_number} successfully OCR'd after 180° rotation")
                    return OCRPageResult(
                        page_number=page_number,
                        text=deepseek_text_rotated,
                        confidence=0.85,
                        words_with_bbox=[]
                    )
                else:
                    logger.warning("DeepSeek returned empty even after rotation, falling back to Tesseract.")
        
        # Determine final text from Tesseract
        words = []
        texts = []
        n_boxes = len(data['text'])
        for i in range(n_boxes):
            text = data['text'][i].strip()
            conf = int(data['conf'][i])
            if text and conf > 0:
                words.append({
                    "text": text,
                    "bbox": {
                        "x": data['left'][i], "y": data['top'][i],
                        "w": data['width'][i], "h": data['height'][i]
                    },
                    "conf": conf / 100.0
                })
                texts.append(text)
        
        return OCRPageResult(
            page_number=page_number,
            text=" ".join(texts),
            confidence=avg_conf,
            words_with_bbox=words
        )
        
    except Exception as e:
        logger.error(f"OCR error on page {page_number}: {e}")
        return OCRPageResult(page_number, "", 0.0, [])


def run_ocr(file_path: str | Path, pages_to_ocr: list[int] | None = None) -> OCRResult:
    """Run OCR on a PDF document."""
    file_path = Path(file_path)
    warnings = []
    
    import fitz
    try:
        doc = fitz.open(file_path)
        total_pages = len(doc)
        doc.close()
    except Exception as e:
        logger.error(f"Could not open PDF for OCR: {e}")
        return OCRResult([], 0.0, [f"Could not open PDF: {e}"], False)
    
    if pages_to_ocr is None:
        pages_to_ocr = list(range(1, total_pages + 1))
    
    results: list[OCRPageResult] = []
    
    # Use ThreadPool but limit to 1 worker to avoid VRAM OOM with DeepSeek
    max_workers = 1 
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for page_num in pages_to_ocr:
            future = executor.submit(
                ocr_page, 
                file_path, 
                page_num, 
                settings.ocr_dpi 
            )
            
            try:
                result = future.result(timeout=700) # Increased timeout for DeepSeek
                results.append(result)
                
                if result.confidence < 0.5:
                    warnings.append(f"Low quality on page {page_num}")
                    
            except FuturesTimeoutError:
                warnings.append(f"OCR timeout on page {page_num}")
                results.append(OCRPageResult(page_num, "", 0.0, []))
            except Exception as e:
                warnings.append(f"OCR error on page {page_num}: {str(e)}")
                results.append(OCRPageResult(page_num, "", 0.0, []))
    
    valid_pages = [p for p in results if p.confidence > 0]
    avg_conf = sum(p.confidence for p in valid_pages) / len(valid_pages) if valid_pages else 0.0
    
    return OCRResult(results, avg_conf, warnings, len(valid_pages) > 0)


def run_ocr_with_rotations(file_path: str | Path, rotations: dict[int, int]) -> OCRResult:
    """
    Run OCR on a PDF document with user-specified rotations applied.
    
    Args:
        file_path: Path to PDF file
        rotations: Dict mapping page_number -> rotation_angle (0, 90, 180, 270)
    """
    file_path = Path(file_path)
    warnings = []
    
    import fitz
    try:
        doc = fitz.open(file_path)
        total_pages = len(doc)
        doc.close()
    except Exception as e:
        logger.error(f"Could not open PDF for OCR with rotations: {e}")
        return OCRResult([], 0.0, [f"Could not open PDF: {e}"], False)
    
    results: list[OCRPageResult] = []
    
    for page_num in range(1, total_pages + 1):
        try:
            rotation = rotations.get(page_num, 0)
            
            # Get page image with rotation applied
            image = get_page_as_image(file_path, page_num, settings.ocr_dpi)
            if rotation:
                image = image.rotate(-rotation, expand=True)  # Negative for clockwise
                logger.info(f"Applied {rotation}° rotation to page {page_num}")
            
            # Run OCR directly on the rotated image using DeepSeek
            deepseek_text = ocr_with_deepseek(image)
            
            if deepseek_text and len(deepseek_text) > 50:
                results.append(OCRPageResult(
                    page_number=page_num,
                    text=deepseek_text,
                    confidence=0.9,
                    words_with_bbox=[]
                ))
            else:
                # Fallback to Tesseract on rotated image
                logger.warning(f"DeepSeek returned empty for page {page_num}, using Tesseract")
                processed = preprocess_image(image)
                custom_config = r'--oem 1 --psm 3'
                data = pytesseract.image_to_data(
                    processed,
                    lang='ita+eng',
                    output_type=pytesseract.Output.DICT,
                    config=custom_config
                )
                
                texts = [t.strip() for t in data['text'] if t.strip()]
                valid_confs = [int(c) for c in data['conf'] if int(c) >= 0]
                avg_conf = sum(valid_confs) / len(valid_confs) if valid_confs else 0.0
                
                results.append(OCRPageResult(
                    page_number=page_num,
                    text=" ".join(texts),
                    confidence=avg_conf / 100.0,
                    words_with_bbox=[]
                ))
                
                if avg_conf < 50:
                    warnings.append(f"Low quality on page {page_num} even after rotation")
                    
        except Exception as e:
            logger.error(f"OCR error on page {page_num}: {e}")
            warnings.append(f"OCR error on page {page_num}: {str(e)}")
            results.append(OCRPageResult(page_num, "", 0.0, []))
    
    valid_pages = [p for p in results if p.confidence > 0]
    avg_conf = sum(p.confidence for p in valid_pages) / len(valid_pages) if valid_pages else 0.0
    
    return OCRResult(results, avg_conf, warnings, len(valid_pages) > 0)
