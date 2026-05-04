import sys
from pathlib import Path
import tempfile
import os
from typing import List, Dict, Any

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Append parent directory to sys.path to allow relative imports
sys.path.append(str(Path(__file__).parent.parent))

from src.extractors.unified_extractor import UnifiedExtractor
from src.embeddings.embedding_generator import EmbeddingGenerator
from src.vectorstore.chroma_db import ChromaDBStore
from src.generator.question_generator import QuestionGenerator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(
    title="STEMplore API",
    description="FastAPI server for STEMplore question generation",
)

# Add CORS middleware to allow requests from Next.js frontend (http://localhost:3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def format_questions_to_stemplore(
    raw_questions: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Convert questions from generator format to STEMplore required format.
    """
    formatted = []

    for idx, question in enumerate(raw_questions, start=1):
        question_type = question.get("question_type", "").upper()
        question_text = question.get("question_text", "")
        options = question.get("options", [])
        answer = question.get("answer", "")

        if not question_text:
            continue

        # Format  options
        challenge_options = []

        if question_type in ["MCQ", "MULTIPLE CHOICE"]:
            # MCQS
            for option in options:
                challenge_options.append(
                    {
                        "text": str(option),
                        "correct": str(option).strip() == str(answer).strip(),
                    }
                )

            formatted_question = {
                "type": "SELECT",
                "question": question_text,
                "order": idx,
                "challenge_options": challenge_options,
            }
            formatted.append(formatted_question)

        elif question_type in ["TRUE/FALSE", "TRUE_FALSE", "BOOLEAN"]:
            for option in ["True", "False"]:
                challenge_options.append(
                    {"text": option, "correct": option == str(answer).strip()}
                )

            formatted_question = {
                "type": "SELECT",
                "question": question_text,
                "order": idx,
                "challenge_options": challenge_options,
            }
            formatted.append(formatted_question)

    return formatted


def generate_questions_with_real_db(
    lesson_id: str, lesson_title: str, db: ChromaDBStore
) -> List[Dict[str, Any]]:
    """
    generate with chroma db
    """
    # Get slide chunks
    slide_chunks = db.get_relevant_chunks(lesson_id)
    if not slide_chunks:
        return []

    question_generator = QuestionGenerator()
    slide_context = question_generator._format_context(slide_chunks)
    prompt_text = question_generator._get_prompt_text(lesson_title, slide_context)

    try:
        # Use QuestionGenerator
        completion = question_generator.client.chat.completions.create(
            model=question_generator.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt_text,
                }
            ],
            temperature=0.3,
        )

        raw_output = completion.choices[0].message.content

        # Use QuestionGenerator's validation method
        validated_questions = question_generator._validate_and_clean_json(raw_output)
        return validated_questions

    except Exception as e:
        print(f"Error calling Groq API: {e}")
        return []


@app.post("/api/generate-questions")
async def generate_questions(
    lessonId: str = Form(...),
    file: UploadFile | None = File(None),
    slidesUrl: str | None = Form(None),
):
    """
    Generate questions from an uploaded lesson file (PPTX, PDF, text, image, video/audio, etc.)
    or from a public Google Slides URL (slidesUrl).
    """
    extractor = UnifiedExtractor()
    allowed = {ext.lower() for ext in extractor.supported_extensions()}
    url = (slidesUrl or "").strip() or None

    tmp_path = None
    try:
        if url:
            from src.extractors.google_slides_extractor import extract_chunks_from_slides_url

            slides_data = extract_chunks_from_slides_url(url)
        elif file is not None and file.filename:
            suffix = Path(file.filename).suffix.lower()
            if suffix not in allowed:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Unsupported file type: {suffix or '(none)'}. "
                        f"Supported extensions: {', '.join(sorted(allowed))}"
                    ),
                )
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                content = await file.read()
                tmp_file.write(content)
                tmp_path = Path(tmp_file.name)
            slides_data = extractor.extract_from_file(tmp_path)
        else:
            raise HTTPException(
                status_code=400,
                detail="Provide either an uploaded file or slidesUrl (Google Slides link).",
            )
        if not slides_data:
            raise HTTPException(
                status_code=400,
                detail="Could not extract data from the provided presentation.",
            )

        # 2. Generate embeddings
        embedding_generator = EmbeddingGenerator()
        embeddings_data = embedding_generator.generate_embeddings_batch(slides_data)

        # 3. Store in ChromaDB
        # Standardize lesson_id for ChromaDB
        clean_lesson_id = lessonId.lower().replace(" ", "-").replace("_", "-")
        clean_lesson_id = "".join(c for c in clean_lesson_id if c.isalnum() or c == "-")

        db = ChromaDBStore()
        db.add_slides(clean_lesson_id, embeddings_data)

        # 4. Generate questions using Groq and the DB context
        # We pass lessonId as the title parameter internally
        raw_questions = generate_questions_with_real_db(
            lesson_id=clean_lesson_id, lesson_title=lessonId, db=db
        )

        if not raw_questions:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate questions. Model may have returned an empty response.",
            )

        # 5. Format to STEMplore required response format
        formatted_questions = format_questions_to_stemplore(raw_questions)

        # 6. Return the raw array
        # JSONResponse will automatically serialize the list to JSON
        return JSONResponse(content=formatted_questions)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if tmp_path is not None and tmp_path.exists():
            os.unlink(tmp_path)
