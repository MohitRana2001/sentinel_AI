import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from redis_pubsub import redis_pubsub
from storage_config import storage_manager
from config import settings
from database import SessionLocal
import models
from document_processor import (
    get_summary,
    process_document_with_docling,
    translate_json_object,
    create_chunks,
)
import langid
from vector_store import vectorise_and_store_alloydb
from insert_pgvector import insert_pgvector
from ollama import Client
import tempfile
import traceback
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone
from docling_core.types.doc.document import DoclingDocument
from docling.chunking import HybridChunker


class DocumentProcessorService:
    
    def __init__(self):
        self.ollama_client = Client(host=settings.SUMMARY_LLM_URL)
        print(f"Document Processor Service initialized")
        print(f"Ollama: {settings.SUMMARY_LLM_URL}")
    
    def process_job(self, message: dict):
        print(f"\n{'='*60}")
        print(f"Received message from document queue")
        print(f"Message: {message}")
        print(f"{'='*60}\n")

        action = message.get("action", "process")
        job_id = message.get("job_id")
        
        print(f"Action: {action}, Job ID: {job_id}")
        
        if action == "process_file":
            self._process_single_file(message)
        else:
            print(f"Unknown action: {action}")
    
    def _process_single_file(self, message: dict):
        job_id = message.get("job_id")
        gcs_path = message.get("gcs_path")
        filename = message.get("filename")
        
        print(f"\nDocument Processor received file: {filename} (job: {job_id})")
        print(f"GCS Path: {gcs_path}")
        
        db = SessionLocal()
        try:
            # Get job from database
            job = db.query(models.ProcessingJob).filter(
                models.ProcessingJob.id == job_id
            ).first()
            
            if not job:
                print(f"Job {job_id} not found")
                return
            
            if job.status == models.JobStatus.QUEUED:
                job.status = models.JobStatus.PROCESSING
                job.started_at = datetime.now(timezone.utc)
                db.commit()
                print(f"Job status updated to PROCESSING")
            
            # Check if this file has already been processed (distributed lock)
            existing_doc = db.query(models.Document).filter(
                models.Document.job_id == job.id,
                models.Document.original_filename == filename
            ).first()
            
            if existing_doc and existing_doc.summary_path:
                print(f"File {filename} already processed by another worker, skipping")
                return
            
            self.process_document(db, job, gcs_path)
            
            self._check_job_completion(db, job)
            
            print(f"Completed processing: {filename}\n")
            
        except Exception as e:
            print(f"Error processing file {filename}: {e}")
            traceback.print_exc()
        finally:
            db.close()
    
    def _check_job_completion(self, db, job):
        # Count documents created for this job
        documents_processed = db.query(models.Document).filter(
            models.Document.job_id == job.id
        ).count()
        
        print(f"Job {job.id}: {documents_processed}/{job.total_files} files processed")
        
        if documents_processed >= job.total_files:
            if job.status != models.JobStatus.PROCESSING:
                job.status = models.JobStatus.PROCESSING
                job.started_at = job.started_at or datetime.now(timezone.utc)
                db.commit()
                print(f"Job {job.id}: all files processed; awaiting graph processing")
        elif documents_processed > 0:
            if job.status == models.JobStatus.QUEUED:
                job.status = models.JobStatus.PROCESSING
                job.started_at = job.started_at or datetime.now(timezone.utc)
                db.commit()
    
    def process_document(self, db, job, gcs_path: str):
        print(f"\n🔄 Processing document: {gcs_path}")
        
        suffix = os.path.splitext(gcs_path)[1]
        temp_file = storage_manager.download_to_temp(gcs_path, suffix=suffix)
        
        try:
            filename = os.path.basename(gcs_path)
            
            use_docling = suffix.lower() in ['.pdf', '.docx']
            supported_langs = ['eng', 'hin', 'ben', 'pan', 'guj', 'kan', 'mal', 'mar', 'tam', 'tel', 'chi_sim']            
            extracted_text = None
            extracted_json = None
            detected_language = None
            translated_doc = None
            
            # Step 1: Extract text from document
            if suffix.lower() == '.txt':
                print(f"Reading text file...")
                try:
                    with open(temp_file, 'r', encoding='utf-8') as f:
                        extracted_text = f.read()
                except UnicodeDecodeError:
                    try:
                        with open(temp_file, 'r', encoding='latin-1') as f:
                            extracted_text = f.read()
                    except Exception as e:
                        print(f"Error reading file with latin-1: {e}, trying cp1252")
                        with open(temp_file, 'r', encoding='cp1252') as f:
                            extracted_text = f.read()
                
                if not extracted_text or not extracted_text.strip():
                    raise ValueError(f"Text file {filename} is empty or could not be read")
                
                print(f"Successfully read {len(extracted_text)} characters from text file")
                
                detected_language, _ = langid.classify(extracted_text)
                print(f"Detected language: {detected_language}")
                
            elif use_docling:
                print(f"Using Docling for document processing...")
                try:
                    extracted_text, extracted_json, detected_language = process_document_with_docling(
                        temp_file, 
                        lang=supported_langs
                    )
                    
                    print(f"Detected language: {detected_language}")
                except Exception as e:
                    print(f"Docling failed: {e}")
                    traceback.print_exc()
                    use_docling = False
            
            needs_translation = detected_language and detected_language != 'en'
            translated_text_path = None
            final_text = extracted_text
            
            # Determine dash prefix based on language
            dash_prefix = "---" if needs_translation else "--"
            
            # Step 2: Translation (if needed)
            if needs_translation:
                print(f"Translating from {detected_language} to English...")
                
                if use_docling and extracted_json:
                    try:
                        print(f"Using Docling JSON-based translation...")
                        translated_markdown, temp_translated_path, translated_doc = translate_json_object(
                            extracted_json,
                            source_lang=detected_language,
                            target_lang='en'
                        )
                        final_text = translated_markdown
                        
                        if not final_text or not final_text.strip():
                            print(f"Translation produced empty result, using original text")
                            final_text = extracted_text
                            translated_doc = None
                        else:
                            translated_text_path = gcs_path.replace(suffix, f'{dash_prefix}translated.md')
                            storage_manager.upload_text(final_text, translated_text_path)
                            print(f"Saved translated text to: {translated_text_path}")
                        
                        if os.path.exists(temp_translated_path):
                            os.unlink(temp_translated_path)
                        
                        print(f"JSON-based translation completed")
                        
                    except Exception as e:
                        print(f"JSON translation failed: {e}")
                        traceback.print_exc()
                        final_text = extracted_text
                        translated_doc = None
                        print(f"Using original extracted text")
            
            # Validate we have extracted text
            if not extracted_text or not extracted_text.strip():
                raise ValueError(f"No text could be extracted from {filename}")
            
            if not final_text or not final_text.strip():
                final_text = extracted_text
            
            # Step 3: Save extracted text
            extracted_ext = '.md' if use_docling and extracted_json else '.txt'
            extracted_text_path = gcs_path.replace(suffix, f'{dash_prefix}extracted{extracted_ext}')
            storage_manager.upload_text(extracted_text, extracted_text_path)
            print(f"Saved extracted text to: {extracted_text_path}")
            
            # Step 4: Generate summary
            print(f"Generating summary...")
            
            if not final_text or not final_text.strip():
                raise ValueError(f"No text available for summarization for {filename}")
            
            temp_final = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
            temp_final.write(final_text)
            temp_final.close()
            
            try:
                summary = get_summary(temp_final.name, self.ollama_client)
                
                if not summary or not summary.strip():
                    print(f"Summary generation returned empty, using fallback")
                    summary = f"Summary not available for {filename}"
                else:
                    print(f"Summary generated: {len(summary)} characters")
            except Exception as e:
                print(f"Summary generation failed: {e}")
                summary = f"Summary generation failed: {str(e)}"
            finally:
                os.unlink(temp_final.name)
            
            summary_path = gcs_path.replace(suffix, f'{dash_prefix}summary.txt')
            storage_manager.upload_text(summary, summary_path)
            print(f"Saved summary to: {summary_path}")
            
            # Step 5: Create/update document record
            document = db.query(models.Document).filter(
                models.Document.job_id == job.id,
                models.Document.original_filename == filename
            ).first()
            
            if not document:
                document = db.query(models.Document).filter(
                    models.Document.gcs_path == gcs_path
                ).first()
            
            is_new_document = document is None
            
            if not document:
                document = models.Document(
                    job_id=job.id,
                    original_filename=filename,
                    file_type=models.FileType.DOCUMENT,
                    gcs_path=gcs_path
                )
                db.add(document)
                try:
                    db.flush()
                    print(f"Created new document record: {filename}")
                except IntegrityError:
                    db.rollback()
                    document = db.query(models.Document).filter(
                        models.Document.job_id == job.id,
                        models.Document.original_filename == filename
                    ).first()
                    if not document:
                        raise
                    print(f"Document already exists (race condition), using existing: {filename}")
            else:
                print(f"Updating existing document: {filename}")
            
            document.gcs_path = gcs_path
            document.extracted_text_path = extracted_text_path
            document.translated_text_path = translated_text_path
            document.summary_path = summary_path
            document.summary_text = summary[:1000] if summary else ""
            db.commit()
            db.refresh(document)
            print(f"Document record saved with ID: {document.id}")

            # Step 6: Create embeddings with chunking
            print(f"Creating embeddings...")
            print(f"DEBUG: About to vectorize document ID: {document.id}")  # ADD THIS
            print(f"DEBUG: Document object: {document}")
            
            # Delete existing chunks
            db.query(models.DocumentChunk).filter(
                models.DocumentChunk.document_id == document.id
            ).delete(synchronize_session=False)
            db.commit()

            print(f"🔍 DEBUG: Calling vectorise_and_store_alloydb with document_id={document.id}")
            
            # Choose the appropriate document for chunking
            doc_for_chunking = None
            # if translated_doc:
            #     # Use translated DoclingDocument
            #     doc_for_chunking = translated_doc
            #     print(f"Using translated document for chunking")
            # elif use_docling and extracted_json:
            #     # Use original DoclingDocument
            #     doc_for_chunking = DoclingDocument.model_validate(extracted_json)
            #     print(f"Using original extracted document for chunking")
            
            # if doc_for_chunking:
            #     print(f"Creating chunks with HybridChunker...")
            #     chunks = create_chunks(doc_for_chunking, translated_text_path or extracted_text_path)
            #     print(f"Created {len(chunks)} chunks")
                
            #     # Insert chunks into vector store
            #     print(f"Inserting chunks into vector store...")
            #     insert_pgvector([chunks], document.id)
            #     print(f"Chunks inserted into vector store")
            # else:
                # Fallback to old method for text files
            print(f"Using legacy vectorization method (no chunking)")
            vectorise_and_store_alloydb(db, document.id, final_text, summary)

            chunk_count = db.query(models.DocumentChunk).filter(
            models.DocumentChunk.document_id == document.id
            ).count()
            print(f"VERIFICATION: Document {document.id} now has {chunk_count} chunks")
            
            # Step 7: Queue for graph processing
            print(f"Queuing for graph processing...")
            username = job.user.username if job.user else "unknown"
            
            graph_message = {
                "job_id": job.id,
                "document_id": document.id,
                "gcs_text_path": translated_text_path or extracted_text_path,
                "username": username
            }
            
            print(f"Graph queue message: {graph_message}")
            redis_pubsub.push_to_queue(settings.REDIS_QUEUE_GRAPH, graph_message)
            print(f"Pushed to graph queue: {settings.REDIS_QUEUE_GRAPH}")
            
            if is_new_document:
                job.processed_files += 1
                db.commit()
            
            print(f"Completed processing: {filename}\n")
            
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)


def main():
    """Main entry point"""
    print("="*60)
    print("Starting Document Processor Service...")
    print("="*60)
    print(f"Redis Queue System")
    print(f"Listening to: {settings.REDIS_QUEUE_DOCUMENT}")
    print(f"Will push to: {settings.REDIS_QUEUE_GRAPH}")
    print("="*60)
    print(f"Now listening for messages...\n")
    
    service = DocumentProcessorService()
    redis_pubsub.listen_queue(
        queue_name=settings.REDIS_QUEUE_DOCUMENT,
        callback=service.process_job
    )


if __name__ == "__main__":
    main()