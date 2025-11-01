"""
Document Processor Service
Listens to Redis Pub/Sub for document processing jobs
Processes PDFs with OCR, translation, summarization
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from redis_pubsub import redis_pubsub
from gcs_storage import gcs_storage
from config import settings
from database import SessionLocal
import models
from document_processor import ocr_pdf_pymupdf, translate, get_summary
from vector_store import vectorise_and_store_alloydb
from ollama import Client
import tempfile
import traceback
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone


class DocumentProcessorService:
    """Service for processing document files"""
    
    def __init__(self):
        self.ollama_client = Client(host=settings.SUMMARY_LLM_URL)
    
    def process_job(self, message: dict):
        """
        Process documents for a job
        
        Message format:
        {
            "job_id": "uuid",
            "gcs_prefix": "uploads/job-uuid/",
            "action": "process"
        }
        """
        job_id = message.get("job_id")
        gcs_prefix = message.get("gcs_prefix")
        
        print(f"📄 Document Processor received job: {job_id}")
        
        db = SessionLocal()
        try:
            # Get job from database
            job = db.query(models.ProcessingJob).filter(
                models.ProcessingJob.id == job_id
            ).first()
            
            if not job:
                print(f"❌ Job {job_id} not found")
                return
            
            # List all document files in GCS prefix (PDF, DOCX, TXT)
            files = gcs_storage.list_files(gcs_prefix)
            document_files = [f for f in files if f.lower().endswith(('.pdf', '.docx', '.txt'))]
            
            print(f"📁 Found {len(document_files)} documents to process")
            
            # Only update status if we have documents to process
            # (Avoid race condition with audio/video processor)
            if len(document_files) > 0:
                job.status = models.JobStatus.PROCESSING
                job.error_message = None
                db.commit()
            
            for file_path in document_files:
                try:
                    self.process_document(db, job, file_path)
                except Exception as e:
                    print(f"❌ Error processing {file_path}: {e}")
                    traceback.print_exc()
            
            print(f"✅ Document processing completed for job {job_id}")
            
            # Only mark job as completed if we processed all expected files
            # (Some files might be audio/video and handled by other processors)
            if len(document_files) == job.total_files:
                # All files were documents, mark as completed
                job.status = models.JobStatus.COMPLETED
                job.completed_at = datetime.now(timezone.utc)
            elif len(document_files) > 0:
                # Some files were documents, update status to processing
                job.status = models.JobStatus.PROCESSING
                job.started_at = job.started_at or datetime.now(timezone.utc)
            # If len(document_files) == 0, don't change status - other processors will handle it
            
            db.commit()
            
        except Exception as e:
            print(f"❌ Error in document processor: {e}")
            traceback.print_exc()
            if 'job' in locals() and job:
                job.status = models.JobStatus.FAILED
                job.error_message = str(e)
                db.commit()
        finally:
            db.close()
    
    def process_document(self, db, job, gcs_path: str):
        """Process a single document"""
        print(f"🔄 Processing: {gcs_path}")
        
        # Download file from GCS to temp
        suffix = os.path.splitext(gcs_path)[1]
        temp_file = gcs_storage.download_to_temp(gcs_path, suffix=suffix)
        
        try:
            # Detect language from filename
            filename = os.path.basename(gcs_path)
            is_hindi = 'hindi' in filename.lower()
            lang = 'hin' if is_hindi else 'eng'
            
            # Step 1: Text Extraction (OCR for PDFs, direct read for TXT)
            if suffix.lower() == '.txt':
                print(f"📄 Reading text file ({lang})...")
                # For .txt files, read directly with UTF-8 encoding
                try:
                    with open(temp_file, 'r', encoding='utf-8') as f:
                        extracted_text = f.read()
                except UnicodeDecodeError:
                    # Fallback to other encodings if UTF-8 fails
                    try:
                        with open(temp_file, 'r', encoding='latin-1') as f:
                            extracted_text = f.read()
                    except Exception as e:
                        print(f"⚠️ Error reading file with latin-1: {e}, trying cp1252")
                        with open(temp_file, 'r', encoding='cp1252') as f:
                            extracted_text = f.read()
                
                if not extracted_text or not extracted_text.strip():
                    raise ValueError(f"Text file {filename} is empty or could not be read")
                
                print(f"✅ Successfully read {len(extracted_text)} characters from text file")
            else:
                # For PDF/DOCX files, use OCR
                print(f"📖 Running OCR ({lang})...")
                extracted_text = ocr_pdf_pymupdf(temp_file, lang)
            
            # Save extracted text to GCS
            extracted_text_path = gcs_path.replace(suffix, '-extracted.txt')
            gcs_storage.upload_text(extracted_text, extracted_text_path)
            
            # Step 2: Translation (if Hindi)
            translated_text_path = None
            final_text = extracted_text
            
            if is_hindi:
                print(f"🌐 Translating from Hindi...")
                # Save temp file for translation
                temp_extracted = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
                temp_extracted.write(extracted_text)
                temp_extracted.close()
                
                # Translate
                temp_dir = os.path.dirname(temp_extracted.name)
                translated_path = translate(temp_dir, temp_extracted.name)
                
                # Read translated text
                with open(translated_path, 'r') as f:
                    final_text = f.read()
                
                # Upload to GCS
                translated_text_path = gcs_path.replace(suffix, '-translated.txt')
                gcs_storage.upload_text(final_text, translated_text_path)
                
                os.unlink(temp_extracted.name)
                os.unlink(translated_path)
            
            # Step 3: Summarization
            print(f"📝 Generating summary...")
            temp_final = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
            temp_final.write(final_text)
            temp_final.close()
            
            summary = get_summary(temp_final.name, self.ollama_client)
            
            # Upload summary to GCS
            summary_path = gcs_path.replace(suffix, '-summary.txt')
            gcs_storage.upload_text(summary, summary_path)
            
            os.unlink(temp_final.name)
            
            # Create or update document record in database
            # Check by BOTH job_id + filename AND gcs_path to avoid duplicates
            document = db.query(models.Document).filter(
                models.Document.job_id == job.id,
                models.Document.original_filename == filename
            ).first()
            
            # Also check by GCS path in case filename changed
            if not document:
                document = db.query(models.Document).filter(
                    models.Document.gcs_path == gcs_path
                ).first()
            
            is_new_document = document is None
            
            if not document:
                # Create new document
                document = models.Document(
                    job_id=job.id,
                    rbac_level=job.rbac_level,
                    station_id=job.station_id,
                    district_id=job.district_id,
                    state_id=job.state_id,
                    original_filename=filename,
                    file_type=models.FileType.DOCUMENT,
                    gcs_path=gcs_path
                )
                db.add(document)
                try:
                    db.flush()
                    print(f"✅ Created new document record: {filename}")
                except IntegrityError:
                    # Race condition: another process created it
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
            
            # Update document paths (whether new or existing)
            document.gcs_path = gcs_path
            document.extracted_text_path = extracted_text_path
            document.translated_text_path = translated_text_path
            document.summary_path = summary_path
            document.summary_text = summary[:1000] if summary else ""
            db.commit()
            db.refresh(document)

            # Step 4: Vectorization and storage in AlloyDB
            print(f"🔢 Creating embeddings...")
            db.query(models.DocumentChunk).filter(
                models.DocumentChunk.document_id == document.id
            ).delete(synchronize_session=False)
            db.commit()
            vectorise_and_store_alloydb(db, document.id, final_text, summary)
            
            # Step 5: Publish to graph processor
            print(f"📊 Queuing for graph processing...")
            redis_pubsub.publish(settings.REDIS_CHANNEL_GRAPH, {
                "job_id": job.id,
                "document_id": document.id,
                "gcs_text_path": translated_text_path or extracted_text_path
            })
            
            # Update job progress
            if is_new_document:
                job.processed_files += 1
                db.commit()
            
            print(f"✅ Completed processing: {filename}")
            
        finally:
            # Cleanup temp file
            if os.path.exists(temp_file):
                os.unlink(temp_file)


def main():
    """Main entry point"""
    print("🚀 Starting Document Processor Service...")
    print(f"📡 Listening to channel: {settings.REDIS_CHANNEL_DOCUMENT}")
    
    service = DocumentProcessorService()
    
    # Listen to Redis channel
    redis_pubsub.listen(
        channel=settings.REDIS_CHANNEL_DOCUMENT,
        callback=service.process_job
    )


if __name__ == "__main__":
    main()
