# Quick Start Guide: VM Integration for Sentinel AI

This guide provides a streamlined path to set up the Document and Graph Processor VMs. For detailed explanations, refer to the full setup guides.

## Prerequisites Checklist

Before starting, ensure you have:

- [ ] 2 VMs provisioned (Ubuntu 22.04 LTS)
  - [ ] Document Processor VM: 4+ cores, 8+ GB RAM, 50 GB disk
  - [ ] Graph Processor VM: 4+ cores, 16+ GB RAM, 50 GB disk
- [ ] SSH access to both VMs
- [ ] Redis server running and accessible
- [ ] AlloyDB/PostgreSQL server running and accessible
- [ ] Neo4j server running and accessible
- [ ] Ollama LLM servers running with models:
  - [ ] `gemma3:1b` for summaries
  - [ ] `gemma3:4b` for graph extraction
  - [ ] `embeddinggemma:latest` for embeddings
- [ ] GCS bucket created (or network storage mounted)
- [ ] Service account key for GCS (if using GCS)

## Document Processor VM - Quick Setup

### 1. Initial Setup (5 minutes)

```bash
# SSH into Document Processor VM
ssh user@<DOCUMENT_PROCESSOR_IP>

# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y build-essential curl wget git python3 python3-pip python3-venv \
  tesseract-ocr tesseract-ocr-eng tesseract-ocr-hin tesseract-ocr-ben \
  poppler-utils libjpeg-dev libpng-dev postgresql-client

# Set Tesseract environment variable
echo 'export TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata/' | sudo tee -a /etc/environment
export TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata/
```

### 2. Application Setup (10 minutes)

```bash
# Create application directory
sudo mkdir -p /opt/sentinel_ai
sudo chown $USER:$USER /opt/sentinel_ai
cd /opt/sentinel_ai

# Clone repository (or copy files)
git clone https://github.com/MohitRana2001/sentinel_AI.git .
cd backend

# Create virtual environment
python3 -m venv ../venv
source ../venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configuration (5 minutes)

```bash
# Copy configuration template from repository
# If you cloned the repo:
cp ../config-templates/document-processor.env.template .env

# Or create .env manually using the template as reference:
# https://github.com/MohitRana2001/sentinel_AI/blob/main/config-templates/document-processor.env.template

# Edit configuration
nano .env

# Replace these placeholders:
# - <REDIS_SERVER_IP>
# - <REDIS_PASSWORD>
# - <ALLOYDB_SERVER_IP>
# - <DB_PASSWORD>
# - <YOUR_BUCKET_NAME>
# - <YOUR_PROJECT_ID>
# - <OLLAMA_SERVER_IP>

# Copy GCS credentials if using GCS
mkdir -p /opt/sentinel_ai/credentials
# scp your-gcs-key.json user@<VM_IP>:/opt/sentinel_ai/credentials/
chmod 600 /opt/sentinel_ai/credentials/gcs-key.json
chmod 600 .env
```

### 4. Test Connectivity (5 minutes)

```bash
# Test Redis
redis-cli -h <REDIS_SERVER_IP> -p 6379 ping

# Test Database
psql -h <ALLOYDB_SERVER_IP> -U postgres -d sentinel_db -c "SELECT 1"

# Test Ollama
curl http://<OLLAMA_SERVER_IP>:11434/api/tags

# Test storage (if GCS)
source /opt/sentinel_ai/venv/bin/activate
python3 -c "from google.cloud import storage; import os; os.environ['GOOGLE_APPLICATION_CREDENTIALS']='/opt/sentinel_ai/credentials/gcs-key.json'; client=storage.Client(); print('GCS OK')"
```

### 5. Create Systemd Service (5 minutes)

```bash
# Create service file
sudo nano /etc/systemd/system/document-processor.service
```

Paste this content (replace `<YOUR_USERNAME>`):

```ini
[Unit]
Description=Sentinel AI Document Processor Service
After=network.target

[Service]
Type=simple
User=<YOUR_USERNAME>
WorkingDirectory=/opt/sentinel_ai/backend
Environment="PATH=/opt/sentinel_ai/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata/"
EnvironmentFile=/opt/sentinel_ai/backend/.env
ExecStart=/opt/sentinel_ai/venv/bin/python3 /opt/sentinel_ai/backend/processors/document_processor_service.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/sentinel_ai/document-processor.log
StandardError=append:/var/log/sentinel_ai/document-processor-error.log

[Install]
WantedBy=multi-user.target
```

```bash
# Create log directory
sudo mkdir -p /var/log/sentinel_ai
sudo chown $USER:$USER /var/log/sentinel_ai

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable document-processor.service
sudo systemctl start document-processor.service
sudo systemctl status document-processor.service

# Check logs
tail -f /var/log/sentinel_ai/document-processor.log
```

**Expected output**: "Listening to queue: document_queue"

---

## Graph Processor VM - Quick Setup

### 1. Initial Setup (5 minutes)

```bash
# SSH into Graph Processor VM
ssh user@<GRAPH_PROCESSOR_IP>

# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y build-essential curl wget git python3 python3-pip python3-venv \
  postgresql-client net-tools
```

### 2. Application Setup (10 minutes)

```bash
# Create application directory
sudo mkdir -p /opt/sentinel_ai
sudo chown $USER:$USER /opt/sentinel_ai
cd /opt/sentinel_ai

# Clone repository (or copy files)
git clone https://github.com/MohitRana2001/sentinel_AI.git .
cd backend

# Create virtual environment
python3 -m venv ../venv
source ../venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configuration (5 minutes)

```bash
# Copy configuration template from repository
# If you cloned the repo:
cp ../config-templates/graph-processor.env.template .env

# Or create .env manually using the template as reference:
# https://github.com/MohitRana2001/sentinel_AI/blob/main/config-templates/graph-processor.env.template

# Edit configuration
nano .env

# Replace these placeholders:
# - <REDIS_SERVER_IP>
# - <REDIS_PASSWORD>
# - <ALLOYDB_SERVER_IP>
# - <DB_PASSWORD>
# - <NEO4J_SERVER_IP>
# - <NEO4J_PASSWORD>
# - <YOUR_BUCKET_NAME>
# - <YOUR_PROJECT_ID>
# - <OLLAMA_SERVER_IP>

# Copy GCS credentials if using GCS
mkdir -p /opt/sentinel_ai/credentials
# scp your-gcs-key.json user@<VM_IP>:/opt/sentinel_ai/credentials/
chmod 600 /opt/sentinel_ai/credentials/gcs-key.json
chmod 600 .env
```

### 4. Test Connectivity (5 minutes)

```bash
# Test Redis
redis-cli -h <REDIS_SERVER_IP> -p 6379 ping

# Test Database
psql -h <ALLOYDB_SERVER_IP> -U postgres -d sentinel_db -c "SELECT 1"

# Test Neo4j
sudo apt install -y cypher-shell
cypher-shell -a bolt://<NEO4J_SERVER_IP>:7687 -u neo4j -p <NEO4J_PASSWORD> "RETURN 1"

# Test Ollama
curl http://<OLLAMA_SERVER_IP>:11434/api/tags | grep gemma3:4b
```

### 5. Create Systemd Service (5 minutes)

```bash
# Create service file
sudo nano /etc/systemd/system/graph-processor.service
```

Paste this content (replace `<YOUR_USERNAME>`):

```ini
[Unit]
Description=Sentinel AI Graph Processor Service
After=network.target

[Service]
Type=simple
User=<YOUR_USERNAME>
WorkingDirectory=/opt/sentinel_ai/backend
Environment="PATH=/opt/sentinel_ai/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
EnvironmentFile=/opt/sentinel_ai/backend/.env
ExecStart=/opt/sentinel_ai/venv/bin/python3 /opt/sentinel_ai/backend/processors/graph_processor_service.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/sentinel_ai/graph-processor.log
StandardError=append:/var/log/sentinel_ai/graph-processor-error.log
MemoryMax=24G
CPUQuota=400%

[Install]
WantedBy=multi-user.target
```

```bash
# Create log directory
sudo mkdir -p /var/log/sentinel_ai
sudo chown $USER:$USER /var/log/sentinel_ai

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable graph-processor.service
sudo systemctl start graph-processor.service
sudo systemctl status graph-processor.service

# Check logs
tail -f /var/log/sentinel_ai/graph-processor.log
```

**Expected output**: "Listening to queue: graph_queue"

---

## End-to-End Test

### 1. Upload a Document

From your main application:

```bash
curl -X POST "http://<MAIN_APP_IP>:8000/api/v1/upload" \
  -H "Authorization: Bearer <YOUR_TOKEN>" \
  -F "files=@test.pdf"
```

### 2. Monitor Document Processing

```bash
# On Document Processor VM
tail -f /var/log/sentinel_ai/document-processor.log
```

Expected flow:
1. "Document Processor received file: test.pdf"
2. "Extracting text..."
3. "Generating summary..."
4. "Creating embeddings..."
5. "Queuing for graph processing..."

### 3. Monitor Graph Processing

```bash
# On Graph Processor VM
tail -f /var/log/sentinel_ai/graph-processor.log
```

Expected flow:
1. "Graph Processor received job for document: X"
2. "Extracting entities and relationships..."
3. "Extracted Y nodes and Z relationships"
4. "Syncing graph for document X..."
5. "Job completed"

### 4. Check Results

```bash
# Check job status
curl "http://<MAIN_APP_IP>:8000/api/v1/jobs/<JOB_ID>/status" \
  -H "Authorization: Bearer <YOUR_TOKEN>"

# Check graph in Neo4j Browser
# Open: http://<NEO4J_IP>:7474
# Run: MATCH (n) RETURN n LIMIT 25
```

---

## Scaling Workers

### Document Processor (add more workers)

```bash
# Copy service file
sudo cp /etc/systemd/system/document-processor.service \
     /etc/systemd/system/document-processor@.service

# Start multiple workers
sudo systemctl start document-processor@{1..3}.service
sudo systemctl enable document-processor@{1..3}.service

# Check status
sudo systemctl status document-processor@*.service
```

### Graph Processor (add more workers)

```bash
# Copy service file
sudo cp /etc/systemd/system/graph-processor.service \
     /etc/systemd/system/graph-processor@.service

# Start 2-3 workers (don't over-scale, LLM is bottleneck)
sudo systemctl start graph-processor@{1..2}.service
sudo systemctl enable graph-processor@{1..2}.service

# Check status
sudo systemctl status graph-processor@*.service
```

---

## Monitoring

### Check Queue Depths

```bash
# Document queue
redis-cli -h <REDIS_SERVER_IP> -p 6379 LLEN document_queue

# Graph queue
redis-cli -h <REDIS_SERVER_IP> -p 6379 LLEN graph_queue
```

### Watch Queues in Real-Time

```bash
watch -n 2 'redis-cli -h <REDIS_SERVER_IP> -p 6379 LLEN document_queue'
watch -n 2 'redis-cli -h <REDIS_SERVER_IP> -p 6379 LLEN graph_queue'
```

### Check Resource Usage

```bash
# CPU and memory
htop

# Disk space
df -h

# Network
iftop
```

---

## Troubleshooting

### Document Processor Issues

```bash
# Check service status
sudo systemctl status document-processor.service

# View logs
tail -100 /var/log/sentinel_ai/document-processor-error.log

# Restart service
sudo systemctl restart document-processor.service

# Test Tesseract
tesseract --version
tesseract --list-langs
```

### Graph Processor Issues

```bash
# Check service status
sudo systemctl status graph-processor.service

# View logs
tail -100 /var/log/sentinel_ai/graph-processor-error.log

# Restart service
sudo systemctl restart graph-processor.service

# Test Neo4j connection
cypher-shell -a bolt://<NEO4J_IP>:7687 -u neo4j -p <PASSWORD> "RETURN 1"
```

### Common Issues

1. **"Connection refused" errors**: Check firewall rules and service status
2. **"Authentication failed"**: Verify passwords in .env file
3. **"Queue not moving"**: Check if workers are running (`systemctl status`)
4. **"Out of memory"**: Reduce number of workers or increase VM RAM
5. **"LLM timeout"**: Check Ollama server, ensure model is loaded

---

## Next Steps

1. **Set up monitoring**: Install Prometheus + Grafana
2. **Configure alerts**: Set up alerts for queue depth, error rate, resource usage
3. **Backup configuration**: Save .env files and service configs
4. **Document runbooks**: Create procedures for common issues
5. **Load testing**: Test with many concurrent uploads
6. **Optimize performance**: Tune worker counts based on observed metrics

---

## Complete Documentation

For detailed explanations and advanced topics:

- **VM_SETUP_DOCUMENT_PROCESSOR.md**: Complete Document Processor setup guide
- **VM_SETUP_GRAPH_PROCESSOR.md**: Complete Graph Processor setup guide
- **VM_INTEGRATION_ARCHITECTURE.md**: System architecture and design decisions
- **config-templates/**: Environment configuration templates

---

## Support

If you encounter issues:

1. Check the detailed setup guides for your specific issue
2. Review the troubleshooting sections
3. Verify all connectivity tests pass
4. Check logs for specific error messages
5. Ensure all services (Redis, AlloyDB, Neo4j, Ollama) are accessible

**Total Setup Time**: ~1 hour for both VMs

**Congratulations!** You now have a fully distributed document processing pipeline! 🎉
