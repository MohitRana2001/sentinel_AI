# Quick Start Guide - Sentinel AI

Get Sentinel AI up and running in under 10 minutes.

## Prerequisites

- Docker & Docker Compose
- 8GB+ RAM
- 20GB+ disk space
- (Optional) Gemini API key for dev mode

## Option 1: Development Mode (Easiest)

Uses Google Gemini API for processing. No local GPU required.

### 1. Get Gemini API Key

Visit https://ai.google.dev/ and get a free API key.

### 2. Clone & Configure

```bash
git clone https://github.com/MohitRana2001/sentinel_AI.git
cd sentinel_AI

# Create .env file
cp .env.example .env

# Edit .env and set:
nano .env
```

```bash
# Development Mode
USE_GEMINI_FOR_DEV=true
GEMINI_API_KEY=your_api_key_here

# Database (SQLite for dev)
USE_SQLITE_FOR_DEV=true
SQLITE_DB_PATH=./sentinel_dev.db

# Storage (Local for dev)
STORAGE_BACKEND=local
LOCAL_STORAGE_PATH=./.local_storage

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# Neo4j (optional for graphs)
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password

# Admin signup
ADMIN_SIGNUP_SECRET=your_secret_here
SECRET_KEY=your_secret_key_here
```

### 3. Start Services

```bash
# Start Redis
docker run -d -p 6379:6379 redis:latest

# (Optional) Start Neo4j
docker run -d -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/your_password \
  neo4j:latest

# Install Python dependencies
cd backend
pip install -r requirements.txt

# Install Tesseract with Hindi support
# Ubuntu/Debian:
sudo apt-get install tesseract-ocr tesseract-ocr-hin tesseract-ocr-ben \
                     tesseract-ocr-pan tesseract-ocr-guj tesseract-ocr-kan \
                     tesseract-ocr-mal tesseract-ocr-mar tesseract-ocr-tam \
                     tesseract-ocr-tel

# macOS:
brew install tesseract tesseract-lang

# Set Tesseract data path
export TESSDATA_PREFIX=/usr/share/tesseract-ocr/5.00/tessdata
```

### 4. Start Workers & API

Open 5 terminals:

**Terminal 1 - API**:
```bash
cd backend
python main.py
```

**Terminal 2 - Document Worker**:
```bash
cd backend
python processors/document_processor_service.py
```

**Terminal 3 - Audio Worker**:
```bash
cd backend
python processors/audio_processor_service.py
```

**Terminal 4 - Video Worker**:
```bash
cd backend
python processors/video_processor_service.py
```

**Terminal 5 - Graph Worker**:
```bash
cd backend
python processors/graph_processor_service.py
```

### 5. Create Admin User

```bash
curl -X POST http://localhost:8000/api/v1/admin/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "username": "admin",
    "password": "adminpass123",
    "secret_key": "your_secret_here"
  }'
```

### 6. Get Auth Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=admin&password=adminpass123"

# Save the access_token from response
export TOKEN="your_access_token_here"
```

### 7. Upload a Test File

```bash
# Upload English PDF
curl -X POST http://localhost:8000/api/v1/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "files=@test.pdf"

# Response will include job_id
# {"job_id": "admin/admin/uuid-123", "status": "queued", ...}
```

### 8. Check Processing Status

```bash
# Poll status
curl http://localhost:8000/api/v1/jobs/admin/admin/uuid-123/status \
  -H "Authorization: Bearer $TOKEN"

# Get results when completed
curl http://localhost:8000/api/v1/jobs/admin/admin/uuid-123/results \
  -H "Authorization: Bearer $TOKEN"
```

### 9. Access API Documentation

Open browser: http://localhost:8000/api/v1/docs

## Option 2: Production Mode (Docker Compose)

Uses local Ollama models for inference. Requires GPU for best performance.

### 1. Configure Environment

```bash
git clone https://github.com/MohitRana2001/sentinel_AI.git
cd sentinel_AI

# Copy and edit .env
cp .env.example .env
nano .env
```

```bash
# Production Mode
USE_GEMINI_FOR_DEV=false

# Database (PostgreSQL for production)
USE_SQLITE_FOR_DEV=false
ALLOYDB_HOST=postgres
ALLOYDB_PORT=5432
ALLOYDB_USER=postgres
ALLOYDB_PASSWORD=your_password
ALLOYDB_DATABASE=sentinel_db

# Storage (GCS for production, or local for testing)
STORAGE_BACKEND=local
LOCAL_STORAGE_PATH=/app/storage

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Neo4j
NEO4J_URI=bolt://neo4j:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password

# LLM Configuration (will use Ollama)
SUMMARY_LLM_HOST=ollama
SUMMARY_LLM_PORT=11434
SUMMARY_LLM_MODEL=gemma3:1b

CHAT_LLM_HOST=ollama
CHAT_LLM_PORT=11436
CHAT_LLM_MODEL=gemma3:1b

MULTIMODAL_LLM_HOST=ollama
MULTIMODAL_LLM_PORT=11437
MULTIMODAL_LLM_MODEL=gemma3:12b

EMBEDDING_LLM_HOST=ollama
EMBEDDING_LLM_PORT=11434
EMBEDDING_MODEL=embeddinggemma:latest
```

### 2. Start with Docker Compose

```bash
# Build and start all services
docker-compose up -d

# Check logs
docker-compose logs -f

# Scale workers if needed
docker-compose up -d --scale document-processor=3
```

### 3. Install Ollama Models

```bash
# Connect to Ollama container
docker-compose exec ollama bash

# Pull models
ollama pull gemma3:1b
ollama pull gemma3:4b
ollama pull gemma3:12b
ollama pull embeddinggemma:latest

exit
```

### 4. Create Admin & Test

Same as steps 5-9 in Development Mode, but use `docker-compose exec api` for commands.

## Testing Different Scenarios

### Test 1: English Document

```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "files=@english_report.pdf"
```

Expected files created:
- `english_report.pdf--extracted.md`
- `english_report.pdf--summary.txt`

### Test 2: Hindi Document

```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "files=@hindi_document.pdf"
```

Expected files created:
- `hindi_document.pdf---extracted.md` (Hindi)
- `hindi_document.pdf---translated.md` (English)
- `hindi_document.pdf---summary.txt` (English)

### Test 3: Audio File

```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "files=@interview.mp3"
```

Expected files created:
- `interview.mp3==transcription.txt`
- `interview.mp3==summary.txt`

### Test 4: Video File

```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "files=@surveillance.mp4"
```

Expected files created:
- `surveillance.mp4==analysis.txt`
- `surveillance.mp4==summary.txt`

### Test 5: Multiple Files (Mixed Types)

```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "files=@doc1.pdf" \
  -F "files=@doc2.docx" \
  -F "files=@audio.mp3" \
  -F "files=@video.mp4"
```

All files processed in parallel by appropriate workers.

## Verification Checklist

After setup, verify:

- [ ] API responds: `curl http://localhost:8000/api/v1/health`
- [ ] Redis accessible: `redis-cli PING`
- [ ] Workers running: Check logs for "Listening to queue"
- [ ] Can create admin user
- [ ] Can login and get token
- [ ] Can upload file
- [ ] File appears in storage
- [ ] Job status shows progression (queued → processing → completed)
- [ ] Results API returns summary
- [ ] Files created with correct naming convention

## Common Setup Issues

### Issue: "Tesseract not found"

```bash
# Install Tesseract
sudo apt-get install tesseract-ocr

# Verify
tesseract --version
```

### Issue: "Redis connection refused"

```bash
# Check Redis is running
redis-cli PING

# If not running
docker run -d -p 6379:6379 redis:latest
```

### Issue: "No module named 'docling'"

```bash
cd backend
pip install -r requirements.txt
```

### Issue: "OCR returns empty text"

```bash
# Install language data
sudo apt-get install tesseract-ocr-hin tesseract-ocr-ben

# Set environment variable
export TESSDATA_PREFIX=/usr/share/tesseract-ocr/5.00/tessdata

# Verify
ls $TESSDATA_PREFIX/hin.traineddata
```

### Issue: "Gemini API rate limit"

Free tier limits: 50 requests/day. Either:
1. Upgrade to paid tier
2. Switch to production mode (USE_GEMINI_FOR_DEV=false)

### Issue: "Job stuck in 'processing'"

```bash
# Check worker logs
docker-compose logs document-processor

# Check Redis queue
redis-cli LLEN document_queue

# Restart workers
docker-compose restart document-processor audio-processor video-processor
```

## What's Next?

1. **Create Users**: Use admin account to create managers and analysts
2. **Configure RBAC**: Assign analysts to managers
3. **Upload Documents**: Test with various file types and languages
4. **Query Knowledge Graph**: Use `/jobs/{job_id}/graph` endpoint
5. **Chat with Documents**: Use `/chat` endpoint for Q&A

## Architecture Overview

```
Your Upload
    ↓
FastAPI (validates, stores, queues)
    ↓
Redis Queue (distributes work)
    ↓
Workers (process in parallel)
    ├─ Document Worker: OCR, translate, summarize
    ├─ Audio Worker: transcribe, translate, summarize
    ├─ Video Worker: extract frames, analyze, summarize
    └─ Graph Worker: extract entities, store in Neo4j
    ↓
Storage (GCS/Local) + Database (AlloyDB/SQLite) + Neo4j
    ↓
Query Results via API
```

## Monitoring

```bash
# Check queue lengths
redis-cli LLEN document_queue
redis-cli LLEN audio_queue
redis-cli LLEN video_queue
redis-cli LLEN graph_queue

# Check job status
curl http://localhost:8000/api/v1/jobs \
  -H "Authorization: Bearer $TOKEN"

# View worker logs
docker-compose logs -f document-processor
```

## Scaling

```bash
# Add more document workers (horizontal scaling)
docker-compose up -d --scale document-processor=5

# Add more workers of all types
docker-compose up -d \
  --scale document-processor=3 \
  --scale audio-processor=2 \
  --scale video-processor=2 \
  --scale graph-processor=2
```

## Resources

- **Full Documentation**: [README.md](README.md)
- **Process Flows**: [PROCESS_FLOW.md](PROCESS_FLOW.md)
- **Troubleshooting**: [TROUBLESHOOTING_HINDI_PDF.md](TROUBLESHOOTING_HINDI_PDF.md)
- **API Docs**: http://localhost:8000/api/v1/docs
- **GitHub Issues**: https://github.com/MohitRana2001/sentinel_AI/issues

---

**Need Help?** Check the [Troubleshooting section](README.md#troubleshooting) in the main README or open an issue on GitHub.
