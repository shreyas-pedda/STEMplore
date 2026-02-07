from pathlib import Path
import sys
import json
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).parent.parent.parent))
load_dotenv()

from src.extractors.slides_extractor import SlidesExtractor
from src.embeddings.embedding_generator import EmbeddingGenerator
from src.vectorstore.chroma_db import ChromaDBStore
from src.generator.question_generator import QuestionGenerator
from src.formatters.json_formatter import format_questions

# Content contains the text data from the presentation
extractor = SlidesExtractor()
content = extractor.extract_from_file(Path("data/inputs/Intro to Java.pptx"))

embedding_generator = EmbeddingGenerator()
embeddings = embedding_generator.generate_embeddings_batch(content)

store = ChromaDBStore()
storing_success = store.add_slides("java-intro",embeddings) #should be true if embeddings stored successfully

question_generator = QuestionGenerator()
questions = question_generator.generate_questions_for_lesson("java-intro","Intro to Java")

#helper for now to convert from generator format to json formatter format
def transform_questions(raw_questions):
    """Convert QuestionGenerator output to format_questions input"""
    transformed = []
    for q in raw_questions:
        #MCQ
        if q['question_type'] == 'MCQ':
            challenge_options = []
            for option in q['options']:
                challenge_options.append({
                    "text": option,
                    "correct": option == q['answer']
                })
            transformed.append({
                "question": q['question_text'],
                "challenge_options": challenge_options
            })
        #True/False as MCQ with 2 options
        elif q['question_type'] == 'True/False':
            challenge_options = [
                {"text": "True", "correct": q['answer'] == "True"},
                {"text": "False", "correct": q['answer'] == "False"},
                {"text": "N/A", "correct": False},  # Padding to 4 options
                {"text": "N/A", "correct": False}
            ]
            transformed.append({
                "question": q['question_text'],
                "challenge_options": challenge_options
            })
    return transformed

#transform and format questions
transformed_questions = transform_questions(questions)
formatted_questions = format_questions(transformed_questions)

#save to output file
output_path = Path("data/outputs/java-intro-questions.json")
with open(output_path, 'w') as f:
    json.dump(formatted_questions, f, indent=2)

#testing pipeline for now
print(f"Extracted {len(content)} slides")
print(f"First slide title: {content[0]['title']}\n")
print(f"Generated embeddings for {len(embeddings)} slides")
print(f"Embedding dimension: {len(embeddings[0]['embedding'])}\n")
print(f"Storage success: {storing_success}\n")
count = store.get_lesson_count("java-intro")
print(f"Slides stored in DB: {count}")
chunks = store.get_relevant_chunks("java-intro")
print(f"Can retrieve {len(chunks)} chunks")
print(f"First chunk text: {chunks[0]['text'][:100]}...\n")
print(f"Generated {len(questions)} raw questions")
print(f"Formatted {len(formatted_questions)} questions for STEMplore")
print(f"Saved questions to: {output_path}\n")
print("First formatted question:")
print(json.dumps(formatted_questions[0], indent=2))
