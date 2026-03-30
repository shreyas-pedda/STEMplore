import streamlit as st
import sys
from pathlib import Path
import json
import tempfile
import os
from typing import List, Dict, Any

st.set_page_config(
    page_title="STEMplore",
    page_icon="",
    layout="wide"
)

# Parent directories
sys.path.append(str(Path(__file__).parent.parent))

try:
    from src.extractors.slides_extractor import SlidesExtractor
    from src.embeddings.embedding_generator import EmbeddingGenerator
    from src.vectorstore.chroma_db import ChromaDBStore
    from src.generator.question_generator import QuestionGenerator
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
except Exception as e:
    st.error(f"Error importing modules: {e}")
    st.stop()

#debug
st.title("Prototype: STEMplore Question Generator")
st.markdown("Upload a PowerPoint presentation to generate curriculum questions automatically.")
st.info("Page loaded (for debugging purposes)")


def format_questions_to_stemplore(raw_questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convert questions from generator format to STEMplore required format.
    """
    formatted = []
    
    for idx, question in enumerate(raw_questions, start=1):
        question_type = question.get('question_type', '').upper()
        question_text = question.get('question_text', '')
        options = question.get('options', [])
        answer = question.get('answer', '')
        
        if not question_text:
            continue
        
        # Format  options
        challenge_options = []
        
        if question_type in ['MCQ', 'MULTIPLE CHOICE']:
            # MCQS
            for option in options:
                challenge_options.append({
                    "text": str(option),
                    "correct": str(option).strip() == str(answer).strip()
                })
            
            formatted_question = {
                "type": "SELECT",
                "question": question_text,
                "order": idx,
                "challenge_options": challenge_options
            }
            formatted.append(formatted_question)
            
        elif question_type in ['TRUE/FALSE', 'TRUE_FALSE', 'BOOLEAN']:
            for option in ['True', 'False']:
                challenge_options.append({
                    "text": option,
                    "correct": option == str(answer).strip()
                })
            
            formatted_question = {
                "type": "SELECT",
                "question": question_text,
                "order": idx,
                "challenge_options": challenge_options
            }
            formatted.append(formatted_question)
    
    return formatted


def generate_questions_with_real_db(lesson_id: str, lesson_title: str, db: ChromaDBStore) -> List[Dict[str, Any]]:
    """
    generate with chroma db
    """
    # Get slide chunks
    slide_chunks = db.get_relevant_chunks(lesson_id)
    if not slide_chunks:
        st.warning(f"No content found for lesson_id: {lesson_id}")
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
        st.error(f"Error calling Groq API: {e}")
        return []


# Initialize session state
if 'questions_generated' not in st.session_state:
    st.session_state.questions_generated = None
if 'lesson_id' not in st.session_state:
    st.session_state.lesson_id = None

# Sidebar for configuration
with st.sidebar:
    st.header("Configuration")
    lesson_title = st.text_input("Lesson Title", placeholder="e.g., Introduction to Java")
    num_questions = st.number_input("Number of Questions", min_value=1, max_value=50, disabled=False)
    
    st.markdown("---")
    st.markdown("### 📋 Instructions")
    st.markdown("""
    1. Enter a lesson title
    2. Upload a .pptx file
    3. Click 'Generate Questions'
    4. Download the generated JSON
    """)
    
    # st.markdown("---")
    # st.markdown("###Note")
    # st.info("GROQ key shud be in .env file")

# Main content area
uploaded_file = st.file_uploader(
    "Upload PowerPoint File (.pptx)",
    type=['pptx'],
    help="Upload a PowerPoint presentation file"
)

if uploaded_file is not None:
    # Show file info
    st.success(f"File uploaded: {uploaded_file.name}")
    st.info(f"File size: {uploaded_file.size / 1024:.2f} KB")
    
    # if not lesson_title:
    #     st.warning("⚠️ Please enter a lesson title in the sidebar before generating questions.")
    
    # Generate button
    if st.button("🚀 Generate Questions", type="primary", disabled=not lesson_title):
        if lesson_title:
            with st.spinner("Processing your presentation..."):
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.pptx') as tmp_file:
                        tmp_file.write(uploaded_file.getvalue())
                        tmp_path = Path(tmp_file.name)
                    
                    # extraction
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    status_text.text("📄 Extracting slides...")
                    extractor = SlidesExtractor()
                    slides_data = extractor.extract_from_file(tmp_path)
                    progress_bar.progress(20)
                    st.success(f"✅ Extracted {len(slides_data)} slides")
                    
                    #Generate embeddings
                    status_text.text(" Generating embeddings...")
                    embedding_generator = EmbeddingGenerator()
                    embeddings_data = embedding_generator.generate_embeddings_batch(slides_data)
                    progress_bar.progress(40)
                    st.success(f"✅ Generated embeddings for {len(embeddings_data)} slides")
                    
                    #Store in ChromaDB
                    status_text.text(" Storing in vector database...")
                    lesson_id = lesson_title.lower().replace(" ", "-").replace("_", "-")
                    # Remove special characters
                    lesson_id = ''.join(c for c in lesson_id if c.isalnum() or c == '-')
                    db = ChromaDBStore()
                    db.add_slides(lesson_id, embeddings_data)
                    progress_bar.progress(60)
                    st.success(f"✅ Stored slides in database (lesson_id: {lesson_id})")
                    
                    # Generate questions using real DB
                    status_text.text(" Generating questions with AI...")
                    raw_questions = generate_questions_with_real_db(
                        lesson_id=lesson_id,
                        lesson_title=lesson_title,
                        db=db
                    )
                    progress_bar.progress(80)
                    
                    if raw_questions:
                        #Format to JSON
                        status_text.text(" Formatting output...")
                        formatted_questions = format_questions_to_stemplore(raw_questions)
                        progress_bar.progress(100)
                        status_text.text("✅ Complete!")
                        st.success(f"✅ Generated {len(formatted_questions)} questions")
                        
                        # Store in session state
                        st.session_state.questions_generated = formatted_questions
                        st.session_state.lesson_id = lesson_id
                        
                        # Clean up temp file
                        os.unlink(tmp_path)
                        
                        st.balloons()
                    else:
                        st.error("❌ Failed to generate questions. Please try again.")
                        os.unlink(tmp_path)
                        
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())
                    if 'tmp_path' in locals() and tmp_path.exists():
                        os.unlink(tmp_path)

# Display results
if st.session_state.questions_generated:
    st.markdown("---")
    st.header("Generated Questions")
    
    # Show summary
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Questions", len(st.session_state.questions_generated))
    with col2:
        mcq_count = sum(1 for q in st.session_state.questions_generated if q.get('type') == 'SELECT')
        st.metric("Multiple Choice", mcq_count)
    with col3:
        st.metric("Lesson ID", st.session_state.lesson_id)
    
    # Display questions
    st.subheader("Question Preview")
    for idx, question in enumerate(st.session_state.questions_generated[:5], 1):
        with st.expander(f"Question {idx}: {question.get('question', 'N/A')[:50]}..."):
            st.json(question)
    
    if len(st.session_state.questions_generated) > 5:
        st.info(f"Showing first 5 of {len(st.session_state.questions_generated)} questions. Download JSON to see all.")
    
    # Download button
    st.markdown("---")
    json_str = json.dumps(st.session_state.questions_generated, indent=2)
    st.download_button(
        label="Download JSON",
        data=json_str,
        file_name=f"{st.session_state.lesson_id}_questions.json",
        mime="application/json"
    )
    with st.expander("View Full JSON"):
        st.code(json_str, language="json")
