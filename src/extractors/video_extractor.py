"""Transcribe video and audio files with Whisper; output matches other extractors."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Dict, List, Optional

try:
    import whisper

    HAS_WHISPER = True
except ImportError:
    HAS_WHISPER = False

# Same media routing as unified_extractor "video" kind
MEDIA_SUFFIXES = {
    ".mp4",
    ".webm",
    ".avi",
    ".mov",
    ".mkv",
    ".m4a",
    ".wav",
    ".mp3",
    ".flac",
}


def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


class VideoExtractor:
    """
    Extract text from video/audio via Whisper transcription.
    Requires ffmpeg on PATH and the openai-whisper package.
    """

    SUPPORTED_SUFFIXES = MEDIA_SUFFIXES

    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self._model = None

    def _load_model(self):
        if not HAS_WHISPER:
            raise ImportError(
                "Video/audio transcription requires openai-whisper. "
                "Install with: pip install openai-whisper"
            )
        if not _ffmpeg_available():
            raise ImportError(
                "ffmpeg is required for Whisper to decode media. "
                "Install ffmpeg and ensure it is on your PATH."
            )
        if self._model is None:
            self._model = whisper.load_model(self.model_size)
        return self._model

    def extract_from_file(self, file_path: Path) -> List[Dict]:
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        suffix = file_path.suffix.lower()
        if suffix not in self.SUPPORTED_SUFFIXES:
            raise ValueError(f"Unsupported media format: {suffix}")

        model = self._load_model()
        result = model.transcribe(str(file_path), fp16=False, verbose=False)
        segments = result.get("segments") or []
        if not segments and result.get("text"):
            text = (result.get("text") or "").strip()
            if not text:
                return []
            return [
                {
                    "slide_number": 1,
                    "title": "Transcript",
                    "text_content": [text],
                    "full_text": text,
                }
            ]

        chunks = self._merge_segments(segments)
        out: List[Dict] = []
        for i, (title, body) in enumerate(chunks, start=1):
            body = body.strip()
            if not body:
                continue
            out.append(
                {
                    "slide_number": i,
                    "title": title,
                    "text_content": [body],
                    "full_text": body,
                }
            )
        return out

    def _merge_segments(
        self,
        segments: List[dict],
        max_chars: int = 1200,
        gap_merge_seconds: float = 1.5,
    ) -> List[tuple]:
        """Merge short Whisper segments into fewer, embedding-sized chunks."""
        merged: List[tuple] = []
        buf_text: List[str] = []
        buf_start: Optional[float] = None
        last_end: Optional[float] = None

        def flush():
            nonlocal buf_text, buf_start, last_end
            if not buf_text:
                return
            text = " ".join(buf_text).strip()
            if text:
                t0 = buf_start or 0.0
                t1 = last_end or t0
                title = f"Transcript {_format_hms(t0)}–{_format_hms(t1)}"
                merged.append((title, text))
            buf_text = []
            buf_start = None
            last_end = None

        for seg in segments:
            t = (seg.get("text") or "").strip()
            if not t:
                continue
            start = float(seg.get("start", 0.0))
            end = float(seg.get("end", start))

            if buf_start is None:
                buf_start = start
            elif last_end is not None and (start - last_end) > gap_merge_seconds:
                flush()
                buf_start = start

            buf_text.append(t)
            last_end = end
            if sum(len(x) + 1 for x in buf_text) >= max_chars:
                flush()

        flush()
        return merged


def _format_hms(seconds: float) -> str:
    seconds = max(0.0, seconds)
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h:d}:{m:02d}:{s:02d}"
    return f"{m:d}:{s:02d}"
