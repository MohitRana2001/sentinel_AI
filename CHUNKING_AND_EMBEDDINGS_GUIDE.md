# Chunking and Embeddings System - Technical Guide

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Chunking Process](#chunking-process)
4. [Embedding Generation](#embedding-generation)
5. [Processing Pipeline by File Type](#processing-pipeline-by-file-type)
6. [Configuration Options](#configuration-options)
7. [Vector Storage and Retrieval](#vector-storage-and-retrieval)
8. [Code Examples](#code-examples)

---

## Overview

Sentinel AI uses a sophisticated chunking and embedding system to process various file types (documents, audio, video) and make them searchable through semantic vector similarity. This guide explains how text is broken into chunks and converted into embeddings for efficient retrieval.

### Key Concepts

- **Chunking**: Breaking large text into smaller, manageable pieces
- **Embeddings**: Converting text chunks into high-dimensional vectors that capture semantic meaning
- **Vector Store**: Database storing embeddings for similarity search
- **Semantic Search**: Finding relevant content using vector similarity rather than keyword matching

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Upload Files                              │
│        (Documents, Audio, Video)                             │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│              File Type Detection                             │
│   PDF/DOCX/TXT → Document Processor                         │
│   MP3/WAV/M4A  → Audio Processor (Transcription)            │
│   MP4/AVI/MOV  → Video Processor (Frame Analysis)           │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│            Text Extraction & Processing                      │
│  • OCR for scanned documents (Tesseract + Docling)          │
│  • Language detection (langid)                               │
│  • Translation (if non-English) using m2m100                 │
│  • Summarization using LLM (Gemma/Gemini)                    │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│                  CHUNKING PHASE                              │
│  ┌─────────────────────────────────────────┐                │
│  │ RecursiveCharacterTextSplitter          │                │
│  │ • chunk_size: 2000 characters (default) │                │
│  │ • chunk_overlap: 100 characters         │                │
│  │ • separators: ["\n\n", "\n", ". ", " "] │                │
│  └─────────────────────────────────────────┘                │
│                                                               │
│  Input: "Long document text..."                              │
│  Output: [chunk1, chunk2, chunk3, ...]                       │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│               EMBEDDING GENERATION                           │
│  ┌─────────────────────────────────────────┐                │
│  │ OllamaEmbeddings                         │                │
│  │ • Model: embeddinggemma:latest           │                │
│  │ • Converts each chunk to vector          │                │
│  │ • Dimensions: 768 (model-dependent)      │                │
│  └─────────────────────────────────────────┘                │
│                                                               │
│  For each chunk:                                              │
│  "Police arrived at scene" → [0.23, -0.45, 0.67, ...]       │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│              VECTOR STORAGE (AlloyDB)                        │
│  ┌─────────────────────────────────────────┐                │
│  │ DocumentChunk table:                     │                │
│  │ • id (Primary Key)                       │                │
│  │ • document_id (Foreign Key)              │                │
│  │ • chunk_index (Position in document)     │                │
│  │ • chunk_text (Original text)             │                │
│  │ • embedding (Vector column - pgvector)   │                │
│  │ • chunk_metadata (JSON)                  │                │
│  └─────────────────────────────────────────┘                │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│            SEMANTIC SEARCH ENABLED                           │
│  User Query → Embed Query → Find Similar Vectors            │
│  "What happened at the scene?" → Top K relevant chunks       │
└─────────────────────────────────────────────────────────────┘
```

---

## Chunking Process

### What is Chunking?

Chunking breaks large documents into smaller pieces for several reasons:
1. **Context Window Limits**: LLMs have maximum input lengths
2. **Improved Relevance**: Smaller chunks provide more precise matches
3. **Efficient Processing**: Easier to process and store
4. **Better Retrieval**: More granular semantic search

### How Chunks Are Created

The system uses **LangChain's RecursiveCharacterTextSplitter**, which intelligently splits text by trying separators in order:

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=2000,        # Target size in characters
    chunk_overlap=100,      # Overlap between chunks
    separators=["\n\n", "\n", ". ", " ", ""]  # Priority order
)
```

#### Splitting Strategy

1. **Primary separator (`\n\n`)**: Splits by paragraphs first
2. **Secondary separator (`\n`)**: Splits by lines if paragraphs too large
3. **Tertiary separator (`. `)**: Splits by sentences
4. **Final separator (` `)**: Splits by words if needed
5. **Character-level**: Last resort if all else fails

#### Chunk Overlap

The 100-character overlap ensures context continuity:

```
Chunk 1: "...police arrived at the scene at 3pm..."
                                    ↓ [100 char overlap]
Chunk 2: "...at the scene at 3pm. The suspects..."
```

This prevents important context from being split across chunks.

### Configuration

You can customize chunking via environment variables in `config.py`:

```bash
# .env
CHUNK_SIZE=2000        # Size of each chunk in characters
CHUNK_OVERLAP=100      # Overlap between consecutive chunks
```

### Example: Document Chunking

**Original Text** (4,500 characters):
```text
On October 31, 2024, police received a distress call...
[long document continues]
...The investigation is ongoing.
```

**After Chunking** (3 chunks):
```text
Chunk 1 (2,000 chars): "On October 31, 2024, police..."
Chunk 2 (2,000 chars): "...at the scene. Multiple witnesses..."  
Chunk 3 (1,500 chars): "...The investigation is ongoing."
```

Each chunk is stored separately with its own embedding.

---

## Embedding Generation

### What are Embeddings?

Embeddings are numerical vector representations of text that capture semantic meaning. Similar concepts are located close together in vector space.

```
"Police officer"     → [0.12, 0.45, -0.23, ...] (768 dims)
"Law enforcement"    → [0.15, 0.43, -0.21, ...]  ← Close in vector space
"Birthday cake"      → [-0.67, 0.89, 0.34, ...]  ← Far in vector space
```

### Embedding Model

Sentinel AI uses **OllamaEmbeddings** with the `embeddinggemma` model:

```python
from langchain_ollama import OllamaEmbeddings

embeddings = OllamaEmbeddings(
    model="embeddinggemma:latest",
    base_url="http://localhost:11434"  # Ollama server
)

# Generate embedding for a chunk
vector = embeddings.embed_query("Police arrived at scene")
# Returns: array of 768 floats
```

### Embedding Process Flow

```python
# In vector_store.py - VectorStore.add_document_chunks()

for idx, chunk_text in enumerate(chunks):
    # 1. Generate embedding vector
    embedding_vector = self.embeddings.embed_query(chunk_text)
    
    # 2. Create database record
    chunk = models.DocumentChunk(
        document_id=document_id,
        chunk_index=idx,
        chunk_text=chunk_text,
        embedding=embedding_vector,  # Stored as pgvector
        chunk_metadata={"source": "document"}
    )
    
    # 3. Store in database
    db.add(chunk)
```

### Vector Storage in Database

The embeddings are stored in AlloyDB (PostgreSQL) with the **pgvector** extension:

```sql
CREATE TABLE document_chunks (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id),
    chunk_index INTEGER,
    chunk_text TEXT,
    embedding VECTOR(768),  -- pgvector column
    chunk_metadata JSONB,
    created_at TIMESTAMP
);

-- Index for fast similarity search
CREATE INDEX ON document_chunks USING ivfflat (embedding vector_cosine_ops);
```

---

## Processing Pipeline by File Type

### 1. Document Files (PDF, DOCX, TXT)

**File**: `backend/processors/document_processor_service.py`

```
┌─────────────────────────────────────┐
│ 1. Upload Document                  │
│    (PDF, DOCX, TXT)                 │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│ 2. Extract Text                     │
│    • PDF/DOCX: Docling (OCR-aware)  │
│    • TXT: Direct read               │
│    • Multi-language support         │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│ 3. Language Detection               │
│    • Uses langid library            │
│    • Detects: hi, bn, ta, te, etc.  │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│ 4. Translation (if non-English)     │
│    • Uses m2m100 model              │
│    • JSON-based for accuracy        │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│ 5. Summarization                    │
│    • Uses Gemma3:1b or Gemini       │
│    • ~200 words                     │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│ 6. Chunking                         │
│    • RecursiveCharacterTextSplitter │
│    • 2000 chars, 100 overlap        │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│ 7. Embedding Generation             │
│    • Each chunk → embedding vector  │
│    • Summary → separate embedding   │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│ 8. Store in AlloyDB                 │
│    • document_chunks table          │
│    • Indexed for vector search      │
└─────────────────────────────────────┘
```

**Code Example**:
```python
# document_processor_service.py (simplified)

def process_document(self, db, job, gcs_path: str):
    # 1. Download and extract text
    extracted_text, extracted_json, lang = process_document_with_docling(temp_file)
    
    # 2. Translate if needed
    if lang != 'en':
        final_text = translate_json_object(extracted_json, lang, 'en')
    else:
        final_text = extracted_text
    
    # 3. Generate summary
    summary = get_summary(final_text)
    
    # 4. Store and create embeddings
    vectorise_and_store_alloydb(db, document.id, final_text, summary)
```

### 2. Audio Files (MP3, WAV, M4A)

**File**: `backend/processors/audio_processor_service.py`

```
┌─────────────────────────────────────┐
│ 1. Upload Audio                     │
│    (MP3, WAV, M4A)                  │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│ 2. Transcription                    │
│    • Dev: Gemini 2.0 Flash (audio)  │
│    • Prod: Gemma3:12b multimodal    │
│    • Supports Hindi/English         │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│ 3. Translation (if Hindi)           │
│    • Uses m2m100 model              │
│    • Sentence-based translation     │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│ 4. Summarization                    │
│    • Summarizes transcription       │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│ 5. Chunking + Embedding             │
│    • Transcription text → chunks    │
│    • Each chunk → embedding         │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│ 6. Store in AlloyDB                 │
│    • Same as document chunks        │
└─────────────────────────────────────┘
```

**Code Example**:
```python
# audio_processor_service.py (simplified)

def process_audio(self, db, job, gcs_path: str):
    # 1. Transcribe audio
    transcription = self.transcribe_audio(temp_file, is_hindi)
    
    # 2. Translate if Hindi
    if is_hindi:
        final_text = translate(transcription)
    else:
        final_text = transcription
    
    # 3. Generate summary
    summary = self.generate_summary(final_text)
    
    # 4. Create embeddings from transcription
    vectorise_and_store_alloydb(db, document.id, final_text, summary)
```

### 3. Video Files (MP4, AVI, MOV)

**File**: `backend/processors/video_processor_service.py`

```
┌─────────────────────────────────────┐
│ 1. Upload Video                     │
│    (MP4, AVI, MOV)                  │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│ 2. Frame Extraction                 │
│    • Rate: 0.3 fps (1 frame/3sec)   │
│    • Uses moviepy                   │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│ 3. Visual Analysis                  │
│    • Vision LLM analyzes frames     │
│    • Gemma3:4b vision model         │
│    • Generates text description     │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│ 4. Translation (if Hindi)           │
│    • Translates analysis            │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│ 5. Summarization                    │
│    • Summarizes video analysis      │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│ 6. Chunking + Embedding             │
│    • Analysis text → chunks         │
│    • Each chunk → embedding         │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│ 7. Store in AlloyDB                 │
│    • Same as document chunks        │
└─────────────────────────────────────┘
```

**Frame Extraction Details**:
```python
# Extracts 1 frame every ~3 seconds
SAVING_FRAMES_PER_SECOND = 0.3

# Example: 60-second video → ~20 frames
video_clip = VideoFileClip(video_file_path)
for current_duration in np.arange(0, video_clip.duration, step):
    video_clip.save_frame(frame_filename, current_duration)
```

---

## Configuration Options

### Environment Variables

Edit `.env` file to customize chunking and embedding behavior:

```bash
# Chunking Configuration
CHUNK_SIZE=2000              # Size of each text chunk (characters)
CHUNK_OVERLAP=100            # Overlap between chunks (characters)

# Embedding Configuration
EMBEDDING_MODEL=embeddinggemma:latest
EMBEDDING_LLM_HOST=localhost
EMBEDDING_LLM_PORT=11434

# LLM Models for Processing
SUMMARY_LLM_MODEL=gemma3:1b  # For summarization
CHAT_LLM_MODEL=gemma3:1b     # For chat/queries
MULTIMODAL_LLM_MODEL=gemma3:12b  # For audio/video

# Translation
TRANSLATION_THRESHOLD_MB=10  # Max file size for translation
TRANSLATION_LOCAL=True       # Use local m2m100 model

# Development Mode
USE_GEMINI_FOR_DEV=false     # Set to true to use Gemini API
GEMINI_API_KEY=your_api_key
```

### Adjusting Chunk Size

**Smaller chunks (500-1000 chars)**:
- ✅ More precise retrieval
- ✅ Better for Q&A
- ❌ More chunks to store
- ❌ May lose context

**Larger chunks (3000-5000 chars)**:
- ✅ Better context preservation
- ✅ Fewer chunks to manage
- ❌ Less precise matching
- ❌ May exceed LLM context in some cases

**Recommended**: 2000 characters (current default)

### Adjusting Overlap

**More overlap (200-300 chars)**:
- ✅ Better context continuity
- ❌ More redundancy
- ❌ More storage

**Less overlap (50 chars)**:
- ✅ Less redundancy
- ✅ Faster processing
- ❌ May lose context at boundaries

**Recommended**: 100 characters (current default)

---

## Vector Storage and Retrieval

### Storage Schema

```python
# models.py - DocumentChunk model

class DocumentChunk(Base):
    __tablename__ = 'document_chunks'
    
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey('documents.id'))
    chunk_index = Column(Integer)           # Position in document
    chunk_text = Column(Text)               # Original text
    embedding = Column(Vector(768))         # Embedding vector (pgvector)
    chunk_metadata = Column(JSON)           # Additional metadata
    created_at = Column(DateTime)
```

### Similarity Search

**File**: `backend/vector_store.py`

```python
def similarity_search(self, query: str, k: int = 5):
    # 1. Convert query to embedding
    query_embedding = self.embeddings.embed_query(query)
    
    # 2. Find similar chunks using cosine similarity
    results = db.query(DocumentChunk).order_by(
        text(f"embedding <=> '{query_embedding}'::vector")
    ).limit(k).all()
    
    return results
```

### Similarity Metrics

The `<=>` operator in PostgreSQL with pgvector performs **cosine similarity**:

```
similarity = (vector1 · vector2) / (||vector1|| × ||vector2||)

Range: -1 (opposite) to 1 (identical)
```

### Retrieval Example

**User Query**: "What time did the incident occur?"

```python
# 1. Query is converted to embedding
query_vector = embeddings.embed_query("What time did the incident occur?")

# 2. Find most similar chunks
results = vector_store.similarity_search(query_vector, k=5)

# 3. Return top 5 most relevant chunks
# Result might include chunks containing:
#   - "...incident occurred at 3:15 PM..."
#   - "...time of occurrence was approximately 3pm..."
#   - "...reported at 15:00 hours..."
```

### RBAC Filtering

The similarity search respects user permissions:

```python
# Admin: Access all documents
# Manager: Access own + analysts' documents
# Analyst: Access only own documents

if user.rbac_level == RBACLevel.ADMIN:
    # No filtering
elif user.rbac_level == RBACLevel.MANAGER:
    query = query.filter(
        or_(
            ProcessingJob.user_id == user.id,
            User.manager_id == user.id
        )
    )
else:  # ANALYST
    query = query.filter(ProcessingJob.user_id == user.id)
```

---

## Code Examples

### Example 1: Processing a Document

```python
from document_processor import process_document_with_docling
from vector_store import vectorise_and_store_alloydb

# 1. Extract text from PDF
extracted_text, json_obj, lang = process_document_with_docling("report.pdf")
# Output: "On October 31, 2024, police received..."

# 2. Store with embeddings
vectorise_and_store_alloydb(
    db=db_session,
    document_id=123,
    text_content=extracted_text,
    summary="Summary of the report"
)

# Behind the scenes:
# - Text split into chunks (RecursiveCharacterTextSplitter)
# - Each chunk converted to embedding (OllamaEmbeddings)
# - Stored in document_chunks table with vectors
```

### Example 2: Querying Documents

```python
from vector_store import VectorStore

# Initialize vector store
vector_store = VectorStore(db_session)

# Search for relevant chunks
results = vector_store.similarity_search(
    query="What happened at the scene?",
    k=5,  # Top 5 results
    document_ids=[123, 124],  # Optional: limit to specific documents
    user=current_user  # RBAC filtering
)

# Results:
# [
#   {
#     "chunk_text": "Police arrived at the scene at 3pm...",
#     "document_id": 123,
#     "chunk_index": 5,
#     "metadata": {"source": "document"}
#   },
#   ...
# ]
```

### Example 3: Custom Chunking

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Create custom splitter
custom_splitter = RecursiveCharacterTextSplitter(
    chunk_size=3000,          # Larger chunks
    chunk_overlap=200,        # More overlap
    separators=["\n\n", "\n", ". ", " ", ""]
)

# Split text
text = "Very long document..."
chunks = custom_splitter.split_text(text)

# Generate embeddings
for chunk in chunks:
    embedding = embeddings.embed_query(chunk)
    # Store embedding...
```

### Example 4: Fallback to Keyword Search

If embedding generation fails, the system falls back to keyword search:

```python
# In vector_store.py

if query_embedding is None:
    # Fallback: keyword search by substring match
    like_query = f"%{query}%"
    results = db.query(DocumentChunk).filter(
        DocumentChunk.chunk_text.ilike(like_query)
    ).limit(k).all()
```

---

## Performance Considerations

### Chunking Performance

- **Time**: ~0.1s per 10,000 characters
- **Memory**: Minimal (streaming approach)
- **Bottleneck**: Usually I/O, not computation

### Embedding Generation Performance

- **Time**: ~0.5s per chunk (depends on model)
- **Batch processing**: Can generate multiple embeddings in parallel
- **Model size**: `embeddinggemma` ~1.5GB

### Storage Requirements

- **Vector size**: 768 floats × 4 bytes = 3KB per chunk
- **1000 chunks**: ~3MB for embeddings alone
- **Index overhead**: ~50% additional space for IVFFLAT index

### Optimization Tips

1. **Batch processing**: Process multiple files in parallel
2. **Caching**: Cache embeddings for summaries
3. **Index tuning**: Adjust IVFFLAT parameters for dataset size
4. **Chunk size**: Balance between precision and performance

---

## Troubleshooting

### Empty Embeddings

**Problem**: No embeddings generated

**Solution**:
```python
# Check if Ollama server is running
curl http://localhost:11434/api/tags

# Verify embedding model is installed
ollama list | grep embeddinggemma

# Pull model if missing
ollama pull embeddinggemma:latest
```

### Slow Similarity Search

**Problem**: Vector search takes too long

**Solution**:
```sql
-- Create index if missing
CREATE INDEX ON document_chunks 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Tune for larger datasets
ALTER INDEX document_chunks_embedding_idx 
SET (lists = 1000);
```

### Poor Search Results

**Problem**: Irrelevant chunks returned

**Solutions**:
1. Increase `k` parameter (get more results)
2. Adjust chunk size (try smaller chunks)
3. Verify embedding model matches training language
4. Check if query is too vague or ambiguous

---

## Summary

The Sentinel AI chunking and embedding system provides:

✅ **Intelligent Text Splitting**: RecursiveCharacterTextSplitter with overlap  
✅ **Semantic Embeddings**: High-quality vectors using embeddinggemma  
✅ **Multi-format Support**: Documents, audio transcriptions, video analysis  
✅ **Efficient Storage**: PostgreSQL with pgvector extension  
✅ **Fast Retrieval**: Vector similarity search with IVFFLAT indexing  
✅ **RBAC Security**: User-level access control on searches  
✅ **Configurable**: Customizable chunk size, overlap, and models  
✅ **Production-Ready**: Error handling, fallbacks, and monitoring  

This system enables powerful semantic search across all uploaded content, regardless of format or language, with millisecond-level retrieval performance.

---

**For more information, see:**
- `backend/vector_store.py` - Vector storage implementation
- `backend/document_chunker.py` - Legacy chunking utilities
- `backend/processors/` - File type processors
- `backend/config.py` - Configuration options
