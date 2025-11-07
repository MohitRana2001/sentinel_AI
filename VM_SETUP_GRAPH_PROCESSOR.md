# Graph Processor VM Setup Guide

## Overview

This guide provides detailed instructions for setting up the **Graph Processor Service** on a dedicated Virtual Machine (VM). The Graph Processor is responsible for:

- Extracting entities (people, organizations, locations, concepts) from processed documents
- Identifying relationships between entities
- Building knowledge graphs in Neo4j
- Storing graph metadata in AlloyDB for quick access
- Performing entity resolution across documents
- Creating cross-document entity links

## Architecture Context

The Graph Processor VM acts as a **downstream worker node** in the Sentinel AI distributed system:

```
┌─────────────────────┐     ┌─────────┐     ┌─────────────────────┐
│ Document Processor  │────▶│  Redis  │◀────│  Graph Processor    │
│      VM             │     │ (Queue) │     │       VM            │
└─────────────────────┘     └─────────┘     └─────────────────────┘
                                                      │
                                                      ▼
┌──────────────┐                           ┌─────────────────┐
│   AlloyDB    │◀──────────────────────────│     Neo4j       │
│  (Postgres)  │                           │  (Graph DB)     │
└──────────────┘                           └─────────────────┘
       ▲                                            │
       │                                            │
       └────────────────────────────────────────────┘
```

### Data Flow

1. **Document Processor** pushes completed documents to Redis queue (`graph_queue`)
2. **Graph Processor VM** pulls messages from Redis queue
3. **Graph Processor VM** downloads processed text from storage
4. **Graph Processor VM** uses LLM to extract entities and relationships
5. **Graph Processor VM** stores graph in Neo4j for visualization
6. **Graph Processor VM** stores metadata in AlloyDB for quick queries
7. **Graph Processor VM** performs entity resolution across documents
8. **Graph Processor VM** marks jobs as COMPLETED when all documents are processed

---

## Prerequisites

### System Requirements

- **Operating System**: Ubuntu 22.04 LTS or higher (recommended)
- **CPU**: Minimum 4 cores (8+ cores recommended for LLM processing)
- **RAM**: Minimum 16GB (32GB+ recommended - LLM is memory-intensive)
- **Disk Space**: Minimum 50GB free space
- **Network**: Stable internet connection for accessing Redis, AlloyDB, Neo4j, and storage

### Required Access

Before starting, ensure you have:

1. **Network Access** to:
   - Redis server (port 6379)
   - AlloyDB/PostgreSQL server (port 5432)
   - Neo4j server (ports 7474 for HTTP, 7687 for Bolt)
   - GCS (if using Google Cloud Storage) or shared network storage
   - Ollama LLM server for graph extraction (port 11434)

2. **Credentials**:
   - GCS service account key (if using GCS)
   - AlloyDB connection credentials
   - Redis password (if authentication is enabled)
   - Neo4j username and password

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

The Graph Processor requires system-level dependencies for database connectivity:

```bash
# Install PostgreSQL client for AlloyDB connectivity
sudo apt install -y postgresql-client

# Install networking tools for diagnostics
sudo apt install -y net-tools dnsutils

# Install system monitoring tools
sudo apt install -y htop iotop
```

**Explanation**:
- **PostgreSQL client**: Enables database connectivity testing
- **Networking tools**: Helps diagnose connectivity issues
- **Monitoring tools**: Tracks resource usage (important for LLM workloads)

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

**Explanation**: This installs all Python libraries needed by the Graph Processor, including:
- FastAPI and database clients
- Redis client
- Neo4j driver and LangChain Neo4j integration
- Google Cloud Storage SDK
- LangChain and Ollama client for LLM-based entity extraction
- Graph processing libraries

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
# Graph Processor VM Configuration
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
REDIS_QUEUE_GRAPH=graph_queue

# AlloyDB/PostgreSQL Configuration
# Point to your main database server
ALLOYDB_HOST=<ALLOYDB_SERVER_IP>
ALLOYDB_PORT=5432
ALLOYDB_USER=postgres
ALLOYDB_PASSWORD=<DB_PASSWORD>
ALLOYDB_DATABASE=sentinel_db

# Neo4j Configuration
# Point to your Neo4j server
NEO4J_URI=bolt://<NEO4J_SERVER_IP>:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=<NEO4J_PASSWORD>
NEO4J_DATABASE=neo4j

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

# Graph LLM Configuration
# Point to Ollama server running Gemma3:4b or similar model
# Note: Graph extraction requires a larger model than document processing
GRAPH_LLM_HOST=<OLLAMA_SERVER_IP>
GRAPH_LLM_PORT=11434
GRAPH_LLM_MODEL=gemma3:4b

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
- The Graph Processor **pulls messages** from the `graph_queue`
- Each message contains document_id, job_id, and path to processed text
- Redis acts as the coordination layer between Document and Graph processors

#### Database Configuration
```bash
ALLOYDB_HOST=<ALLOYDB_SERVER_IP>   # IP of your PostgreSQL/AlloyDB server
ALLOYDB_PORT=5432                  # Default PostgreSQL port
```
- Graph metadata (entities, relationships) is stored in AlloyDB
- Job completion status is updated in AlloyDB
- The processor needs both READ and WRITE access to the database

#### Neo4j Configuration
```bash
NEO4J_URI=bolt://<NEO4J_SERVER_IP>:7687  # Neo4j Bolt protocol endpoint
NEO4J_USERNAME=neo4j                      # Neo4j username (default: neo4j)
NEO4J_PASSWORD=<NEO4J_PASSWORD>           # Neo4j password
NEO4J_DATABASE=neo4j                      # Database name (default: neo4j)
```
- **Neo4j stores the actual graph structure** for visualization
- Bolt protocol (port 7687) is used for efficient graph queries
- HTTP interface (port 7474) is for browser-based administration
- Graph data includes nodes (entities) and relationships

#### Storage Configuration
```bash
STORAGE_BACKEND=gcs                # 'gcs' or 'local'
GCS_BUCKET_NAME=<YOUR_BUCKET_NAME> # Your GCS bucket
```
- **GCS mode**: Downloads processed text from Google Cloud Storage
- **Local mode**: Uses local filesystem or network-mounted storage
- Only reads from storage (no writes), as Document Processor has already saved text

#### LLM Configuration
```bash
GRAPH_LLM_HOST=<OLLAMA_SERVER_IP>  # Ollama server for entity extraction
GRAPH_LLM_MODEL=gemma3:4b          # Larger model for better entity recognition
```
- Graph LLM extracts entities and relationships from text
- **Requires a more powerful model than document processing** (4b vs 1b)
- This is the most resource-intensive operation
- Can point to a dedicated GPU-enabled Ollama instance for better performance

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

**Explanation**: The service account key authenticates the Graph Processor to access your GCS bucket. Keep this file secure with restricted permissions.

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

### 5.3 Test Neo4j Connection

```bash
# Test Neo4j connectivity using cypher-shell
# First, install cypher-shell if not available
sudo apt install -y cypher-shell

# Test connection
cypher-shell -a bolt://<NEO4J_SERVER_IP>:7687 -u neo4j -p <NEO4J_PASSWORD> "RETURN 1"

# Expected output: 1

# Alternative: Test with curl (HTTP interface)
curl -u neo4j:<NEO4J_PASSWORD> http://<NEO4J_SERVER_IP>:7474/db/data/
```

**Expected output**: JSON response with Neo4j server information

**Important**: If you get connection errors:
- Check Neo4j is running: `systemctl status neo4j` (on Neo4j server)
- Verify firewall allows port 7687: `sudo ufw allow 7687`
- Check Neo4j configuration allows remote connections

### 5.4 Test Storage Access

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

### 5.5 Test Ollama LLM Connection

```bash
# Test graph LLM
curl http://<OLLAMA_SERVER_IP>:11434/api/tags

# Expected output: JSON list of available models including gemma3:4b

# Verify the specific model is available
curl http://<OLLAMA_SERVER_IP>:11434/api/tags | grep "gemma3:4b"
```

**Important**: If the model is not listed:
```bash
# On the Ollama server, pull the model:
ollama pull gemma3:4b
```

---

## Step 6: Create Systemd Service

To run the Graph Processor as a system service that starts automatically on boot:

### 6.1 Create Service File

```bash
sudo nano /etc/systemd/system/graph-processor.service
```

Add the following content:

```ini
[Unit]
Description=Sentinel AI Graph Processor Service
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=<YOUR_USERNAME>
Group=<YOUR_USERNAME>
WorkingDirectory=/opt/sentinel_ai/backend
Environment="PATH=/opt/sentinel_ai/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
EnvironmentFile=/opt/sentinel_ai/backend/.env

# Start the graph processor service
ExecStart=/opt/sentinel_ai/venv/bin/python3 /opt/sentinel_ai/backend/processors/graph_processor_service.py

# Restart policy
Restart=always
RestartSec=10

# Logging
StandardOutput=append:/var/log/sentinel_ai/graph-processor.log
StandardError=append:/var/log/sentinel_ai/graph-processor-error.log

# Security settings
NoNewPrivileges=true
PrivateTmp=true

# Resource limits (adjust based on your VM)
# LLM processing can be memory-intensive
MemoryMax=24G
CPUQuota=400%

[Install]
WantedBy=multi-user.target
```

**Replace** `<YOUR_USERNAME>` with your actual username (run `whoami` to find it).

**Note**: `MemoryMax=24G` limits memory usage to 24GB. Adjust based on your VM's RAM.

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
sudo systemctl enable graph-processor.service

# Start the service
sudo systemctl start graph-processor.service

# Check service status
sudo systemctl status graph-processor.service
```

**Expected output**: Service should be "active (running)"

---

## Step 7: Verify Service is Working

### 7.1 Check Service Logs

```bash
# View real-time logs
tail -f /var/log/sentinel_ai/graph-processor.log

# Check for errors
tail -f /var/log/sentinel_ai/graph-processor-error.log
```

**What to look for:**
- "Starting Graph Processor Service..." - Service started
- "Listening to queue: graph_queue" - Connected to Redis
- "Using LLMGraphTransformer" - LLM client initialized
- No error messages about connection failures

### 7.2 Monitor Redis Queue

```bash
# Check queue length
redis-cli -h <REDIS_SERVER_IP> -p 6379 LLEN graph_queue

# Peek at a message (without removing it)
redis-cli -h <REDIS_SERVER_IP> -p 6379 LINDEX graph_queue -1
```

### 7.3 Test End-to-End Flow

**Step 1**: Upload a document through the main application (this will be processed by Document Processor first)

**Step 2**: Monitor Document Processor pushing to graph queue:

```bash
# Watch graph queue size increase
watch -n 2 'redis-cli -h <REDIS_SERVER_IP> -p 6379 LLEN graph_queue'
```

**Step 3**: Monitor Graph Processor logs:

```bash
tail -f /var/log/sentinel_ai/graph-processor.log
```

**Expected log flow:**
1. "Graph Processor received job for document: 123"
2. "Extracting entities and relationships..."
3. "Calling LLM for entity extraction..."
4. "Extracted X nodes and Y relationships"
5. "Syncing graph for document 123..."
6. "Added graph documents to Neo4j"
7. "Document successfully linked to user"
8. "Neo4j sync complete"
9. "Graph building completed for document 123"
10. "Job X marked as COMPLETED" (when all documents in job are done)

### 7.4 Verify Neo4j Graph

Access Neo4j Browser at `http://<NEO4J_SERVER_IP>:7474`

Run a simple query to see your data:

```cypher
// Count all nodes
MATCH (n) RETURN count(n)

// Show sample entities
MATCH (n)
WHERE NOT 'Document' IN labels(n) AND NOT 'User' IN labels(n)
RETURN n
LIMIT 25

// Show relationships
MATCH (n)-[r]->(m)
RETURN n, r, m
LIMIT 50
```

### 7.5 Verify AlloyDB Metadata

```bash
# Connect to database
psql -h <ALLOYDB_SERVER_IP> -U postgres -d sentinel_db

# Check graph entities
SELECT entity_name, entity_type, COUNT(*) 
FROM graph_entities 
GROUP BY entity_name, entity_type 
ORDER BY COUNT(*) DESC 
LIMIT 10;

# Check graph relationships
SELECT relationship_type, COUNT(*) 
FROM graph_relationships 
GROUP BY relationship_type 
ORDER BY COUNT(*) DESC;

# Exit
\q
```

---

## Step 8: Scaling and Performance

### 8.1 Running Multiple Workers

To process graphs in parallel, run multiple instances:

```bash
# Copy the service file
sudo cp /etc/systemd/system/graph-processor.service \
     /etc/systemd/system/graph-processor@.service

# Start multiple instances
sudo systemctl start graph-processor@1.service
sudo systemctl start graph-processor@2.service
sudo systemctl start graph-processor@3.service

# Enable them to start on boot
sudo systemctl enable graph-processor@{1..3}.service
```

**Explanation**: Each worker independently pulls from the Redis queue. Redis ensures each message is processed by only ONE worker.

**Important Considerations for Graph Processing:**

- **LLM is the bottleneck**: Each request to the LLM takes 5-30 seconds
- **Memory intensive**: Each worker needs 4-8GB RAM for LLM processing
- **Optimal worker count**: 2-4 workers for most setups
- **GPU acceleration**: If using GPU-enabled Ollama, more workers help (4-8)

### 8.2 Performance Tuning

**Adjust worker count based on resources:**

- **2-3 workers**: For 16GB RAM VMs with CPU-only LLM
- **4-6 workers**: For 32GB RAM VMs with CPU-only LLM
- **8-12 workers**: For GPU-enabled LLM servers (GPU handles parallelism better)

**Monitor resource usage:**

```bash
# CPU and memory usage
htop

# GPU usage (if applicable)
nvidia-smi -l 5

# Network usage
iftop
```

### 8.3 LLM Optimization

**For CPU-only setups:**

```bash
# On Ollama server, ensure model is loaded in memory
curl http://<OLLAMA_SERVER_IP>:11434/api/generate \
  -d '{"model": "gemma3:4b", "prompt": "test", "keep_alive": -1}'
```

**Setting `keep_alive: -1` keeps the model in memory permanently**, avoiding reload overhead.

**For GPU setups:**

- Ensure CUDA is properly configured
- Use larger batch sizes if Ollama supports it
- Consider using `llama.cpp` with GPU acceleration

---

## Step 9: Maintenance and Troubleshooting

### 9.1 Service Management Commands

```bash
# Start service
sudo systemctl start graph-processor.service

# Stop service
sudo systemctl stop graph-processor.service

# Restart service
sudo systemctl restart graph-processor.service

# View status
sudo systemctl status graph-processor.service

# View logs
journalctl -u graph-processor.service -f
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

#### Issue 2: "Failed to connect to Neo4j"

**Symptoms**: "Neo4j not connected" or "Bolt connection failed"

**Solution**:
```bash
# Test Neo4j connection
cypher-shell -a bolt://<NEO4J_SERVER_IP>:7687 -u neo4j -p <PASSWORD> "RETURN 1"

# On Neo4j server, check if service is running
sudo systemctl status neo4j

# Check Neo4j logs for errors
sudo journalctl -u neo4j -n 100

# Verify Neo4j accepts remote connections
# Edit /etc/neo4j/neo4j.conf:
# dbms.connector.bolt.listen_address=0.0.0.0:7687
# dbms.connector.http.listen_address=0.0.0.0:7474

# Restart Neo4j
sudo systemctl restart neo4j
```

#### Issue 3: "LLM timeout" or "Ollama not responding"

**Symptoms**: "Entity extraction failed", "LLM timeout after 60s"

**Solution**:
```bash
# Check Ollama is running and responsive
curl http://<OLLAMA_SERVER_IP>:11434/api/tags

# Check if model is loaded
curl http://<OLLAMA_SERVER_IP>:11434/api/ps

# If Ollama is slow, check resource usage on LLM server
ssh <OLLAMA_SERVER>
htop  # Check CPU/RAM
nvidia-smi  # Check GPU (if applicable)

# If model is not loaded, warm it up:
curl http://<OLLAMA_SERVER_IP>:11434/api/generate \
  -d '{"model": "gemma3:4b", "prompt": "test", "keep_alive": -1}'

# Consider upgrading to a faster model or adding GPU
```

#### Issue 4: "No graph documents generated"

**Symptoms**: "Extracted 0 nodes and 0 relationships"

**Solution**:

This usually means the LLM didn't extract any entities. Possible causes:

```bash
# Check if text is empty
# Look in logs for "Text truncated to X chars"
# If X is very small, the document might not have enough content

# Check LLM is working properly
curl http://<OLLAMA_SERVER_IP>:11434/api/generate \
  -d '{"model": "gemma3:4b", "prompt": "Extract entities from: John Smith works at Microsoft in Seattle", "stream": false}'

# Try a smaller, simpler document to test
# If it works for simple docs but not complex ones, LLM might need more time
```

#### Issue 5: "Job stuck in PROCESSING status"

**Symptoms**: Job never reaches COMPLETED status

**Solution**:
```bash
# Check if all documents have graph entities
psql -h <ALLOYDB_SERVER_IP> -U postgres -d sentinel_db << EOF
SELECT 
  j.id as job_id,
  j.total_files,
  j.processed_files,
  COUNT(DISTINCT d.id) as docs_created,
  COUNT(DISTINCT ge.document_id) as docs_with_graphs
FROM processing_jobs j
LEFT JOIN documents d ON j.id = d.job_id
LEFT JOIN graph_entities ge ON d.id = ge.document_id
WHERE j.status = 'PROCESSING'
GROUP BY j.id;
EOF

# If docs_with_graphs < total_files, some documents failed graph processing
# Check logs for those specific document IDs
grep "document_id.*<DOC_ID>" /var/log/sentinel_ai/graph-processor.log
```

#### Issue 6: "Memory issues / OOM killer"

**Symptoms**: Service stops unexpectedly, logs show "Killed"

**Solution**:
```bash
# Check system logs for OOM killer
sudo dmesg | grep -i "killed process"

# If Graph Processor was killed, it ran out of memory
# Solutions:
# 1. Reduce number of workers
sudo systemctl stop graph-processor@3.service
sudo systemctl disable graph-processor@3.service

# 2. Increase VM RAM
# 3. Use swap space (not ideal but helps):
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Make swap permanent
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### 9.3 Log Rotation

Prevent logs from consuming too much disk space:

```bash
sudo nano /etc/logrotate.d/sentinel-graph-processor
```

Add:

```
/var/log/sentinel_ai/graph-processor*.log {
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
watch -n 5 'redis-cli -h <REDIS_SERVER_IP> -p 6379 LLEN graph_queue'
```

**If queue is growing:**
- Check if workers are processing (look at logs)
- Check if LLM is responding (it may be overloaded)
- Check if Neo4j is accepting connections
- Consider adding more workers (but beware of memory limits)

**Monitor Neo4j performance:**

```cypher
// In Neo4j Browser
CALL dbms.queryJmx("org.neo4j:instance=kernel#0,name=Store file sizes")
```

**Monitor processing rate:**

```bash
# Count documents processed in last hour
psql -h <ALLOYDB_SERVER_IP> -U postgres -d sentinel_db -c "
SELECT COUNT(*) 
FROM graph_entities 
WHERE created_at > NOW() - INTERVAL '1 hour';
"
```

---

## Step 10: Security Hardening

### 10.1 Firewall Configuration

```bash
# Enable UFW firewall
sudo ufw enable

# Allow SSH
sudo ufw allow ssh

# Allow only necessary outbound connections
# Redis, AlloyDB, Neo4j, and Ollama are typically on internal network

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

### 10.3 Neo4j Security

**On Neo4j server**, ensure security is configured:

```bash
# Change default password
cypher-shell -u neo4j -p neo4j
# Run: ALTER CURRENT USER SET PASSWORD FROM 'neo4j' TO 'strong_password'

# Enable authentication (in neo4j.conf)
# dbms.security.auth_enabled=true

# Restrict network access
# dbms.connector.bolt.listen_address=<INTERNAL_IP>:7687
```

### 10.4 Updates and Patches

```bash
# Regular system updates
sudo apt update && sudo apt upgrade -y

# Update Python packages (periodically)
source /opt/sentinel_ai/venv/bin/activate
pip install --upgrade -r /opt/sentinel_ai/backend/requirements.txt
```

---

## Step 11: Advanced Topics

### 11.1 Entity Resolution Tuning

The Graph Processor performs **entity resolution** to link same entities across documents:

```python
# In graph_processor_service.py, entities are matched by "canonical_label"
# Canonical label normalizes: "John Smith" → "john-smith"
# This enables fuzzy matching

# To tune entity resolution, adjust the _canonical() function
# Current implementation:
# - Normalizes Unicode (é → e)
# - Converts to lowercase
# - Replaces non-alphanumeric with hyphens
# - Removes leading/trailing hyphens
```

**Example**: "Microsoft Corp.", "Microsoft Corporation", "microsoft-corp" all map to "microsoft-corp"

### 11.2 Cross-Document Graph Queries

After processing multiple documents, you can query cross-document relationships:

```cypher
// Find entities appearing in multiple documents
MATCH (d1:Document)-[:CONTAINS_ENTITY]->(e)<-[:CONTAINS_ENTITY]-(d2:Document)
WHERE d1.document_id <> d2.document_id
RETURN e.id, COUNT(DISTINCT d1) + COUNT(DISTINCT d2) as document_count
ORDER BY document_count DESC
LIMIT 10

// Find documents sharing entities
MATCH (d1:Document)-[:SHARES_ENTITY]->(d2:Document)
RETURN d1.document_id, d2.document_id, COUNT(*) as shared_entities
ORDER BY shared_entities DESC

// Find user's complete knowledge graph
MATCH (u:User {username: 'user@example.com'})-[:OWNS]->(d:Document)
MATCH (d)-[:CONTAINS_ENTITY]->(e)
MATCH (e)-[r]->(e2)
RETURN e, r, e2
```

### 11.3 Custom Graph Schema

To add custom node types or relationships, modify `graph_processor_service.py`:

```python
# Example: Add "Project" nodes linking multiple documents
# In _sync_neo4j() method, after existing code:

# Create Project node from job_id
project_query = """
MERGE (p:Project {job_id: $job_id})
ON CREATE SET p.created_at = datetime()
SET p.updated_at = datetime()
"""
graph.query(project_query, {"job_id": job_id})

# Link Document to Project
link_project_query = """
MATCH (d:Document {document_id: $doc_id})
MATCH (p:Project {job_id: $job_id})
MERGE (d)-[r:BELONGS_TO]->(p)
ON CREATE SET r.created_at = datetime()
"""
graph.query(link_project_query, {"doc_id": str(document.id), "job_id": job_id})
```

---

## Summary

You have successfully set up the Graph Processor VM! Here's what you accomplished:

1. ✅ Installed system dependencies and Python environment
2. ✅ Configured connection to Redis, AlloyDB, Neo4j, GCS, and Ollama LLM
3. ✅ Set up systemd service for automatic startup
4. ✅ Configured logging and monitoring
5. ✅ Implemented security best practices
6. ✅ Tested end-to-end graph processing flow

### Key Points to Remember

- **Redis Queue**: The service pulls from `graph_queue` (populated by Document Processor)
- **LLM Dependency**: Entity extraction requires a capable LLM (Gemma3:4b or better)
- **Memory Intensive**: Graph processing uses 4-8GB RAM per worker
- **Neo4j Storage**: Primary graph storage for visualization and queries
- **AlloyDB Metadata**: Fast access to entities without Neo4j queries
- **Entity Resolution**: Automatically links same entities across documents
- **Job Completion**: Marks jobs as COMPLETED after all documents processed

### Integration with Document Processor

The two VMs work in sequence:

1. **Document Processor** processes files → stores in DB → pushes to `graph_queue`
2. **Graph Processor** pulls from `graph_queue` → extracts entities → stores in Neo4j
3. **Main Application** queries Neo4j for graph visualization

This creates a **distributed pipeline** with each VM specializing in its task.

### Next Steps

1. Test the complete pipeline: Upload → Document VM → Graph VM → View Results
2. Monitor both VMs to ensure smooth operation
3. Scale workers based on throughput requirements
4. Set up monitoring dashboards (Prometheus + Grafana)
5. Configure automated backups for Neo4j and logs
6. Tune LLM parameters for better entity extraction

### Performance Benchmarks

**Typical processing times per document:**

- **Small document** (1-2 pages): 10-20 seconds
- **Medium document** (10-20 pages): 30-60 seconds
- **Large document** (50+ pages): 2-5 minutes

**Bottlenecks:**

1. **LLM inference time** (5-30 seconds per document)
2. **Neo4j write operations** (1-5 seconds per document)
3. **Network latency** between VM and Neo4j

**Optimization strategies:**

- Use GPU-accelerated Ollama for 3-5x speedup
- Increase Neo4j memory settings for faster writes
- Run multiple workers (2-4 optimal for most setups)
- Use fast network connections between VMs

### Support

For issues or questions:
- Check logs: `/var/log/sentinel_ai/graph-processor.log`
- Review this guide's troubleshooting section
- Verify all connectivity tests from Step 5
- Check Neo4j Browser for data verification
- Ensure Redis queue is flowing properly

---

**Congratulations!** Your Graph Processor VM is now operational. 🎉

Together with the Document Processor VM, you now have a fully distributed document intelligence pipeline!
