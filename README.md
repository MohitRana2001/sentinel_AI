# Sentinel AI - Edge Inference Document Analysis System

A production-ready document analysis and semantic search system designed for edge deployment with multi-format support (documents, audio, video) and intelligent text processing.

## 📚 Documentation

### Core Features
- **Multi-format Processing**: PDF, DOCX, TXT, MP3, WAV, MP4, AVI, MOV
- **Intelligent Text Extraction**: OCR with Tesseract, Docling for documents
- **Multi-language Support**: Auto-detection and translation (Hindi, Bengali, Tamil, Telugu, etc.)
- **Semantic Search**: Vector embeddings with pgvector
- **Knowledge Graphs**: Neo4j for entity relationships
- **RBAC**: Role-based access control (Admin, Manager, Analyst)

### Technical Documentation

#### Chunking & Embeddings
- 📖 **[Chunking and Embeddings Guide](./CHUNKING_AND_EMBEDDINGS_GUIDE.md)** - Complete technical explanation
  - How text is broken into chunks
  - Embedding generation process
  - Processing pipelines for documents, audio, and video
  - Vector storage and retrieval
  - Configuration and optimization
  
- ⚡ **[Quick Reference](./docs/CHUNKING_QUICK_REFERENCE.md)** - Fast lookup for developers
  - TL;DR overview
  - Configuration options
  - Common operations
  - Troubleshooting

#### Storage
- 🗄️ **[Storage Configuration Guide](./backend/storage/README.md)** - Multi-backend storage system
  - GCS, S3, Local, Azure support
  - Configuration examples
  - Migration guide

#### Architecture
- 🔄 **[Redis Pub/Sub Diagram](./redis_pubsub_diagram.md)** - Queue-based processing

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Ollama (for embeddings and LLMs)
- PostgreSQL with pgvector (or SQLite for development)
- Neo4j (for knowledge graphs)
- Redis (for job queuing)

### Installation

```bash
# Clone repository
git clone https://github.com/MohitRana2001/sentinel_AI.git
cd sentinel_AI

# Copy environment template
cp .env.example .env

# Edit configuration
nano .env

# Start services
docker-compose up -d
```

### Configuration

Key environment variables in `.env`:

```bash
# Chunking & Embeddings
CHUNK_SIZE=2000                      # Text chunk size
CHUNK_OVERLAP=100                    # Overlap between chunks
EMBEDDING_MODEL=embeddinggemma:latest

# Storage Backend
STORAGE_BACKEND=gcs                  # Options: gcs, s3, local
GCS_BUCKET_NAME=your-bucket

# Database
ALLOYDB_HOST=localhost
ALLOYDB_DATABASE=sentinel_db
USE_SQLITE_FOR_DEV=true              # For local development

# LLM Models
SUMMARY_LLM_MODEL=gemma3:1b
MULTIMODAL_LLM_MODEL=gemma3:12b
```

## 📦 Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                    │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              FastAPI Backend (main.py)                   │
│  • File Upload API                                       │
│  • Chat/Query API                                        │
│  • RBAC & Authentication                                 │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│                Redis Queue System                        │
│  • Parallel processing of multiple files                │
│  • Separate queues for document/audio/video             │
└───┬──────────────────┬──────────────────┬───────────────┘
    │                  │                  │
    ▼                  ▼                  ▼
┌─────────┐      ┌──────────┐      ┌──────────┐
│Document │      │  Audio   │      │  Video   │
│Processor│      │Processor │      │Processor │
└────┬────┘      └─────┬────┘      └─────┬────┘
     │                 │                  │
     └─────────────────┼──────────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │    Chunking & Embeddings     │
        │  • Split text into chunks     │
        │  • Generate vector embeddings │
        └──────────────┬───────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │      Vector Store (AlloyDB)   │
        │  • PostgreSQL + pgvector      │
        │  • Semantic search            │
        └──────────────────────────────┘
```

## 🔧 Key Components

### Processing Services

- **Document Processor** (`processors/document_processor_service.py`)
  - PDF/DOCX/TXT extraction with Docling
  - OCR support with Tesseract
  - Language detection and translation
  
- **Audio Processor** (`processors/audio_processor_service.py`)
  - Audio transcription (Gemini/Gemma)
  - Hindi/English support
  - Transcription chunking

- **Video Processor** (`processors/video_processor_service.py`)
  - Frame extraction (1 per 3 seconds)
  - Vision model analysis
  - Scene description generation

- **Graph Processor** (`processors/graph_processor_service.py`)
  - Entity extraction
  - Relationship mapping
  - Neo4j knowledge graph

### Core Modules

- **Vector Store** (`vector_store.py`)
  - Chunking with RecursiveCharacterTextSplitter
  - Embedding generation with Ollama
  - Similarity search with pgvector
  
- **Storage System** (`storage/`)
  - Multi-backend support (GCS, S3, Local)
  - Automatic fallback
  - Production-ready

## 🎯 Use Cases

- **Law Enforcement**: CCTV footage analysis, incident reports
- **Document Analysis**: Multi-format document processing
- **Semantic Search**: Natural language queries across all content
- **Knowledge Extraction**: Entity and relationship discovery
- **Multi-language**: Automatic translation and processing

## 🔍 How Chunking & Embeddings Work

When you upload a file:

1. **Text Extraction**: OCR, transcription, or vision analysis
2. **Chunking**: Text split into 2000-character chunks with 100-char overlap
3. **Embedding**: Each chunk converted to 768-dimensional vector
4. **Storage**: Vectors stored in PostgreSQL with pgvector
5. **Search**: User queries matched with semantic similarity

**Example**:
```python
# User uploads report.pdf (10,000 chars)
# System creates 5 chunks
# Each chunk → embedding vector [0.12, 0.45, -0.23, ...]
# User queries "What time did incident occur?"
# System finds most similar chunks and returns relevant text
```

📖 **[Read the full guide](./CHUNKING_AND_EMBEDDINGS_GUIDE.md)** for complete details.

## 🛠️ Development

### Running Locally

```bash
# Backend
cd backend
pip install -r requirements.txt
python main.py

# Frontend
npm install
npm run dev
```

### Running with Docker

```bash
docker-compose up -d
```

### Testing

```bash
# Unit tests
pytest backend/tests/

# Integration tests
pytest backend/tests/integration/
```

## 📊 Performance

- **Chunking**: ~0.1s per 10,000 characters
- **Embedding**: ~0.5s per chunk
- **Search**: <100ms for top 5 results
- **Storage**: ~3KB per chunk (embeddings)

## 🤝 Contributing

Contributions are welcome! Please read the documentation before contributing:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

[Add your license information here]

## 🆘 Support

- 📖 [Chunking & Embeddings Guide](./CHUNKING_AND_EMBEDDINGS_GUIDE.md)
- ⚡ [Quick Reference](./docs/CHUNKING_QUICK_REFERENCE.md)
- 🗄️ [Storage Guide](./backend/storage/README.md)

## 🙏 Acknowledgments

Built with:
- [LangChain](https://python.langchain.com/) - Text processing
- [Docling](https://github.com/DS4SD/docling) - Document extraction
- [Ollama](https://ollama.ai/) - Local LLM inference
- [pgvector](https://github.com/pgvector/pgvector) - Vector similarity search
- [Neo4j](https://neo4j.com/) - Knowledge graphs
- [FastAPI](https://fastapi.tiangolo.com/) - Backend framework
- [Next.js](https://nextjs.org/) - Frontend framework

---

**Made with ❤️ for intelligent document analysis at the edge**
