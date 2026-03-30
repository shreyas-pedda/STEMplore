"""Extract content from PDF files into unified chunks (one per page or logical block)."""
from pathlib import Path
from typing import List, Dict

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False


class PDFExtractor:
    """Extract text from PDFs, one chunk per page."""

    SUPPORTED_SUFFIXES = {".pdf"}

    def extract_from_file(self, file_path: Path) -> List[Dict]:
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        if file_path.suffix.lower() != ".pdf":
            raise ValueError("Only .pdf files are supported")
        if not HAS_PYMUPDF:
            raise ImportError("PDF support requires PyMuPDF. Install with: pip install pymupdf")

        doc = fitz.open(file_path)
        chunks = []
        for i, page in enumerate(doc):
            text = page.get_text().strip()
            if not text:
                continue
            chunks.append({
                "slide_number": len(chunks) + 1,
                "title": f"Page {i + 1}",
                "text_content": [text],
                "full_text": text,
            })
        doc.close()
        return chunks
