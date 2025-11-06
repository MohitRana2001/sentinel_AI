# Chunking & Embeddings - Quick Reference

## TL;DR

Sentinel AI breaks uploaded files into **chunks** and converts them to **embeddings** for semantic search.

```
Upload File → Extract Text → Chunk Text → Generate Embeddings → Store in DB → Search
```

---

## What Happens When You Upload a File?

### For Documents (PDF, DOCX, TXT)
1. **Extract text** using Docling (with OCR support)
2. **Detect language** and translate if needed
3. **Break into chunks** (2000 chars, 100 overlap)
4. **Generate embeddings** for each chunk
5. **Store in database** with vectors

### For Audio (MP3, WAV)
1. **Transcribe audio** to text
2. **Translate** if Hindi
3. **Break into chunks**
4. **Generate embeddings**
5. **Store in database**

### For Video (MP4, AVI)
1. **Extract frames** (1 per 3 seconds)
2. **Analyze frames** with vision model
3. **Break analysis into chunks**
4. **Generate embeddings**
5. **Store in database**

---

## How Chunking Works

### Simple Example

**Original text (5000 chars)**:
```
The police received a call at 3pm on October 31st. Officers arrived at the 
scene within 10 minutes. Multiple witnesses were interviewed...
[continues for 5000 characters]
```

**After chunking**:
```
Chunk 1 (2000 chars): "The police received a call at 3pm..."
Chunk 2 (2000 chars): "...Officers arrived at the scene..."  [100 char overlap]
Chunk 3 (1000 chars): "...Multiple witnesses were interviewed..."
```

### Why Chunk?
- **Context limits**: LLMs can only process so much text
- **Better search**: Smaller pieces = more precise matches
- **Efficiency**: Faster processing and storage

### Configuration
```bash
# .env file
CHUNK_SIZE=2000        # Chunk size in characters
CHUNK_OVERLAP=100      # Overlap between chunks
```

---

## How Embeddings Work

### What's an Embedding?

An embedding is a list of numbers that represents text meaning:

```
"Police officer"     → [0.12, 0.45, -0.23, 0.67, ...] (768 numbers)
"Law enforcement"    → [0.15, 0.43, -0.21, 0.65, ...]  ← Similar!
"Birthday cake"      → [-0.67, 0.89, 0.34, -0.12, ...]  ← Different!
```

Similar meanings = similar numbers = close in "vector space"

### How It's Used

**When storing**:
```python
chunk_text = "Police arrived at 3pm"
embedding = model.embed(chunk_text)  # → [0.12, 0.45, ...]
database.store(chunk_text, embedding)
```

**When searching**:
```python
query = "What time did they arrive?"
query_embedding = model.embed(query)  # → [0.14, 0.43, ...]

# Find chunks with similar embeddings
results = database.find_similar(query_embedding, limit=5)
# Returns: chunks about arrival times
```

---

## Key Files

| File | Purpose |
|------|---------|
| `vector_store.py` | Main chunking & embedding logic |
| `document_processor.py` | Document extraction & processing |
| `processors/document_processor_service.py` | Document pipeline |
| `processors/audio_processor_service.py` | Audio transcription → chunks |
| `processors/video_processor_service.py` | Video analysis → chunks |
| `models.py` | Database schema (`DocumentChunk` table) |

---

## Database Schema

```sql
document_chunks
├─ id (primary key)
├─ document_id (which document this came from)
├─ chunk_index (position: 0, 1, 2...)
├─ chunk_text (the actual text)
├─ embedding (vector of 768 numbers)
└─ chunk_metadata (JSON: {"source": "document"})
```

---

## Configuration Quick Reference

### Models
```bash
EMBEDDING_MODEL=embeddinggemma:latest     # Creates embeddings
SUMMARY_LLM_MODEL=gemma3:1b              # Summarization
MULTIMODAL_LLM_MODEL=gemma3:12b          # Audio/Video processing
```

### Chunking
```bash
CHUNK_SIZE=2000          # Smaller = more precise, more chunks
CHUNK_OVERLAP=100        # Prevents context loss at boundaries
```

### Storage
```bash
STORAGE_BACKEND=gcs      # Where files are stored
ALLOYDB_HOST=localhost   # Where embeddings are stored
```

---

## Common Operations

### Change chunk size
```bash
# Edit .env
CHUNK_SIZE=3000

# Restart services
docker-compose restart
```

### Query with embeddings
```python
from vector_store import VectorStore

vector_store = VectorStore(db)
results = vector_store.similarity_search(
    query="What happened at the scene?",
    k=5  # Return top 5 matches
)
```

### Check if embeddings are working
```bash
# Test Ollama server
curl http://localhost:11434/api/tags

# Check embedding model
ollama list | grep embeddinggemma
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| No search results | Check if Ollama is running: `curl http://localhost:11434` |
| Slow searches | Verify pgvector index exists in database |
| Poor results | Try adjusting `CHUNK_SIZE` (smaller = more precise) |
| Empty embeddings | Pull model: `ollama pull embeddinggemma:latest` |

---

## Performance

| Metric | Value |
|--------|-------|
| Chunk generation | ~0.1s per 10,000 chars |
| Embedding generation | ~0.5s per chunk |
| Vector storage | ~3KB per chunk |
| Search latency | <100ms for top 5 results |

---

## Architecture at a Glance

```
┌──────────────┐
│ Upload File  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Extract Text │  ← Docling, Tesseract, Vision models
└──────┬───────┘
       │
       ▼
┌──────────────────────┐
│ Split into Chunks    │  ← RecursiveCharacterTextSplitter
│ • 2000 char size     │     chunk_size=2000
│ • 100 char overlap   │     chunk_overlap=100
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Generate Embeddings  │  ← OllamaEmbeddings
│ Each chunk → vector  │     embeddinggemma model
│ [0.12, 0.45, ...]    │     768 dimensions
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Store in AlloyDB     │  ← PostgreSQL + pgvector
│ chunk_text + vector  │     Indexed for fast search
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Ready for Search! 🔍 │  ← Semantic similarity
└──────────────────────┘
```

---

## Example: End-to-End

1. **Upload**: `incident_report.pdf` (5 pages, 10,000 chars)
2. **Extract**: Docling extracts text with OCR
3. **Chunk**: Split into 5 chunks (2000 chars each, 100 overlap)
4. **Embed**: Generate 5 embedding vectors (768 floats each)
5. **Store**: Save 5 rows in `document_chunks` table
6. **Search**: User asks "What time?", system finds relevant chunk

**Storage footprint**: 
- Text: 10KB
- Embeddings: 5 chunks × 3KB = 15KB
- Total: ~25KB

---

## Next Steps

- 📖 Read full guide: [CHUNKING_AND_EMBEDDINGS_GUIDE.md](../CHUNKING_AND_EMBEDDINGS_GUIDE.md)
- 🔧 Customize: Edit `config.py` or `.env`
- 🧪 Experiment: Try different chunk sizes
- 📊 Monitor: Check embedding generation times
- 🚀 Optimize: Tune pgvector index for your dataset

---

**Questions?** Check the detailed guide or the code:
- `backend/vector_store.py` - Core implementation
- `backend/config.py` - All configuration options
