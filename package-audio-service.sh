#!/bin/bash

# Script to package Audio Service with all required backend dependencies
# This creates a deployment-ready tarball

set -e

echo "=========================================="
echo "Audio Service Deployment Package Creator"
echo "=========================================="

# Configuration
SERVICE_NAME="audio-service"
PACKAGE_NAME="audio-service-deploy"
BACKEND_FILES=(
    "config.py"
    "database.py"
    "models.py"
    "redis_pubsub.py"
    "storage_config.py"
    "vector_store.py"
)

STORAGE_FILES=(
    "__init__.py"
    "base.py"
    "manager.py"
    "factory.py"
    "gcs_backend.py"
    "local_backend.py"
)

# Optional files
OPTIONAL_FILES=(
    "backend/storage/s3_backend.py"
)

echo ""
echo "Step 1: Creating package directory..."
rm -rf $PACKAGE_NAME
mkdir -p $PACKAGE_NAME/backend/storage

echo ""
echo "Step 2: Copying audio service files..."
cp -r $SERVICE_NAME/* $PACKAGE_NAME/
echo "  ✅ Copied audio service files"

echo ""
echo "Step 3: Copying required backend files..."
# Create backend __init__.py if it doesn't exist
if [ -f "backend/__init__.py" ]; then
    cp backend/__init__.py $PACKAGE_NAME/backend/
else
    touch $PACKAGE_NAME/backend/__init__.py
fi
echo "  ✅ Created backend/__init__.py"

# Copy main backend files
for file in "${BACKEND_FILES[@]}"; do
    if [ -f "backend/$file" ]; then
        cp "backend/$file" "$PACKAGE_NAME/backend/"
        echo "  ✅ Copied backend/$file"
    else
        echo "  ❌ Warning: backend/$file not found"
    fi
done

echo ""
echo "Step 4: Copying storage module files..."
for file in "${STORAGE_FILES[@]}"; do
    if [ -f "backend/storage/$file" ]; then
        cp "backend/storage/$file" "$PACKAGE_NAME/backend/storage/"
        echo "  ✅ Copied backend/storage/$file"
    else
        echo "  ❌ Warning: backend/storage/$file not found"
    fi
done

# Copy optional files
echo ""
echo "Step 5: Copying optional files..."
for file in "${OPTIONAL_FILES[@]}"; do
    if [ -f "$file" ]; then
        cp "$file" "$PACKAGE_NAME/$file"
        echo "  ✅ Copied $file"
    else
        echo "  ⚠️  Skipped $file (optional, not found)"
    fi
done

echo ""
echo "Step 6: Creating .env template..."
cat > $PACKAGE_NAME/.env.template <<'EOF'
# Environment Configuration
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
ALLOYDB_PASSWORD=CHANGE_ME
ALLOYDB_DATABASE=sentinel_db

# Storage Configuration
STORAGE_BACKEND=gcs  # Options: 'gcs', 'local', 's3'
GCS_BUCKET_NAME=your-bucket-name
GCS_PROJECT_ID=your-project-id
GCS_CREDENTIALS_PATH=/opt/sentinel-ai/credentials/gcs-key.json

# Local Storage (if STORAGE_BACKEND=local)
LOCAL_STORAGE_PATH=/opt/sentinel-ai/storage

# LLM Configuration
SUMMARY_LLM_URL=http://localhost:11434
SUMMARY_LLM_MODEL=gemma3:1b
MULTIMODAL_LLM_URL=http://localhost:11434
EOF
echo "  ✅ Created .env.template"

echo ""
echo "Step 7: Creating deployment instructions..."
cat > $PACKAGE_NAME/INSTALL.md <<'EOF'
# Audio Service Installation Instructions

## 1. Transfer to VM

```bash
# Upload tarball to VM
scp audio-service-deploy.tar.gz user@vm-ip:/tmp/

# SSH to VM
ssh user@vm-ip
```

## 2. Extract and Install

```bash
# Extract
cd /tmp
tar -xzf audio-service-deploy.tar.gz

# Move to installation directory
sudo mkdir -p /opt/sentinel-ai
sudo mv audio-service-deploy/audio-service /opt/sentinel-ai/
sudo mv audio-service-deploy/backend /opt/sentinel-ai/

# Copy environment template
sudo cp audio-service-deploy/.env.template /opt/sentinel-ai/.env

# Edit configuration
sudo nano /opt/sentinel-ai/.env
# Update all CHANGE_ME values
```

## 3. Install System Dependencies

```bash
sudo apt-get update
sudo apt-get install -y ffmpeg python3.10 python3.10-venv
```

## 4. Setup Python Environment

```bash
cd /opt/sentinel-ai/audio-service
python3.10 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 5. Install NeMo (for Indic languages)

```bash
pip install nemo_toolkit[asr]

# Download Indic Conformer model
wget https://objectstore.e2enetworks.net/indic-asr-public/indicConformer/ai4b_indicConformer_hybrid.nemo
mv ai4b_indicConformer_hybrid.nemo indicconformer_stt_multi_hybrid_rnnt_600m.nemo
```

## 6. Verify Installation

```bash
python -c "
import sys
sys.path.append('/opt/sentinel-ai')
from backend.redis_pubsub import RedisPubSub
from backend.storage_config import storage_manager
from backend.config import settings
print('✅ All imports successful!')
"
```

## 7. Install as System Service

```bash
sudo cp audio-processor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable audio-processor
sudo systemctl start audio-processor
```

## 8. Check Status

```bash
sudo systemctl status audio-processor
sudo journalctl -u audio-processor -f
```
EOF
echo "  ✅ Created INSTALL.md"

echo ""
echo "Step 8: Creating directory structure info..."
cat > $PACKAGE_NAME/STRUCTURE.txt <<EOF
Audio Service Deployment Package Structure:

.
├── audio-service/
│   ├── audio_processor.py          # Main service file
│   ├── requirements.txt            # Python dependencies
│   ├── audio-processor.service     # Systemd service file
│   └── README.md                   # Documentation
├── backend/
│   ├── __init__.py
│   ├── config.py                   # Configuration management
│   ├── database.py                 # Database session
│   ├── models.py                   # SQLAlchemy models
│   ├── redis_pubsub.py            # Redis pub/sub
│   ├── storage_config.py          # Storage initialization
│   ├── vector_store.py            # Vector operations
│   └── storage/
│       ├── __init__.py
│       ├── base.py                # Storage interface
│       ├── manager.py             # Storage manager
│       ├── factory.py             # Storage factory
│       ├── gcs_backend.py         # GCS implementation
│       └── local_backend.py       # Local storage implementation
├── .env.template                   # Environment variables template
├── INSTALL.md                      # Installation instructions
└── STRUCTURE.txt                   # This file

Installation Path on VM: /opt/sentinel-ai/
EOF
echo "  ✅ Created STRUCTURE.txt"

echo ""
echo "Step 9: Validating package..."
MISSING_FILES=0

# Check critical files
if [ ! -f "$PACKAGE_NAME/audio-service/audio_processor.py" ]; then
    echo "  ❌ Missing: audio_processor.py"
    MISSING_FILES=$((MISSING_FILES + 1))
fi

if [ ! -f "$PACKAGE_NAME/backend/config.py" ]; then
    echo "  ❌ Missing: backend/config.py"
    MISSING_FILES=$((MISSING_FILES + 1))
fi

if [ ! -f "$PACKAGE_NAME/backend/storage/__init__.py" ]; then
    echo "  ❌ Missing: backend/storage/__init__.py"
    MISSING_FILES=$((MISSING_FILES + 1))
fi

if [ $MISSING_FILES -eq 0 ]; then
    echo "  ✅ All critical files present"
else
    echo "  ⚠️  $MISSING_FILES critical file(s) missing"
fi

echo ""
echo "Step 10: Creating tarball..."
tar -czf audio-service-deploy.tar.gz $PACKAGE_NAME/
TARBALL_SIZE=$(du -h audio-service-deploy.tar.gz | cut -f1)
echo "  ✅ Created audio-service-deploy.tar.gz ($TARBALL_SIZE)"

echo ""
echo "=========================================="
echo "✅ Package created successfully!"
echo "=========================================="
echo ""
echo "📦 Package: audio-service-deploy.tar.gz ($TARBALL_SIZE)"
echo "📁 Contents:"
echo "   - audio-service/ (service files)"
echo "   - backend/ (shared backend modules)"
echo "   - .env.template (configuration template)"
echo "   - INSTALL.md (installation guide)"
echo ""
echo "Next steps:"
echo "1. Transfer to VM:"
echo "   scp audio-service-deploy.tar.gz user@vm-ip:/tmp/"
echo ""
echo "2. On VM, follow instructions in INSTALL.md"
echo ""
echo "For detailed instructions, see:"
echo "   tar -xzf audio-service-deploy.tar.gz"
echo "   cat audio-service-deploy/INSTALL.md"
echo ""
