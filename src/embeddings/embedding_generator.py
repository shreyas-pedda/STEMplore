from typing import List, Dict
from sentence_transformers import SentenceTransformer
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from src.extractors.slides_extractor import SlidesExtractor



class EmbeddingGenerator:
    def __init__(self, model_name: str = 'sentence-transformers/all-MiniLM-L6-v2' ):
        self.model_name = model_name
        self.model = None

    def _load_model(self) -> SentenceTransformer:
        if self.model is None:
            self.model = SentenceTransformer(self.model_name)
        return self.model
    
    #helper to create a slide embedding
    def generate_embedding(self,text:str) -> List[float]:
       model = self._load_model()
       embedding = model.encode(text) 
       return embedding.tolist() #numpy arrays to python lists
    
    #processing multiple slides at once
    #using content output from extractor to create embedding for each slide, adding this to output dictionary 
    def generate_embeddings_batch(self,slides_data: List[Dict]) -> List[Dict]:
        slide_dict_list = []
        for slide in slides_data:
            if not slide.get('full_text') or slide['full_text'].strip() == '':
                continue
            slide_embedding = self.generate_embedding(slide['full_text'])

            #output dictionary
            slide_dict = {
                'slide_number': slide['slide_number'],
                'text' : slide['full_text'],
                'embedding' : slide_embedding,
                'metadata': {'title': slide['title'], 'slide_number': slide['slide_number']}  #for ChromaDB
            }
            slide_dict_list.append(slide_dict)
        return slide_dict_list

#testing
if __name__ == "__main__":

    #extract text from test file
    extractor = SlidesExtractor()
    slides_data = extractor.extract_from_file(Path("data/inputs/Intro to Java.pptx"))
    print(f"Extracted {len(slides_data)} slides\n")
    
    #create embedding generator
    generator = EmbeddingGenerator()
    
    #generate embeddings for all slides
    embeddings_data = generator.generate_embeddings_batch(slides_data)
    print(f"Generated embeddings for {len(embeddings_data)} slides\n")
    
    #display results from slide 1
    if embeddings_data:
        first_slide = embeddings_data[0]
        print(f"Slide Number: {first_slide['slide_number']}")
        print(f"Metadata: {first_slide['metadata']}")
        print(f"Text: {first_slide['text'][:100]}...")  #first 100 chars
        print(f"Embedding dimension: {len(first_slide['embedding'])}")
        print(f"First 10 values: {first_slide['embedding'][:10]}")
        print("\n Embedding generation done (for now at least lol)")