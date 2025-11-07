# Minimal Files Required for VM Services

This guide lists the **exact files needed** for each service, allowing you to deploy without cloning the entire repository. You can download only the specific files you need.

## 📋 Overview

Instead of cloning the entire repository, you can download only the required files for each service:

- **Document Processor VM**: 15 core files + dependencies
- **Graph Processor VM**: 13 core files + dependencies

---

## 📄 Document Processor VM Files

### Required Python Files (from `backend/` directory)

You need to create the following directory structure on your VM:

```
/opt/sentinel_ai/backend/
├── processors/
│   └── document_processor_service.py    # Main service file
├── storage/
│   ├── __init__.py
│   ├── base.py
│   ├── factory.py
│   ├── manager.py
│   ├── gcs_backend.py
│   └── local_backend.py
├── config.py                            # Configuration loader
├── database.py                          # Database connection
├── models.py                            # Database models
├── redis_pubsub.py                      # Redis queue client
├── storage_config.py                    # Storage manager initialization
├── document_processor.py                # Document processing functions
├── document_chunker.py                  # Text chunking
├── vector_store.py                      # Embedding storage
└── requirements.txt                     # Python dependencies
```

### File List with GitHub URLs

Download these files from the repository:

1. **`processors/document_processor_service.py`**
   - Main service that processes documents
   - URL: `https://raw.githubusercontent.com/MohitRana2001/sentinel_AI/main/backend/processors/document_processor_service.py`

2. **`config.py`**
   - Loads environment variables and settings
   - URL: `https://raw.githubusercontent.com/MohitRana2001/sentinel_AI/main/backend/config.py`

3. **`database.py`**
   - Database connection setup
   - URL: `https://raw.githubusercontent.com/MohitRana2001/sentinel_AI/main/backend/database.py`

4. **`models.py`**
   - SQLAlchemy models for tables
   - URL: `https://raw.githubusercontent.com/MohitRana2001/sentinel_AI/main/backend/models.py`

5. **`redis_pubsub.py`**
   - Redis client for queue operations
   - URL: `https://raw.githubusercontent.com/MohitRana2001/sentinel_AI/main/backend/redis_pubsub.py`

6. **`storage_config.py`**
   - Initializes storage manager (GCS or local)
   - URL: `https://raw.githubusercontent.com/MohitRana2001/sentinel_AI/main/backend/storage_config.py`

7. **`document_processor.py`**
   - Core document processing functions (OCR, translation)
   - URL: `https://raw.githubusercontent.com/MohitRana2001/sentinel_AI/main/backend/document_processor.py`

8. **`document_chunker.py`**
   - Text chunking for embeddings
   - URL: `https://raw.githubusercontent.com/MohitRana2001/sentinel_AI/main/backend/document_chunker.py`

9. **`vector_store.py`**
   - Embedding generation and storage
   - URL: `https://raw.githubusercontent.com/MohitRana2001/sentinel_AI/main/backend/vector_store.py`

10. **`storage/__init__.py`**
    - Storage module initialization
    - URL: `https://raw.githubusercontent.com/MohitRana2001/sentinel_AI/main/backend/storage/__init__.py`

11. **`storage/base.py`**
    - Storage backend interface
    - URL: `https://raw.githubusercontent.com/MohitRana2001/sentinel_AI/main/backend/storage/base.py`

12. **`storage/factory.py`**
    - Storage backend factory
    - URL: `https://raw.githubusercontent.com/MohitRana2001/sentinel_AI/main/backend/storage/factory.py`

13. **`storage/manager.py`**
    - Storage manager implementation
    - URL: `https://raw.githubusercontent.com/MohitRana2001/sentinel_AI/main/backend/storage/manager.py`

14. **`storage/gcs_backend.py`**
    - Google Cloud Storage backend
    - URL: `https://raw.githubusercontent.com/MohitRana2001/sentinel_AI/main/backend/storage/gcs_backend.py`

15. **`storage/local_backend.py`**
    - Local filesystem backend
    - URL: `https://raw.githubusercontent.com/MohitRana2001/sentinel_AI/main/backend/storage/local_backend.py`

16. **`requirements.txt`**
    - Python dependencies
    - URL: `https://raw.githubusercontent.com/MohitRana2001/sentinel_AI/main/backend/requirements.txt`

### Download Script for Document Processor

```bash
#!/bin/bash
# Download Document Processor files

BASE_URL="https://raw.githubusercontent.com/MohitRana2001/sentinel_AI/main/backend"
TARGET_DIR="/opt/sentinel_ai/backend"

# Create directory structure
mkdir -p $TARGET_DIR/processors
mkdir -p $TARGET_DIR/storage

# Download main files
curl -o $TARGET_DIR/processors/document_processor_service.py $BASE_URL/processors/document_processor_service.py
curl -o $TARGET_DIR/config.py $BASE_URL/config.py
curl -o $TARGET_DIR/database.py $BASE_URL/database.py
curl -o $TARGET_DIR/models.py $BASE_URL/models.py
curl -o $TARGET_DIR/redis_pubsub.py $BASE_URL/redis_pubsub.py
curl -o $TARGET_DIR/storage_config.py $BASE_URL/storage_config.py
curl -o $TARGET_DIR/document_processor.py $BASE_URL/document_processor.py
curl -o $TARGET_DIR/document_chunker.py $BASE_URL/document_chunker.py
curl -o $TARGET_DIR/vector_store.py $BASE_URL/vector_store.py
curl -o $TARGET_DIR/requirements.txt $BASE_URL/requirements.txt

# Download storage module files
curl -o $TARGET_DIR/storage/__init__.py $BASE_URL/storage/__init__.py
curl -o $TARGET_DIR/storage/base.py $BASE_URL/storage/base.py
curl -o $TARGET_DIR/storage/factory.py $BASE_URL/storage/factory.py
curl -o $TARGET_DIR/storage/manager.py $BASE_URL/storage/manager.py
curl -o $TARGET_DIR/storage/gcs_backend.py $BASE_URL/storage/gcs_backend.py
curl -o $TARGET_DIR/storage/local_backend.py $BASE_URL/storage/local_backend.py

echo "Document Processor files downloaded to $TARGET_DIR"
```

### Python Dependencies for Document Processor

Instead of installing all packages from `requirements.txt`, you can install only what's needed:

```bash
# Core dependencies
pip install fastapi uvicorn pydantic pydantic-settings python-dotenv

# Database
pip install psycopg2-binary sqlalchemy pgvector

# Redis
pip install redis==5.2.1 hiredis==3.0.0

# Storage
pip install google-cloud-storage==2.19.0 google-auth==2.37.0

# Document processing
pip install PyMuPDF==1.25.1 Pillow==11.0.0 pytesseract==0.3.13
pip install python-docx==1.1.2 langid
pip install docling docling-core

# Translation
pip install dl-translate==0.3.0 indic-nlp-library==0.92

# LLM client
pip install ollama

# HTTP client
pip install httpx requests aiofiles
```

**Total size**: ~500 MB installed

---

## 🕸️ Graph Processor VM Files

### Required Python Files (from `backend/` directory)

You need to create the following directory structure on your VM:

```
/opt/sentinel_ai/backend/
├── processors/
│   └── graph_processor_service.py       # Main service file
├── storage/
│   ├── __init__.py
│   ├── base.py
│   ├── factory.py
│   ├── manager.py
│   ├── gcs_backend.py
│   └── local_backend.py
├── config.py                            # Configuration loader
├── database.py                          # Database connection
├── models.py                            # Database models
├── redis_pubsub.py                      # Redis queue client
├── storage_config.py                    # Storage manager initialization
├── graph_builer.py                      # Graph transformer setup
└── requirements.txt                     # Python dependencies
```

### File List with GitHub URLs

Download these files from the repository:

1. **`processors/graph_processor_service.py`**
   - Main service that builds knowledge graphs
   - URL: `https://raw.githubusercontent.com/MohitRana2001/sentinel_AI/main/backend/processors/graph_processor_service.py`

2. **`config.py`**
   - Loads environment variables and settings
   - URL: `https://raw.githubusercontent.com/MohitRana2001/sentinel_AI/main/backend/config.py`

3. **`database.py`**
   - Database connection setup
   - URL: `https://raw.githubusercontent.com/MohitRana2001/sentinel_AI/main/backend/database.py`

4. **`models.py`**
   - SQLAlchemy models for tables
   - URL: `https://raw.githubusercontent.com/MohitRana2001/sentinel_AI/main/backend/models.py`

5. **`redis_pubsub.py`**
   - Redis client for queue operations
   - URL: `https://raw.githubusercontent.com/MohitRana2001/sentinel_AI/main/backend/redis_pubsub.py`

6. **`storage_config.py`**
   - Initializes storage manager (GCS or local)
   - URL: `https://raw.githubusercontent.com/MohitRana2001/sentinel_AI/main/backend/storage_config.py`

7. **`graph_builer.py`**
   - Graph transformer and LLM setup
   - URL: `https://raw.githubusercontent.com/MohitRana2001/sentinel_AI/main/backend/graph_builer.py`

8. **`storage/__init__.py`**
   - Storage module initialization
   - URL: `https://raw.githubusercontent.com/MohitRana2001/sentinel_AI/main/backend/storage/__init__.py`

9. **`storage/base.py`**
   - Storage backend interface
   - URL: `https://raw.githubusercontent.com/MohitRana2001/sentinel_AI/main/backend/storage/base.py`

10. **`storage/factory.py`**
    - Storage backend factory
    - URL: `https://raw.githubusercontent.com/MohitRana2001/sentinel_AI/main/backend/storage/factory.py`

11. **`storage/manager.py`**
    - Storage manager implementation
    - URL: `https://raw.githubusercontent.com/MohitRana2001/sentinel_AI/main/backend/storage/manager.py`

12. **`storage/gcs_backend.py`**
    - Google Cloud Storage backend
    - URL: `https://raw.githubusercontent.com/MohitRana2001/sentinel_AI/main/backend/storage/gcs_backend.py`

13. **`storage/local_backend.py`**
    - Local filesystem backend
    - URL: `https://raw.githubusercontent.com/MohitRana2001/sentinel_AI/main/backend/storage/local_backend.py`

### Download Script for Graph Processor

```bash
#!/bin/bash
# Download Graph Processor files

BASE_URL="https://raw.githubusercontent.com/MohitRana2001/sentinel_AI/main/backend"
TARGET_DIR="/opt/sentinel_ai/backend"

# Create directory structure
mkdir -p $TARGET_DIR/processors
mkdir -p $TARGET_DIR/storage

# Download main files
curl -o $TARGET_DIR/processors/graph_processor_service.py $BASE_URL/processors/graph_processor_service.py
curl -o $TARGET_DIR/config.py $BASE_URL/config.py
curl -o $TARGET_DIR/database.py $BASE_URL/database.py
curl -o $TARGET_DIR/models.py $BASE_URL/models.py
curl -o $TARGET_DIR/redis_pubsub.py $BASE_URL/redis_pubsub.py
curl -o $TARGET_DIR/storage_config.py $BASE_URL/storage_config.py
curl -o $TARGET_DIR/graph_builer.py $BASE_URL/graph_builer.py

# Download storage module files
curl -o $TARGET_DIR/storage/__init__.py $BASE_URL/storage/__init__.py
curl -o $TARGET_DIR/storage/base.py $BASE_URL/storage/base.py
curl -o $TARGET_DIR/storage/factory.py $BASE_URL/storage/factory.py
curl -o $TARGET_DIR/storage/manager.py $BASE_URL/storage/manager.py
curl -o $TARGET_DIR/storage/gcs_backend.py $BASE_URL/storage/gcs_backend.py
curl -o $TARGET_DIR/storage/local_backend.py $BASE_URL/storage/local_backend.py

echo "Graph Processor files downloaded to $TARGET_DIR"
```

### Python Dependencies for Graph Processor

Instead of installing all packages from `requirements.txt`, you can install only what's needed:

```bash
# Core dependencies
pip install fastapi uvicorn pydantic pydantic-settings python-dotenv

# Database
pip install psycopg2-binary sqlalchemy

# Redis
pip install redis==5.2.1 hiredis==3.0.0

# Storage
pip install google-cloud-storage==2.19.0 google-auth==2.37.0

# Neo4j
pip install neo4j==5.28.2

# LangChain for graph building
pip install langchain==0.3.27
pip install langchain-neo4j==0.5.0
pip install langchain-experimental==0.3.4
pip install langchain-text-splitters==0.3.11
pip install langchain-ollama==0.2.2
pip install langchain-core

# HTTP client
pip install httpx requests
```

**Total size**: ~400 MB installed

---

## 🚀 Quick Setup Guide

### Document Processor VM

```bash
# 1. Create directory structure
sudo mkdir -p /opt/sentinel_ai/backend/{processors,storage,credentials}
sudo chown $USER:$USER /opt/sentinel_ai

# 2. Download files using the script above
# Save the download script as download_doc_processor.sh
chmod +x download_doc_processor.sh
./download_doc_processor.sh

# 3. Create virtual environment
cd /opt/sentinel_ai
python3 -m venv venv
source venv/bin/activate

# 4. Install dependencies
cd backend
pip install --upgrade pip

# Install only document processor dependencies (listed above)
pip install fastapi uvicorn pydantic pydantic-settings python-dotenv \
  psycopg2-binary sqlalchemy pgvector \
  redis==5.2.1 hiredis==3.0.0 \
  google-cloud-storage==2.19.0 google-auth==2.37.0 \
  PyMuPDF==1.25.1 Pillow==11.0.0 pytesseract==0.3.13 \
  python-docx==1.1.2 langid docling docling-core \
  dl-translate==0.3.0 indic-nlp-library==0.92 \
  ollama httpx requests aiofiles

# 5. Install system dependencies
sudo apt install -y tesseract-ocr tesseract-ocr-eng tesseract-ocr-hin \
  poppler-utils libjpeg-dev libpng-dev

# 6. Create .env file
# Download config template
curl -o .env https://raw.githubusercontent.com/MohitRana2001/sentinel_AI/main/config-templates/document-processor.env.template

# Edit and fill in your values
nano .env

# 7. Create systemd service (see VM_SETUP_DOCUMENT_PROCESSOR.md for details)
```

### Graph Processor VM

```bash
# 1. Create directory structure
sudo mkdir -p /opt/sentinel_ai/backend/{processors,storage,credentials}
sudo chown $USER:$USER /opt/sentinel_ai

# 2. Download files using the script above
# Save the download script as download_graph_processor.sh
chmod +x download_graph_processor.sh
./download_graph_processor.sh

# 3. Create virtual environment
cd /opt/sentinel_ai
python3 -m venv venv
source venv/bin/activate

# 4. Install dependencies
cd backend
pip install --upgrade pip

# Install only graph processor dependencies (listed above)
pip install fastapi uvicorn pydantic pydantic-settings python-dotenv \
  psycopg2-binary sqlalchemy \
  redis==5.2.1 hiredis==3.0.0 \
  google-cloud-storage==2.19.0 google-auth==2.37.0 \
  neo4j==5.28.2 \
  langchain==0.3.27 langchain-neo4j==0.5.0 langchain-experimental==0.3.4 \
  langchain-text-splitters==0.3.11 langchain-ollama==0.2.2 langchain-core \
  httpx requests

# 5. Create .env file
# Download config template
curl -o .env https://raw.githubusercontent.com/MohitRana2001/sentinel_AI/main/config-templates/graph-processor.env.template

# Edit and fill in your values
nano .env

# 6. Create systemd service (see VM_SETUP_GRAPH_PROCESSOR.md for details)
```

---

## 📦 Dependency Sizes

### Document Processor Dependencies

| Category | Packages | Approx Size |
|----------|----------|-------------|
| Core (FastAPI, Pydantic) | 10 packages | 50 MB |
| Database (PostgreSQL + pgvector) | 5 packages | 30 MB |
| Redis | 2 packages | 10 MB |
| Storage (GCS) | 10 packages | 80 MB |
| Document Processing (PyMuPDF, Docling) | 20 packages | 200 MB |
| OCR (Pillow, pytesseract) | 5 packages | 40 MB |
| Translation | 10 packages | 60 MB |
| LLM Client (Ollama) | 5 packages | 30 MB |
| **Total** | **~67 packages** | **~500 MB** |

### Graph Processor Dependencies

| Category | Packages | Approx Size |
|----------|----------|-------------|
| Core (FastAPI, Pydantic) | 10 packages | 50 MB |
| Database (PostgreSQL) | 3 packages | 20 MB |
| Redis | 2 packages | 10 MB |
| Storage (GCS) | 10 packages | 80 MB |
| Neo4j Driver | 3 packages | 20 MB |
| LangChain (Graph building) | 30 packages | 180 MB |
| LLM Client (Ollama) | 5 packages | 30 MB |
| **Total** | **~63 packages** | **~400 MB** |

---

## 🔍 Verification

After downloading files and installing dependencies, verify everything is in place:

### Document Processor Verification

```bash
cd /opt/sentinel_ai/backend
source ../venv/bin/activate

# Check if all files exist
ls -la processors/document_processor_service.py
ls -la config.py database.py models.py redis_pubsub.py
ls -la storage_config.py document_processor.py document_chunker.py vector_store.py
ls -la storage/*.py

# Test imports
python3 -c "from processors.document_processor_service import DocumentProcessorService; print('✓ Imports OK')"

# Check dependencies
python3 -c "import redis, psycopg2, docling, pytesseract, PyMuPDF; print('✓ Dependencies OK')"
```

### Graph Processor Verification

```bash
cd /opt/sentinel_ai/backend
source ../venv/bin/activate

# Check if all files exist
ls -la processors/graph_processor_service.py
ls -la config.py database.py models.py redis_pubsub.py
ls -la storage_config.py graph_builer.py
ls -la storage/*.py

# Test imports
python3 -c "from processors.graph_processor_service import GraphProcessorService; print('✓ Imports OK')"

# Check dependencies
python3 -c "import redis, psycopg2, neo4j, langchain; print('✓ Dependencies OK')"
```

---

## 📝 Notes

1. **No git required**: You don't need git installed on the VMs
2. **Minimal footprint**: Only essential files and dependencies
3. **Update mechanism**: Re-run download scripts to update files
4. **Version pinning**: Dependencies are pinned to tested versions

## 🔄 Updating Files

To update files without cloning:

```bash
# Re-run the download script
cd /opt/sentinel_ai
./download_doc_processor.sh  # or download_graph_processor.sh

# Restart the service
sudo systemctl restart document-processor.service
# or
sudo systemctl restart graph-processor.service
```

---

## 🆘 Troubleshooting

### Missing File Errors

If you see errors about missing modules:

```bash
# Check which file is missing
python3 -c "from processors.document_processor_service import DocumentProcessorService"

# Download that specific file
BASE_URL="https://raw.githubusercontent.com/MohitRana2001/sentinel_AI/main/backend"
curl -o /opt/sentinel_ai/backend/missing_file.py $BASE_URL/missing_file.py
```

### Dependency Errors

If you see import errors:

```bash
# Activate virtual environment
source /opt/sentinel_ai/venv/bin/activate

# Install missing package
pip install <package-name>
```

---

## 📚 Related Documentation

- **VM_SETUP_DOCUMENT_PROCESSOR.md** - Complete setup guide with systemd service
- **VM_SETUP_GRAPH_PROCESSOR.md** - Complete setup guide with systemd service
- **config-templates/** - Environment configuration templates

---

## ✅ Summary

**For Document Processor VM:**
- Download 16 Python files
- Install ~67 packages (~500 MB)
- Configure .env file
- Set up systemd service

**For Graph Processor VM:**
- Download 13 Python files
- Install ~63 packages (~400 MB)
- Configure .env file
- Set up systemd service

**Total setup time**: ~30 minutes per VM (excluding package installation time)

This approach gives you a **minimal, production-ready deployment** without cloning the entire repository!
