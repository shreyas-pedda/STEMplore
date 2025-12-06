from pathlib import Path
from extractors.slides_extractor import SlidesExtractor

# Content contains the text data from the presentation
extractor = SlidesExtractor()
content = extractor.extract_from_file(Path("data/inputs/Intro to Java.pptx"))