"""
Audio/Video Processor Service
Listens to Redis Pub/Sub for audio/video processing jobs
Uses Gemini (dev mode) or Gemma3:12b multimodal LLM (production) for transcription
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from redis_pubsub import redis_pubsub
from gcs_storage import gcs_storage
from config import settings
from database import SessionLocal
import models
from ollama import Client
import traceback
import tempfile
from datetime import datetime, timezone


class AudioVideoProcessorService:
    """Service for processing audio/video files"""
    
    def __init__(self):
        self.multimodal_client = Client(host=settings.MULTIMODAL_LLM_URL)
    
    def process_job(self, message: dict):
        """
        Process audio/video files for a job
        
        Message format:
        {
            "job_id": "uuid",
            "gcs_prefix": "uploads/job-uuid/",
            "action": "process"
        }
        """
        job_id = message.get("job_id")
        gcs_prefix = message.get("gcs_prefix")
        
        print(f"🎬 Audio/Video Processor received job: {job_id}")
        
        db = SessionLocal()
        try:
            # Get job from database
            job = db.query(models.ProcessingJob).filter(
                models.ProcessingJob.id == job_id
            ).first()
            
            if not job:
                print(f"❌ Job {job_id} not found")
                return
            
            # List all audio/video files in GCS prefix
            files = gcs_storage.list_files(gcs_prefix)
            media_files = [f for f in files if f.lower().endswith(
                ('.mp3', '.wav', '.mp4', '.avi', '.mov', '.m4a')
            )]
            
            print(f"📁 Found {len(media_files)} media files to process")
            
            for file_path in media_files:
                try:
                    self.process_media(db, job, file_path)
                except Exception as e:
                    print(f"❌ Error processing {file_path}: {e}")
                    traceback.print_exc()
            
            print(f"✅ Media processing completed for job {job_id}")
            
            # Check if all files have been processed and mark job as completed
            db.refresh(job)  # Reload job from database to get latest counts
            if job.processed_files >= job.total_files:
                job.status = models.JobStatus.COMPLETED
                job.completed_at = datetime.now(timezone.utc)
                db.commit()
                print(f"🎉 Job {job_id} marked as COMPLETED ({job.processed_files}/{job.total_files} files processed)")
            
        except Exception as e:
            print(f"❌ Error in audio/video processor: {e}")
            traceback.print_exc()
        finally:
            db.close()
    
    def process_media(self, db, job, gcs_path: str):
        """
        Process a single audio/video file
        
        Steps:
        1. Download media from GCS
        2. Transcribe using Gemini (dev) or Gemma3:12b (production)
        3. Detect language and translate if Hindi
        4. Save transcription and translation to GCS
        5. Generate summary
        6. Create document record
        """
        print(f"🔄 Processing media: {gcs_path}")
        
        filename = os.path.basename(gcs_path)
        is_hindi = 'hindi' in filename.lower()
        
        # Download media file to temp
        suffix = os.path.splitext(gcs_path)[1]
        temp_file = gcs_storage.download_to_temp(gcs_path, suffix=suffix)
        
        try:
            # Step 1: Transcription
            transcription = self.transcribe_media(temp_file, filename, is_hindi)
            
            if not transcription or not transcription.strip():
                transcription = "[ No transcription available ]"
                print(f"⚠️ Empty transcription for {filename}")
            
            # Save transcription to GCS
            transcription_path = gcs_path + '-transcription.txt'
            gcs_storage.upload_text(transcription, transcription_path)
            print(f"✅ Transcription saved: {len(transcription)} characters")
            
            # Step 2: Translation (if Hindi)
            translated_text_path = None
            final_text = transcription
            
            if is_hindi and transcription != "[ No transcription available ]":
                print(f"🌐 Translating transcription from Hindi...")
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
                    
                    # Upload to GCS
                    translated_text_path = gcs_path + '-translated.txt'
                    gcs_storage.upload_text(final_text, translated_text_path)
                    
                    # Cleanup
                    os.unlink(temp_trans.name)
                    os.unlink(translated_path)
                    
                    print(f"✅ Translation completed: {len(final_text)} characters")
                except Exception as e:
                    print(f"⚠️ Translation failed: {e}")
                    # Continue without translation
            
            # Step 3: Summarization
            print(f"📝 Generating summary...")
            summary = self.generate_summary(final_text)
            
            # Save summary to GCS
            summary_path = gcs_path + '-summary.txt'
            gcs_storage.upload_text(summary, summary_path)
            
        finally:
            # Cleanup temp file
            if os.path.exists(temp_file):
                os.unlink(temp_file)
        
        # Step 4: Create document record
        document = models.Document(
            job_id=job.id,
            rbac_level=job.rbac_level,
            station_id=job.station_id,
            district_id=job.district_id,
            state_id=job.state_id,
            original_filename=filename,
            file_type=models.FileType.AUDIO if filename.lower().endswith(('.mp3', '.wav', '.m4a')) else models.FileType.VIDEO,
            gcs_path=gcs_path,
            transcription_path=transcription_path,
            translated_text_path=translated_text_path,
            summary_path=summary_path,
            summary_text=summary[:1000] if summary else ""
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        
        # Step 5: Vectorize the text
        print(f"🔢 Creating embeddings from transcription...")
        try:
            from vector_store import vectorise_and_store_alloydb
            # Delete existing chunks for this document
            db.query(models.DocumentChunk).filter(
                models.DocumentChunk.document_id == document.id
            ).delete(synchronize_session=False)
            db.commit()
            # Vectorize the final text (translated if Hindi, original if English)
            vectorise_and_store_alloydb(db, document.id, final_text, summary)
            print(f"✅ Embeddings created for audio transcription")
        except Exception as e:
            print(f"⚠️ Vectorization failed: {e}")
        
        # Step 6: Queue for graph processing
        print(f"📊 Queuing for graph processing...")
        redis_pubsub.publish(settings.REDIS_CHANNEL_GRAPH, {
            "job_id": job.id,
            "document_id": document.id,
            "gcs_text_path": translated_text_path or transcription_path
        })
        
        # Update job progress
        job.processed_files += 1
        db.commit()
        
        print(f"✅ Completed processing: {filename}")
    
    def transcribe_media(self, file_path: str, filename: str, is_hindi: bool = False) -> str:
        """
        Transcribe audio/video file using Gemini (dev) or Gemma (production)
        """
        # ===== LOCAL DEV MODE: Use Gemini if configured =====
        try:
            if settings.USE_GEMINI_FOR_DEV and settings.GEMINI_API_KEY:
                print(f"🔷 Using Gemini API for transcription (LOCAL DEV MODE)")
                import google.generativeai as genai
                
                # Configure Gemini
                genai.configure(api_key=settings.GEMINI_API_KEY)
                
                # Use Gemini 2.0 Flash which supports audio
                model = genai.GenerativeModel('gemini-2.0-flash-exp')
                
                # Upload audio file
                print(f"📤 Uploading audio file to Gemini...")
                audio_file = genai.upload_file(file_path)
                print(f"✅ Audio file uploaded")
                
                # Create transcription prompt
                lang_hint = "Hindi (Devanagari script)" if is_hindi else "English"
                prompt = f"""Please transcribe this audio file accurately.
The audio is in {lang_hint}.
Provide the complete transcription with proper punctuation and formatting.
Only output the transcription text, no additional commentary."""
                
                # Generate transcription
                print(f"🎤 Transcribing audio...")
                response = model.generate_content([prompt, audio_file])
                transcription = response.text.strip()
                
                # Delete the uploaded file
                audio_file.delete()
                
                print(f"✅ Gemini transcription completed: {len(transcription)} characters")
                return transcription
                
        except (ImportError, AttributeError) as e:
            print(f"⚠️ Gemini not configured, falling back to placeholder: {e}")
        except Exception as e:
            print(f"⚠️ Gemini transcription error: {e}")
            import traceback
            traceback.print_exc()
        
        # ===== PRODUCTION MODE: Use Gemma3:12b multimodal =====
        print(f"🔧 Using Gemma3:12b multimodal for transcription (PRODUCTION MODE)")
        print(f"⚠️ Multimodal LLM integration not yet implemented")
        
        # TODO: Implement Gemma3:12b multimodal transcription
        # For now, return a placeholder
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
                print(f"🔷 Using Gemini API for summarization (LOCAL DEV MODE)")
                from gemini_client import gemini_client
                summary = gemini_client.generate_summary(text, max_words=200)
                print(f"✅ Gemini summary generated")
                return summary
        except (ImportError, AttributeError) as e:
            print(f"⚠️ Gemini not configured for summary: {e}")
        except Exception as e:
            print(f"⚠️ Gemini summary error: {e}")
        
        # ===== PRODUCTION MODE: Use Ollama =====
        print(f"🔧 Using Ollama for summarization (PRODUCTION MODE)")
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
            print(f"⚠️ Ollama summary error: {e}")
            return "Summary generation failed"


def main():
    """Main entry point"""
    print("🚀 Starting Audio/Video Processor Service...")
    print(f"📡 Listening to channels: {settings.REDIS_CHANNEL_AUDIO}, {settings.REDIS_CHANNEL_VIDEO}")
    
    service = AudioVideoProcessorService()
    
    # Listen to both audio and video channels
    redis_pubsub.listen_async(
        channel=settings.REDIS_CHANNEL_AUDIO,
        callback=service.process_job
    )
    
    redis_pubsub.listen(
        channel=settings.REDIS_CHANNEL_VIDEO,
        callback=service.process_job
    )


if __name__ == "__main__":
    main()

