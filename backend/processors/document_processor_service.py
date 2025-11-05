import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from redis_pubsub import redis_pubsub
from gcs_storage import gcs_storage
from config import settings
from database import SessionLocal
import models
from document_processor import ocr_pdf_pymupdf, translate, get_summary, process_document_with_docling, DOCLING_SUPPORTED_FORMATS
from vector_store import vectorise_and_store_alloydb
from ollama import Client
import tempfile
import traceback
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone


class DocumentProcessorService:
    
    def __init__(self):
        self.ollama_client = Client(host=settings.SUMMARY_LLM_URL)
    
    def process_job(self, message: dict):
        """
        Process documents for a job
        
        Message format (NEW - per-file):
        {
            "job_id": "uuid",
            "gcs_path": "uploads/job-uuid/file.pdf",
            "filename": "file.pdf",
            "action": "process_file"
        }
        
        Message format (OLD - per-job, for backward compatibility):
        {
            "job_id": "uuid",
            "gcs_prefix": "uploads/job-uuid/",
            "action": "process"
        }
        """
        action = message.get("action", "process")
        job_id = message.get("job_id")
        
        # Route to appropriate handler based on action
        if action == "process_file":
            # NEW: Process single file (parallel processing)
            self._process_single_file(message)
        else:
            # OLD: Process all files in job (sequential, backward compatibility)
            self._process_job_legacy(message)
    
    def _process_single_file(self, message: dict):
        """
        Process a single file (NEW parallel processing approach)
        Includes distributed locking to prevent duplicate processing
        """
        job_id = message.get("job_id")
        gcs_path = message.get("gcs_path")
        filename = message.get("filename")
        
        print(f"📄 Document Processor received file: {filename} (job: {job_id})")
        
        db = SessionLocal()
        try:
            # Get job from database
            job = db.query(models.ProcessingJob).filter(
                models.ProcessingJob.id == job_id
            ).first()
            
            if not job:
                print(f"❌ Job {job_id} not found")
                return
            
            # Update job status to PROCESSING if it's still QUEUED
            if job.status == models.JobStatus.QUEUED:
                job.status = models.JobStatus.PROCESSING
                job.started_at = datetime.now(timezone.utc)
                db.commit()
            
            # Check if this file has already been processed (distributed lock)
            # Try to create document record - if it exists, another worker is handling it
            existing_doc = db.query(models.Document).filter(
                models.Document.job_id == job.id,
                models.Document.original_filename == filename
            ).first()
            
            if existing_doc and existing_doc.summary_path:
                # File already processed by another worker
                print(f"⏭️  File {filename} already processed by another worker, skipping")
                return
            
            # Process this file
            self.process_document(db, job, gcs_path)
            
            # Check if all files in the job have been processed
            self._check_job_completion(db, job)
            
            print(f"✅ Completed processing: {filename}")
            
        except Exception as e:
            print(f"❌ Error processing file {filename}: {e}")
            traceback.print_exc()
            # Don't mark job as failed for single file errors
        finally:
            db.close()
    
    def _process_job_legacy(self, message: dict):
        """
        Process all files in a job sequentially (OLD approach for backward compatibility)
        """
        job_id = message.get("job_id")
        gcs_prefix = message.get("gcs_prefix")
        
        print(f"📄 Document Processor received job (legacy): {job_id}")
        
        db = SessionLocal()
        try:
            # Get job from database
            job = db.query(models.ProcessingJob).filter(
                models.ProcessingJob.id == job_id
            ).first()
            
            if not job:
                print(f"Job {job_id} not found")
                return
            
            files = gcs_storage.list_files(gcs_prefix)
            document_files = [f for f in files if f.lower().endswith(('.pdf', '.docx', '.txt'))]
            
            print(f"Found {len(document_files)} documents to process")
            
            if len(document_files) > 0:
                job.status = models.JobStatus.PROCESSING
                job.error_message = None
                db.commit()
            
            for file_path in document_files:
                try:
                    self.process_document(db, job, file_path)
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
                    traceback.print_exc()
            
            print(f"Document processing completed for job {job_id}")
            
            # Check if all files have been processed
            self._check_job_completion(db, job)
            
        except Exception as e:
            print(f"Error in document processor: {e}")
            traceback.print_exc()
            if 'job' in locals() and job:
                job.status = models.JobStatus.FAILED
                job.error_message = str(e)
                db.commit()
        finally:
            db.close()
    
    def _check_job_completion(self, db, job):
        """
        Check if all files in the job have been processed
        If yes, mark job as completed (only if no audio/video files pending)
        """
        # Count documents created for this job
        documents_processed = db.query(models.Document).filter(
            models.Document.job_id == job.id
        ).count()
        
        print(f"📊 Job {job.id}: {documents_processed}/{job.total_files} files processed")
        
        # Only mark as completed if all files are done
        # Note: This works for both document-only jobs and mixed jobs
        # because audio/video processor will also call this check
        if documents_processed >= job.total_files:
            if job.status != models.JobStatus.COMPLETED:
                job.status = models.JobStatus.COMPLETED
                job.completed_at = datetime.now(timezone.utc)
                db.commit()
                print(f"✅ Job {job.id} marked as COMPLETED")
        elif documents_processed > 0:
            # Some files processed, ensure status is PROCESSING
            if job.status == models.JobStatus.QUEUED:
                job.status = models.JobStatus.PROCESSING
                job.started_at = job.started_at or datetime.now(timezone.utc)
                db.commit()
    
    def process_document(self, db, job, gcs_path: str):
        print(f"🔄 Processing: {gcs_path}")
        
        suffix = os.path.splitext(gcs_path)[1]
        temp_file = gcs_storage.download_to_temp(gcs_path, suffix=suffix)
        
        try:
            filename = os.path.basename(gcs_path)
            is_hindi = 'hindi' in filename.lower()
            
            lang = 'eng+hin+ben+guj+kan+mal+mar+pan+tam+tel+chi_sim+chi_tra'
            
            if suffix.lower() == '.txt':
                print(f"📄 Reading text file ({lang})...")
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
            elif suffix.lower() in DOCLING_SUPPORTED_FORMATS:
                # Use Docling for document processing (PDF, DOCX, PPTX, images)
                print(f"📄 Processing {suffix} with Docling ({lang})...")
                extracted_text = process_document_with_docling(temp_file, lang)
            else:
                # Fallback to old method for other formats
                print(f"Running OCR with legacy method ({lang})...")
                extracted_text = ocr_pdf_pymupdf(temp_file, lang)
            
            translated_text_path = None
            final_text = extracted_text
            dash_prefix = "---" if is_hindi else "--"
            
            if is_hindi:
                print(f"🌐 Translating from Hindi...")
                temp_extracted = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
                temp_extracted.write(extracted_text)
                temp_extracted.close()

                temp_dir = os.path.dirname(temp_extracted.name)
                translated_path = translate(temp_dir, temp_extracted.name)
                
                with open(translated_path, 'r') as f:
                    final_text = f.read()
                
                translated_text_path = gcs_path.replace(suffix, f'{dash_prefix}translated.txt')
                gcs_storage.upload_text(final_text, translated_text_path)
                
                os.unlink(temp_extracted.name)
                os.unlink(translated_path)
            
            extracted_text_path = gcs_path.replace(suffix, f'{dash_prefix}extracted.txt')
            gcs_storage.upload_text(extracted_text, extracted_text_path)
            
            print(f"Generating summary...")
            temp_final = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
            temp_final.write(final_text)
            temp_final.close()
            
            summary = get_summary(temp_final.name, self.ollama_client)
            
            summary_path = gcs_path.replace(suffix, f'{dash_prefix}summary.txt')
            gcs_storage.upload_text(summary, summary_path)
            
            os.unlink(temp_final.name)
            
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
                    print(f"ℹ️  Document already exists (race condition), using existing: {filename}")
            else:
                print(f"ℹ️  Updating existing document: {filename}")
            
            document.gcs_path = gcs_path
            document.extracted_text_path = extracted_text_path
            document.translated_text_path = translated_text_path
            document.summary_path = summary_path
            document.summary_text = summary[:1000] if summary else ""
            db.commit()
            db.refresh(document)

            print(f"Creating embeddings...")
            db.query(models.DocumentChunk).filter(
                models.DocumentChunk.document_id == document.id
            ).delete(synchronize_session=False)
            db.commit()
            vectorise_and_store_alloydb(db, document.id, final_text, summary)
            
            # Step 5: Push to graph processor queue
            print(f"📊 Queuing for graph processing...")
            redis_pubsub.push_to_queue(settings.REDIS_QUEUE_GRAPH, {
                "job_id": job.id,
                "document_id": document.id,
                "gcs_text_path": translated_text_path or extracted_text_path
            })
            
            if is_new_document:
                job.processed_files += 1
                db.commit()
            
            print(f"Completed processing: {filename}")
            
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)


def main():
    """Main entry point"""
    print("🚀 Starting Document Processor Service...")
    print(f"📡 Using Redis Queue for true parallel processing")
    print(f"👂 Listening to queue: {settings.REDIS_QUEUE_DOCUMENT}")
    
    service = DocumentProcessorService()
    
    # Listen to Redis queue (each worker gets different messages)
    redis_pubsub.listen_queue(
        queue_name=settings.REDIS_QUEUE_DOCUMENT,
        callback=service.process_job
    )


if __name__ == "__main__":
    main()
