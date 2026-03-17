"""Extract content from plain text and markdown files into unified chunks."""
from pathlib import Path
from typing import List, Dict

# Chunk size in characters; each chunk becomes one "slide" for embedding
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100


class TextExtractor:
    """Extract and chunk content from .txt and .md files."""

    SUPPORTED_SUFFIXES = {".txt", ".md", ".markdown"}

    def extract_from_file(self, file_path: Path) -> List[Dict]:
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        suffix = file_path.suffix.lower()
        if suffix not in self.SUPPORTED_SUFFIXES:
            raise ValueError(f"Unsupported format: {suffix}")

        raw = file_path.read_text(encoding="utf-8", errors="replace").strip()
        if not raw:
            return []

        chunks = self._split_into_chunks(raw)
        return [
            {
                "slide_number": i + 1,
                "title": f"Section {i + 1}",
                "text_content": [chunk],
                "full_text": chunk,
            }
            for i, chunk in enumerate(chunks)
        ]

    def _split_into_chunks(self, text: str) -> List[str]:
        """Split text into overlapping chunks by paragraphs first, then by size."""
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [text]

        result = []
        current = []
        current_len = 0

        for para in paragraphs:
            if current_len + len(para) + 2 <= CHUNK_SIZE and current:
                current.append(para)
                current_len += len(para) + 2
            else:
                if current:
                    result.append("\n\n".join(current))
                # Start new chunk; if single para is huge, split by size
                if len(para) > CHUNK_SIZE:
                    for i in range(0, len(para), CHUNK_SIZE - CHUNK_OVERLAP):
                        result.append(para[i : i + CHUNK_SIZE])
                    current = []
                    current_len = 0
                else:
                    current = [para]
                    current_len = len(para)

        if current:
            result.append("\n\n".join(current))
        return result if result else [text[:CHUNK_SIZE]]
