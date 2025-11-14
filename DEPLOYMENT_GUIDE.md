# Sentinel AI - Microservices Deployment Guide

This guide explains how to deploy the 5 separate microservices for the Sentinel AI system.

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                         Redis Queues                          │
│  audio_queue | document_queue | video_queue | graph_queue    │
│                      | cdr_queue                              │
└────────┬─────────────┬──────────────┬──────────────┬─────────┘
         │             │              │              │
    ┌────▼───┐   ┌────▼───┐    ┌────▼───┐    ┌────▼───┐
    │ Audio  │   │Document│    │ Video  │    │ Graph  │
    │Service │   │Service │    │Service │    │Service │
    └────┬───┘   └────┬───┘    └────┬───┘    └────────┘
         │            │             │
         └────────────┴─────────────┘
                      │
                ┌─────▼─────┐
                │    CDR    │
                │  Service  │
                └───────────┘
                      │
         ┌────────────┴────────────┐
         │                         │
    ┌────▼────┐             ┌─────▼─────┐
    │ AlloyDB │             │   Neo4j   │
    │(Postgres│             │  (Graph)  │
    │ +Vector)│             └───────────┘
    └─────────┘
```

## Services Overview

### 1. **Audio Service** (Priority #1)
- **Purpose**: Transcription, translation, and processing of audio files
- **Technologies**: NeMo (AI4Bharat), Vosk, dl_translate, Ollama
- **Queue**: `audio_queue`
- **Dependencies**: FFmpeg, CUDA (recommended)

### 2. **Document Service**
- **Purpose**: PDF, DOCX, TXT document extraction, translation, summarization
- **Technologies**: Docling, PyMuPDF, pytesseract, dl_translate
- **Queue**: `document_queue`
- **Dependencies**: Tesseract OCR

### 3. **Video Service** (2 sub-services)
- **Purpose**: 
  - a. Face Recognition (FRS)
  - b. Summarization, transcription, translation
- **Technologies**: OpenCV, face_recognition, moviepy
- **Queue**: `video_queue`
- **Dependencies**: FFmpeg

### 4. **Graph Service**
- **Purpose**: Entity extraction and knowledge graph building
- **Technologies**: LangChain, Neo4j, Ollama/Gemini
- **Queue**: `graph_queue`
- **Dependencies**: Neo4j database

### 5. **CDR Service**
- **Purpose**: Call Data Records processing and phone number matching
- **Technologies**: Pandas, SQLAlchemy
- **Queue**: `cdr_queue`
- **Dependencies**: None (lightweight)

## Deployment Steps

### Prerequisites

1. **System Requirements** (per service):
   - Ubuntu 20.04+ / Debian 11+
   - Python 3.10+
   - 4-8GB RAM (varies by service)
   - CUDA GPU (recommended for audio/video)

2. **Common Infrastructure**:
   - Redis Server (for queues and pub/sub)
   - PostgreSQL with pgvector (AlloyDB)
   - Neo4j Database
   - Google Cloud Storage or S3 (or local storage)

3. **System Packages**:
```bash
sudo apt-get update
sudo apt-get install -y \\
    python3.10 python3.10-venv python3-pip \\
    ffmpeg tesseract-ocr \\
    libpq-dev build-essential
```

### Deployment Directory Structure

```
/opt/sentinel-ai/
├── .env                          # Shared environment variables
├── backend/                      # Shared backend modules
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── redis_pubsub.py
│   ├── storage_config.py
│   ├── vector_store.py
│   └── storage/
├── audio-service/
│   ├── audio_processor.py
│   ├── requirements.txt
│   ├── audio-processor.service
│   ├── venv/
│   └── README.md
├── document-service/
│   ├── document_processor_service.py
│   ├── requirements.txt
│   ├── document-processor.service
│   ├── venv/
│   └── README.md
├── video-service/
│   ├── video_processor_service.py
│   ├── requirements.txt
│   ├── video-processor.service
│   ├── venv/
│   └── README.md
├── graph-service/
│   ├── graph_processor_service.py
│   ├── requirements.txt
│   ├── graph-processor.service
│   ├── venv/
│   └── README.md
└── cdr-service/
    ├── cdr_processor_service.py
    ├── requirements.txt
    ├── cdr-processor.service
    ├── venv/
    └── README.md
```

### Step-by-Step Deployment

#### 1. Setup Base Directory

```bash
# Create deployment directory
sudo mkdir -p /opt/sentinel-ai
sudo chown -R $USER:$USER /opt/sentinel-ai
cd /opt/sentinel-ai

# Copy backend shared modules
cp -r backend /opt/sentinel-ai/

# Copy service folders
cp -r audio-service document-service video-service graph-service cdr-service /opt/sentinel-ai/
```

#### 2. Configure Environment Variables

Create `/opt/sentinel-ai/.env`:

```bash
# Environment
ENV=production
DEBUG=False

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your_redis_password

# Database Configuration (AlloyDB/PostgreSQL)
ALLOYDB_HOST=localhost
ALLOYDB_PORT=5432
ALLOYDB_USER=postgres
ALLOYDB_PASSWORD=your_db_password
ALLOYDB_DATABASE=sentinel_db

# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_neo4j_password
NEO4J_DATABASE=neo4j

# Storage Configuration
STORAGE_BACKEND=gcs  # or 'local', 's3'
GCS_BUCKET_NAME=your-bucket-name
GCS_PROJECT_ID=your-project-id
GCS_CREDENTIALS_PATH=/opt/sentinel-ai/credentials/gcs-key.json

# LLM Configuration
SUMMARY_LLM_URL=http://localhost:11434
SUMMARY_LLM_MODEL=gemma3:1b
MULTIMODAL_LLM_URL=http://localhost:11434

# Optional: Gemini for development
USE_GEMINI_FOR_DEV=false
GEMINI_API_KEY=
```

#### 3. Deploy Each Service

**For Audio Service** (Repeat similar steps for other services):

```bash
cd /opt/sentinel-ai/audio-service

# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install NeMo (separate installation)
pip install nemo_toolkit[asr]

# Download NeMo model
wget https://objectstore.e2enetworks.net/indic-asr-public/indicConformer/ai4b_indicConformer_hybrid.nemo
mv ai4b_indicConformer_hybrid.nemo indicconformer_stt_multi_hybrid_rnnt_600m.nemo

# Install Vosk
pip install vosk

# Test service
python audio_processor.py
```

**For Document Service**:

```bash
cd /opt/sentinel-ai/document-service
python3.10 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Test service
python document_processor_service.py
```

**For Video Service**:

```bash
cd /opt/sentinel-ai/video-service
python3.10 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Test service
python video_processor_service.py
```

**For Graph Service**:

```bash
cd /opt/sentinel-ai/graph-service
python3.10 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Test service
python graph_processor_service.py
```

**For CDR Service**:

```bash
cd /opt/sentinel-ai/cdr-service
python3.10 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Test service
python cdr_processor_service.py
```

#### 4. Install as Systemd Services

```bash
# Copy service files
sudo cp /opt/sentinel-ai/audio-service/audio-processor.service /etc/systemd/system/
sudo cp /opt/sentinel-ai/document-service/document-processor.service /etc/systemd/system/
sudo cp /opt/sentinel-ai/video-service/video-processor.service /etc/systemd/system/
sudo cp /opt/sentinel-ai/graph-service/graph-processor.service /etc/systemd/system/
sudo cp /opt/sentinel-ai/cdr-service/cdr-processor.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable services (start on boot)
sudo systemctl enable audio-processor
sudo systemctl enable document-processor
sudo systemctl enable video-processor
sudo systemctl enable graph-processor
sudo systemctl enable cdr-processor

# Start services
sudo systemctl start audio-processor
sudo systemctl start document-processor
sudo systemctl start video-processor
sudo systemctl start graph-processor
sudo systemctl start cdr-processor
```

#### 5. Verify Services

```bash
# Check status
sudo systemctl status audio-processor
sudo systemctl status document-processor
sudo systemctl status video-processor
sudo systemctl status graph-processor
sudo systemctl status cdr-processor

# View logs
sudo journalctl -u audio-processor -f
sudo journalctl -u document-processor -f
sudo journalctl -u video-processor -f
sudo journalctl -u graph-processor -f
sudo journalctl -u cdr-processor -f

# Check Redis queues
redis-cli LLEN audio_queue
redis-cli LLEN document_queue
redis-cli LLEN video_queue
redis-cli LLEN graph_queue
redis-cli LLEN cdr_queue
```

## Scaling

### Horizontal Scaling

Each service can be scaled horizontally by running multiple instances:

```bash
# Example: Run 3 audio processor workers
sudo systemctl start audio-processor@1
sudo systemctl start audio-processor@2
sudo systemctl start audio-processor@3
```

### Resource Allocation

Recommended resources per service:

| Service   | CPU | RAM | GPU | Storage |
|-----------|-----|-----|-----|---------|
| Audio     | 2   | 8GB | Yes | 10GB    |
| Document  | 2   | 4GB | No  | 5GB     |
| Video     | 2   | 8GB | Yes | 20GB    |
| Graph     | 2   | 4GB | No  | 5GB     |
| CDR       | 1   | 2GB | No  | 2GB     |

## Monitoring

### Health Checks

Create monitoring script `/opt/sentinel-ai/monitor.sh`:

```bash
#!/bin/bash

echo "=== Service Status ==="
systemctl is-active audio-processor || echo "❌ Audio service down"
systemctl is-active document-processor || echo "❌ Document service down"
systemctl is-active video-processor || echo "❌ Video service down"
systemctl is-active graph-processor || echo "❌ Graph service down"
systemctl is-active cdr-processor || echo "❌ CDR service down"

echo ""
echo "=== Queue Lengths ==="
echo "Audio: $(redis-cli LLEN audio_queue)"
echo "Document: $(redis-cli LLEN document_queue)"
echo "Video: $(redis-cli LLEN video_queue)"
echo "Graph: $(redis-cli LLEN graph_queue)"
echo "CDR: $(redis-cli LLEN cdr_queue)"
```

Make executable and run:
```bash
chmod +x /opt/sentinel-ai/monitor.sh
./monitor.sh
```

## Troubleshooting

### Service Won't Start

```bash
# Check logs
sudo journalctl -u audio-processor -n 50

# Check permissions
ls -la /opt/sentinel-ai/audio-service

# Verify environment
sudo systemctl show audio-processor | grep Environment
```

### High Memory Usage

```bash
# Check memory per service
systemctl status audio-processor | grep Memory

# Adjust limits in service file
sudo nano /etc/systemd/system/audio-processor.service
# Change: MemoryMax=8G
sudo systemctl daemon-reload
sudo systemctl restart audio-processor
```

### Queue Backlog

```bash
# Check queue length
redis-cli LLEN audio_queue

# Add more workers
sudo systemctl start audio-processor@2

# Clear stuck jobs (careful!)
redis-cli DEL audio_queue
```

## Maintenance

### Updating Services

```bash
# Stop service
sudo systemctl stop audio-processor

# Update code
cd /opt/sentinel-ai/audio-service
git pull  # or copy new files

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt --upgrade

# Restart service
sudo systemctl start audio-processor
```

### Backup Configuration

```bash
# Backup environment and service files
tar -czf sentinel-config-backup.tar.gz \\
    /opt/sentinel-ai/.env \\
    /etc/systemd/system/*-processor.service
```

## Support

For issues with specific services, check:
- Audio: `/opt/sentinel-ai/audio-service/README.md`
- Document: `/opt/sentinel-ai/document-service/README.md`
- Video: `/opt/sentinel-ai/video-service/README.md`
- Graph: `/opt/sentinel-ai/graph-service/README.md`
- CDR: `/opt/sentinel-ai/cdr-service/README.md`
