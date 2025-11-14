# Audio Processor Service

This service handles audio file processing including transcription, translation, and vectorization.

## Features

- **Transcription**: Using NeMo (Indic languages) and Vosk (English)
- **Translation**: Using dl_translate for non-English audio
- **Summarization**: Using Ollama/Gemini LLMs
- **Vectorization**: Creating embeddings for semantic search
- **Storage Integration**: Works with GCS, S3, or local storage
- **Redis Integration**: Queue-based parallel processing

## Prerequisites

### System Requirements
- Python 3.10+
- FFmpeg (for audio downsampling)
- CUDA-capable GPU (recommended for NeMo)
- 8GB+ RAM

### External Dependencies

1. **FFmpeg** (required):
```bash
sudo apt-get update
sudo apt-get install -y ffmpeg
```

2. **NeMo ASR** (for Indic language transcription):
Follow AI4Bharat setup instructions:
```bash
# Install NeMo
pip install nemo_toolkit[asr]

# Download Indic Conformer model
wget https://objectstore.e2enetworks.net/indic-asr-public/indicConformer/ai4b_indicConformer_hybrid.nemo
mv ai4b_indicConformer_hybrid.nemo indicconformer_stt_multi_hybrid_rnnt_600m.nemo
```

3. **Vosk** (for English transcription):
```bash
pip install vosk
# Download Vosk model (English)
wget https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip
unzip vosk-model-en-us-0.22.zip
```

4. **dl_translate Model** (for translation):
```bash
mkdir -p dlt/cached_model_m2m100
# Model will be auto-downloaded on first run
```

## Installation

1. **Create virtual environment**:
```bash
cd /opt/sentinel-ai/audio-service
python3 -m venv venv
source venv/bin/activate
```

2. **Install Python dependencies**:
```bash
pip install -r requirements.txt
```

3. **Install NeMo** (separately):
```bash
pip install nemo_toolkit[asr]
```

4. **Configure environment**:
Create `/opt/sentinel-ai/.env` with:
```bash
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Database Configuration
ALLOYDB_HOST=localhost
ALLOYDB_PORT=5432
ALLOYDB_USER=postgres
ALLOYDB_PASSWORD=your_password
ALLOYDB_DATABASE=sentinel_db

# Storage Configuration
STORAGE_BACKEND=gcs  # or 'local', 's3'
GCS_BUCKET_NAME=your-bucket
GCS_PROJECT_ID=your-project
GCS_CREDENTIALS_PATH=/opt/sentinel-ai/credentials/gcs-key.json

# LLM Configuration
SUMMARY_LLM_URL=http://localhost:11434
SUMMARY_LLM_MODEL=gemma3:1b
```

## Running the Service

### Development Mode
```bash
cd /opt/sentinel-ai/audio-service
source venv/bin/activate
python audio_processor.py
```

### Production Mode (systemd)

1. **Copy service file**:
```bash
sudo cp audio-processor.service /etc/systemd/system/
```

2. **Enable and start**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable audio-processor
sudo systemctl start audio-processor
```

3. **Check status**:
```bash
sudo systemctl status audio-processor
sudo journalctl -u audio-processor -f
```

## Configuration

### Supported Languages
- English (en) - Vosk
- Hindi (hi) - NeMo
- Bengali (bn) - NeMo
- Punjabi (pa) - NeMo
- Kannada (kn) - NeMo
- Malayalam (ml) - NeMo
- Marathi (mr) - NeMo
- Tamil (ta) - NeMo

### Redis Queue
The service listens to: `audio_queue`

### Message Format
```json
{
  "job_id": "manager/analyst/uuid",
  "gcs_path": "uploads/job-id/audio-hi.mp3",
  "filename": "audio-hi.mp3",
  "action": "process_file",
  "metadata": {
    "language": "hi"
  }
}
```

## Troubleshooting

### NeMo Model Not Loading
- Ensure model file `indicconformer_stt_multi_hybrid_rnnt_600m.nemo` is in working directory
- Check CUDA availability: `python -c "import torch; print(torch.cuda.is_available())"`

### FFmpeg Not Found
```bash
sudo apt-get install ffmpeg
which ffmpeg  # Should show /usr/bin/ffmpeg
```

### Translation Model Download Issues
- Check internet connectivity
- Ensure sufficient disk space (model is ~2GB)
- Manual download to `./dlt/cached_model_m2m100/`

### Memory Issues
- Reduce batch size in translation
- Increase system memory limit in service file
- Process fewer files concurrently

## Architecture

```
┌─────────────┐
│ Redis Queue │
│ audio_queue │
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│ Audio Processor  │
│  Service         │
└────────┬─────────┘
         │
         ├─► Download from Storage
         ├─► Downsample (FFmpeg)
         ├─► Transcribe (NeMo/Vosk)
         ├─► Translate (dl_translate)
         ├─► Summarize (Ollama)
         ├─► Vectorize (AlloyDB)
         └─► Queue Graph Processing
```

## Performance

- **Transcription**: ~2-3 minutes per hour of audio
- **Translation**: ~30 seconds per 1000 words
- **Summarization**: ~5 seconds per document
- **Vectorization**: ~10 seconds per document

## Monitoring

### Logs
```bash
# Real-time logs
sudo journalctl -u audio-processor -f

# Last 100 lines
sudo journalctl -u audio-processor -n 100
```

### Metrics
- Check Redis queue length: `redis-cli LLEN audio_queue`
- Database records: Check `documents` table
- Processing stages: Check `processing_stages` JSON field

## Support

For issues, check:
1. System logs: `journalctl -u audio-processor`
2. Redis connectivity: `redis-cli PING`
3. Database connectivity: `psql -h localhost -U postgres`
4. Storage access: Check GCS credentials/permissions
