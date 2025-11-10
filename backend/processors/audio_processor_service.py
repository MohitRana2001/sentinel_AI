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
import torch
import soundfile as sf
import nemo.collections.asr as nemo_asr
import numpy as np
import langid
import time


class AudioProcessorService:
    """Service for processing audio files"""
    
    def __init__(self):
        self.multimodal_client = Client(host=settings.MULTIMODAL_LLM_URL)
        self.nemo_model = None  # Lazy load NeMo model
        self.nemo_device = None
    
    def process_job(self, message: dict):
        """
        Process audio files for a job
        
        Message format (NEW - per-file):
        {
            "job_id": "uuid",
            "gcs_path": "uploads/job-uuid/audio.mp3",
            "filename": "audio.mp3",
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
        Process a single audio file (NEW parallel processing approach)
        Includes distributed locking to prevent duplicate processing
        """
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
                print(f"❌ Job {job_id} not found")
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
                # File already processed by another worker
                print(f"⏭️  File {filename} already processed by another worker, skipping")
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
    
    def _process_job_legacy(self, message: dict):
        """
        Process all audio files in a job sequentially (OLD approach for backward compatibility)
        """
        job_id = message.get("job_id")
        gcs_prefix = message.get("gcs_prefix")
        
        print(f"🎵 Audio Processor received job (legacy): {job_id}")
        
        db = SessionLocal()
        try:
            # Get job from database
            job = db.query(models.ProcessingJob).filter(
                models.ProcessingJob.id == job_id
            ).first()
            
            if not job:
                print(f"Job {job_id} not found")
                return
            
            # List all audio files in GCS prefix
            files = storage_manager.list_files(gcs_prefix)
            audio_files = [f for f in files if f.lower().endswith(
                ('.mp3', '.wav', '.m4a')
            )]
            
            print(f"Found {len(audio_files)} audio files to process")
            
            for file_path in audio_files:
                try:
                    self.process_audio(db, job, file_path)
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
                    traceback.print_exc()
            
            print(f"✅ Audio processing completed for job {job_id}")
            
            # Check if all files have been processed
            self._check_job_completion(db, job)
            
        except Exception as e:
            print(f"Error in audio processor: {e}")
            traceback.print_exc()
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
        
        print(f"📊 Job {job.id}: {documents_processed}/{job.total_files} files processed")
        
        # Only mark as completed if all files are done
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
    
    def process_audio(self, db, job, gcs_path: str):
        """
        Process a single audio file
        
        Steps:
        1. Download audio from GCS
        2. Transcribe using NeMo/Gemini (dev) or Gemma3:12b (production)
        3. Detect language and translate if needed
        4. Rewrite text for consistency
        5. Save transcription and translation to GCS
        6. Generate summary
        7. Create document record
        8. Vectorize and store in database
        """
        print(f"🔄 Processing audio: {gcs_path}")
        
        filename = os.path.basename(gcs_path)
        is_hindi = 'hindi' in filename.lower()
        
        # Download audio file to temp
        suffix = os.path.splitext(gcs_path)[1]
        temp_file_path = storage_manager.download_to_temp(gcs_path, suffix=suffix)
        
        try:
            # Step 1: Transcription
            transcription = self.transcribe_audio(temp_file_path, filename, is_hindi)
            
            if not transcription or not transcription.strip():
                transcription = "[ No transcription available ]"
                print(f"Empty transcription for {filename}")
            
            # Step 2: Detect language if not already known
            detected_language = None
            if transcription != "[ No transcription available ]":
                try:
                    language_info = langid.classify(transcription)
                    detected_language = language_info[0]
                    print(f"🔍 Detected language: {detected_language}")
                except Exception as e:
                    print(f"⚠️ Language detection failed: {e}")
                    detected_language = 'hi' if is_hindi else 'en'
            
            # Determine naming convention based on translation
            # == (two equal signs) for transcription + summary
            # === (three equal signs) for transcription + summary + translation
            needs_translation = detected_language and detected_language != 'en'
            equal_prefix = "===" if needs_translation else "=="
            
            # Save transcription to GCS with naming convention
            transcription_path = gcs_path + f'{equal_prefix}transcription.txt'
            storage_manager.upload_text(transcription, transcription_path)
            print(f"Transcription saved: {len(transcription)} characters")
            
            # Step 3: Translation (if not English)
            translated_text_path = None
            final_text = transcription
            
            if needs_translation and transcription != "[ No transcription available ]":
                print(f"🌐 Translating transcription from {detected_language} to English...")
                try:
                    from document_processor import translate
                    
                    # Save transcription to temp file for translation
                    temp_trans = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8')
                    temp_trans.write(transcription)
                    temp_trans.close()
                    
                    # Translate
                    temp_dir = os.path.dirname(temp_trans.name)
                    translated_path = translate(temp_dir, temp_trans.name, source_lang=detected_language)
                    
                    # Read translation
                    with open(translated_path, 'r', encoding='utf-8') as f:
                        final_text = f.read()
                    
                    # Upload to GCS with three-equal-sign naming
                    translated_text_path = gcs_path + f'{equal_prefix}translated.txt'
                    storage_manager.upload_text(final_text, translated_text_path)
                    
                    # Cleanup
                    os.unlink(temp_trans.name)
                    os.unlink(translated_path)
                    
                    print(f"✅ Translation completed: {len(final_text)} characters")
                except Exception as e:
                    print(f"⚠️ Translation failed: {e}")
                    traceback.print_exc()
                    # Continue without translation
            
            # Step 4: Text rewriting for consistency (if translated or transcribed)
            corrected_text_path = None
            if final_text and final_text != "[ No transcription available ]":
                print(f"✍️  Rewriting text for consistency...")
                try:
                    corrected_text = self.text_rewrite(final_text)
                    
                    # Upload corrected text to GCS
                    corrected_text_path = gcs_path + f'{equal_prefix}corrected.txt'
                    storage_manager.upload_text(corrected_text, corrected_text_path)
                    
                    # Use corrected text for final processing
                    final_text = corrected_text
                    print(f"✅ Text rewriting completed: {len(final_text)} characters")
                except Exception as e:
                    print(f"⚠️ Text rewriting failed: {e}")
                    traceback.print_exc()
                    # Continue with uncorrected text
            
            # Step 5: Summarization
            print(f"📝 Generating summary...")
            summary = self.generate_summary(final_text)
            
            # Save summary to GCS with naming convention
            summary_path = gcs_path + f'{equal_prefix}summary.txt'
            storage_manager.upload_text(summary, summary_path)
            
        finally:
            # Cleanup temp file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
        
        # Step 6: Create document record
        document = models.Document(
            job_id=job.id,
            original_filename=filename,
            file_type=models.FileType.AUDIO,
            gcs_path=gcs_path,
            transcription_path=transcription_path,
            translated_text_path=translated_text_path,
            summary_path=summary_path,
            summary_text=summary[:1000] if summary else ""
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        
        # Step 7: Vectorize the text
        print(f"🔢 Creating embeddings from transcription...")
        try:
            from vector_store import vectorise_and_store_alloydb
            # Delete existing chunks for this document
            db.query(models.DocumentChunk).filter(
                models.DocumentChunk.document_id == document.id
            ).delete(synchronize_session=False)
            db.commit()
            # Vectorize the final text (corrected/translated if available, original if English)
            vectorise_and_store_alloydb(db, document.id, final_text, summary)
            print(f"✅ Embeddings created for audio transcription")
        except Exception as e:
            print(f"⚠️ Vectorization failed: {e}")
        
        # Step 8: Push to graph processor queue
        print(f"📊 Queuing for graph processing...")
        username = job.user.username if job.user else "unknown"
        redis_pubsub.push_to_queue(settings.REDIS_QUEUE_GRAPH, {
            "job_id": job.id,
            "document_id": document.id,
            "gcs_text_path": corrected_text_path or translated_text_path or transcription_path,
            "username": username
        })
        
        # Update job progress
        job.processed_files += 1
        db.commit()
        
        print(f"✅ Completed processing: {filename}")
    
    def transcribe_audio(self, file_path: str, filename: str, is_hindi: bool = False) -> str:
        """
        Transcribe audio file using NeMo (if available), Gemini (dev) or Gemma (production)
        """
        # ===== Try NeMo ASR first if available =====
        try:
            if os.getenv("USE_NEMO_ASR", "false").lower() == "true":
                print(f"🔶 Attempting to use NeMo ASR for transcription")
                transcription = self.transcribe_nemo(file_path)
                if transcription:
                    return transcription
                print(f"⚠️ NeMo ASR failed, falling back to other methods")
        except Exception as e:
            print(f"⚠️ NeMo ASR error: {e}")
        
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
    
    def transcribe_nemo(self, audio_file_path: str) -> str:
        """
        Transcribe audio file using NeMo ASR model
        
        Args:
            audio_file_path: Path to the audio file
            
        Returns:
            Transcribed text
        """
        try:
            print(f"🎤 Transcribing audio using NeMo ASR model...")
            
            # Set up numpy types for compatibility
            np.sctypes = {
                "int": [np.int8, np.int16, np.int32, np.int64],
                "uint": [np.uint8, np.uint16, np.uint32, np.uint64],
                "float": [np.float16, np.float32, np.float64],
                "complex": [np.complex64, np.complex128],
            }
            
            # Initialize device and model (lazy loading)
            if self.nemo_model is None:
                self.nemo_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                print(f"Loading NeMo model on device: {self.nemo_device}")
                
                # Load NeMo model (assuming model file is available)
                model_path = os.getenv("NEMO_MODEL_PATH", "indicconformer_stt_multi_hybrid_rnnt_600m.nemo")
                if not os.path.exists(model_path):
                    raise FileNotFoundError(f"NeMo model not found at {model_path}")
                
                self.nemo_model = nemo_asr.models.EncDecCTCModel.restore_from(restore_path=model_path)
                self.nemo_model.eval()  # inference mode
                self.nemo_model = self.nemo_model.to(self.nemo_device)  # transfer model to device
                self.nemo_model.cur_decoder = "rnnt"
                print(f"✅ NeMo model loaded successfully")
            
            # Transcribe audio
            s = time.time()
            transcription = self.nemo_model.transcribe(
                [audio_file_path], 
                batch_size=1, 
                logprobs=False, 
                language_id='hi'
            )[0]
            
            print(f"✅ NeMo transcription completed in {(time.time() - s) * 1e3:.2f} ms")
            return transcription
            
        except FileNotFoundError as e:
            print(f"⚠️ NeMo model file not found: {e}")
            return None
        except Exception as e:
            print(f"⚠️ NeMo transcription error: {e}")
            traceback.print_exc()
            return None
    
    def text_rewrite(self, text: str) -> str:
        """
        Rewrite transcribed/translated text to fix inconsistencies
        
        This function corrects grammatical errors, removes repetitions, and fixes
        inconsistencies in text that was generated by transcription and translation.
        
        Args:
            text: Text to rewrite
            
        Returns:
            Rewritten text
        """
        try:
            print(f"✍️  Rewriting text for consistency...")
            
            prompt = f'''Consider the text between the <summarise></summarise> tags. This text has been generated by first transcribing an audio file and then translating the content into english. Hence, this content may have incoherrent and illogical text. This may be grammatically incorrect or may have repititions etc. Please rewrite the content without losing any meanings such that the content is correct and free from any inconsistencies. Don't miss any information. Try and rewrite in about the same amount of words, as that of the original text. Also, please only return the converted text. Please don't add any comments from your side. Just return the converted text:
    <summarise>{text}</summarise>"
    '''
            
            s = time.time()
            response = self.multimodal_client.chat(
                model=settings.SUMMARY_LLM_MODEL,
                messages=[
                    {
                        'role': 'user',
                        'content': prompt,
                    },
                ],
            )
            
            rewritten_text = response['message']['content'].strip()
            print(f"✅ Text rewriting completed in {(time.time() - s) * 1e3:.2f} ms")
            return rewritten_text
            
        except Exception as e:
            print(f"⚠️ Text rewriting error: {e}")
            traceback.print_exc()
            # Return original text if rewriting fails
            return text


def main():
    """Main entry point"""
    print("🚀 Starting Audio Processor Service...")
    print(f"📡 Using Redis Queue for parallel processing")
    print(f"👂 Listening to queue: {settings.REDIS_QUEUE_AUDIO}")
    
    service = AudioProcessorService()
    
    # Listen to audio queue (blocking)
    redis_pubsub.listen_queue(
        queue_name=settings.REDIS_QUEUE_AUDIO,
        callback=service.process_job
    )


if __name__ == "__main__":
    main()

