# STEMplore AI Curriculum Question Generator

> **Phase 2: Prototype** - Automated generation of curriculum questions from Google Slides using RAG (Retrieval-Augmented Generation)

### Problem Being Solved
- Manual content structuring in admin panel
- Time-intensive question generation from slides
- Manual JSON formatting and data entry

### Solution
An LLM-powered RAG pipeline that:
- Extracts content from Google Slides (PowerPoint format)
- Generates embeddings for semantic search
- Creates structured questions using LLM
- Outputs STEMplore-compatible JSON

## Architecture

```
User Upload (.pptx)
    ↓
[Slides Extractor] → Extract text, notes, titles
    ↓
[Embedding Generator] → Create vector embeddings (HuggingFace)
    ↓
[ChromaDB Vector Store] → Store for semantic retrieval
    ↓
[Question Generator] → Generate questions via LLM (OpenAI/Anthropic)
    ↓
[JSON Formatter] → Format to STEMplore schema
    ↓
Output JSON File
```

## Project Structure

```
stemplore-question-generator/
├── requirements.txt          # Python dependencies
├── README.md                # This file
├── .env                     # Specify env variables 
├── settings.py              # Store global configs here 
│
├── src/
│   ├── extractors/
│   │   └── slides_extractor.py      # Extract content from PPTX
│   ├── embeddings/
│   │   └── embedding_generator.py   # Generate embeddings
│   ├── vectorstore/
│   │   └── chroma_store.py          # ChromaDB operations
│   ├── generators/
│   │   └── question_generator.py    # LLM question generation
│   ├── formatters/
│   │   └── json_formatter.py        # Format to JSON schema
│   └── pipeline/
│       └── rag_pipeline.py          # Main orchestration
│
├── app/                             # UI Implementation
│   └── 
│
├── tests/                             
│   └── 
│
└── data/                    # Store curriculum samples and outputted files here for easy use
    ├── inputs/             # Uploaded slides curriculum for testing
    └── outputs/             # Generated JSON files
```

## Getting Started

### Prerequisites
- Python 3.1+

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/shreyas-pedda/STEMplore.git
cd STEMplore
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
```
# Create a .env file and add the required environment variables.
```

### Running the Application

Specify once process is created.

## Using the UI

1. **Fill in once we create**

## Output Format
Look at this document for all information: https://docs.google.com/document/d/1EfO9AhHfHMhV8wzIw0jkoGfjMJQvAtZyLnK0PdfFQQM/edit?usp=sharing

Here is a sample of generated JSON that follows the proper structure:

```json
[
  {
    "type": "SELECT",
    "question": "What is considered the fundamental building block of everything around us?",
    "order": 1,
    "challenge_options": [
      {
        "text": "Molecules",
        "correct": false
      },
      {
        "text": "Compounds",
        "correct": false
      },
      {
        "text": "Atoms",
        "correct": true
      },
      {
        "text": "Mixtures",
        "correct": false
      } loop
    ]
  },
.....
```

## Configuration

### Environment Variables

Create a `.env` file with:

```env
# Add necessary environment variables here as we go
```

### Supported Models

- Look into finding best working open-source models for our usage, if necessary we will reach out for funding.
- https://huggingface.co/models
Find models 

## Testing

Run basic tests:
```bash
python -m pytest tests/
```
Using the pytest library will discover any tests following the proper naming convention and run them. Use this for unit tests.

## Known Limitations (Prototype Phase)

- Only supports .pptx format (no native Google Slides API yet)
- No user authentication
- No database for storing previous generations
- Limited error recovery
- No batch processing of multiple files
- Manual API key entry required

**Status**: Phase 2 - Active Development
