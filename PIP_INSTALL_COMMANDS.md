# Installation Commands for Docling Integration

This file contains all the pip install commands needed for the Docling integration.

## Core Dependencies

Install all dependencies from requirements.txt:
```bash
cd backend
pip install -r requirements.txt
```

## Individual Package Installation

If you prefer to install packages individually or need to troubleshoot:

### 1. Docling and Core Packages
```bash
pip install docling
pip install docling-core
pip install docling-ibm-models
pip install pypdfium2
```

### 2. Existing Document Processing Libraries (Kept for Compatibility)
```bash
pip install PyMuPDF==1.25.1
pip install Pillow==11.0.0
pip install pytesseract==0.3.13
pip install python-docx==1.1.2
```

### 3. Translation and NLP
```bash
pip install dl-translate==0.3.0
pip install indic-nlp-library==0.92
```

### 4. LangChain and LLM Integration
```bash
pip install langchain
pip install langchain-community
pip install langchain-core
pip install langchain-experimental
pip install langchain-text-splitters
pip install langchain-ollama
pip install langchain-google-genai
pip install ollama
pip install google-generativeai
```

### 5. Database and Vector Store
```bash
pip install psycopg2-binary
pip install sqlalchemy
pip install alembic
pip install pgvector
```

### 6. Graph Database
```bash
pip install neo4j
pip install langchain-neo4j
```

### 7. FastAPI and Web Framework
```bash
pip install fastapi
pip install uvicorn
pip install python-multipart
pip install pydantic
pip install pydantic-settings
pip install pydantic[email]
```

### 8. Redis
```bash
pip install redis==5.2.1
pip install hiredis==3.0.0
```

### 9. Google Cloud
```bash
pip install google-cloud-storage==2.19.0
pip install google-auth==2.37.0
```

### 10. Authentication and Security
```bash
pip install python-jose[cryptography]
pip install passlib[bcrypt]
pip install bcrypt
pip install python-dateutil
```

### 11. Utilities
```bash
pip install python-dotenv
pip install httpx
pip install aiofiles
pip install requests
pip install dotenv
```

## System Dependencies

### Tesseract OCR

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr

# Language packs
sudo apt-get install tesseract-ocr-eng  # English
sudo apt-get install tesseract-ocr-hin  # Hindi
sudo apt-get install tesseract-ocr-ben  # Bengali
sudo apt-get install tesseract-ocr-guj  # Gujarati
sudo apt-get install tesseract-ocr-kan  # Kannada
sudo apt-get install tesseract-ocr-mal  # Malayalam
sudo apt-get install tesseract-ocr-mar  # Marathi
sudo apt-get install tesseract-ocr-pan  # Punjabi
sudo apt-get install tesseract-ocr-tam  # Tamil
sudo apt-get install tesseract-ocr-tel  # Telugu
sudo apt-get install tesseract-ocr-chi-sim  # Chinese Simplified
sudo apt-get install tesseract-ocr-chi-tra  # Chinese Traditional
```

**macOS:**
```bash
brew install tesseract
brew install tesseract-lang  # All languages
```

**Windows:**
Download installer from: https://github.com/UB-Mannheim/tesseract/wiki

## Verification

Verify installation:
```bash
python3 -c "from docling.document_converter import DocumentConverter; print('✅ Docling installed successfully!')"
python3 -c "import pytesseract; print('✅ Pytesseract installed successfully!')"
python3 -c "import dl_translate; print('✅ dl-translate installed successfully!')"
```

## Troubleshooting

### SSL Certificate Errors
```bash
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt
```

### Version Conflicts
```bash
# Uninstall conflicting packages first
pip uninstall -y langchain langchain-community langchain-core langchain-experimental

# Then reinstall with specific versions
pip install -r requirements_langchain.txt
```

### Tesseract Not Found
Make sure Tesseract is in your PATH:
```bash
# Linux/macOS
which tesseract

# Windows (PowerShell)
where.exe tesseract
```

Set TESSDATA_PREFIX if needed:
```bash
export TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata/
```

## Notes

- The `dlt` folder (m2m100 model) and `tessdata` dataset should be uploaded separately as mentioned in the project requirements
- For production deployment, consider using a virtual environment:
  ```bash
  python3 -m venv venv
  source venv/bin/activate  # Linux/macOS
  # or
  venv\Scripts\activate  # Windows
  ```
