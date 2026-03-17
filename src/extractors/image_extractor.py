"""Extract text from images using OCR (Tesseract)."""
from pathlib import Path
from typing import List, Dict

try:
    import pytesseract
    from PIL import Image
    HAS_OCR = True
except ImportError:
    HAS_OCR = False

# Common image extensions
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff", ".tif"}


class ImageExtractor:
    """Extract text from images via OCR. Requires Tesseract installed on the system."""

    SUPPORTED_SUFFIXES = IMAGE_SUFFIXES

    def extract_from_file(self, file_path: Path) -> List[Dict]:
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        suffix = file_path.suffix.lower()
        if suffix not in self.SUPPORTED_SUFFIXES:
            raise ValueError(f"Unsupported image format: {suffix}")
        if not HAS_OCR:
            raise ImportError("Image OCR requires pytesseract and Pillow. Install with: pip install pytesseract Pillow. Also install Tesseract: https://github.com/tesseract-ocr/tesseract")

        img = Image.open(file_path)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        text = pytesseract.image_to_string(img).strip()
        if not text:
            text = "[No text detected in image]"
        return [{
            "slide_number": 1,
            "title": "Image content",
            "text_content": [text],
            "full_text": text,
        }]
