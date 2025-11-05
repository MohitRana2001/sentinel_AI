from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TesseractOcrOptions
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
import glob
import time
from pathlib import Path
import random
import traceback
import dl_translate as dlt
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from uuid import uuid4
from langchain_core.documents import Document
import ollama
from ollama import Client
import pickle
import sys
from indicnlp.tokenize import sentence_tokenize
import os

# Import config for flexible configuration
try:
    from config import settings
    OLLAMA_HOST = settings.SUMMARY_LLM_URL
    TRANSLATION_THRESHOLD_MB = settings.TRANSLATION_THRESHOLD_MB
except ImportError:
    # Fallback for standalone usage
    OLLAMA_HOST = 'http://localhost:11434'
    TRANSLATION_THRESHOLD_MB = 10

# Supported document formats for Docling processing
DOCLING_SUPPORTED_FORMATS = {'.pdf', '.docx', '.pptx', '.png', '.jpg', '.jpeg', '.tiff', '.bmp'}

def _create_docling_converter_with_ocr(lang=None):
    """
    Helper function to create a Docling converter with OCR configuration.
    
    Args:
        lang: Language code for OCR (e.g., 'eng', 'hin', 'eng+hin')
    
    Returns:
        Configured DocumentConverter instance
    """
    tesseract_options = TesseractOcrOptions(
        lang=lang if lang else "eng"
    )
    
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.ocr_options = tesseract_options
    
    return DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pipeline_options,
                backend=PyPdfiumDocumentBackend
            )
        }
    )

def ocr_pdf_pymupdf(pdf_path, lang):
    """
    Extract text from PDF using Docling with Tesseract OCR support.
    Replaces the old PyMuPDF + Pytesseract implementation.
    
    Args:
        pdf_path: Path to the PDF file
        lang: Language code for OCR (e.g., 'eng', 'hin', 'eng+hin')
    
    Returns:
        Extracted text as string
    """
    print(f"📄 Processing document with Docling: {pdf_path}")
    
    try:
        # Create document converter with OCR enabled
        converter = _create_docling_converter_with_ocr(lang)
        
        # Convert the document
        print(f"🔄 Converting document...")
        result = converter.convert(pdf_path)
        
        # Extract text from the result
        # Docling provides markdown output by default
        text = result.document.export_to_markdown()
        
        print(f"✅ Extracted {len(text)} characters using Docling")
        return text
        
    except Exception as e:
        print(f"❌ Error processing with Docling: {e}")
        traceback.print_exc()
        
        # Fallback: try simple text extraction without OCR
        try:
            print("⚠️  Attempting fallback extraction...")
            converter = DocumentConverter()
            result = converter.convert(pdf_path)
            text = result.document.export_to_markdown()
            print(f"✅ Fallback extracted {len(text)} characters")
            return text
        except Exception as fallback_error:
            print(f"❌ Fallback also failed: {fallback_error}")
            traceback.print_exc()
            return ""


def process_document_with_docling(file_path, lang=None):
    """
    Process any document format using Docling (PDF, DOCX, PPTX, images, etc.)
    This is a more general function that auto-detects format and processes accordingly.
    
    Args:
        file_path: Path to the document file
        lang: Optional language code for OCR (e.g., 'eng', 'hin', 'eng+hin')
    
    Returns:
        Extracted text as string
    """
    print(f"📄 Processing document with Docling: {file_path}")
    
    try:
        # Get file extension to determine format
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # Configure OCR for formats that might need it (PDF and images)
        if file_ext in {'.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp'}:
            converter = _create_docling_converter_with_ocr(lang)
        else:
            # For DOCX, PPTX, etc., use default converter
            converter = DocumentConverter()
        
        # Convert the document
        print(f"🔄 Converting {file_ext} document...")
        result = converter.convert(file_path)
        
        # Extract text (Docling can export to markdown, JSON, or plain text)
        text = result.document.export_to_markdown()
        
        print(f"✅ Extracted {len(text)} characters using Docling")
        return text
        
    except Exception as e:
        print(f"❌ Error processing with Docling: {e}")
        traceback.print_exc()
        return ""

def translate(dir_path, file_path):
    """
    Translate Hindi text to English using Gemini (dev mode) or m2m100 (production)
    
    Args:
        dir_path: Directory to save the translated file
        file_path: Path to the file to translate
    
    Returns:
        Path to the translated file
    """
    # Read the source text
    with open(file_path) as f:
        sents = f.read()
    
    # ===== LOCAL DEV MODE: Use Gemini if configured =====
    try:
        from config import settings
        if settings.USE_GEMINI_FOR_DEV and settings.GEMINI_API_KEY:
            print("🔷 Using Gemini API for translation (LOCAL DEV MODE)")
            from gemini_client import gemini_client
            
            # For long texts, split into chunks to avoid token limits
            max_chunk_size = 4000  # characters per chunk
            if len(sents) > max_chunk_size:
                print(f"📏 Text is {len(sents)} chars, splitting into chunks...")
                # Split by sentences if possible
                try:
                    texts = sentence_tokenize.sentence_split(sents, lang='hi')
                    print(f"Split into {len(texts)} sentences")
                except:
                    # Fallback: split by character chunks
                    texts = [sents[i:i+max_chunk_size] for i in range(0, len(sents), max_chunk_size)]
                    print(f"Split into {len(texts)} character chunks")
                
                # Translate in batches
                translated_chunks = []
                for i, chunk in enumerate(texts):
                    if not chunk.strip():
                        continue
                    print(f"Translating chunk {i+1}/{len(texts)}...")
                    translated = gemini_client.translate_text(chunk, target_language="English")
                    translated_chunks.append(translated)
                
                eng_translated_text = " ".join(translated_chunks)
            else:
                # Translate in one go
                print(f"Translating {len(sents)} characters...")
                eng_translated_text = gemini_client.translate_text(sents, target_language="English")
            
            # Save translated text
            file_name = file_path.split(".")[-2].split('/')[-1]
            file_name += "-translated-eng"
            translated_path = f'{dir_path}/{file_name}.{file_path.split(".")[-1]}'
            print(f"💾 Saving translation to: {translated_path}")
            with open(translated_path, 'w') as f:
                f.write(eng_translated_text)
            
            print(f"✅ Gemini translation completed for {file_path}")
            return translated_path
            
    except (ImportError, AttributeError) as e:
        print(f"⚠️  Gemini not configured, falling back to m2m100: {e}")
    
    # ===== PRODUCTION MODE: Use local m2m100 model =====
    print("🔧 Using local m2m100 model for translation (PRODUCTION MODE)")
    mt = dlt.TranslationModel("./dlt/cached_model_m2m100", model_family="m2m100")
    
    # Split into sentences
    texts = sentence_tokenize.sentence_split(sents, lang='hi')
    print(len(texts), " are the number of chunks")
    print(texts)
    
    # Translate
    eng_translated_text = " ".join(mt.translate(texts, source='hi', target='en', verbose=True, batch_size=4))
    
    # Save translated text
    file_name = file_path.split(".")[-2].split('/')[-1]
    file_name += "-translated-eng"
    translated_path = f'{dir_path}/{file_name}.{file_path.split(".")[-1]}'
    print(translated_path)
    with open(translated_path, 'w') as f:
        f.write(eng_translated_text)
    
    return translated_path

def get_summary(file_path, ollama_client=None):
    """
    Generate summary using Ollama LLM or Gemini (dev mode)
    Can be called standalone or with custom ollama_client
    """
    with open(file_path, 'r') as file:
        document_content = file.read()
    
    # ===== LOCAL DEV MODE: Use Gemini if configured =====
    try:
        from config import settings
        if settings.USE_GEMINI_FOR_DEV and settings.GEMINI_API_KEY:
            print("🔷 Using Gemini API for summarization (LOCAL DEV MODE)")
            from gemini_client import gemini_client
            summary = gemini_client.generate_summary(document_content, max_words=200)
            print(f"✅ Gemini summary generated for {file_path}")
            return summary
    except (ImportError, AttributeError) as e:
        print(f"⚠️  Gemini not configured, falling back to Ollama: {e}")
    
    # ===== PRODUCTION MODE: Use Ollama/Gemma =====
    if ollama_client is None:
        ollama_client = Client(host=OLLAMA_HOST)
    
    prompt = f'''Please summarise the content between the tags <summarise></summarise>.
    Please only summarize the content here and not anything else.  Start your response with an          overall understanding of the entire content. Then summarise any specific points that are         important.
    Please note that, some content have been generated via OCR and machine translations. Try your best to understand and summarize them:
    <summarise>{document_content}</summarise>"
    '''
    print(prompt)
    s = time.time()
    
    try:
        model = settings.SUMMARY_LLM_MODEL if 'settings' in globals() else 'gemma3:1b'
    except:
        model = 'gemma3:1b'
    
    stream = ollama_client.chat(
        model=model,
        messages=[
            {
                'role': 'user',
                'content': prompt,
            },
        ],
    )
    print(f"Summarization for {file_path} in ",(time.time() - s) * 1e3, "ms")
    print(stream['message']['content'])
    summary = stream['message']['content']
    return summary
            
if __name__ == "__main__":
    s = time.time()
    ollama_client = Client(
        host=OLLAMA_HOST
    )
    file_paths = []
    final_file_paths = []
    if len(sys.argv)!=2:
        print("Only one positional argument expected. Please specify directory")
        sys.exit()
    input_path = sys.argv[-1]
    pdfs = glob.glob(f"{input_path}/*.pdf")
    dir_num = random.randint(1,10000)
    dir_path = f"output/{dir_num}"
    path = Path(dir_path)
    non_eng_files = []
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {path}")
    i=10
    for pdf_path in pdfs:
        print(pdf_path)
        if "hindi" in pdf_path:
            print("Processing a Hindi File")
            extracted_text = ocr_pdf_pymupdf(pdf_path,lang='hin')
            file_path = f"{dir_path}/hindi-pdf-{i}.txt"
            non_eng_files.append(file_path)
        else:
            print("Processing an English File")
            extracted_text = ocr_pdf_pymupdf(pdf_path,lang='eng')
            file_path = f"{dir_path}/english-pdf-{i}.txt"
            final_file_paths.append(file_path)
        print(file_path)
        file_paths.append(file_path)
        with open(file_path, 'a') as the_file:
            the_file.write(extracted_text)
        i+=1
        print(f"{pdf_path} OCRed in ",(time.time() - s) * 1e3, "ms")
    print(f"All files: ",file_paths,"OCRed in ",(time.time() - s) * 1e3, "ms")
    trans_s = time.time()
    if len(non_eng_files) > 0:
        for file in non_eng_files:
            translated_path = translate(dir_path,file)
            final_file_paths.append(translated_path)
            print(f"{pdf_path} translated in ",(time.time() - trans_s) * 1e3, "ms")
        print(f"All files: ",file_paths,"translated in ",(time.time() - trans_s) * 1e3, "ms")
    with open(f'{input_path}/final_file_paths.pkl','wb') as file:
        pickle.dump(final_file_paths,file)
        print("Written the final file list object")
    for final_file in final_file_paths:
        summary = get_summary(final_file,ollama_client)
        file_name = final_file.split(".")[-2].split('/')[-1]
        file_name += "-summary.txt"
        with open(f'{input_path}/{file_name}','w') as file:
            file.write(summary)
        
