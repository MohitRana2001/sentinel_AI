"""
Audio Processor Service
Handles transcription, translation, and vectorization of audio files
Integrates with Redis PubSub and Storage Manager
"""
import torch
import soundfile as sf
import numpy as np
import dl_translate as dlt
import langid
import time
import sys
import os
import traceback
import tempfile
from datetime import datetime, timezone
from indicnlp.tokenize import sentence_tokenize
from langchain_text_splitters import RecursiveCharacterTextSplitter
from ollama import Client
from langchain_core.documents import Document
import subprocess

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.redis_pubsub import RedisPubSub
from backend.storage_config import storage_manager
from backend.config import settings
from backend.database import SessionLocal
import backend.models as models
from backend.vector_store import vectorise_and_store_alloydb
import nemo.collections.asr as nemo_asr

class AudioProcessor:
    
    def __init__(self):
        self.ollama_client = Client(host=settings.SUMMARY_LLM_URL)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        try:
            self.nemo_model = nemo_asr.models.EncDecCTCModel.restore_from(
                restore_path='indicconformer_stt_multi_hybrid_rnnt_600m.nemo'
            )
            self.nemo_model.eval()
            self.nemo_model = self.nemo_model.to(self.device)
            self.nemo_model.cur_decoder = "rnnt"
            print(f"NeMo model loaded on {self.device}")
        except Exception as e:
            print(f"NeMo model not available: {e}")
            self.nemo_model = None
        
        try:
            self.translation_model = dlt.TranslationModel(
                "./dlt/cached_model_m2m100", 
                model_family="m2m100"
            )
            print("Translation model loaded")
        except Exception as e:
            print(f"Translation model not available: {e}")
            self.translation_model = None
    
        np.sctypes = {
            "int": [np.int8, np.int16, np.int32, np.int64],
            "uint": [np.uint8, np.uint16, np.uint32, np.uint64],
            "float": [np.float16, np.float32, np.float64],
            "complex": [np.complex64, np.complex128],
        }
    
    def downsample_audio(self, audio_file: str) -> str:
        """Downsample audio to 16kHz mono for processing"""
        ds_audio_path, extension = os.path.splitext(audio_file)
        ds_audio_file_name = ds_audio_path + "-ds" + extension
        
        print(f"Downsampling {audio_file} to {ds_audio_file_name}")
        result = subprocess.run(
            ['ffmpeg', '-y', '-i', audio_file, '-ac', '1', '-ar', '16000', ds_audio_file_name],
            capture_output=True, 
            text=True
        )
        
        if result.returncode != 0:
            raise Exception(f"FFmpeg downsampling failed: {result.stderr}")
        
        print(f"Audio downsampled successfully")
        return ds_audio_file_name
    
    def transcribe(self, audio_file: str, lang_code: str) -> str:
        """
        Transcribe audio using NeMo or Vosk
        
        Args:
            audio_file: Path to downsampled audio file
            lang_code: Language code (en, hi, bn, pa, kn, ml, mr, ta)
        
        Returns:
            Transcribed text
        """
        allowed_lang_codes = ["en", "pa", "bn", "hi", "kn", "ml", "mr", "ta"]
        
        if lang_code not in allowed_lang_codes:
            raise Exception(f"Unsupported language: {lang_code}")
        
        # English: Use Vosk
        if lang_code == 'en':
            print("Using Vosk for English transcription")
            result = subprocess.run(
                ['vosk-transcriber', '-i', audio_file, '-o', 'transcribed.txt'],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                raise Exception(f"Vosk transcription failed: {result.stderr}")
            
            with open('transcribed.txt', 'r') as f:
                return f.read()
        
        # Other languages: Use NeMo
        if not self.nemo_model:
            raise Exception("NeMo model not available for non-English transcription")
        
        print(f"Using NeMo for {lang_code} transcription")
        transcribed_text = self.nemo_model.transcribe(
            [audio_file], 
            batch_size=1, 
            logprobs=False, 
            language_id=lang_code
        )[0]
        
        return transcribed_text
    
    def translate(self, text: str, source_lang: str) -> str:
        """
        Translate text from source language to English
        
        Args:
            text: Text to translate
            source_lang: Source language code (hi, bn, etc.)
        
        Returns:
            Translated English text
        """
        if not self.translation_model:
            raise Exception("Translation model not available")
        
        # Handle special language mappings
        language_maps = {'be': 'bn'}
        if source_lang in language_maps:
            source_lang = language_maps[source_lang]
        
        # Split into chunks for translation
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=0
        )
        texts = text_splitter.split_text(text)
        
        print(f"Translating {len(texts)} chunks from {source_lang} to English")
        
        translated_text = " ".join(
            self.translation_model.translate(
                texts, 
                source=source_lang, 
                target='en', 
                verbose=True, 
                batch_size=1
            )
        )
        
        return translated_text
    
    def get_chunks(self, content: str, file_path: str):
        """Create chunks from content for vectorization"""
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=850,
            chunk_overlap=150
        )
        chunks = text_splitter.split_text(content)
        
        chunk_dict_list = []
        for i, chunk in enumerate(chunks):
            chunk_dict = {
                'enriched_text': chunk,
                'chunk_index': i,
                'file_path': file_path
            }
            chunk_dict_list.append(chunk_dict)
        
        return chunk_dict_list
    
    def text_rewrite(self, content: str) -> str:
        """
        Rewrite transcribed and translated text to fix inconsistencies
        
        Args:
            content: Raw transcribed/translated content
        
        Returns:
            Cleaned and rewritten content
        """
        prompt = f'''Consider the text between the <summarise></summarise> tags. This text has been generated by first transcribing an audio file and then translating the content into english. Hence, this content may have incoherent and illogical text. This may be grammatically incorrect or may have repetitions etc. Please rewrite the content without losing any meanings such that the content is correct and free from any inconsistencies. Don't miss any information. Try and rewrite in about the same amount of words, as that of the original text. Also, please only return the converted text. Please don't add any comments from your side. Just return the converted text:
        <summarise>{content}</summarise>
        '''
        
        print("Rewriting text for consistency...")
        start = time.time()
        
        stream = self.ollama_client.chat(
            model='gemma3:1b',
            messages=[
                {
                    'role': 'user',
                    'content': prompt,
                },
            ],
        )
        
        print(f"Text rewriting completed in {(time.time() - start) * 1e3:.2f}ms")
        return stream['message']['content']
    
    def generate_summary(self, text: str) -> str:
        """Generate summary of transcribed text"""
        if not text or text.startswith("[ "):
            return "No summary available"
        
        prompt = f"""Summarize the following transcribed audio in 200 words or less:

{text[:5000]}

Summary:"""
        
        try:
            response = self.ollama_client.chat(
                model=settings.SUMMARY_LLM_MODEL,
                messages=[{'role': 'user', 'content': prompt}],
            )
            return response['message']['content'].strip()
        except Exception as e:
            print(f"Summary generation error: {e}")
            return "Summary generation failed"


class AudioProcessorService:
    """Service for processing audio files with Redis and Storage integration"""
    
    def __init__(self):
        self.processor = AudioProcessor()
        self.redis_pubsub = RedisPubSub()
    
    def process_job(self, message: dict):
        """
        Process audio file from Redis queue
        
        Message format:
        {
            "job_id": "uuid",
            "gcs_path": "uploads/job-uuid/audio.mp3",
            "filename": "audio.mp3",
            "action": "process_file",
            "metadata": {"language": "hi"}
        }
        """
        action = message.get("action", "process")
        
        if action == "process_file":
            self._process_single_file(message)
    
    def _process_single_file(self, message: dict):
        """Process a single audio file"""
        job_id = message.get("job_id")
        gcs_path = message.get("gcs_path")
        filename = message.get("filename")
        metadata = message.get("metadata", {})
        language = metadata.get("language", None)
        
        print(f"Processing audio: {filename} (job: {job_id}, language: {language})")
        
        db = SessionLocal()
        try:
            # Get job from database
            job = db.query(models.ProcessingJob).filter(
                models.ProcessingJob.id == job_id
            ).first()
            
            if not job:
                print(f"Job {job_id} not found")
                return
            
            # Update job status to PROCESSING if queued
            if job.status == models.JobStatus.QUEUED:
                job.status = models.JobStatus.PROCESSING
                job.started_at = datetime.now(timezone.utc)
                db.commit()
            
            # Check if already processed
            existing_doc = db.query(models.Document).filter(
                models.Document.job_id == job.id,
                models.Document.original_filename == filename
            ).first()
            
            if existing_doc and existing_doc.summary_path:
                print(f"⚠️ File {filename} already processed, skipping")
                return
            
            # Process the file
            self.process_audio(db, job, gcs_path, filename, language)
            
            # Check job completion
            self._check_job_completion(db, job)
            
            print(f"Completed processing: {filename}")
            
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            traceback.print_exc()
        finally:
            db.close()
    
    def _check_job_completion(self, db, job):
        """Check if all files in job are processed"""
        documents_processed = db.query(models.Document).filter(
            models.Document.job_id == job.id
        ).count()
        
        print(f"Job {job.id}: {documents_processed}/{job.total_files} files processed")
        
        if documents_processed >= job.total_files:
            if job.status != models.JobStatus.COMPLETED:
                job.status = models.JobStatus.COMPLETED
                job.completed_at = datetime.now(timezone.utc)
                db.commit()
                print(f"Job {job.id} marked as COMPLETED")
    
    def process_audio(self, db, job, gcs_path: str, filename: str, language: str = None):
        """
        Process a single audio file
        
        Steps:
        1. Download audio from storage
        2. Downsample to 16kHz
        3. Transcribe using NeMo/Vosk
        4. Translate if non-English
        5. Generate summary
        6. Vectorize and store
        7. Queue for graph processing
        """
        # Extract language code from filename or metadata
        if language:
            lang_code = language.lower()[:2]  # Get 2-letter code
        else:
            # Try to extract from filename (e.g., "audio-hi.mp3")
            parts = filename.split('-')
            lang_code = 'en'  # default
            for part in parts:
                if part in ['en', 'hi', 'bn', 'pa', 'kn', 'ml', 'mr', 'ta']:
                    lang_code = part
                    break
        
        needs_translation = lang_code != 'en'
        
        artifact_start_time = datetime.now(timezone.utc)
        stage_times = {}
        
        # Create or get document record
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
                processing_stages={},
                detected_language=lang_code
            )
            db.add(doc_record)
            db.commit()
            db.refresh(doc_record)
        
        # Publish status
        self.redis_pubsub.publish_artifact_status(
            job_id=job.id,
            filename=filename,
            status="processing",
            current_stage="starting",
            file_type="audio"
        )
        
        # Download audio
        suffix = os.path.splitext(gcs_path)[1]
        temp_file_path = storage_manager.download_to_temp(gcs_path, suffix=suffix)
        
        try:
            # Stage 1: Downsample
            doc_record.current_stage = "downsampling"
            db.commit()
            
            ds_start = datetime.now(timezone.utc)
            ds_audio_path = self.processor.downsample_audio(temp_file_path)
            stage_times['downsampling'] = (datetime.now(timezone.utc) - ds_start).total_seconds()
            
            # Stage 2: Transcription
            doc_record.current_stage = "transcription"
            doc_record.processing_stages = stage_times
            db.commit()
            
            self.redis_pubsub.publish_artifact_status(
                job_id=job.id,
                filename=filename,
                status="processing",
                current_stage="transcription",
                processing_stages=stage_times,
                file_type="audio"
            )
            
            trans_start = datetime.now(timezone.utc)
            transcription = self.processor.transcribe(ds_audio_path, lang_code)
            stage_times['transcription'] = (datetime.now(timezone.utc) - trans_start).total_seconds()
            
            # Handle list or string transcription
            if isinstance(transcription, list):
                transcription = ". ".join(transcription)
            
            if not transcription or not transcription.strip():
                transcription = "[ No transcription available ]"
            
            # Save transcription
            equal_prefix = "===" if needs_translation else "=="
            transcription_path = gcs_path + f'{equal_prefix}transcription.txt'
            storage_manager.upload_text(transcription, transcription_path)
            doc_record.transcription_path = transcription_path
            
            print(f"Transcription saved: {len(transcription)} characters")
            
            # Stage 3: Translation (if needed)
            final_text = transcription
            translated_text_path = None
            
            if needs_translation and transcription != "[ No transcription available ]":
                doc_record.current_stage = "translation"
                doc_record.processing_stages = stage_times
                db.commit()
                
                self.redis_pubsub.publish_artifact_status(
                    job_id=job.id,
                    filename=filename,
                    status="processing",
                    current_stage="translation",
                    processing_stages=stage_times,
                    file_type="audio"
                )
                
                translate_start = datetime.now(timezone.utc)
                final_text = self.processor.translate(transcription, lang_code)
                stage_times['translation'] = (datetime.now(timezone.utc) - translate_start).total_seconds()
                
                # Save translation
                translated_text_path = gcs_path + f'{equal_prefix}translated.txt'
                storage_manager.upload_text(final_text, translated_text_path)
                doc_record.translated_text_path = translated_text_path
                
                print(f"Translation saved: {len(final_text)} characters")
            
            # Stage 4: Summarization
            doc_record.current_stage = "summarization"
            doc_record.processing_stages = stage_times
            db.commit()
            
            self.redis_pubsub.publish_artifact_status(
                job_id=job.id,
                filename=filename,
                status="processing",
                current_stage="summarization",
                processing_stages=stage_times,
                file_type="audio"
            )
            
            summary_start = datetime.now(timezone.utc)
            summary = self.processor.generate_summary(final_text)
            stage_times['summarization'] = (datetime.now(timezone.utc) - summary_start).total_seconds()
            
            # Save summary
            summary_path = gcs_path + f'{equal_prefix}summary.txt'
            storage_manager.upload_text(summary, summary_path)
            doc_record.summary_path = summary_path
            doc_record.summary_text = summary[:1000] if summary else ""
            
            # Stage 5: Vectorization
            doc_record.current_stage = "vectorization"
            doc_record.processing_stages = stage_times
            db.commit()
            
            self.redis_pubsub.publish_artifact_status(
                job_id=job.id,
                filename=filename,
                status="processing",
                current_stage="vectorization",
                processing_stages=stage_times,
                file_type="audio"
            )
            
            vector_start = datetime.now(timezone.utc)
            
            # Delete existing chunks
            db.query(models.DocumentChunk).filter(
                models.DocumentChunk.document_id == doc_record.id
            ).delete(synchronize_session=False)
            db.commit()
            
            # Vectorize
            vectorise_and_store_alloydb(db, doc_record.id, final_text, summary)
            stage_times['vectorization'] = (datetime.now(timezone.utc) - vector_start).total_seconds()
            
            print(f"Embeddings created")
            
            # Update record
            doc_record.current_stage = "awaiting_graph"
            doc_record.processing_stages = stage_times
            db.commit()
            
            # Publish status
            self.redis_pubsub.publish_artifact_status(
                job_id=job.id,
                filename=filename,
                status="processing",
                current_stage="awaiting_graph",
                processing_stages=stage_times,
                file_type="audio"
            )
            
            # Queue for graph processing
            username = job.user.username if job.user else "unknown"
            self.redis_pubsub.push_to_queue(settings.REDIS_QUEUE_GRAPH, {
                "job_id": job.id,
                "document_id": doc_record.id,
                "gcs_text_path": translated_text_path or transcription_path,
                "username": username,
                "filename": filename
            })
            
            # Update job progress
            job.processed_files += 1
            db.commit()
            
            print(f"Audio processing complete: {filename}")
            
        finally:
            # Cleanup temp files
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            ds_path = temp_file_path.rsplit('.', 1)[0] + '-ds.' + temp_file_path.rsplit('.', 1)[1]
            if os.path.exists(ds_path):
                os.unlink(ds_path)


def main():
    """Main entry point for audio processor service"""
    print("=" * 60)
    print("🎵 Audio Processor Service Starting...")
    print("=" * 60)
    print(f"Redis Queue: {settings.REDIS_QUEUE_AUDIO}")
    print(f"Storage Backend: {settings.STORAGE_BACKEND}")
    print(f"Database: {settings.DATABASE_URL}")
    print("=" * 60)
    
    service = AudioProcessorService()
    
    # Listen to audio queue
    service.redis_pubsub.listen_queue(
        queue_name=settings.REDIS_QUEUE_AUDIO,
        callback=service.process_job
    )


if __name__ == "__main__":
    main()
