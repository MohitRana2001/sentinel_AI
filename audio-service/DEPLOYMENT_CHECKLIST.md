# Audio Service - Required Backend Files

## Files Required from Backend

The `audio_processor.py` imports the following from the backend:

1. **`backend/redis_pubsub.py`** - Redis queue and pub/sub functionality
2. **`backend/storage_config.py`** - Storage manager initialization
3. **`backend/config.py`** - Settings and configuration
4. **`backend/database.py`** - Database session management
5. **`backend/models.py`** - SQLAlchemy models
6. **`backend/vector_store.py`** - Vector embedding functions
7. **`backend/storage/`** - Complete storage module (directory)
   - `backend/storage/__init__.py`
   - `backend/storage/base.py`
   - `backend/storage/manager.py`
   - `backend/storage/factory.py`
   - `backend/storage/gcs_backend.py`
   - `backend/storage/local_backend.py`
   - `backend/storage/s3_backend.py`

## Additional Backend Dependencies

The imported files have their own dependencies:

### From `redis_pubsub.py`:
- `backend/config.py` ✅ (already listed)

### From `storage_config.py`:
- `backend/config.py` ✅ (already listed)
- `backend/storage/` ✅ (already listed)

### From `database.py`:
- `backend/config.py` ✅ (already listed)

### From `vector_store.py`:
- `backend/config.py` ✅ (already listed)
- `backend/database.py` ✅ (already listed)
- `backend/models.py` ✅ (already listed)

## Complete Backend File List

```
backend/
├── __init__.py                 # Make it a package
├── config.py                   # Settings and configuration
├── database.py                 # Database session and engine
├── models.py                   # SQLAlchemy models
├── redis_pubsub.py            # Redis pub/sub and queue
├── storage_config.py          # Storage manager init
├── vector_store.py            # Vector embeddings
└── storage/                   # Storage abstraction layer
    ├── __init__.py
    ├── base.py
    ├── manager.py
    ├── factory.py
    ├── gcs_backend.py
    ├── local_backend.py
    └── s3_backend.py
```

## Directory Structure on VM

```
/opt/sentinel-ai/
├── .env                       # Environment variables
├── backend/                   # Shared backend modules
│   ├── __init__.py
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── redis_pubsub.py
│   ├── storage_config.py
│   ├── vector_store.py
│   └── storage/
│       ├── __init__.py
│       ├── base.py
│       ├── manager.py
│       ├── factory.py
│       ├── gcs_backend.py
│       ├── local_backend.py
│       └── s3_backend.py
└── audio-service/
    ├── audio_processor.py
    ├── requirements.txt
    ├── audio-processor.service
    ├── venv/
    └── README.md
```

## Transfer Commands

### Option 1: Create deployment package
```bash
# On your development machine
cd /home/mohitrana/ib-bureau

# Create deployment directory
mkdir -p audio-service-deploy/backend/storage

# Copy audio service files
cp -r audio-service/* audio-service-deploy/

# Copy backend files
cp backend/__init__.py audio-service-deploy/backend/ 2>/dev/null || touch audio-service-deploy/backend/__init__.py
cp backend/config.py audio-service-deploy/backend/
cp backend/database.py audio-service-deploy/backend/
cp backend/models.py audio-service-deploy/backend/
cp backend/redis_pubsub.py audio-service-deploy/backend/
cp backend/storage_config.py audio-service-deploy/backend/
cp backend/vector_store.py audio-service-deploy/backend/

# Copy storage module
cp backend/storage/__init__.py audio-service-deploy/backend/storage/
cp backend/storage/base.py audio-service-deploy/backend/storage/
cp backend/storage/manager.py audio-service-deploy/backend/storage/
cp backend/storage/factory.py audio-service-deploy/backend/storage/
cp backend/storage/gcs_backend.py audio-service-deploy/backend/storage/
cp backend/storage/local_backend.py audio-service-deploy/backend/storage/
cp backend/storage/s3_backend.py audio-service-deploy/backend/storage/ 2>/dev/null || echo "s3_backend.py not found (optional)"

# Create tarball
tar -czf audio-service-deploy.tar.gz audio-service-deploy/

# Transfer to VM
scp audio-service-deploy.tar.gz user@vm-ip:/tmp/
```

### Option 2: Transfer individual directories
```bash
# On your development machine
cd /home/mohitrana/ib-bureau

# Transfer audio-service folder
rsync -avz audio-service/ user@vm-ip:/opt/sentinel-ai/audio-service/

# Transfer backend folder
rsync -avz backend/ user@vm-ip:/opt/sentinel-ai/backend/
```

### On the VM:
```bash
# If using tarball (Option 1)
cd /tmp
tar -xzf audio-service-deploy.tar.gz
sudo mkdir -p /opt/sentinel-ai
sudo mv audio-service-deploy/audio-service /opt/sentinel-ai/
sudo mv audio-service-deploy/backend /opt/sentinel-ai/

# Or if using rsync (Option 2), files are already in place

# Set proper permissions
sudo chown -R sentinelai:sentinelai /opt/sentinel-ai

# Create .env file
sudo nano /opt/sentinel-ai/.env
# (paste environment variables)
```

## Environment Variables (.env)

Create `/opt/sentinel-ai/.env` on the VM:

```bash
# Environment
ENV=production
DEBUG=False

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Database Configuration (AlloyDB/PostgreSQL)
ALLOYDB_HOST=localhost
ALLOYDB_PORT=5432
ALLOYDB_USER=postgres
ALLOYDB_PASSWORD=your_password
ALLOYDB_DATABASE=sentinel_db

# Storage Configuration
STORAGE_BACKEND=gcs  # or 'local'
GCS_BUCKET_NAME=your-bucket-name
GCS_PROJECT_ID=your-project-id
GCS_CREDENTIALS_PATH=/opt/sentinel-ai/credentials/gcs-key.json

# Local storage (if STORAGE_BACKEND=local)
LOCAL_STORAGE_PATH=/opt/sentinel-ai/storage

# LLM Configuration
SUMMARY_LLM_URL=http://localhost:11434
SUMMARY_LLM_MODEL=gemma3:1b
MULTIMODAL_LLM_URL=http://localhost:11434
```

## Installation on VM

```bash
cd /opt/sentinel-ai/audio-service

# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install NeMo separately
pip install nemo_toolkit[asr]

# Download NeMo model
wget https://objectstore.e2enetworks.net/indic-asr-public/indicConformer/ai4b_indicConformer_hybrid.nemo
mv ai4b_indicConformer_hybrid.nemo indicconformer_stt_multi_hybrid_rnnt_600m.nemo

# Test the service
python audio_processor.py
```

## Quick Verification

Test that all imports work:

```bash
cd /opt/sentinel-ai/audio-service
source venv/bin/activate
python -c "
import sys
sys.path.append('/opt/sentinel-ai')
from backend.redis_pubsub import RedisPubSub
from backend.storage_config import storage_manager
from backend.config import settings
from backend.database import SessionLocal
import backend.models as models
from backend.vector_store import vectorise_and_store_alloydb
print('✅ All backend imports successful!')
"
```

## Checklist

- [ ] Copy `audio-service/` folder to VM
- [ ] Copy `backend/` folder to VM
- [ ] Create `.env` file with correct configuration
- [ ] Create virtual environment
- [ ] Install Python dependencies
- [ ] Install NeMo toolkit
- [ ] Download NeMo model
- [ ] Install FFmpeg (`sudo apt-get install ffmpeg`)
- [ ] Verify all imports work
- [ ] Test service manually
- [ ] Install systemd service
- [ ] Start and enable service
