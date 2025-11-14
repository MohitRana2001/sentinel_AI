# Quick Reference Card - Sentinel AI Microservices

## 📦 What Was Created

```
ib-bureau/
├── audio-service/              ✅ COMPLETE
│   ├── audio_processor.py      (Full implementation with Redis & Storage)
│   ├── requirements.txt        (Audio-specific deps)
│   ├── audio-processor.service (Systemd file)
│   └── README.md              (Complete guide)
│
├── document-service/           ✅ STRUCTURE READY
│   ├── requirements.txt        (Document-specific deps)
│   └── document-processor.service
│
├── video-service/              ✅ STRUCTURE READY
│   ├── requirements.txt        (Video-specific deps)
│   └── video-processor.service
│
├── graph-service/              ✅ STRUCTURE READY
│   ├── requirements.txt        (Graph-specific deps)
│   └── graph-processor.service
│
├── cdr-service/                ✅ STRUCTURE READY
│   ├── requirements.txt        (CDR-specific deps)
│   └── cdr-processor.service
│
├── DEPLOYMENT_GUIDE.md         ✅ Complete deployment guide
├── SERVICES_SUMMARY.md         ✅ This summary
└── setup-services.sh          ✅ Automated setup script
```

---

## 🎯 Key Features Implemented

### Audio Service (Full Implementation)
```python
# Redis Integration ✅
from backend.redis_pubsub import RedisPubSub
redis_pubsub = RedisPubSub()

# Storage Integration ✅
from backend.storage_config import storage_manager
temp_file = storage_manager.download_to_temp(gcs_path)

# Processing Pipeline ✅
1. Download from storage
2. Downsample with FFmpeg
3. Transcribe (NeMo/Vosk)
4. Translate (dl_translate)
5. Summarize (Ollama)
6. Vectorize (AlloyDB)
7. Queue for graph processing
```

---

## 🚀 Quick Deployment Commands

### Setup All Services
```bash
cd /home/mohitrana/ib-bureau
chmod +x setup-services.sh
./setup-services.sh
```

### Manual Deployment (Audio Example)
```bash
# 1. Copy to deployment location
sudo mkdir -p /opt/sentinel-ai
sudo cp -r audio-service /opt/sentinel-ai/
sudo cp -r backend /opt/sentinel-ai/

# 2. Setup virtual environment
cd /opt/sentinel-ai/audio-service
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Install systemd service
sudo cp audio-processor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable audio-processor
sudo systemctl start audio-processor

# 4. Check status
sudo systemctl status audio-processor
sudo journalctl -u audio-processor -f
```

---

## 📋 Service Files Checklist

### What You Have Now ✅
- [x] All 5 service folders created
- [x] Individual requirements.txt (minimal deps only)
- [x] Systemd service files for all
- [x] Audio processor fully implemented
- [x] Deployment documentation
- [x] Setup automation script

### What You Need to Add
- [ ] Copy service Python files from `/backend/processors/`:
  ```bash
  cp backend/processors/document_processor_service.py document-service/
  cp backend/processors/video_processor_service.py video-service/
  cp backend/processors/graph_processor_service.py graph-service/
  cp backend/cdr_processor.py cdr-service/cdr_processor_service.py
  ```

- [ ] Install external dependencies:
  - NeMo (AI4Bharat model)
  - Vosk (English model)
  - FFmpeg (`apt-get install ffmpeg`)
  - Tesseract OCR (`apt-get install tesseract-ocr`)

- [ ] Configure `.env` file with production values

---

## 🔧 Service-Specific Dependencies

### Audio (Heavy)
- torch, nemo_toolkit
- dl_translate, vosk
- FFmpeg binary
- 8GB RAM, GPU recommended

### Document (Medium)
- docling, PyMuPDF, pytesseract
- Tesseract OCR binary
- 4GB RAM

### Video (Heavy)
- opencv, face-recognition
- moviepy, FFmpeg
- 8GB RAM, GPU recommended

### Graph (Medium)
- neo4j, langchain
- Neo4j database
- 4GB RAM

### CDR (Light)
- pandas, openpyxl
- 2GB RAM

---

## 📊 Redis Queues

Each service listens to its own queue:

| Service   | Queue Name       | Message Format                           |
|-----------|------------------|------------------------------------------|
| Audio     | `audio_queue`    | `{job_id, gcs_path, filename, metadata}` |
| Document  | `document_queue` | `{job_id, gcs_path, filename}`          |
| Video     | `video_queue`    | `{job_id, gcs_path, filename, metadata}` |
| Graph     | `graph_queue`    | `{job_id, document_id, gcs_text_path}`  |
| CDR       | `cdr_queue`      | `{job_id, gcs_path, filename}`          |

---

## 🏃 Service Commands

### Start Services
```bash
sudo systemctl start audio-processor
sudo systemctl start document-processor
sudo systemctl start video-processor
sudo systemctl start graph-processor
sudo systemctl start cdr-processor
```

### Stop Services
```bash
sudo systemctl stop audio-processor
# ... (repeat for others)
```

### Check Status
```bash
sudo systemctl status audio-processor
```

### View Logs
```bash
sudo journalctl -u audio-processor -f
```

### Monitor Queues
```bash
redis-cli LLEN audio_queue
redis-cli LLEN document_queue
redis-cli LLEN video_queue
redis-cli LLEN graph_queue
redis-cli LLEN cdr_queue
```

---

## 🎨 Audio Service Implementation Highlights

The audio service (`audio-service/audio_processor.py`) includes:

1. **NeMo Integration**: AI4Bharat Indic languages transcription
2. **Vosk Integration**: English transcription
3. **FFmpeg Downsampling**: Audio preprocessing
4. **dl_translate**: Multi-language translation
5. **Text Rewriting**: Gemma3:1b for consistency
6. **Redis Queue Listening**: Parallel processing
7. **Storage Manager**: GCS/S3/Local abstraction
8. **Database Integration**: AlloyDB for vectors
9. **Status Tracking**: Per-artifact progress
10. **Error Handling**: Graceful failures

---

## 📝 Configuration Template

Create `/opt/sentinel-ai/.env`:

```bash
# Services
ENV=production
DEBUG=False

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Database
ALLOYDB_HOST=localhost
ALLOYDB_PORT=5432
ALLOYDB_USER=postgres
ALLOYDB_PASSWORD=your_password
ALLOYDB_DATABASE=sentinel_db

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password

# Storage
STORAGE_BACKEND=gcs
GCS_BUCKET_NAME=your-bucket
GCS_CREDENTIALS_PATH=/opt/sentinel-ai/credentials/gcs-key.json

# LLM
SUMMARY_LLM_URL=http://localhost:11434
SUMMARY_LLM_MODEL=gemma3:1b
MULTIMODAL_LLM_URL=http://localhost:11434
```

---

## 🎯 Priority Implementation Order

1. ✅ **Audio Service** - COMPLETE (top priority as requested)
2. **Document Service** - Copy from backend/processors/
3. **Video Service** - Copy from backend/processors/
4. **Graph Service** - Copy from backend/processors/
5. **CDR Service** - Copy from backend/cdr_processor.py

---

## 💡 Tips

### Testing Individual Services
```bash
cd /opt/sentinel-ai/audio-service
source venv/bin/activate
python audio_processor.py
```

### Debugging
```bash
# Enable debug mode
export DEBUG=True

# Tail all logs
sudo journalctl -f | grep -E 'audio|document|video|graph|cdr'
```

### Scaling
Run multiple instances:
```bash
# Start 3 audio workers
sudo systemctl start audio-processor@1
sudo systemctl start audio-processor@2
sudo systemctl start audio-processor@3
```

---

## 📞 Support Files

- **Full Guide**: `DEPLOYMENT_GUIDE.md`
- **Summary**: `SERVICES_SUMMARY.md`
- **Audio Details**: `audio-service/README.md`
- **Setup Script**: `setup-services.sh`

---

**Status**: ✅ Ready for deployment  
**Last Updated**: November 14, 2025
