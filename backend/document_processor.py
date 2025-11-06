import fitz # PyMuPDF
from PIL import Image
import pytesseract
import glob
import time
from pathlib import Path
import random
import traceback
import dl_translate as dlt
from langchain_text_splitters import RecursiveCharacterTextSplitter
# from langchain_ollama import OllamaEmbeddings
from uuid import uuid4
from langchain_core.documents import Document
import ollama
from ollama import Client
import pickle
import sys
import os
import json
import tempfile
from typing import Dict, Any, Tuple, Optional
from indicnlp.tokenize import sentence_tokenize
import langid
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.datamodel.base_models import InputFormat
from docling.document_converter import (
    DocumentConverter,
    PdfFormatOption,
    WordFormatOption,
)
from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    TesseractOcrOptions
)
from docling_core.types.doc.document import DoclingDocument
from docling.pipeline.simple_pipeline import SimplePipeline
from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline

try:
    from config import settings
    OLLAMA_HOST = settings.SUMMARY_LLM_URL
    TRANSLATION_THRESHOLD_MB = settings.TRANSLATION_THRESHOLD_MB
except ImportError:
    OLLAMA_HOST = 'http://localhost:11434'
    TRANSLATION_THRESHOLD_MB = 10

# Language mapping for Tesseract and translation
LANGUAGE_MAPPING = {
    'hi': 'hin',  # Hindi
    'bn': 'ben',  # Bengali
    'pa': 'pan',  # Punjabi
    'gu': 'guj',  # Gujarati
    'kn': 'kan',  # Kannada
    'ml': 'mal',  # Malayalam
    'mr': 'mar',  # Marathi
    'ta': 'tam',  # Tamil
    'te': 'tel',  # Telugu
    'zh': 'chi_sim',  # Chinese Simplified
    'en': 'eng',  # English
}

# Reverse mapping (tesseract code -> dl_translate code)
TESSERACT_TO_DL_TRANSLATE = {
    'hin': 'hi',
    'ben': 'bn',
    'pan': 'pa',
    'guj': 'gu',
    'kan': 'kn',
    'mal': 'ml',
    'mar': 'mr',
    'tam': 'ta',
    'tel': 'te',
    'chi_sim': 'zh',
    'eng': 'en',
}


def process_document_with_docling(input_path: str, lang: list = None) -> Tuple[str, Dict[str, Any], str]:
    
    if lang is None:
        lang = ['eng', 'hin', 'ben', 'pan', 'guj', 'kan', 'mal', 'mar', 'tam', 'tel', 'chi_sim']
    
    # Ensure TESSDATA_PREFIX is set
    if not os.environ.get('TESSDATA_PREFIX'):
        possible_paths = [
            '/usr/share/tesseract-ocr/4.00/tessdata',
            '/usr/share/tesseract-ocr/5.00/tessdata',
            '/usr/share/tessdata',
            '/opt/homebrew/share/tessdata',  # macOS Homebrew
        ]
        for path in possible_paths:
            if os.path.exists(path):
                os.environ['TESSDATA_PREFIX'] = path
                break
    
    print(f"TESSDATA_PREFIX is {os.environ.get('TESSDATA_PREFIX')}")
    
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.do_table_structure = True
    pipeline_options.table_structure_options.do_cell_matching = True
    
    # TesseractOcrOptions expects a list, not a string
    # Handle both list and string inputs (strings may use '+' as separator)
    if isinstance(lang, list):
        tesseract_lang = lang
    elif isinstance(lang, str):
        # Split by '+' if it's a concatenated string like 'eng+hin+ben'
        tesseract_lang = lang.split('+')
    else:
        tesseract_lang = [lang]
    
    pipeline_options.ocr_options = TesseractOcrOptions(lang=tesseract_lang)
    pipeline_options.accelerator_options = AcceleratorOptions(
        num_threads=4, device=AcceleratorDevice.AUTO
    )
    
    # Create document converter
    doc_converter = DocumentConverter(
        allowed_formats=[
            InputFormat.PDF,
            InputFormat.DOCX,
            InputFormat.ASCIIDOC,
        ],
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pipeline_options
            ),
            InputFormat.DOCX: WordFormatOption(
                pipeline_cls=SimplePipeline
            ),
        },
    )
    
    # Convert document
    start_time = time.time()
    print(f"🔄 Starting Docling conversion for file {input_path}")
    print(f"   OCR enabled: {pipeline_options.do_ocr}")
    print(f"   OCR languages: {tesseract_lang} (type: {type(tesseract_lang)})")
    print(f"   TESSDATA_PREFIX: {os.environ.get('TESSDATA_PREFIX', 'NOT SET')}")
    
    conv_result = doc_converter.convert(input_path)
    end_time = time.time() - start_time
    print(f"✅ Document converted in {end_time:.2f} seconds.")
    
    # Debug: Check conversion result
    print(f"📊 Conversion result details:")
    print(f"   - Document pages: {len(conv_result.document.pages) if hasattr(conv_result.document, 'pages') else 'N/A'}")
    print(f"   - Document type: {type(conv_result.document)}")
    
    # Export to markdown and JSON
    markdown = conv_result.document.export_to_markdown()
    json_obj = conv_result.document.export_to_dict()
    
    # Debug markdown output
    print(f"📝 Markdown export:")
    print(f"   - Length: {len(markdown)}")
    print(f"   - First 300 chars: {markdown[:300] if markdown else 'EMPTY'}")
    
    # Debug JSON output
    if json_obj:
        text_items = json_obj.get("texts", [])
        print(f"📋 JSON structure:")
        print(f"   - Text items: {len(text_items)}")
        if text_items:
            print(f"   - First text item: {text_items[0] if len(text_items) > 0 else 'NONE'}")
    
    # Detect language
    if markdown and markdown.strip():
        language_info = langid.classify(markdown)
        detected_language = language_info[0]
        print(f"Language detected: {detected_language}")
    else:
        print(f"WARNING: Empty markdown, cannot detect language. Defaulting to 'en'")
        detected_language = 'en'
    
    return markdown, json_obj, detected_language


def translate_json_object(doc_dict: Dict[str, Any], source_lang: str, target_lang: str = 'en') -> Tuple[str, str]:
    print("🔧 Using local m2m100 model for JSON translation (PRODUCTION MODE)")
    mt = dlt.TranslationModel("./dlt/cached_model_m2m100", model_family="m2m100")
    
    text_items = doc_dict.get("texts", [])
    print(f"Translating {len(text_items)} text items from {source_lang} to {target_lang}")
    
    translated_count = 0
    for item in text_items:
        if "text" in item:
            original_text = item["text"]
            if original_text and original_text.strip():
                translated_text = mt.translate(original_text, source=source_lang, target=target_lang)
                item["text"] = translated_text
                translated_count += 1
    
    print(f"Translated {translated_count} text items")
    
    # Convert back to markdown
    translated_doc = DoclingDocument.model_validate(doc_dict)
    markdown_output = translated_doc.export_to_markdown()
    
    # Write to temp file
    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md')
    temp_file.write(markdown_output)
    temp_file.close()
    
    return markdown_output, temp_file.name

def translate(dir_path, file_path, source_lang: str = 'hi'):
    # Read the source text
    with open(file_path) as f:
        sents = f.read()
    
    # Auto-detect language if not specified or detect from filename
    if not source_lang or source_lang == 'auto':
        # Try to detect from filename first
        file_base = os.path.basename(file_path)
        for lang_code in LANGUAGE_MAPPING.keys():
            if lang_code in file_base.lower():
                source_lang = lang_code
                break
        
        # If still not detected, use langid
        if not source_lang or source_lang == 'auto':
            detected_lang, _ = langid.classify(sents)
            source_lang = detected_lang
            print(f"Auto-detected language: {source_lang}")
    
    print(f"Translating from {source_lang} to English")
    
    print("Using local m2m100 model for translation (PRODUCTION MODE)")
    mt = dlt.TranslationModel("./dlt/cached_model_m2m100", model_family="m2m100")
    
    # Split into sentences
    try:
        texts = sentence_tokenize.sentence_split(sents, lang=source_lang)
        print(f"Split into {len(texts)} sentences")
    except:
        # Fallback to character-based splitting
        max_chunk = 1000
        texts = [sents[i:i+max_chunk] for i in range(0, len(sents), max_chunk)]
        print(f"Split into {len(texts)} chunks (fallback)")
    
    # Translate
    eng_translated_text = " ".join(mt.translate(texts, source=source_lang, target='en', verbose=True, batch_size=4))
    
    # Save translated text
    file_name = file_path.split(".")[-2].split('/')[-1]
    file_name += "-translated-eng"
    translated_path = f'{dir_path}/{file_name}.{file_path.split(".")[-1]}'
    print(f"💾 Saving to: {translated_path}")
    with open(translated_path, 'w') as f:
        f.write(eng_translated_text)
    
    print(f"✅ Translation completed")
    return translated_path

def get_summary(file_path, ollama_client=None):

    with open(file_path, 'r') as file:
        document_content = file.read()
    
    # Use Ollama for summarization
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

    start_time = time.time()
    
    if len(sys.argv) != 2:
        print("Usage: python document_processor.py <directory_path>")
        print("\nExample: python document_processor.py ./test_documents/")
        sys.exit(1)
    
    input_path = sys.argv[-1]
    
    # Find all supported document files
    pdfs = glob.glob(f"{input_path}/*.pdf")
    docx_files = glob.glob(f"{input_path}/*.docx")
    all_docs = pdfs + docx_files
    
    if not all_docs:
        print(f"No PDF or DOCX files found in {input_path}")
        sys.exit(1)
    
    print(f"\nFound {len(all_docs)} documents to process")
    print(f"Supported languages: {', '.join(LANGUAGE_MAPPING.keys())}\n")
    
    # Create output directory
    dir_num = random.randint(1, 10000)
    dir_path = f"output/{dir_num}"
    Path(dir_path).mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {dir_path}\n")
    
    # Initialize Ollama client
    ollama_client = Client(host=OLLAMA_HOST)
    
    # Track files for final processing
    extracted_files = []  # All extracted files (markdown)
    files_to_translate = []  # Non-English files needing translation
    final_files = []  # Files ready for summarization (English only)
    
    # Process each document
    for i, doc_path in enumerate(all_docs, start=1):
        print(f"{'='*60}")
        print(f"Processing {i}/{len(all_docs)}: {os.path.basename(doc_path)}")
        print(f"{'='*60}")
        
        try:
            # Use Docling to process document
            doc_start = time.time()
            extracted_text, extracted_json, detected_lang = process_document_with_docling(doc_path)
            
            # Save extracted text as markdown
            base_name = os.path.splitext(os.path.basename(doc_path))[0]
            extracted_file = f"{dir_path}/{base_name}-{detected_lang}-extracted.md"
            
            with open(extracted_file, 'w', encoding='utf-8') as f:
                f.write(extracted_text)
            
            extracted_files.append(extracted_file)
            print(f"Extracted: {extracted_file}")
            print(f"Time: {(time.time() - doc_start):.2f}s")
            
            # Determine if translation is needed
            if detected_lang != 'en':
                files_to_translate.append({
                    'file': extracted_file,
                    'json': extracted_json,
                    'lang': detected_lang,
                    'base_name': base_name
                })
                print(f"Language: {detected_lang} - Will translate to English")
            else:
                final_files.append(extracted_file)
                print(f"Language: {detected_lang} - No translation needed")
            
        except Exception as e:
            print(f"ERROR processing {doc_path}: {e}")
            traceback.print_exc()
            continue
    
    # Translate non-English documents
    if files_to_translate:
        print(f"\n{'='*60}")
        print(f"Translating {len(files_to_translate)} non-English documents")
        print(f"{'='*60}\n")
        
        for file_info in files_to_translate:
            try:
                trans_start = time.time()
                print(f"Translating {file_info['base_name']} ({file_info['lang']} → en)...")
                
                # Use JSON-based translation for better accuracy
                translated_md, temp_path = translate_json_object(
                    file_info['json'],
                    source_lang=file_info['lang'],
                    target_lang='en'
                )
                
                # Save translated markdown
                translated_file = f"{dir_path}/{file_info['base_name']}-translated-en.md"
                with open(translated_file, 'w', encoding='utf-8') as f:
                    f.write(translated_md)
                
                final_files.append(translated_file)
                
                # Clean up temp file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                
                print(f"Translated: {translated_file}")
                print(f"Time: {(time.time() - trans_start):.2f}s\n")
                
            except Exception as e:
                print(f"ERROR translating {file_info['base_name']}: {e}")
                traceback.print_exc()
                continue
    
    # Generate summaries for all final files
    if final_files:
        print(f"\n{'='*60}")
        print(f"Generating summaries for {len(final_files)} documents")
        print(f"{'='*60}\n")
        
        for final_file in final_files:
            try:
                sum_start = time.time()
                base_name = os.path.splitext(os.path.basename(final_file))[0]
                print(f"Summarizing {base_name}...")
                
                summary = get_summary(final_file, ollama_client)
                
                # Save summary
                summary_file = f"{dir_path}/{base_name}-summary.txt"
                with open(summary_file, 'w', encoding='utf-8') as f:
                    f.write(summary)
                
                print(f"Summary: {summary_file}")
                print(f"Time: {(time.time() - sum_start):.2f}s\n")
                
            except Exception as e:
                print(f"ERROR summarizing {final_file}: {e}")
                traceback.print_exc()
                continue
    
    # Save file paths for reference
    with open(f'{dir_path}/processed_files.pkl', 'wb') as f:
        pickle.dump({
            'extracted': extracted_files,
            'translated': [f for info in files_to_translate for f in [f"{dir_path}/{info['base_name']}-translated-en.md"]],
            'final': final_files
        }, f)
    
    # Final summary
    total_time = time.time() - start_time
    print(f"\n{'='*60}")
    print("PROCESSING COMPLETE")
    print(f"{'='*60}")
    print(f"Total documents processed: {len(all_docs)}")
    print(f"Extracted files: {len(extracted_files)}")
    print(f"Translated files: {len(files_to_translate)}")
    print(f"Summaries generated: {len(final_files)}")
    print(f"Total time: {total_time:.2f}s")
    print(f"Output directory: {dir_path}")
    print(f"{'='*60}\n")
