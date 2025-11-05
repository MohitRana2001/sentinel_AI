# Docling Integration Setup Guide

This document provides instructions for setting up the new Docling-based document processing implementation.

## Overview

The document processor has been upgraded from PyMuPDF + Pytesseract to use **Docling**, IBM's advanced document understanding library. This provides:

- Better document parsing and understanding
- Support for multiple formats (PDF, DOCX, PPTX, images, etc.)
- Enhanced table extraction
- Improved OCR with multiple backend options
- Cleaner, more maintainable code

## Installation

### 1. Install Python Dependencies

Navigate to the `backend` directory and install the required packages:

```bash
cd backend
pip install -r requirements.txt
```

### 2. Install Docling and Core Dependencies

If you prefer to install dependencies individually, use these commands:

```bash
# Core Docling packages
pip install docling
pip install docling-core
pip install docling-ibm-models

# PDF backend
pip install pypdfium2

# Keep existing translation and NLP tools
pip install dl-translate==0.3.0
pip install indic-nlp-library==0.92
```

### 3. System Dependencies

**Tesseract OCR** (required for OCR functionality):

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install tesseract-ocr
sudo apt-get install tesseract-ocr-eng tesseract-ocr-hin tesseract-ocr-ben tesseract-ocr-guj

# macOS
brew install tesseract
brew install tesseract-lang

# Windows
# Download installer from: https://github.com/UB-Mannheim/tesseract/wiki
```

### 4. Model Files and Datasets

The following files need to be uploaded separately (as mentioned in the requirements):

#### a. Translation Model (m2m100)
Place the `dlt` folder containing the m2m100 model in the backend directory:
```
backend/
  dlt/
    cached_model_m2m100/
      (model files)
```

#### b. Tesseract Data
Place the `tessdata` folder in an appropriate location and ensure Tesseract can find it:
```bash
# Set environment variable (add to .env file)
TESSDATA_PREFIX=/path/to/tessdata
```

Or place in default Tesseract location:
```
# Linux: /usr/share/tesseract-ocr/4.00/tessdata/
# macOS: /usr/local/share/tessdata/
# Windows: C:\Program Files\Tesseract-OCR\tessdata\
```

## Configuration

### Environment Variables

Add these to your `.env` file if needed:

```bash
# Tesseract configuration
TESSDATA_PREFIX=/path/to/tessdata

# Ollama/LLM configuration (existing)
SUMMARY_LLM_URL=http://localhost:11434
SUMMARY_LLM_MODEL=gemma3:1b

# Translation settings (existing)
TRANSLATION_THRESHOLD_MB=10
USE_GEMINI_FOR_DEV=false
```

## Usage

### Using Docling in Code

The new implementation maintains backward compatibility. The main function `ocr_pdf_pymupdf()` now uses Docling internally:

```python
from document_processor import ocr_pdf_pymupdf, process_document_with_docling

# Old function name, new implementation (backward compatible)
text = ocr_pdf_pymupdf(pdf_path, lang='eng+hin')

# New general-purpose function for any document format
text = process_document_with_docling(file_path, lang='eng')
```

### Supported Formats

Docling supports:
- PDF (with and without OCR)
- DOCX (Microsoft Word)
- PPTX (Microsoft PowerPoint)
- Images (PNG, JPG, TIFF, etc.)
- HTML
- Markdown
- And more...

### Language Support

The OCR supports multiple languages. Use Tesseract language codes:

```python
# English only
text = process_document_with_docling(file, lang='eng')

# Hindi only
text = process_document_with_docling(file, lang='hin')

# Multiple languages
text = process_document_with_docling(file, lang='eng+hin+ben+guj')
```

## Testing

Test the installation:

```python
python3 -c "from docling.document_converter import DocumentConverter; print('Docling installed successfully!')"
```

Test document processing:

```python
from backend.document_processor import process_document_with_docling

# Test with a sample PDF
text = process_document_with_docling('sample.pdf', lang='eng')
print(f"Extracted {len(text)} characters")
```

## Migration Notes

### What Changed

1. **Document Processing**: Uses Docling instead of PyMuPDF + Pytesseract
2. **Text Extraction**: More robust with better formatting preservation
3. **Table Handling**: Enhanced table extraction and formatting
4. **Multi-format Support**: Can now handle DOCX, PPTX, images natively

### Backward Compatibility

- Function names remain the same (`ocr_pdf_pymupdf`)
- Translation and summarization logic unchanged
- Service integration points unchanged
- All existing workflows continue to work

## Troubleshooting

### Common Issues

1. **Import Error: No module named 'docling'**
   ```bash
   pip install docling docling-core
   ```

2. **Tesseract not found**
   ```bash
   # Install Tesseract OCR system package
   sudo apt-get install tesseract-ocr
   ```

3. **Language data missing**
   ```bash
   # Install additional language packs
   sudo apt-get install tesseract-ocr-hin tesseract-ocr-ben
   ```

4. **Model files not found**
   - Ensure `dlt/cached_model_m2m100/` exists in backend directory
   - Check file permissions

## Performance Considerations

- Docling may be slightly slower than PyMuPDF for simple text extraction
- OCR performance depends on image quality and Tesseract configuration
- For large batches, consider parallel processing (already implemented in service)

## Additional Resources

- [Docling Documentation](https://github.com/DS4SD/docling)
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)
- [dl-translate](https://github.com/xhlulu/dl-translate)

## Support

For issues related to this integration, please check:
1. This setup guide
2. The error logs
3. Docling GitHub issues
4. Project documentation
