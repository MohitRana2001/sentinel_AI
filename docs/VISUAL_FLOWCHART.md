# Visual Process Flowchart

This document provides visual flowcharts to understand how chunking and embeddings work in Sentinel AI.

## Complete Processing Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          USER UPLOADS FILE                               │
│                     (PDF, DOCX, TXT, MP3, MP4)                          │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │  File Type Detection    │
                    └────────┬───────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
    ┌────────┐          ┌────────┐         ┌────────┐
    │Document│          │ Audio  │         │ Video  │
    │  .pdf  │          │  .mp3  │         │  .mp4  │
    │  .docx │          │  .wav  │         │  .avi  │
    │  .txt  │          │  .m4a  │         │  .mov  │
    └───┬────┘          └───┬────┘         └───┬────┘
        │                   │                   │
        │                   │                   │
        ▼                   ▼                   ▼
    ┌─────────────┐    ┌──────────────┐   ┌──────────────┐
    │   Docling   │    │ Transcription│   │   Extract    │
    │   + OCR     │    │   (Gemini/   │   │   Frames     │
    │  Extract    │    │    Gemma)    │   │ (1 per 3sec) │
    └───┬─────────┘    └──────┬───────┘   └──────┬───────┘
        │                     │                   │
        │                     │                   │
        ▼                     ▼                   ▼
    ┌─────────────┐    ┌──────────────┐   ┌──────────────┐
    │  Language   │    │  Language    │   │  Vision LLM  │
    │  Detection  │    │  Detection   │   │  Analysis    │
    │  (langid)   │    │              │   │  (Gemma 4b)  │
    └───┬─────────┘    └──────┬───────┘   └──────┬───────┘
        │                     │                   │
        │                     │                   │
        ▼                     ▼                   ▼
    ┌─────────────┐    ┌──────────────┐   ┌──────────────┐
    │ Translation │    │ Translation  │   │ Translation  │
    │ (if needed) │    │ (if Hindi)   │   │ (if needed)  │
    │   m2m100    │    │   m2m100     │   │              │
    └───┬─────────┘    └──────┬───────┘   └──────┬───────┘
        │                     │                   │
        └─────────────────────┼───────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  TEXT EXTRACTED  │
                    │   (English)      │
                    └────────┬─────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         CHUNKING PHASE                                    │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────┐           │
│  │  RecursiveCharacterTextSplitter                           │           │
│  │  ┌────────────────────────────────────────────────────┐   │           │
│  │  │  chunk_size = 2000                                 │   │           │
│  │  │  chunk_overlap = 100                               │   │           │
│  │  │  separators = ["\n\n", "\n", ". ", " ", ""]       │   │           │
│  │  └────────────────────────────────────────────────────┘   │           │
│  └──────────────────────────────────────────────────────────┘           │
│                                                                           │
│  Input:  "Long text document with 10,000 characters..."                  │
│  Output: [Chunk1, Chunk2, Chunk3, Chunk4, Chunk5]                        │
│                                                                           │
└────────────────────────────────┬──────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                      EMBEDDING GENERATION                                 │
│                                                                           │
│  For EACH chunk:                                                          │
│                                                                           │
│  ┌────────────────────────────────────────────────────────┐              │
│  │  Chunk 1: "Police received a call at 3pm..."           │              │
│  │           ↓                                             │              │
│  │  OllamaEmbeddings (embeddinggemma:latest)              │              │
│  │           ↓                                             │              │
│  │  Vector: [0.12, 0.45, -0.23, 0.67, ..., 0.89]         │              │
│  │           (768 dimensions)                              │              │
│  └────────────────────────────────────────────────────────┘              │
│                                                                           │
│  ┌────────────────────────────────────────────────────────┐              │
│  │  Chunk 2: "Officers arrived at the scene..."           │              │
│  │           ↓                                             │              │
│  │  Vector: [0.15, 0.43, -0.21, 0.65, ..., 0.87]         │              │
│  └────────────────────────────────────────────────────────┘              │
│                                                                           │
│  ... (continues for all chunks)                                           │
│                                                                           │
└────────────────────────────────┬──────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    DATABASE STORAGE (AlloyDB/PostgreSQL)                  │
│                                                                           │
│  document_chunks table:                                                   │
│  ┌────┬───────────┬────────┬─────────────────────┬──────────────┐       │
│  │ id │ doc_id    │ index  │ chunk_text          │ embedding    │       │
│  ├────┼───────────┼────────┼─────────────────────┼──────────────┤       │
│  │ 1  │ 123       │ 0      │ "Police received.." │ [0.12, ...]  │       │
│  │ 2  │ 123       │ 1      │ "Officers arrived"  │ [0.15, ...]  │       │
│  │ 3  │ 123       │ 2      │ "Witnesses stated"  │ [0.18, ...]  │       │
│  │ 4  │ 123       │ 3      │ "Evidence found.."  │ [0.21, ...]  │       │
│  │ 5  │ 123       │ 4      │ "Investigation.."   │ [0.24, ...]  │       │
│  └────┴───────────┴────────┴─────────────────────┴──────────────┘       │
│                                                                           │
│  ✅ Indexed with pgvector for fast similarity search                     │
│  ✅ Ready for semantic queries                                            │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

## Search Query Flow

```
┌─────────────────────────────────────────────────────────────┐
│  USER QUERY: "What time did the incident occur?"            │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
                ┌────────────────────────────┐
                │  Embed Query Text          │
                │  (OllamaEmbeddings)        │
                └────────┬───────────────────┘
                         │
                         ▼
                ┌────────────────────────────┐
                │ Query Vector:              │
                │ [0.14, 0.44, -0.22, ...]  │
                └────────┬───────────────────┘
                         │
                         ▼
        ┌────────────────────────────────────────┐
        │  Vector Similarity Search              │
        │  (PostgreSQL + pgvector)               │
        │                                        │
        │  SELECT chunk_text, embedding          │
        │  FROM document_chunks                  │
        │  ORDER BY embedding <=> query_vector   │
        │  LIMIT 5;                              │
        └────────┬───────────────────────────────┘
                 │
                 ▼
        ┌─────────────────────────────────────────┐
        │  Top 5 Most Similar Chunks:             │
        │                                         │
        │  1. "...call received at 3:15 PM..."    │
        │     Similarity: 0.92                    │
        │                                         │
        │  2. "...incident occurred at 3pm..."    │
        │     Similarity: 0.89                    │
        │                                         │
        │  3. "...time of arrival was 15:20..."   │
        │     Similarity: 0.85                    │
        │                                         │
        │  4. "...officers responded at 3:10..."  │
        │     Similarity: 0.82                    │
        │                                         │
        │  5. "...dispatch logged call at 3pm..." │
        │     Similarity: 0.80                    │
        └─────────┬───────────────────────────────┘
                  │
                  ▼
        ┌──────────────────────────────┐
        │  Return Results to User      │
        │  + Generate AI Response      │
        └──────────────────────────────┘
```

## Detailed Chunking Process

```
Original Text (10,000 characters)
═══════════════════════════════════════════════════════════════

"On October 31, 2024, police received a distress call at 3:15 PM 
regarding a suspicious activity in the downtown area. Officers 
arrived at the scene within 10 minutes and secured the perimeter.
Multiple witnesses were interviewed, and preliminary evidence was 
collected. The investigation is ongoing, and authorities are 
requesting anyone with additional information to come forward..."

                        ↓

RecursiveCharacterTextSplitter
• chunk_size = 2000
• chunk_overlap = 100
• Try separators in order: ["\n\n", "\n", ". ", " ", ""]

                        ↓

┌───────────────────────────────────────────────────────────┐
│ Chunk 0 (2000 chars)                                      │
│ Index: 0-1999                                             │
│ ─────────────────────────────────────────────────────── │
│ "On October 31, 2024, police received a distress call   │
│ at 3:15 PM regarding a suspicious activity in the       │
│ downtown area. Officers arrived at the scene within     │
│ 10 minutes and secured the perimeter. Multiple          │
│ witnesses were interviewed, and preliminary evidence... │
│ [continues for 2000 characters]                          │
└───────────────────────────────────────────────────────────┘
                        ↓
                [100 char overlap]
                        ↓
┌───────────────────────────────────────────────────────────┐
│ Chunk 1 (2000 chars)                                      │
│ Index: 1900-3899                                          │
│ ─────────────────────────────────────────────────────── │
│ "...preliminary evidence was collected. The              │
│ investigation is ongoing, and authorities are            │
│ requesting anyone with additional information to         │
│ come forward. Several surveillance cameras in the        │
│ area captured footage that is currently being analyzed...│
│ [continues for 2000 characters]                          │
└───────────────────────────────────────────────────────────┘
                        ↓
                [100 char overlap]
                        ↓
┌───────────────────────────────────────────────────────────┐
│ Chunk 2 (2000 chars)                                      │
│ Index: 3800-5799                                          │
│ ─────────────────────────────────────────────────────── │
│ "...footage that is currently being analyzed. A          │
│ detailed description of the suspect was provided by      │
│ witnesses. The suspect is described as approximately     │
│ 5'10" tall, wearing dark clothing and a baseball cap...  │
│ [continues for 2000 characters]                          │
└───────────────────────────────────────────────────────────┘
                        ↓
                    [continues...]
                        ↓
┌───────────────────────────────────────────────────────────┐
│ Chunk 4 (1500 chars) - Final chunk                        │
│ Index: 8500-10000                                         │
│ ─────────────────────────────────────────────────────── │
│ "...The police department has increased patrols in the   │
│ area as a precautionary measure. Residents are advised   │
│ to remain vigilant and report any suspicious activity    │
│ immediately. The investigation continues."                │
└───────────────────────────────────────────────────────────┘

Result: 5 chunks created from 10,000 character document
Each chunk maintains context through 100-character overlap
```

## Embedding Vector Visualization

```
Text Chunk: "Police arrived at the scene"
                    ↓
            OllamaEmbeddings
         (embeddinggemma:latest)
                    ↓
    ┌───────────────────────────────────┐
    │  768-Dimensional Vector           │
    │                                   │
    │  [0.123, 0.456, -0.234, 0.678,   │
    │   0.901, -0.123, 0.345, 0.567,   │
    │   ...,                            │
    │   0.789, 0.234, -0.567, 0.890]   │
    │                                   │
    │  Each number captures semantic    │
    │  meaning of the text              │
    └───────────────────────────────────┘

Similar Texts = Similar Vectors

"Police arrived at the scene"     → [0.12, 0.45, -0.23, ...]
"Officers reached the location"   → [0.14, 0.43, -0.21, ...]  ← Close!
"Law enforcement arrived"         → [0.13, 0.44, -0.22, ...]  ← Close!
"Sunny day at the beach"          → [-0.67, 0.89, 0.34, ...]  ← Far!
```

## Multi-Format Processing Comparison

```
┌─────────────┬──────────────┬──────────────┬──────────────┐
│   Format    │  Extraction  │  Processing  │   Chunking   │
├─────────────┼──────────────┼──────────────┼──────────────┤
│   PDF       │  Docling     │  OCR if      │  2000 char   │
│   DOCX      │  + OCR       │  image-based │  chunks      │
│   TXT       │              │  + translate │  100 overlap │
│             │              │  if needed   │              │
├─────────────┼──────────────┼──────────────┼──────────────┤
│   MP3       │  Gemini/     │  Transcribe  │  2000 char   │
│   WAV       │  Gemma       │  → translate │  chunks of   │
│   M4A       │  Audio API   │  if Hindi    │  transcript  │
├─────────────┼──────────────┼──────────────┼──────────────┤
│   MP4       │  Frame       │  Vision LLM  │  2000 char   │
│   AVI       │  extraction  │  analysis    │  chunks of   │
│   MOV       │  (0.3 fps)   │  → describe  │  description │
└─────────────┴──────────────┴──────────────┴──────────────┘

All formats converge to TEXT → CHUNKS → EMBEDDINGS
```

## Performance Timeline

```
Upload Document (incident_report.pdf - 5 pages, 10,000 chars)
│
├─ [0s - 3s]    File upload and validation
│
├─ [3s - 8s]    Text extraction (Docling + OCR)
│                • Page scanning
│                • OCR processing
│                • Text assembly
│
├─ [8s - 9s]    Language detection
│                • Analyze text sample
│                • Determine if translation needed
│
├─ [9s - 15s]   Translation (if needed)
│                • m2m100 model
│                • Sentence-by-sentence
│
├─ [15s - 20s]  Summarization
│                • LLM generates summary
│                • 200 word limit
│
├─ [20s - 21s]  Chunking
│                • RecursiveCharacterTextSplitter
│                • Creates 5 chunks
│
├─ [21s - 24s]  Embedding Generation
│                • 5 chunks × ~0.5s each
│                • embeddinggemma model
│                • 768-dim vectors
│
├─ [24s - 25s]  Database Storage
│                • Insert chunks
│                • Store embeddings
│                • Create indexes
│
└─ [25s]        ✅ COMPLETE - Ready for search!

Total: ~25 seconds for 5-page PDF
```

## Storage Structure

```
┌────────────────────────────────────────────────────────────┐
│                     PostgreSQL Database                     │
│                     (with pgvector extension)               │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  documents                        document_chunks          │
│  ┌────────────────┐               ┌──────────────────┐    │
│  │ id: 123        │◄──────────────│ document_id: 123 │    │
│  │ filename       │               │ chunk_index: 0   │    │
│  │ file_type      │               │ chunk_text       │    │
│  │ gcs_path       │               │ embedding (vector)│   │
│  │ summary        │               └──────────────────┘    │
│  └────────────────┘                        │               │
│                                             │               │
│                                    ┌──────────────────┐    │
│                                    │ document_id: 123 │    │
│                                    │ chunk_index: 1   │    │
│                                    │ chunk_text       │    │
│                                    │ embedding (vector)│   │
│                                    └──────────────────┘    │
│                                             │               │
│                                    ┌──────────────────┐    │
│                                    │ document_id: 123 │    │
│                                    │ chunk_index: 2   │    │
│                                    │ chunk_text       │    │
│                                    │ embedding (vector)│   │
│                                    └──────────────────┘    │
│                                                             │
│  Index: CREATE INDEX ON document_chunks                    │
│         USING ivfflat (embedding vector_cosine_ops)        │
│         ↑                                                   │
│         └─ Enables fast similarity search O(log n)         │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

## Key Takeaways

1. **One Process**: All file types → Text → Chunks → Embeddings → Storage
2. **Chunking**: Smart splitting with overlap to preserve context
3. **Embeddings**: Semantic vectors enable intelligent search
4. **Storage**: PostgreSQL + pgvector for fast retrieval
5. **Performance**: ~25s for 5-page document, <100ms for search

---

For detailed explanations, see:
- [CHUNKING_AND_EMBEDDINGS_GUIDE.md](../CHUNKING_AND_EMBEDDINGS_GUIDE.md)
- [CHUNKING_QUICK_REFERENCE.md](./CHUNKING_QUICK_REFERENCE.md)
