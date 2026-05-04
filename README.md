# STEMplore — AI curriculum question generator

Prototype pipeline that ingests lesson content from **multiple file types** (and optionally a **public Google Slides URL**), embeds it in **ChromaDB**, and uses **Groq** to generate **STEMplore-shaped** quiz JSON.

## Problem

- Structuring curriculum and writing questions by hand is slow.
- Teams want one flow that accepts slides, PDFs, notes, images, and more—not only `.pptx`.

## What this repo does

1. **Extract** text (and transcript-style chunks when video/audio support is enabled) into a common chunk format.
2. **Embed** chunks with `sentence-transformers/all-MiniLM-L6-v2`.
3. **Store** vectors in **ChromaDB** keyed by a normalized lesson id.
4. **Generate** MCQ / True–False style questions with an LLM and return JSON the STEMplore app can consume.

## Architecture (high level)

```
Upload file OR Google Slides URL
        ↓
[Extractors] → unified chunks (slide_number, title, text_content, full_text)
        ↓
[EmbeddingGenerator] → vectors
        ↓
[ChromaDBStore] → persist per lesson_id
        ↓
[QuestionGenerator + Groq] → raw JSON
        ↓
[format_questions_to_stemplore] → STEMplore SELECT / challenge_options JSON
```

## Repository layout

```
STEMplore/
├── README.md
├── LICENSE
├── requirements.txt          # Core Python deps (torch, chromadb, streamlit, …)
├── run.py                    # Starts FastAPI dev server (uvicorn)
├── app/
│   ├── api.py                # FastAPI: POST /api/generate-questions
│   └── app.py                # Streamlit UI prototype
├── src/
│   ├── extractors/
│   │   ├── unified_extractor.py      # Routes local files by extension
│   │   ├── slides_extractor.py       # .pptx (python-pptx)
│   │   ├── google_slides_extractor.py # Public Slides URL → export PPTX → parse
│   │   ├── text_extractor.py         # .txt, .md
│   │   ├── pdf_extractor.py          # .pdf (PyMuPDF)
│   │   └── image_extractor.py        # Raster images (Tesseract OCR)
│   ├── embeddings/
│   │   └── embedding_generator.py
│   ├── generator/
│   │   └── question_generator.py     # Groq client + prompts
│   ├── vectorstore/
│   │   └── chroma_db.py
│   ├── formatters/
│   │   ├── json_formatter.py
│   │   └── stemplore_schema.json
│   └── pipeline/
│       └── rag_pipeline.py           # Example wiring / experiments
├── tests/
│   └── test_smoke.py
└── data/
    ├── inputs/               # Sample decks / docs for local testing
    └── outputs/              # Example generated JSON
```

There is no `settings.py` at the repo root; configuration is via **environment variables** (see below).

## Prerequisites

- **Python 3.10+** (recommended; Torch and Chroma are tested on recent 3.x releases).
- **Groq API key** for question generation (`GROQ_API_KEY`).
- Optional, depending on what you upload:
  - **Tesseract OCR** on the system PATH for image extraction (`pytesseract` + [Tesseract install](https://github.com/tesseract-ocr/tesseract)).
  - **ffmpeg** on PATH if you enable **Whisper**-based video/audio extraction (see `UnifiedExtractor` / optional `VideoExtractor` work in progress).

## Installation

```bash
git clone https://github.com/shreyas-pedda/STEMplore.git
cd STEMplore

python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### Environment variables

Create a `.env` file in the project root (do not commit secrets):

```env
GROQ_API_KEY=your_groq_key_here
```

The Groq Python client reads this automatically when the key is set in the environment.

## How to run

All commands assume the **repository root** as the current working directory and an **activated venv**.

### Streamlit UI (`app/app.py`)

```bash
streamlit run app/app.py
```

Open the URL Streamlit prints (usually `http://localhost:8501`). Enter a **lesson title**, then either **upload a file** or paste a **Google Slides link** (see compatibility below), then generate questions.

### FastAPI (`app/api.py`)

```bash
python run.py
```

- Serves **`http://0.0.0.0:8000`** with reload.
- **Endpoint:** `POST /api/generate-questions`  
  - `multipart/form-data`: **`lessonId`** (string), and either **`file`** (upload) or **`slidesUrl`** (Google Slides URL).

Example with `curl` (file upload):

```bash
curl -X POST "http://localhost:8000/api/generate-questions" \
  -F "lessonId=My Lesson" \
  -F "file=@./data/inputs/your-deck.pptx"
```

Example with a Slides URL:

```bash
curl -X POST "http://localhost:8000/api/generate-questions" \
  -F "lessonId=My Lesson" \
  -F "slidesUrl=https://docs.google.com/presentation/d/YOUR_ID/edit"
```

CORS is configured for local frontends on ports **3000** and **3001**; adjust `app/api.py` if your dev URL differs.

## Supported content sources

Behavior is implemented in **`UnifiedExtractor`** (local paths) and **`google_slides_extractor`** (URLs). The Streamlit file picker and the API only allow extensions returned by **`UnifiedExtractor.supported_extensions()`**, which depends on **optional dependencies** loading successfully.

| Source | Extensions / input | Notes |
|--------|--------------------|--------|
| **PowerPoint** | `.pptx` | Local files; slide text and titles. |
| **Google Slides** | `https://docs.google.com/presentation/d/...` | Uses Google’s **export/pptx** link. The deck must be reachable without your own OAuth app (typically **“Anyone with the link can view”**). Used via **`slidesUrl`** (API) or the Slides URL field (Streamlit). Implemented in **`extract_chunks_from_slides_url`** (lazy-imported in the app layer). |
| **Plain / Markdown text** | `.txt`, `.md`, `.markdown` | Chunked for embedding. |
| **PDF** | `.pdf` | One chunk per page (text). Requires **PyMuPDF** (`pymupdf`). |
| **Images** | `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.webp`, `.tiff`, `.tif` | OCR via **Tesseract**; requires system Tesseract + `pytesseract` / Pillow. |
| **Video / audio** | `.mp4`, `.webm`, `.avi`, `.mov`, `.mkv`, `.m4a`, `.wav`, `.mp3`, `.flac` | **Whisper** transcription via **`VideoExtractor`** when **`openai-whisper`** imports and **ffmpeg** is on `PATH`. If Whisper fails to import, these extensions are omitted from **`supported_extensions()`**. |

Empty or unreadable chunks are skipped during embedding (see `EmbeddingGenerator.generate_embeddings_batch`).

## Output format

STEMplore expects structured challenge JSON (e.g. `SELECT` with `challenge_options`). See the product spec:

https://docs.google.com/document/d/1EfO9AhHfHMhV8wzIw0jkoGfjMJQvAtZyLnK0PdfFQQM/edit?usp=sharing

Minimal example of a multiple-choice item:

```json
[
  {
    "type": "SELECT",
    "question": "What is considered the fundamental building block of matter in many introductory science lessons?",
    "order": 1,
    "challenge_options": [
      { "text": "Molecules", "correct": false },
      { "text": "Atoms", "correct": true },
      { "text": "Mixtures", "correct": false },
      { "text": "Solutions", "correct": false }
    ]
  }
]
```

## Testing

```bash
python -m pytest tests/
```

Add real tests under `tests/` as the codebase grows; `test_smoke.py` is currently a placeholder.

## Known limitations (prototype)

- **No** built-in user authentication or multi-tenant isolation beyond lesson id strings.
- **ChromaDB** is local; not a managed cloud vector DB.
- **Google Slides** path does not use the official Google Slides API with per-user OAuth—only **link-export** suitable for public / link-shared decks.
- **Batch** processing (many files in one job) is not implemented in the API.
- First run with **sentence-transformers** downloads model weights; ensure disk and network are available.

## License

See `LICENSE` in this repository.
