# Sentinel AI Documentation Index

Welcome to the Sentinel AI documentation. This index will help you find the information you need.

## 📚 Documentation Files

### Getting Started
- **[QUICKSTART.md](QUICKSTART.md)** - Start here! Quick setup guide for both development and production modes
  - Get running in under 10 minutes
  - Includes test commands for all file types
  - Common setup issues and solutions

### Core Documentation
- **[README.md](README.md)** - Complete system documentation
  - Architecture overview
  - Processing flows for all file types
  - Language support (11 languages)
  - Model configuration (Gemini vs Gemma)
  - Deployment instructions
  - Troubleshooting guide

### Detailed Technical Documentation
- **[PROCESS_FLOW.md](PROCESS_FLOW.md)** - Detailed process flow diagrams
  - Mermaid flowcharts for each scenario
  - Document processing (English vs Hindi)
  - Audio processing flows
  - Video processing flows
  - Graph extraction flows
  - Model selection decision trees
  - Error handling patterns

- **[REDIS_QUEUE_SYSTEM.md](REDIS_QUEUE_SYSTEM.md)** - Queue architecture
  - Why queues over pub/sub
  - Queue implementation details
  - Scaling workers
  - Distributed locking
  - Monitoring commands

### Troubleshooting
- **[TROUBLESHOOTING_HINDI_PDF.md](TROUBLESHOOTING_HINDI_PDF.md)** - Specific guide for queue behavior
  - Explains "immediate processing" behavior
  - Verification steps
  - Diagnostic commands
  - Performance benchmarks
  - Common misunderstandings

## 🎯 Quick Navigation by Use Case

### "I want to set up Sentinel AI"
→ Start with [QUICKSTART.md](QUICKSTART.md)

### "I want to understand how it works"
→ Read [README.md](README.md) Architecture section

### "I want to see detailed process flows"
→ Check [PROCESS_FLOW.md](PROCESS_FLOW.md)

### "I have a specific issue"
→ Look in [README.md](README.md) Troubleshooting section or [TROUBLESHOOTING_HINDI_PDF.md](TROUBLESHOOTING_HINDI_PDF.md)

### "I want to understand Redis queues"
→ See [REDIS_QUEUE_SYSTEM.md](REDIS_QUEUE_SYSTEM.md)

### "I want to know which models are used"
→ Read [README.md](README.md) Model Configuration section

## 📖 Documentation Structure

```
sentinel_AI/
├── README.md                      # Main documentation (start here after quickstart)
├── QUICKSTART.md                  # Setup guide (start here first)
├── PROCESS_FLOW.md                # Detailed technical flows
├── REDIS_QUEUE_SYSTEM.md          # Queue architecture details
├── TROUBLESHOOTING_HINDI_PDF.md   # Queue behavior troubleshooting
└── DOCUMENTATION_INDEX.md         # This file
```

## 🔍 Finding Information

### File Types Supported
- See [README.md](README.md#processing-flow) - Document/Audio/Video sections

### Language Support
- See [README.md](README.md#language-support) - Complete language list with translation support

### File Naming Conventions
- See [README.md](README.md#file-naming-conventions) - Explanation of --, ---, ==, === prefixes
- See [PROCESS_FLOW.md](PROCESS_FLOW.md#summary-of-key-differences) - Quick reference table

### Model Configuration
- See [README.md](README.md#model-configuration) - Gemini vs Gemma, dev vs production
- See [PROCESS_FLOW.md](PROCESS_FLOW.md#model-selection-decision-trees) - Decision trees

### Scaling Workers
- See [REDIS_QUEUE_SYSTEM.md](REDIS_QUEUE_SYSTEM.md#scaling-workers) - Docker Compose scaling
- See [README.md](README.md#deployment) - Production deployment

### API Documentation
- Interactive docs: http://localhost:8000/api/v1/docs (when running)

## 🐛 Common Issues

| Issue | Documentation |
|-------|--------------|
| "Hindi PDF not being queued" | [TROUBLESHOOTING_HINDI_PDF.md](TROUBLESHOOTING_HINDI_PDF.md) |
| "OCR returns empty text" | [README.md](README.md#issue-ocr-not-extracting-text) |
| "Translation fails" | [README.md](README.md#issue-translation-fails) |
| "Workers not scaling" | [README.md](README.md#issue-workers-not-scaling) |
| "Gemini API errors" | [README.md](README.md#issue-gemini-api-errors) |
| "Graph processing stuck" | [README.md](README.md#issue-graph-processing-stuck) |

## 📊 Process Flow Examples

### English PDF
```
Upload → Store → Queue → OCR → Summary → Store → Graph
See: PROCESS_FLOW.md#english-pdf-processing
```

### Hindi PDF
```
Upload → Store → Queue → OCR → Detect Language → Translate → Summary → Store → Graph
See: PROCESS_FLOW.md#hindi-pdf-processing
```

### Audio
```
Upload → Store → Queue → Transcribe → Translate (if Hindi) → Summary → Store → Graph
See: PROCESS_FLOW.md#audio-processing-flows
```

### Video
```
Upload → Store → Queue → Extract Frames → Vision Analysis → Translate (if Hindi) → Summary → Store → Graph
See: PROCESS_FLOW.md#video-processing-flows
```

## 🔧 Development vs Production

| Aspect | Development | Production |
|--------|-------------|------------|
| Setup Guide | [QUICKSTART.md](QUICKSTART.md#option-1-development-mode-easiest) | [QUICKSTART.md](QUICKSTART.md#option-2-production-mode-docker-compose) |
| LLM Backend | Gemini API | Ollama (Gemma) |
| Database | SQLite | PostgreSQL/AlloyDB |
| Storage | Local | GCS/Local |
| Configuration | [README.md](README.md#development-mode-use_gemini_for_devtrue) | [README.md](README.md#production-mode-edge-inference) |

## 🎓 Learning Path

**Beginner**:
1. [QUICKSTART.md](QUICKSTART.md) - Get it running
2. [README.md](README.md) Overview section - Understand what it does
3. Test with sample files following QUICKSTART examples

**Intermediate**:
1. [README.md](README.md) Architecture section - Understand components
2. [PROCESS_FLOW.md](PROCESS_FLOW.md) - See detailed flows
3. [REDIS_QUEUE_SYSTEM.md](REDIS_QUEUE_SYSTEM.md) - Understand queue system

**Advanced**:
1. [PROCESS_FLOW.md](PROCESS_FLOW.md) Error Handling section - Handle failures
2. [README.md](README.md) Model Configuration - Optimize models
3. Source code in `backend/` directory - Modify and extend

## 📝 Additional Resources

- **API Documentation**: http://localhost:8000/api/v1/docs (when server running)
- **Storage Backend**: `backend/storage/README.md` - Configurable storage system
- **GitHub Repository**: https://github.com/MohitRana2001/sentinel_AI
- **Issues & Support**: https://github.com/MohitRana2001/sentinel_AI/issues

## 🔄 Documentation Updates

This documentation was last updated: **2025-11-06**

Version: **1.0.0**

---

**Ready to get started?** → [QUICKSTART.md](QUICKSTART.md)
