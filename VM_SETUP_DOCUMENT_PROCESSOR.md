# Document Processor VM Setup Guide

## Overview

This guide provides detailed instructions for setting up the **Document Processor Service** on a dedicated Virtual Machine (VM). The Document Processor is responsible for:

- Extracting text from documents (PDF, DOCX, TXT)
- Performing OCR on image-based PDFs
- Detecting document language
- Translating non-English documents to English
- Generating document summaries
- Creating text embeddings and storing them in the vector database
- Queueing documents for graph processing

## Architecture Context

The Document Processor VM acts as a **worker node** in the Sentinel AI distributed system:

```
┌──────────────┐     ┌─────────┐     ┌─────────────────────┐
│  Main App    │────▶│  Redis  │◀────│ Document Processor  │
│  (FastAPI)   │     │ (Queue) │     │      VM             │
└──────────────┘     └─────────┘     └─────────────────────┘
       │                                        │
       ▼                                        ▼
┌──────────────┐                      ┌─────────────────┐
│   AlloyDB    │◀─────────────────────│  GCS / Storage  │
│  (Postgres)  │                      └─────────────────┘
└──────────────┘
```

### Data Flow

1. **Main Application** uploads files to storage and pushes messages to Redis queue (`document_queue`)
2. **Document Processor VM** pulls messages from Redis queue
3. **Document Processor VM** downloads files from storage, processes them, uploads results
4. **Document Processor VM** updates AlloyDB with document metadata and embeddings
5. **Document Processor VM** queues processed documents to `graph_queue` for next stage

---

## Prerequisites

### System Requirements

- **Operating System**: Ubuntu 22.04 LTS or higher (recommended)
- **CPU**: Minimum 4 cores (8+ cores recommended for parallel processing)
- **RAM**: Minimum 8GB (16GB+ recommended)
- **Disk Space**: Minimum 50GB free space
- **Network**: Stable internet connection for accessing Redis, AlloyDB, and GCS

### Required Access

Before starting, ensure you have:

1. **Network Access** to:
   - Redis server (port 6379)
   - AlloyDB/PostgreSQL server (port 5432)
   - GCS (if using Google Cloud Storage) or shared network storage
   - Ollama LLM server for summaries (port 11434)
   - Ollama LLM server for embeddings (port 11434)

2. **Credentials**:
   - GCS service account key (if using GCS)
   - AlloyDB connection credentials
   - Redis password (if authentication is enabled)

3. **SSH Access** to the VM

---

## Step 1: Initial VM Setup

### 1.1 Update System Packages

Connect to your VM via SSH and update the system:

```bash
# Update package lists
sudo apt update

# Upgrade installed packages
sudo apt upgrade -y

# Install essential build tools and dependencies
sudo apt install -y build-essential curl wget git python3 python3-pip python3-venv
```

**Explanation**: This ensures your system has the latest security patches and essential tools for building Python packages.

### 1.2 Install System Dependencies

The Document Processor requires several system-level dependencies for PDF processing, OCR, and image handling:

```bash
# Install Tesseract OCR for text extraction from images
sudo apt install -y tesseract-ocr

# Install language data for Tesseract (Indian languages + English + Chinese)
sudo apt install -y \
    tesseract-ocr-eng \
    tesseract-ocr-hin \
    tesseract-ocr-ben \
    tesseract-ocr-pan \
    tesseract-ocr-guj \
    tesseract-ocr-kan \
    tesseract-ocr-mal \
    tesseract-ocr-mar \
    tesseract-ocr-tam \
    tesseract-ocr-tel \
    tesseract-ocr-chi-sim

# Install Poppler utils for PDF manipulation
sudo apt install -y poppler-utils

# Install image processing libraries
sudo apt install -y libjpeg-dev libpng-dev libtiff-dev

# Install PostgreSQL client for AlloyDB connectivity
sudo apt install -y postgresql-client
```

**Explanation**:
- **Tesseract OCR**: Performs optical character recognition on image-based PDFs
- **Language packs**: Enables multilingual OCR support
- **Poppler**: Provides PDF rendering and conversion utilities
- **Image libraries**: Required by Pillow for image processing
- **PostgreSQL client**: Allows testing database connectivity

### 1.3 Set Environment Variable for Tesseract

Configure Tesseract data path:

```bash
# Add to system-wide environment
echo 'export TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata/' | sudo tee -a /etc/environment

# Add to current session
export TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata/

# Verify Tesseract installation
tesseract --version
tesseract --list-langs
```

**Explanation**: `TESSDATA_PREFIX` tells Tesseract where to find language data files. This prevents "failed to load language" errors during OCR.

---

## Step 2: Python Environment Setup

### 2.1 Create Application Directory

```bash
# Create directory for the application
sudo mkdir -p /opt/sentinel_ai
sudo chown $USER:$USER /opt/sentinel_ai
cd /opt/sentinel_ai
```

**Explanation**: Using `/opt` is a Linux best practice for third-party applications. We set ownership to avoid permission issues.

### 2.2 Create Python Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel
```

**Explanation**: Virtual environments isolate Python dependencies, preventing conflicts with system packages.

---

## Step 3: Application Code Deployment

### 3.1 Clone or Copy Application Code

**Option A: Clone from Git Repository** (Recommended for development)

```bash
# Clone the repository
git clone https://github.com/MohitRana2001/sentinel_AI.git .

# Navigate to backend directory
cd backend
```

**Option B: Copy Files Manually** (Recommended for production)

```bash
# From your local machine, copy the backend directory
# Replace <VM_IP> with your VM's IP address
scp -r /path/to/sentinel_AI/backend user@<VM_IP>:/opt/sentinel_ai/
```

### 3.2 Install Python Dependencies

```bash
# Ensure you're in the virtual environment
source /opt/sentinel_ai/venv/bin/activate

# Navigate to backend directory
cd /opt/sentinel_ai/backend

# Install all required packages
pip install -r requirements.txt
```

**Explanation**: This installs all Python libraries needed by the Document Processor, including:
- FastAPI and database clients
- Redis client
- Google Cloud Storage SDK
- Document processing libraries (PyMuPDF, python-docx, docling)
- Machine learning libraries (langchain, ollama client)
- OCR and translation utilities

**Note**: This step may take 10-15 minutes depending on your internet connection.

---

## Step 4: Configuration

### 4.1 Create Environment Configuration File

Create a `.env` file with your specific configuration:

```bash
cd /opt/sentinel_ai/backend
nano .env
```

Add the following configuration (replace placeholders with actual values):

```bash
# ============================================
# Document Processor VM Configuration
# ============================================

# Environment
ENV=production
DEBUG=False

# Redis Configuration
# Point to your main Redis server
REDIS_HOST=<REDIS_SERVER_IP>
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=<REDIS_PASSWORD>  # Leave empty if no password

# Redis Queue Names (must match main application)
REDIS_QUEUE_DOCUMENT=document_queue
REDIS_QUEUE_GRAPH=graph_queue

# AlloyDB/PostgreSQL Configuration
# Point to your main database server
ALLOYDB_HOST=<ALLOYDB_SERVER_IP>
ALLOYDB_PORT=5432
ALLOYDB_USER=postgres
ALLOYDB_PASSWORD=<DB_PASSWORD>
ALLOYDB_DATABASE=sentinel_db

# Storage Configuration
# Use 'gcs' for Google Cloud Storage or 'local' for network storage
STORAGE_BACKEND=gcs

# GCS Configuration (if using GCS)
GCS_BUCKET_NAME=<YOUR_BUCKET_NAME>
GCS_PROJECT_ID=<YOUR_PROJECT_ID>
GCS_CREDENTIALS_PATH=/opt/sentinel_ai/credentials/gcs-key.json

# Local Storage Configuration (if using local/network storage)
LOCAL_STORAGE_PATH=/mnt/shared_storage
# Or for local testing:
# LOCAL_GCS_STORAGE_PATH=/opt/sentinel_ai/.local_gcs

# Summary LLM Configuration
# Point to Ollama server running Gemma3:1b or similar model
SUMMARY_LLM_HOST=<OLLAMA_SERVER_IP>
SUMMARY_LLM_PORT=11434
SUMMARY_LLM_MODEL=gemma3:1b

# Embedding LLM Configuration
# Point to Ollama server running embedding model
EMBEDDING_LLM_HOST=<OLLAMA_SERVER_IP>
EMBEDDING_LLM_PORT=11434
EMBEDDING_MODEL=embeddinggemma:latest

# Document Processing Configuration
CHUNK_SIZE=2000
CHUNK_OVERLAP=100
TRANSLATION_THRESHOLD_MB=10
TRANSLATION_LOCAL=True

# File Upload Configuration (for reference only)
MAX_UPLOAD_FILES=10
MAX_FILE_SIZE_MB=4
ALLOWED_EXTENSIONS=.pdf,.docx,.txt,.mp3,.wav,.mp4,.avi,.mov
```

**Save and exit**: Press `Ctrl+X`, then `Y`, then `Enter`

### 4.2 Configuration Explanation

Let's break down the critical configuration sections:

#### Redis Configuration
```bash
REDIS_HOST=<REDIS_SERVER_IP>      # IP address of your Redis server
REDIS_PORT=6379                    # Default Redis port
REDIS_PASSWORD=<REDIS_PASSWORD>    # Password if Redis has AUTH enabled
```
- The Document Processor **pulls messages** from the `document_queue`
- It **pushes messages** to the `graph_queue` after processing
- Redis acts as the coordination layer between services

#### Database Configuration
```bash
ALLOYDB_HOST=<ALLOYDB_SERVER_IP>   # IP of your PostgreSQL/AlloyDB server
ALLOYDB_PORT=5432                  # Default PostgreSQL port
```
- Document metadata, chunks, and embeddings are stored here
- The processor needs both READ and WRITE access to the database

#### Storage Configuration
```bash
STORAGE_BACKEND=gcs                # 'gcs' or 'local'
GCS_BUCKET_NAME=<YOUR_BUCKET_NAME> # Your GCS bucket
```
- **GCS mode**: Downloads files from Google Cloud Storage
- **Local mode**: Uses local filesystem or network-mounted storage
- All processed outputs (extracted text, summaries) are uploaded back to storage

#### LLM Configuration
```bash
SUMMARY_LLM_HOST=<OLLAMA_SERVER_IP>  # Ollama server for summarization
SUMMARY_LLM_MODEL=gemma3:1b          # Smaller model for speed
EMBEDDING_LLM_HOST=<OLLAMA_SERVER_IP> # Ollama server for embeddings
```
- Summary LLM generates concise summaries of documents
- Embedding LLM creates vector representations for semantic search
- Can point to the same Ollama instance or separate instances

### 4.3 GCS Credentials Setup (If Using GCS)

If you're using Google Cloud Storage:

```bash
# Create credentials directory
mkdir -p /opt/sentinel_ai/credentials

# Copy your GCS service account key
# From your local machine:
scp /path/to/gcs-key.json user@<VM_IP>:/opt/sentinel_ai/credentials/

# Set appropriate permissions
chmod 600 /opt/sentinel_ai/credentials/gcs-key.json
```

**Explanation**: The service account key authenticates the Document Processor to access your GCS bucket. Keep this file secure with restricted permissions.

---

## Step 5: Test Connectivity

Before starting the service, verify all connections work:

### 5.1 Test Redis Connection

```bash
# Install Redis CLI if not already present
sudo apt install -y redis-tools

# Test connection (replace <REDIS_SERVER_IP> with actual IP)
redis-cli -h <REDIS_SERVER_IP> -p 6379 ping

# If Redis has a password:
redis-cli -h <REDIS_SERVER_IP> -p 6379 -a <REDIS_PASSWORD> ping

# Expected output: PONG
```

### 5.2 Test Database Connection

```bash
# Test PostgreSQL connection
psql -h <ALLOYDB_SERVER_IP> -U postgres -d sentinel_db -c "SELECT version();"

# You'll be prompted for the password
```

**Expected output**: PostgreSQL version information

### 5.3 Test Storage Access

**For GCS:**

```bash
# Activate virtual environment
source /opt/sentinel_ai/venv/bin/activate

# Test GCS access with Python
python3 << EOF
from google.cloud import storage
import os

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/opt/sentinel_ai/credentials/gcs-key.json'

client = storage.Client()
bucket = client.bucket('<YOUR_BUCKET_NAME>')
print(f"Successfully connected to bucket: {bucket.name}")
blobs = list(bucket.list_blobs(max_results=5))
print(f"Found {len(blobs)} objects (showing first 5)")
EOF
```

**For Local Storage:**

```bash
# Check if directory is accessible
ls -la /mnt/shared_storage
# or
ls -la /opt/sentinel_ai/.local_gcs
```

### 5.4 Test Ollama LLM Connection

```bash
# Test summary LLM
curl http://<OLLAMA_SERVER_IP>:11434/api/tags

# Expected output: JSON list of available models including gemma3:1b
```

---

## Step 6: Create Systemd Service

To run the Document Processor as a system service that starts automatically on boot:

### 6.1 Create Service File

```bash
sudo nano /etc/systemd/system/document-processor.service
```

Add the following content:

```ini
[Unit]
Description=Sentinel AI Document Processor Service
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=<YOUR_USERNAME>
Group=<YOUR_USERNAME>
WorkingDirectory=/opt/sentinel_ai/backend
Environment="PATH=/opt/sentinel_ai/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata/"
EnvironmentFile=/opt/sentinel_ai/backend/.env

# Start the document processor service
ExecStart=/opt/sentinel_ai/venv/bin/python3 /opt/sentinel_ai/backend/processors/document_processor_service.py

# Restart policy
Restart=always
RestartSec=10

# Logging
StandardOutput=append:/var/log/sentinel_ai/document-processor.log
StandardError=append:/var/log/sentinel_ai/document-processor-error.log

# Security settings
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

**Replace** `<YOUR_USERNAME>` with your actual username (run `whoami` to find it).

### 6.2 Create Log Directory

```bash
sudo mkdir -p /var/log/sentinel_ai
sudo chown $USER:$USER /var/log/sentinel_ai
```

### 6.3 Enable and Start Service

```bash
# Reload systemd to recognize the new service
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable document-processor.service

# Start the service
sudo systemctl start document-processor.service

# Check service status
sudo systemctl status document-processor.service
```

**Expected output**: Service should be "active (running)"

---

## Step 7: Verify Service is Working

### 7.1 Check Service Logs

```bash
# View real-time logs
tail -f /var/log/sentinel_ai/document-processor.log

# Check for errors
tail -f /var/log/sentinel_ai/document-processor-error.log
```

**What to look for:**
- "Starting Document Processor Service..." - Service started
- "Listening to queue: document_queue" - Connected to Redis
- No error messages about connection failures

### 7.2 Monitor Redis Queue

```bash
# Check queue length
redis-cli -h <REDIS_SERVER_IP> -p 6379 LLEN document_queue

# Peek at a message (without removing it)
redis-cli -h <REDIS_SERVER_IP> -p 6379 LINDEX document_queue -1
```

### 7.3 Test with a Sample Upload

From your **main application**, upload a test document:

```bash
# This should be run from wherever your main FastAPI app is running
curl -X POST "http://<MAIN_APP_IP>:8000/api/v1/upload" \
  -H "Authorization: Bearer <YOUR_TOKEN>" \
  -F "files=@test.pdf"
```

Then monitor the Document Processor logs:

```bash
tail -f /var/log/sentinel_ai/document-processor.log
```

**Expected log flow:**
1. "Document Processor received file: test.pdf"
2. "Processing: uploads/..."
3. "Successfully extracted X characters"
4. "Generating summary..."
5. "Creating embeddings..."
6. "Queuing for graph processing..."
7. "Completed processing: test.pdf"

---

## Step 8: Scaling and Performance

### 8.1 Running Multiple Workers

To process documents in parallel, run multiple instances:

```bash
# Copy the service file
sudo cp /etc/systemd/system/document-processor.service \
     /etc/systemd/system/document-processor@.service

# Start multiple instances
sudo systemctl start document-processor@1.service
sudo systemctl start document-processor@2.service
sudo systemctl start document-processor@3.service

# Enable them to start on boot
sudo systemctl enable document-processor@{1..3}.service
```

**Explanation**: Each worker independently pulls from the Redis queue. Redis ensures each message is processed by only ONE worker, providing true parallelism.

### 8.2 Performance Tuning

**Adjust concurrency based on your VM resources:**

- **2-4 workers**: For 4-core VMs with 8GB RAM
- **4-8 workers**: For 8-core VMs with 16GB RAM
- **8-16 workers**: For 16+ core VMs with 32GB+ RAM

**Monitor resource usage:**

```bash
# CPU and memory usage
htop

# Disk I/O
iostat -x 5

# Network usage
iftop
```

---

## Step 9: Maintenance and Troubleshooting

### 9.1 Service Management Commands

```bash
# Start service
sudo systemctl start document-processor.service

# Stop service
sudo systemctl stop document-processor.service

# Restart service
sudo systemctl restart document-processor.service

# View status
sudo systemctl status document-processor.service

# View logs
journalctl -u document-processor.service -f
```

### 9.2 Common Issues and Solutions

#### Issue 1: "Failed to connect to Redis"

**Symptoms**: Service fails to start, logs show connection refused

**Solution**:
```bash
# Check Redis is accessible
redis-cli -h <REDIS_SERVER_IP> -p 6379 ping

# Check firewall rules
sudo ufw status

# Allow Redis port if blocked
sudo ufw allow from <VM_IP> to any port 6379
```

#### Issue 2: "Failed to connect to AlloyDB"

**Symptoms**: Database errors in logs

**Solution**:
```bash
# Test database connection
psql -h <ALLOYDB_SERVER_IP> -U postgres -d sentinel_db

# Check database is accepting connections
# On the database server, ensure postgresql.conf has:
# listen_addresses = '*'

# Check pg_hba.conf allows connections from VM IP
```

#### Issue 3: "Tesseract failed to load language"

**Symptoms**: OCR errors for PDFs

**Solution**:
```bash
# Verify TESSDATA_PREFIX is set
echo $TESSDATA_PREFIX

# Verify language files exist
ls -la /usr/share/tesseract-ocr/5/tessdata/

# Reinstall language packs
sudo apt install --reinstall tesseract-ocr-eng tesseract-ocr-hin
```

#### Issue 4: "GCS authentication failed"

**Symptoms**: Cannot download files from GCS

**Solution**:
```bash
# Verify credentials file exists and has correct permissions
ls -la /opt/sentinel_ai/credentials/gcs-key.json
chmod 600 /opt/sentinel_ai/credentials/gcs-key.json

# Test GCS access manually (see Step 5.3)

# Ensure service account has Storage Object Viewer role
```

#### Issue 5: "Ollama LLM timeout"

**Symptoms**: Summary generation fails

**Solution**:
```bash
# Check Ollama is running
curl http://<OLLAMA_SERVER_IP>:11434/api/tags

# Verify model is pulled
curl http://<OLLAMA_SERVER_IP>:11434/api/tags | grep gemma3:1b

# If model not found, pull it:
# (Run on Ollama server)
ollama pull gemma3:1b
```

### 9.3 Log Rotation

Prevent logs from consuming too much disk space:

```bash
sudo nano /etc/logrotate.d/sentinel-document-processor
```

Add:

```
/var/log/sentinel_ai/document-processor*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    missingok
    copytruncate
}
```

### 9.4 Monitoring and Alerts

**Monitor queue depth:**

```bash
# Check if queue is backing up
watch -n 5 'redis-cli -h <REDIS_SERVER_IP> -p 6379 LLEN document_queue'
```

**If queue is growing:**
- Add more worker instances (Step 8.1)
- Check if workers are processing slowly (check logs)
- Check if Ollama LLM is responding (it may be overloaded)

---

## Step 10: Security Hardening

### 10.1 Firewall Configuration

```bash
# Enable UFW firewall
sudo ufw enable

# Allow SSH
sudo ufw allow ssh

# Allow only necessary outbound connections
# Redis, AlloyDB, and Ollama are typically on internal network

# Deny incoming connections (this is a worker, not a server)
sudo ufw default deny incoming
sudo ufw default allow outgoing
```

### 10.2 Secure Credentials

```bash
# Ensure .env file is not world-readable
chmod 600 /opt/sentinel_ai/backend/.env

# Ensure GCS key is secure
chmod 600 /opt/sentinel_ai/credentials/gcs-key.json

# Set ownership
chown $USER:$USER /opt/sentinel_ai/backend/.env
chown $USER:$USER /opt/sentinel_ai/credentials/gcs-key.json
```

### 10.3 Updates and Patches

```bash
# Regular system updates
sudo apt update && sudo apt upgrade -y

# Update Python packages (periodically)
source /opt/sentinel_ai/venv/bin/activate
pip install --upgrade -r /opt/sentinel_ai/backend/requirements.txt
```

---

## Summary

You have successfully set up the Document Processor VM! Here's what you accomplished:

1. ✅ Installed system dependencies (Tesseract OCR, image libraries)
2. ✅ Created Python environment with all required packages
3. ✅ Configured connection to Redis, AlloyDB, GCS, and Ollama LLMs
4. ✅ Set up systemd service for automatic startup
5. ✅ Configured logging and monitoring
6. ✅ Implemented security best practices

### Key Points to Remember

- **Redis Queue**: The service pulls from `document_queue` and pushes to `graph_queue`
- **Parallel Processing**: Multiple worker instances can run simultaneously
- **Stateless Design**: Each worker can process any message independently
- **Fault Tolerance**: If a worker crashes, systemd automatically restarts it
- **Resource Management**: Scale workers based on CPU/RAM availability

### Next Steps

1. Set up the **Graph Processor VM** (see VM_SETUP_GRAPH_PROCESSOR.md)
2. Monitor both services to ensure they work together smoothly
3. Test end-to-end flow: Upload → Document Processing → Graph Processing → Results
4. Set up automated backups of logs and configurations
5. Implement monitoring dashboards (Prometheus + Grafana recommended)

### Support

For issues or questions:
- Check logs: `/var/log/sentinel_ai/document-processor.log`
- Review this guide's troubleshooting section
- Verify all connectivity tests from Step 5
- Ensure Redis queue is not backing up

---

**Congratulations!** Your Document Processor VM is now operational. 🎉
