import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from redis_pubsub import redis_pubsub
from storage_config import storage_manager
from gcs_storage import gcs_storage
from config import settings
from database import SessionLocal
import models
from ollama import Client
import traceback
import tempfile
from datetime import datetime, timezone


class AudioProcessorService:
    """Service for processing audio files"""
    
    def __init__(self):
        self.multimodal_client = Client(host=settings.MULTIMODAL_LLM_URL)
    
    def process_job(self, message: dict):
        """
        Process audio files for a job
        
        Message format (per-file):
        {
            "job_id": "uuid",
            "gcs_path": "uploads/job-uuid/audio.mp3",
            "filename": "audio.mp3",
            "action": "process_file"
        }
        """
        action = message.get("action", "process")
        job_id = message.get("job_id")
        
        # Route to appropriate handler based on action
        if action == "process_file":
            # NEW: Process single file (parallel processing)
            self._process_single_file(message)
    
    def _process_single_file(self, message: dict):
        job_id = message.get("job_id")
        gcs_path = message.get("gcs_path")
        filename = message.get("filename")
        
        print(f"🎵 Audio Processor received file: {filename} (job: {job_id})")
        
        db = SessionLocal()
        try:
            # Get job from database
            job = db.query(models.ProcessingJob).filter(
                models.ProcessingJob.id == job_id
            ).first()
            
            if not job:
                print(f"Job {job_id} not found")
                return
            
            # Update job status to PROCESSING if it's still QUEUED
            if job.status == models.JobStatus.QUEUED:
                job.status = models.JobStatus.PROCESSING
                job.started_at = datetime.now(timezone.utc)
                db.commit()
            
            # Check if this file has already been processed (distributed lock)
            existing_doc = db.query(models.Document).filter(
                models.Document.job_id == job.id,
                models.Document.original_filename == filename
            ).first()
            
            if existing_doc and existing_doc.summary_path:
                print(f"File {filename} already processed by another worker, skipping")
                return
            
            # Process this file
            self.process_audio(db, job, gcs_path)
            
            # Check if all files in the job have been processed
            self._check_job_completion(db, job)
            
            print(f"Completed processing: {filename}")
            
        except Exception as e:
            print(f"Error processing file {filename}: {e}")
            traceback.print_exc()
            # Don't mark job as failed for single file errors
        finally:
            db.close()
    
    def _check_job_completion(self, db, job):
        """
        Check if all files in the job have been processed
        If yes, mark job as completed
        """
        # Count documents created for this job
        documents_processed = db.query(models.Document).filter(
            models.Document.job_id == job.id
        ).count()
        
        print(f"Job {job.id}: {documents_processed}/{job.total_files} files processed")
        
        # Only mark as completed if all files are done
        if documents_processed >= job.total_files:
            if job.status != models.JobStatus.COMPLETED:
                job.status = models.JobStatus.COMPLETED
                job.completed_at = datetime.now(timezone.utc)
                db.commit()
                print(f"Job {job.id} marked as COMPLETED")
        elif documents_processed > 0:
            # Some files processed, ensure status is PROCESSING
            if job.status == models.JobStatus.QUEUED:
                job.status = models.JobStatus.PROCESSING
                job.started_at = job.started_at or datetime.now(timezone.utc)
                db.commit()
    
    def process_audio(self, db, job, gcs_path: str):
        """
        Process a single audio file
        
        Steps:
        1. Download audio from GCS
        2. Transcribe using Gemini (dev) or Gemma3:12b (production)
        3. Detect language and translate if Hindi
        4. Save transcription and translation to GCS
        5. Generate summary
        6. Create document record with PROCESSING status
        7. Queue for graph processing (status will be updated by graph processor)
        """
        print(f"Processing audio: {gcs_path}")
        
        filename = os.path.basename(gcs_path)
        is_hindi = 'hindi' in filename.lower()
        artifact_start_time = datetime.now(timezone.utc)
        stage_times = {}
        
        # Check if document record already exists
        doc_record = db.query(models.Document).filter(
            models.Document.job_id == job.id,
            models.Document.original_filename == filename
        ).first()
        
        if not doc_record:
            doc_record = models.Document(
                job_id=job.id,
                original_filename=filename,
                file_type=models.FileType.AUDIO,
                gcs_path=gcs_path,
                status=models.JobStatus.PROCESSING,
                started_at=artifact_start_time,
                current_stage="starting",
                processing_stages={}
            )
            db.add(doc_record)
            db.commit()
            db.refresh(doc_record)
        
        # Publish artifact status: PROCESSING
        redis_pubsub.publish_artifact_status(
            job_id=job.id,
            filename=filename,
            status="processing",
            current_stage="starting",
            file_type="audio"
        )
        
        # Download audio file to temp
        suffix = os.path.splitext(gcs_path)[1]
        temp_file_path = storage_manager.download_to_temp(gcs_path, suffix=suffix)
        
        try:
            # Step 1: Transcription
            transcription_start = datetime.now(timezone.utc)
            doc_record.current_stage = "transcription"
            db.commit()
            redis_pubsub.publish_artifact_status(
                job_id=job.id,
                filename=filename,
                status="processing",
                current_stage="transcription",
                file_type="audio"
            )
            
            transcription = self.transcribe_audio(temp_file_path, filename, is_hindi)
            
            if not transcription or not transcription.strip():
                transcription = "[ No transcription available ]"
                print(f"Empty transcription for {filename}")
            
            transcription_end = datetime.now(timezone.utc)
            stage_times['transcription'] = (transcription_end - transcription_start).total_seconds()
            
            # Determine naming convention based on translation
            # == (two equal signs) for transcription + summary
            # === (three equal signs) for transcription + summary + translation
            equal_prefix = "===" if is_hindi else "=="
            
            # Save transcription to GCS with naming convention
            transcription_path = gcs_path + f'{equal_prefix}transcription.txt'
            storage_manager.upload_text(transcription, transcription_path)
            print(f"Transcription saved: {len(transcription)} characters")
            
            # Step 2: Translation (if Hindi)
            translated_text_path = None
            final_text = transcription
            
            if is_hindi and transcription != "[ No transcription available ]":
                translation_start = datetime.now(timezone.utc)
                doc_record.current_stage = "translation"
                doc_record.processing_stages = stage_times
                db.commit()
                redis_pubsub.publish_artifact_status(
                    job_id=job.id,
                    filename=filename,
                    status="processing",
                    current_stage="translation",
                    processing_stages=stage_times,
                    file_type="audio"
                )
                
                print(f"Translating transcription from Hindi...")
                try:
                    from document_processor import translate
                    
                    # Save transcription to temp file for translation
                    temp_trans = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8')
                    temp_trans.write(transcription)
                    temp_trans.close()
                    
                    # Translate
                    temp_dir = os.path.dirname(temp_trans.name)
                    translated_path = translate(temp_dir, temp_trans.name)
                    
                    # Read translation
                    with open(translated_path, 'r', encoding='utf-8') as f:
                        final_text = f.read()
                    
                    # Upload to GCS with three-equal-sign naming
                    translated_text_path = gcs_path + f'{equal_prefix}translated.txt'
                    storage_manager.upload_text(final_text, translated_text_path)
                    
                    # Cleanup
                    os.unlink(temp_trans.name)
                    os.unlink(translated_path)
                    
                    print(f"Translation completed: {len(final_text)} characters")
                except Exception as e:
                    print(f"Translation failed: {e}")
                    # Continue without translation
                
                translation_end = datetime.now(timezone.utc)
                stage_times['translation'] = (translation_end - translation_start).total_seconds()
            
            # Step 3: Summarization
            summarization_start = datetime.now(timezone.utc)
            doc_record.current_stage = "summarization"
            doc_record.processing_stages = stage_times
            db.commit()
            redis_pubsub.publish_artifact_status(
                job_id=job.id,
                filename=filename,
                status="processing",
                current_stage="summarization",
                processing_stages=stage_times,
                file_type="audio"
            )
            
            print(f"Generating summary...")
            summary = self.generate_summary(final_text)
            
            # Save summary to GCS with naming convention
            summary_path = gcs_path + f'{equal_prefix}summary.txt'
            storage_manager.upload_text(summary, summary_path)
            
            summarization_end = datetime.now(timezone.utc)
            stage_times['summarization'] = (summarization_end - summarization_start).total_seconds()
            
        finally:
            # Cleanup temp file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
        
        # Step 4: Update document record with paths
        doc_record.transcription_path = transcription_path
        doc_record.translated_text_path = translated_text_path
        doc_record.summary_path = summary_path
        doc_record.summary_text = summary[:1000] if summary else ""
        db.commit()
        db.refresh(doc_record)
        
        # Step 5: Vectorize the text
        vectorization_start = datetime.now(timezone.utc)
        doc_record.current_stage = "vectorization"
        doc_record.processing_stages = stage_times
        db.commit()
        redis_pubsub.publish_artifact_status(
            job_id=job.id,
            filename=filename,
            status="processing",
            current_stage="vectorization",
            processing_stages=stage_times,
            file_type="audio"
        )
        
        print(f"Creating embeddings from transcription...")
        try:
            from vector_store import vectorise_and_store_alloydb
            # Delete existing chunks for this document
            db.query(models.DocumentChunk).filter(
                models.DocumentChunk.document_id == doc_record.id
            ).delete(synchronize_session=False)
            db.commit()
            # Vectorize the final text (translated if Hindi, original if English)
            vectorise_and_store_alloydb(db, doc_record.id, final_text, summary)
            print(f"Embeddings created for audio transcription")
        except Exception as e:
            print(f"Vectorization failed: {e}")
        
        vectorization_end = datetime.now(timezone.utc)
        stage_times['vectorization'] = (vectorization_end - vectorization_start).total_seconds()
        
        # Update processing stages but keep status as PROCESSING (will be updated by graph processor)
        doc_record.current_stage = "awaiting_graph"
        doc_record.processing_stages = stage_times
        db.commit()
        
        # Publish status: still processing, awaiting graph
        redis_pubsub.publish_artifact_status(
            job_id=job.id,
            filename=filename,
            status="processing",
            current_stage="awaiting_graph",
            processing_stages=stage_times,
            file_type="audio"
        )
        
        # Step 6: Push to graph processor queue
        print(f"Queuing for graph processing...")
        username = job.user.username if job.user else "unknown"
        redis_pubsub.push_to_queue(settings.REDIS_QUEUE_GRAPH, {
            "job_id": job.id,
            "document_id": doc_record.id,
            "gcs_text_path": translated_text_path or transcription_path,
            "username": username,
            "filename": filename  # Add filename for status tracking
        })
        
        # Update job progress
        job.processed_files += 1
        db.commit()
        
        print(f"Completed audio processing (awaiting graph): {filename}")
    
    def transcribe_audio(self, file_path: str, filename: str, is_hindi: bool = False) -> str:
        """
        Transcribe audio file using Gemini (dev) or Gemma (production)
        """
        # ===== LOCAL DEV MODE: Use Gemini if configured =====
        try:
            if settings.USE_GEMINI_FOR_DEV and settings.GEMINI_API_KEY:
                print(f"Using Gemini API for transcription (LOCAL DEV MODE)")
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                model = genai.GenerativeModel('gemini-2.0-flash-exp')
                
                # Upload audio file
                print(f"Uploading audio file to Gemini...")
                audio_file = genai.upload_file(file_path)
                print(f"Audio file uploaded")
                
                # Create transcription prompt
                lang_hint = "Hindi (Devanagari script)" if is_hindi else "English"
                prompt = f"""Please transcribe this audio file accurately.
                The audio is in {lang_hint}.
                Provide the complete transcription with proper punctuation and formatting.
                Only output the transcription text, no additional commentary."""
                
                # Generate transcription
                print(f"Transcribing audio...")
                response = model.generate_content([prompt, audio_file])
                transcription = response.text.strip()
                
                audio_file.delete()
                
                print(f"Gemini transcription completed: {len(transcription)} characters")
                return transcription
                
        except (ImportError, AttributeError) as e:
            print(f"Gemini not configured, falling back to placeholder: {e}")
        except Exception as e:
            print(f"Gemini transcription error: {e}")
            import traceback
            traceback.print_exc()
        
        # ===== PRODUCTION MODE: Use Gemma3:12b multimodal =====
        print(f"Using Gemma3:12b multimodal for transcription (PRODUCTION MODE)")
        print(f"Multimodal LLM integration not yet implemented")
        
        # TODO: Implement Gemma3:12b multimodal transcription
        # For now, returning a placeholder
        # Update with AI4Bharat Model
        return f"[ Audio transcription pending - Gemma3:12b multimodal integration required ]\nFile: {filename}"
    
    def generate_summary(self, text: str) -> str:
        """
        Generate summary of transcribed text using Gemini (dev) or Gemma (production)
        """
        if not text or text.startswith("[ "):
            return "No summary available"
        
        # ===== LOCAL DEV MODE: Use Gemini if configured =====
        try:
            if settings.USE_GEMINI_FOR_DEV and settings.GEMINI_API_KEY:
                print(f"Using Gemini API for summarization (LOCAL DEV MODE)")
                from gemini_client import gemini_client
                summary = gemini_client.generate_summary(text, max_words=200)
                print(f"Gemini summary generated")
                return summary
        except (ImportError, AttributeError) as e:
            print(f"Gemini not configured for summary: {e}")
        except Exception as e:
            print(f"Gemini summary error: {e}")
        
        # ===== PRODUCTION MODE: Use Ollama =====
        print(f"Using Ollama for summarization (PRODUCTION MODE)")
        try:
            prompt = f"""Summarize the following transcribed audio in 200 words or less:

{text[:5000]}

Summary:"""
            
            response = self.multimodal_client.chat(
                model=settings.SUMMARY_LLM_MODEL,
                messages=[{'role': 'user', 'content': prompt}],
            )
            return response['message']['content'].strip()
        except Exception as e:
            print(f"Ollama summary error: {e}")
            return "Summary generation failed"


def main():
    """Main entry point"""
    print("Starting Audio Processor Service...")
    print(f"Using Redis Queue for parallel processing")
    print(f"Listening to queue: {settings.REDIS_QUEUE_AUDIO}")
    
    service = AudioProcessorService()
    
    # Listen to audio queue (blocking)
    redis_pubsub.listen_queue(
        queue_name=settings.REDIS_QUEUE_AUDIO,
        callback=service.process_job
    )


if __name__ == "__main__":
    main()

