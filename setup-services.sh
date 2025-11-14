#!/bin/bash

# Sentinel AI - Quick Setup Script
# This script sets up all 5 microservices

set -e

echo "=========================================="
echo "Sentinel AI Microservices Setup"
echo "=========================================="

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
   echo "Please do not run as root"
   exit 1
fi

# Base directory
BASE_DIR="/opt/sentinel-ai"
SERVICES=("audio-service" "document-service" "video-service" "graph-service" "cdr-service")

echo ""
echo "Step 1: Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y \\
    python3.10 python3.10-venv python3-pip \\
    ffmpeg tesseract-ocr \\
    libpq-dev build-essential \\
    redis-server postgresql-client

echo ""
echo "Step 2: Creating base directory..."
sudo mkdir -p $BASE_DIR
sudo chown -R $USER:$USER $BASE_DIR

echo ""
echo "Step 3: Copying files to deployment directory..."
cp -r backend $BASE_DIR/
for service in "${SERVICES[@]}"; do
    echo "  - Copying $service..."
    cp -r $service $BASE_DIR/
done

echo ""
echo "Step 4: Setting up Python virtual environments..."
for service in "${SERVICES[@]}"; do
    echo "  - Setting up venv for $service..."
    cd $BASE_DIR/$service
    python3.10 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip > /dev/null 2>&1
    pip install -r requirements.txt
    deactivate
done

echo ""
echo "Step 5: Creating .env file..."
if [ ! -f "$BASE_DIR/.env" ]; then
    cat > $BASE_DIR/.env <<EOF
# Environment
ENV=production
DEBUG=False

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Database Configuration
ALLOYDB_HOST=localhost
ALLOYDB_PORT=5432
ALLOYDB_USER=postgres
ALLOYDB_PASSWORD=changeme
ALLOYDB_DATABASE=sentinel_db

# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=changeme
NEO4J_DATABASE=neo4j

# Storage Configuration
STORAGE_BACKEND=local
LOCAL_STORAGE_PATH=/opt/sentinel-ai/storage

# LLM Configuration
SUMMARY_LLM_URL=http://localhost:11434
SUMMARY_LLM_MODEL=gemma3:1b
MULTIMODAL_LLM_URL=http://localhost:11434
EOF
    echo "  ✅ Created .env file - Please edit $BASE_DIR/.env with your configuration"
else
    echo "  ⚠️  .env file already exists, skipping..."
fi

echo ""
echo "Step 6: Installing systemd service files..."
for service in "${SERVICES[@]}"; do
    service_name="${service%-service}-processor"
    sudo cp $BASE_DIR/$service/$service_name.service /etc/systemd/system/
    echo "  - Installed $service_name.service"
done

sudo systemctl daemon-reload

echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit configuration: nano $BASE_DIR/.env"
echo "2. Start services:"
for service in "${SERVICES[@]}"; do
    service_name="${service%-service}-processor"
    echo "   sudo systemctl start $service_name"
done
echo ""
echo "3. Enable services (start on boot):"
for service in "${SERVICES[@]}"; do
    service_name="${service%-service}-processor"
    echo "   sudo systemctl enable $service_name"
done
echo ""
echo "4. Check status:"
echo "   sudo systemctl status audio-processor"
echo ""
echo "For detailed documentation, see:"
echo "  - $BASE_DIR/DEPLOYMENT_GUIDE.md"
echo "  - $BASE_DIR/audio-service/README.md"
echo ""
