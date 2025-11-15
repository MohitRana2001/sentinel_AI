# Documentation Index

Welcome to the Sentinel AI documentation! This index will help you find the information you need.

## 📚 Complete Documentation

### Core Concepts

#### [Chunking and Embeddings Guide](../CHUNKING_AND_EMBEDDINGS_GUIDE.md) 📖
**Comprehensive technical guide** explaining how Sentinel AI processes files and makes them searchable.

**Topics covered:**
- Architecture overview
- Chunking process and strategies
- Embedding generation
- Processing pipelines by file type (documents, audio, video)
- Vector storage and retrieval
- Configuration options
- Performance considerations
- Troubleshooting
- Code examples

**Best for:** Developers who need deep understanding of the system

**Length:** ~30 minutes read

---

#### [Chunking Quick Reference](./CHUNKING_QUICK_REFERENCE.md) ⚡
**Fast lookup guide** with essential information in a concise format.

**Topics covered:**
- TL;DR overview
- Simple examples
- Key files and schema
- Configuration quick reference
- Common operations
- Troubleshooting table
- Performance metrics

**Best for:** Quick lookups during development

**Length:** ~5 minutes read

---

### System Components

#### [Storage Configuration Guide](../backend/storage/README.md) 🗄️
Guide to the configurable storage system supporting GCS, S3, Local, and Azure backends.

**Topics covered:**
- Quick start
- Backend configuration
- Migration from legacy code
- Adding custom backends
- Troubleshooting

**Best for:** DevOps and deployment

---

#### [Redis Pub/Sub Architecture](../redis_pubsub_diagram.md) 🔄
Overview of the queue-based parallel processing system.

**Topics covered:**
- Queue architecture
- Worker distribution
- Job processing flow

**Best for:** Understanding the processing pipeline

---

## 🎯 By Use Case

### I want to understand how files are processed
→ Start with **[Quick Reference](./CHUNKING_QUICK_REFERENCE.md)**  
→ Then read **[Full Guide](../CHUNKING_AND_EMBEDDINGS_GUIDE.md)** for details

### I want to configure the system
→ Read **[Quick Reference - Configuration](./CHUNKING_QUICK_REFERENCE.md#configuration-quick-reference)**  
→ Check **[Full Guide - Configuration](../CHUNKING_AND_EMBEDDINGS_GUIDE.md#configuration-options)**

### I need to troubleshoot issues
→ Check **[Quick Reference - Troubleshooting](./CHUNKING_QUICK_REFERENCE.md#troubleshooting)**  
→ Review **[Full Guide - Troubleshooting](../CHUNKING_AND_EMBEDDINGS_GUIDE.md#troubleshooting)**

### I want to deploy the system
→ Read **[Storage Guide](../backend/storage/README.md)**  
→ Configure environment variables in `.env`

### I want to understand the code
→ Review **[Full Guide - Code Examples](../CHUNKING_AND_EMBEDDINGS_GUIDE.md#code-examples)**  
→ Check the key files listed in **[Quick Reference](./CHUNKING_QUICK_REFERENCE.md#key-files)**

---

## 📂 File Structure

```
sentinel_AI/
├── README.md                              # Main project README
├── CHUNKING_AND_EMBEDDINGS_GUIDE.md      # Complete chunking/embedding guide
├── docs/
│   ├── INDEX.md                          # This file
│   └── CHUNKING_QUICK_REFERENCE.md       # Quick reference
├── backend/
│   ├── vector_store.py                   # Core chunking & embedding
│   ├── document_processor.py             # Document processing
│   ├── processors/
│   │   ├── document_processor_service.py # Document pipeline
│   │   ├── audio_processor_service.py    # Audio pipeline
│   │   └── video_processor_service.py    # Video pipeline
│   └── storage/
│       └── README.md                     # Storage system guide
└── redis_pubsub_diagram.md               # Queue architecture
```

---

## 🚀 Quick Navigation

### For New Developers
1. Read [README.md](../README.md) - Project overview
2. Skim [Quick Reference](./CHUNKING_QUICK_REFERENCE.md) - Core concepts
3. Explore code with [Full Guide](../CHUNKING_AND_EMBEDDINGS_GUIDE.md) - Deep dive

### For DevOps/Deployment
1. Read [Storage Guide](../backend/storage/README.md) - Setup storage
2. Configure `.env` using [Quick Reference](./CHUNKING_QUICK_REFERENCE.md#configuration-quick-reference)
3. Review [Full Guide - Performance](../CHUNKING_AND_EMBEDDINGS_GUIDE.md#performance-considerations)

### For Integrators
1. Check [Quick Reference - Key Files](./CHUNKING_QUICK_REFERENCE.md#key-files)
2. Review [Full Guide - Code Examples](../CHUNKING_AND_EMBEDDINGS_GUIDE.md#code-examples)
3. Test with [Quick Reference - Common Operations](./CHUNKING_QUICK_REFERENCE.md#common-operations)

---

## 🔗 External Resources

### LangChain
- [Text Splitters](https://python.langchain.com/docs/modules/data_connection/document_transformers/)
- [Embeddings](https://python.langchain.com/docs/modules/data_connection/text_embedding/)

### Ollama
- [Embedding Models](https://ollama.ai/library)
- [API Documentation](https://github.com/ollama/ollama/blob/main/docs/api.md)

### pgvector
- [GitHub Repository](https://github.com/pgvector/pgvector)
- [PostgreSQL Extension](https://www.postgresql.org/about/news/pgvector-050-released-2865/)

### Docling
- [GitHub Repository](https://github.com/DS4SD/docling)
- [Documentation](https://ds4sd.github.io/docling/)

---

## 📝 Contributing to Documentation

Found an error or want to improve the docs?

1. Fork the repository
2. Edit the relevant markdown file
3. Submit a pull request

**Documentation files:**
- Main guide: `CHUNKING_AND_EMBEDDINGS_GUIDE.md`
- Quick reference: `docs/CHUNKING_QUICK_REFERENCE.md`
- This index: `docs/INDEX.md`

---

## 💡 Tips

- 📖 **Complete guide** = ~30 min read, comprehensive understanding
- ⚡ **Quick reference** = ~5 min read, fast lookups
- 🎯 **Use search** (Ctrl+F) in documents for specific topics
- 🔄 **Code examples** are in both guides
- 📊 **Architecture diagrams** are in the complete guide
- 🛠️ **Configuration** details are in both guides

---

**Last Updated:** November 2024  
**Maintained By:** Sentinel AI Team
