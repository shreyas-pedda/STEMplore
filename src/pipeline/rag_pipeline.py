from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.extractors.slides_extractor import SlidesExtractor
from src.embeddings.embedding_generator import EmbeddingGenerator
from src.vectorstore.chroma_db import ChromaDBStore
from src.generator.question_generator import QuestionGenerator
#from src.formatters.json_formatter import

# Content contains the text data from the presentation
extractor = SlidesExtractor()
content = extractor.extract_from_file(Path("data/inputs/Intro to Java.pptx"))

embedding_generator = EmbeddingGenerator()
embeddings = embedding_generator.generate_embeddings_batch(content)

store = ChromaDBStore()
storing_success = store.add_slides("java-intro",embeddings) #should be true if embeddings stored successfully

question_generator = QuestionGenerator()
questions = question_generator.generate_questions_for_lesson("java-intro","Intro to Java")


#testing pipeline until chromadb
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
