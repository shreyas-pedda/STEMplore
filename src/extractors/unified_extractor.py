"""
Unified content extractor: routes to the appropriate extractor by file type.
All extractors return a list of chunks with: slide_number, title, text_content, full_text.

Google Slides URLs are not handled here; use google_slides_extractor.extract_chunks_from_slides_url
in the app/API layer (this module is file-path only).
"""
from pathlib import Path
from typing import List, Dict, Optional

from src.extractors.slides_extractor import SlidesExtractor
from src.extractors.text_extractor import TextExtractor

# Optional extractors (may fail to import if deps missing)
_pdf_extractor: Optional[type] = None
_image_extractor: Optional[type] = None
_video_extractor: Optional[type] = None

try:
    from src.extractors.pdf_extractor import PDFExtractor
    _pdf_extractor = PDFExtractor
except Exception:
    pass

try:
    from src.extractors.image_extractor import ImageExtractor
    _image_extractor = ImageExtractor
except Exception:
    pass

try:
    from src.extractors.video_extractor import VideoExtractor

    _video_extractor = VideoExtractor
except Exception:
    pass


# All supported extensions and their extractor names
SUPPORTED_EXTENSIONS = {
    ".pptx": "slides",
    ".txt": "text",
    ".md": "text",
    ".markdown": "text",
    ".pdf": "pdf",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".gif": "image",
    ".bmp": "image",
    ".webp": "image",
    ".tiff": "image",
    ".tif": "image",
    ".mp4": "video",
    ".webm": "video",
    ".avi": "video",
    ".mov": "video",
    ".mkv": "video",
    ".m4a": "video",
    ".wav": "video",
    ".mp3": "video",
    ".flac": "video",
}


class UnifiedExtractor:
    """
    Single entry point to extract content from any supported file.
    Returns list of dicts with keys: slide_number, title, text_content, full_text.
    """

    def __init__(self):
        self._slides = SlidesExtractor()
        self._text = TextExtractor()
        self._pdf = _pdf_extractor() if _pdf_extractor else None
        self._image = _image_extractor() if _image_extractor else None
        self._video = _video_extractor(model_size="base") if _video_extractor else None

    def supported_extensions(self) -> List[str]:
        """Return list of supported extensions with dot (e.g. ['.pptx', '.pdf', '.txt', ...])."""
        out = [".pptx", ".txt", ".md", ".markdown"]
        if self._pdf:
            out.append(".pdf")
        if self._image:
            out.extend([".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff", ".tif"])
        if self._video:
            out.extend(
                [
                    ".mp4",
                    ".webm",
                    ".avi",
                    ".mov",
                    ".mkv",
                    ".m4a",
                    ".wav",
                    ".mp3",
                    ".flac",
                ]
            )
        return sorted(set(out))

    def extract_from_file(self, file_path: Path) -> List[Dict]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        suffix = path.suffix.lower()
        kind = SUPPORTED_EXTENSIONS.get(suffix)
        if not kind:
            raise ValueError(
                f"Unsupported file type: {suffix}. "
                f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS.keys()))}"
            )

        if kind == "slides":
            return self._slides.extract_from_file(path)
        if kind == "text":
            return self._text.extract_from_file(path)
        if kind == "pdf":
            if not self._pdf:
                raise ImportError("PDF support not available. Install with: pip install pymupdf")
            return self._pdf.extract_from_file(path)
        if kind == "image":
            if not self._image:
                raise ImportError("Image OCR not available. Install pytesseract and Pillow, and install Tesseract.")
            return self._image.extract_from_file(path)
        if kind == "video":
            if not self._video:
                raise ImportError(
                    "Video/audio transcription not available. "
                    "Install openai-whisper and ffmpeg, and ensure ffmpeg is on PATH."
                )
            return self._video.extract_from_file(path)
        raise ValueError(f"Unknown extractor kind: {kind}")
