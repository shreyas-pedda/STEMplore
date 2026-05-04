"""Download a Google Slides deck as PPTX and extract with SlidesExtractor."""
from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import Dict, List, Optional
import requests

from src.extractors.slides_extractor import SlidesExtractor

# Presentation ID in URLs like https://docs.google.com/presentation/d/<ID>/edit
_ID_RE = re.compile(
    r"docs\.google\.com/presentation/d/([a-zA-Z0-9_-]+)",
    re.IGNORECASE,
)


class GoogleSlidesExtractor:
    """
    Fetch a publicly accessible Google Slides presentation as .pptx and parse it.
    The deck must be shared so anyone with the link can view (or use an export-enabled link).
    """

    EXPORT_PATH = "export/pptx"

    def __init__(self):
        self._slides = SlidesExtractor()

    @staticmethod
    def presentation_id_from_url(url: str) -> Optional[str]:
        if not url or not isinstance(url, str):
            return None
        m = _ID_RE.search(url.strip())
        return m.group(1) if m else None

    def extract_from_url(self, url: str, timeout: int = 120) -> List[Dict]:
        pid = self.presentation_id_from_url(url)
        if not pid:
            raise ValueError(
                "Not a Google Slides URL. Expected docs.google.com/presentation/d/<id>/..."
            )

        export_url = f"https://docs.google.com/presentation/d/{pid}/{self.EXPORT_PATH}"
        headers = {
            "User-Agent": "STEMplore/1.0 (+https://github.com/)",
        }
        resp = requests.get(export_url, headers=headers, timeout=timeout, allow_redirects=True)
        if resp.status_code != 200:
            raise ValueError(
                f"Could not download presentation (HTTP {resp.status_code}). "
                "Share the deck as 'Anyone with the link can view' or export PPTX manually."
            )

        content_type = (resp.headers.get("content-type") or "").lower()
        body = resp.content
        if not body or len(body) < 1000:
            raise ValueError("Downloaded file too small; check sharing permissions on the deck.")

        # Google may return HTML login/warning page instead of binary pptx
        if "html" in content_type or body[:4] == b"<htm" or body[:5] == b"<!DOC":
            raise ValueError(
                "Got an HTML page instead of a PPTX file. "
                "Set sharing to 'Anyone with the link can view' and try again."
            )

        suffix = ".pptx"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(body)
            tmp_path = Path(tmp.name)

        try:
            return self._slides.extract_from_file(tmp_path)
        finally:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass


def is_google_slides_url(value: str) -> bool:
    """True if this string looks like a Google Slides presentation URL."""
    s = (value or "").strip()
    return s.startswith("http") and "docs.google.com/presentation" in s


def extract_chunks_from_slides_url(url: str, timeout: int = 120) -> List[Dict]:
    """
    App/API entry point for Slides-by-URL (kept here so UnifiedExtractor stays file-only).
    Same chunk shape as other extractors: slide_number, title, text_content, full_text.
    """
    return GoogleSlidesExtractor().extract_from_url(url, timeout=timeout)
