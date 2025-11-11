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
from typing import Dict, Any, Tuple, Optional, List
from indicnlp.tokenize import sentence_tokenize
import langid
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.datamodel.base_models import InputFormat
from docling.document_converter import (
    DocumentConverter,
    PdfFormatOption,
    WordFormatOption,
)
from docling.chunking import HybridChunker
from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    TesseractOcrOptions
)
from docling_core.types.doc.document import DoclingDocument
from docling.pipeline.simple_pipeline import SimplePipeline
from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline
from langchain_ollama import OllamaEmbeddings
from langchain_postgres import PGVector
from insert_pgvector import insert_pgvector

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
            '/opt/homebrew/share/tessdata',
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
    print(f"Starting Docling conversion for file {input_path}")
    print(f"OCR enabled: {pipeline_options.do_ocr}")
    print(f"OCR languages: {tesseract_lang} (type: {type(tesseract_lang)})")
    print(f"TESSDATA_PREFIX: {os.environ.get('TESSDATA_PREFIX', 'NOT SET')}")
    
    conv_result = doc_converter.convert(input_path)
    end_time = time.time() - start_time
    print(f"Document converted in {end_time:.2f} seconds.")
    
    # Export to markdown and JSON
    markdown = conv_result.document.export_to_markdown()
    json_obj = conv_result.document.export_to_dict()
    
    if json_obj:
        text_items = json_obj.get("texts", [])
    
    # Detect language
    if markdown and markdown.strip():
        language_info = langid.classify(markdown)
        detected_language = language_info[0]
        print(f"Language detected: {detected_language}")
    else:
        print(f"WARNING: Empty markdown, cannot detect language. Defaulting to 'en'")
        detected_language = 'en'
    
    return markdown, json_obj, detected_language


def translate_json_object(doc_dict: Dict[str, Any], source_lang: str, target_lang: str = 'en', dir_path: str = None, file_name: str = None) -> Tuple[str, str, DoclingDocument]:
    
    print("Using local m2m100 model for JSON translation (PRODUCTION MODE)")
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
    
    if dir_path and file_name:
        translated_path = f'{dir_path}/{file_name}-translated-en.md'
        with open(translated_path, 'w', encoding='utf-8') as f:
            f.write(markdown_output)
    else:
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md', encoding='utf-8')
        temp_file.write(markdown_output)
        temp_file.close()
        translated_path = temp_file.name
    
    return markdown_output, translated_path, translated_doc

def create_chunks(document: DoclingDocument, file_path: str) -> List[Dict[str, Any]]:

    chunker = HybridChunker()
    chunk_iter = chunker.chunk(dl_doc=document)
    chunks = []
    
    for i, chunk in enumerate(chunk_iter):
        print(f"=== Chunk {i} ===")
        print(f"chunk.text:\n{f'{chunk.text[:300]}…'!r}")
    
        enriched_text = chunker.contextualize(chunk=chunk)
        print(f"chunker.contextualize(chunk):\n{f'{enriched_text[:300]}…'!r}")
        
        chunks.append({
            'normal_chunk': chunk.text,
            'enriched_chunk': enriched_text,
            'file_path': file_path,
            'chunk_index': i
        })
        print()
    
    return chunks


def get_summary(file_path, ollama_client=None):

    with open(file_path, 'r') as file:
        document_content = file.read()
    
    try:
        from config import settings
        if settings.USE_GEMINI_FOR_DEV and settings.GEMINI_API_KEY:
            print("Using Gemini API for summarization (LOCAL DEV MODE)")
            from gemini_client import gemini_client
            summary = gemini_client.generate_summary(document_content, max_words=200)
            print(f"Gemini summary generated for {file_path}")
            return summary
    except (ImportError, AttributeError) as e:
        print(f"Gemini not configured, falling back to Ollama: {e}")
    
    # ===== PRODUCTION MODE: Use Ollama/Gemma =====
    if ollama_client is None:
        ollama_client = Client(host=OLLAMA_HOST)
    
    prompt = f'''Please summarise the content between the tags <summarise></summarise>.
    Please only summarize the content here and not anything else. Start your response with an overall understanding of the entire content. Then summarise any specific points that are important. Please note that, some content have been generated via OCR and machine translations. Try your best to understand and summarize them: <summarise>{document_content}</summarise>"
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
    
    extracted_files = []
    files_to_translate = []
    final_files = []

    try:
        embed = OllamaEmbeddings(model="embeddinggemma:latest", base_url='http://10.0.2.222:11434')
        db_user = 'postgres'
        db_password = 'newpassword'
        connection = f"postgresql+psycopg://{db_user}:{db_password}@10.0.2.35:5432/sentinel_db"
        collection_name = "document_chunks_1"
        vector_store = PGVector(
            embeddings=embed,
            collection_name=collection_name,
            connection=connection,
            use_jsonb=True,
        )
        print("Vector store initialized")
    except Exception as e:
        print(f"Vector store initialization failed: {e}")
        vector_store = None
    
    # Process each document
    for i, doc_path in enumerate(all_docs, start=1):
        print(f"{'='*60}")
        print(f"Processing {i}/{len(all_docs)}: {os.path.basename(doc_path)}")
        print(f"{'='*60}")
        
        try:
            # Use Docling to process document
            doc_start = time.time()
            languages = ['eng', 'pan', 'ben', 'hin', 'kan', 'mal', 'mar', 'tam']
            extracted_text, extracted_json, extract_language = process_document_with_docling(doc_path, lang=languages)

            if not extracted_text:
                print(f"File {doc_path} has an undetectable language. Moving on to next file")
                continue
            
            # Save extracted text as markdown
            if extract_language == 'en':
                file_path = f"{dir_path}/-{extract_language}-{i}.md"
                final_files.append(file_path)
                
                # Create chunks for English documents
                eng_doc = DoclingDocument.model_validate(extracted_json)
                doc_chunks.append(create_chunks(eng_doc, file_path))
            else:
                file_path = f"{dir_path}/-{extract_language}-{i}.md"
                file_path_json = f"{dir_path}/-{extract_language}-{i}.json"
                
                # Save JSON for non-English files
                with open(file_path_json, 'w', encoding='utf-8') as json_file:
                    json.dump(extracted_json, json_file)
                
                # Mark for translation
                files_to_translate.append({
                    'file': file_path,
                    'json': extracted_json,
                    'lang': extract_language,
                    'base_name': f"-{extract_language}-{i}",
                    'index': i
                })
            
            # Save extracted markdown
            print(f"Saving extracted file: {file_path}")
            extracted_files.append(file_path)
            with open(file_path, 'w', encoding='utf-8') as the_file:
                the_file.write(extracted_text)
            
            print(f"Processed in {(time.time() - doc_start):.2f}s")
            i += 1
            
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
                translated_md, translated_path, translated_doc = translate_json_object(
                    doc_dict=file_info['json'],
                    source_lang=file_info['lang'],
                    target_lang='en',
                    dir_path=dir_path,
                    file_name=file_info['base_name']
                )
                
                # Save translated markdown
                doc_chunks.append(create_chunks(translated_doc, translated_path))
                final_files.append(translated_path)
                
                # Clean up temp file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                
                print(f"Translated: {translated_file}")
                print(f"Time: {(time.time() - trans_start):.2f}s\n")
                
            except Exception as e:
                print(f"ERROR translating {file_info['base_name']}: {e}")
                traceback.print_exc()
                continue

    if len(doc_chunks) > 0:
        print(f"\n{'='*60}")
        print(f"Inserting chunks into vector store")
        print(f"{'='*60}\n")
        try:
            print('Writing to Vector Store')
            insert_pgvector(doc_chunks)
            print(' --- Written to Vector Store')
        except Exception as e:
            print(f"ERROR inserting to vector store: {e}")
            traceback.print_exc()
    
    # Generate summaries for all final files
    if final_files:
        print(f"\n{'='*60}")
        print(f"Generating summaries for {len(final_files)} documents")
        print(f"{'='*60}\n")

        with open(f'{input_path}/final_file_paths.pkl', 'wb') as file:
            pickle.dump(final_files, file)
            print("Written the final file list object")
        
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
    else:
        print("Could not process any file in the directory")
    
    # Save all processed file paths for reference
    with open(f'{dir_path}/processed_files.pkl', 'wb') as f:
        pickle.dump({
            'extracted': extracted_files,
            'translated': [info['base_name'] + '-translated-en.md' for info in files_to_translate],
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
