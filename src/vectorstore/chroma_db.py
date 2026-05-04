import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
from pathlib import Path
import uuid


class ChromaDBStore:
    
    def __init__(self, persist_directory: str = "./chroma_db", collection_name: str = "stemplore_slides"):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client with ephemeral (in-memory) storage for Vercel
        self.client = chromadb.EphemeralClient(
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "STEMplore slide embeddings for question generation"}
        )
    
    def add_slides(self, lesson_id: str, slides_data: List[Dict[str, Any]]) -> bool:
        """
        Add slide embeddings to the database for a specific lesson.
        
        Args:
            lesson_id: Unique identifier for the lesson
            slides_data: List of slide dictionaries with keys:
                - 'slide_number': int
                - 'text': str (full_text content)
                - 'embedding': List[float]
                - 'metadata': Dict with 'title' and 'slide_number'
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not slides_data:
            print("No slides data provided to add.")
            return False
        
        try:
            # Prepare data for ChromaDB
            ids = []
            embeddings = []
            documents = []
            metadatas = []
            
            for slide in slides_data:
                # Generate unique ID for each slide
                slide_id = f"{lesson_id}_slide_{slide['slide_number']}"
                ids.append(slide_id)
                
                # Extract embedding
                if 'embedding' not in slide:
                    print(f"Warning: Slide {slide['slide_number']} missing embedding, skipping.")
                    continue
                embeddings.append(slide['embedding'])
                
                # Extract text content
                text = slide.get('text', slide.get('full_text', ''))
                documents.append(text)
                
                # Prepare metadata with lesson_id
                metadata = slide.get('metadata', {}).copy()
                metadata['lesson_id'] = lesson_id
                metadata['slide_id'] = slide['slide_number']
                if 'title' not in metadata:
                    metadata['title'] = slide.get('title', '')
                metadatas.append(metadata)
            
            if not ids:
                print("No valid slides to add after processing.")
                return False
            
            # Add to ChromaDB collection
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
            
            print(f"Successfully added {len(ids)} slides for lesson_id: {lesson_id}")
            return True
            
        except Exception as e:
            print(f"Error adding slides to ChromaDB: {e}")
            return False
    
    def get_relevant_chunks(self, lesson_id: str, n_results: int = 10, query_text: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieve relevant slide chunks for a lesson.
        
        Args:
            lesson_id: The lesson identifier to retrieve slides for
            n_results: Maximum number of results to return
            query_text: Optional query text for semantic search. If None, returns all slides for the lesson.
        
        Returns:
            List of dictionaries with keys: 'slide_id', 'text', 'metadata'
        """
        try:
            if query_text:
                # Semantic search using query text
                results = self.collection.query(
                    query_texts=[query_text],
                    n_results=n_results,
                    where={"lesson_id": lesson_id}
                )
                
                # Process results
                chunks = []
                if results['ids'] and len(results['ids'][0]) > 0:
                    for i in range(len(results['ids'][0])):
                        chunk = {
                            'slide_id': results['metadatas'][0][i].get('slide_id', 0),
                            'text': results['documents'][0][i],
                            'metadata': results['metadatas'][0][i]
                        }
                        chunks.append(chunk)
            else:
                # Get all slides for the lesson (filtered by lesson_id)
                results = self.collection.get(
                    where={"lesson_id": lesson_id}
                )
                
                # Process results and sort by slide_id
                chunks = []
                slide_data = []
                for i in range(len(results['ids'])):
                    slide_data.append({
                        'slide_id': results['metadatas'][i].get('slide_id', 0),
                        'text': results['documents'][i],
                        'metadata': results['metadatas'][i],
                        'id': results['ids'][i]
                    })
                
                # Sort by slide_id to maintain order
                slide_data.sort(key=lambda x: x['slide_id'])
                
                # Format as expected
                for slide in slide_data[:n_results]:
                    chunks.append({
                        'slide_id': slide['slide_id'],
                        'text': slide['text'],
                        'metadata': slide['metadata']
                    })
            
            return chunks
            
        except Exception as e:
            print(f"Error retrieving chunks from ChromaDB: {e}")
            return []
    
    def delete_lesson(self, lesson_id: str) -> bool:
        """
        Delete all slides for a specific lesson.
        
        Args:
            lesson_id: The lesson identifier to delete
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get all IDs for this lesson
            results = self.collection.get(
                where={"lesson_id": lesson_id}
            )
            
            if results['ids']:
                self.collection.delete(ids=results['ids'])
                print(f"Deleted {len(results['ids'])} slides for lesson_id: {lesson_id}")
                return True
            else:
                print(f"No slides found for lesson_id: {lesson_id}")
                return False
                
        except Exception as e:
            print(f"Error deleting lesson from ChromaDB: {e}")
            return False
    
    def get_lesson_count(self, lesson_id: str) -> int:
        """
        Get the number of slides stored for a lesson.
        
        Args:
            lesson_id: The lesson identifier
        
        Returns:
            int: Number of slides for the lesson
        """
        try:
            results = self.collection.get(
                where={"lesson_id": lesson_id}
            )
            return len(results['ids'])
        except Exception as e:
            print(f"Error getting lesson count: {e}")
            return 0
    
    def clear_collection(self) -> bool:
        """
        Clear all data from the collection.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Delete the collection and recreate it
            self.client.delete_collection(name=self.collection.name)
            self.collection = self.client.get_or_create_collection(
                name=self.collection.name,
                metadata={"description": "STEMplore slide embeddings for question generation"}
            )
            print("Collection cleared successfully.")
            return True
        except Exception as e:
            print(f"Error clearing collection: {e}")
            return False


# Testing code
if __name__ == "__main__":
    from pathlib import Path
    import sys
    sys.path.append(str(Path(__file__).parent.parent.parent))
    
    from src.extractors.slides_extractor import SlidesExtractor
    from src.embeddings.embedding_generator import EmbeddingGenerator
    
    # Test the ChromaDB implementation
    print("Testing ChromaDB implementation...")
    
    # Extract slides
    extractor = SlidesExtractor()
    slides_data = extractor.extract_from_file(Path("data/inputs/Intro to Java.pptx"))
    print(f"Extracted {len(slides_data)} slides\n")
    
    # Generate embeddings
    generator = EmbeddingGenerator()
    embeddings_data = generator.generate_embeddings_batch(slides_data)
    print(f"Generated embeddings for {len(embeddings_data)} slides\n")
    
    # Initialize ChromaDB
    db = ChromaDBStore()
    
    # Add slides to database
    lesson_id = "intro-to-java"
    success = db.add_slides(lesson_id, embeddings_data)
    print(f"Add slides result: {success}\n")
    
    # Get all chunks for the lesson
    chunks = db.get_relevant_chunks(lesson_id)
    print(f"Retrieved {len(chunks)} chunks for lesson_id: {lesson_id}")
    if chunks:
        print(f"\nFirst chunk preview:")
        print(f"Slide ID: {chunks[0]['slide_id']}")
        print(f"Text preview: {chunks[0]['text'][:100]}...")
        print(f"Metadata: {chunks[0]['metadata']}")
    
    # Test semantic search
    print(f"\n--- Testing Semantic Search ---")
    search_chunks = db.get_relevant_chunks(lesson_id, query_text="What is Java?", n_results=3)
    print(f"Found {len(search_chunks)} relevant chunks for query 'What is Java?'")
    if search_chunks:
        print(f"Most relevant chunk: {search_chunks[0]['text'][:150]}...")
    
    print("\nChromaDB test completed!")
