import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from redis_pubsub import redis_pubsub
from gcs_storage import gcs_storage
from storage_config import storage_manager
from config import settings
from database import SessionLocal
import models
import traceback
import tempfile
from datetime import datetime, timezone, timedelta
from moviepy import VideoFileClip
import numpy as np
import base64
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage
import glob
import shutil


# Frame extraction rate: 0.3 frames per second = 1 frame every ~3 seconds
SAVING_FRAMES_PER_SECOND = 0.3


class VideoProcessorService:
    
    def __init__(self):
        # Initialize LangChain OpenAI client pointing to local Gemma3:4b vision model
        self.vision_llm = ChatOpenAI(
            base_url=f"http://{settings.MULTIMODAL_LLM_HOST}:{settings.MULTIMODAL_LLM_PORT}/v1",
            api_key="lm-studio",
            model=settings.MULTIMODAL_LLM_MODEL,
            temperature=0
        )
    
    def process_job(self, message: dict):
        """
        Process video files for a job
        
        Message format (NEW - per-file):
        {
            "job_id": "uuid",
            "gcs_path": "uploads/job-uuid/video.mp4",
            "filename": "video.mp4",
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
        Process a single video file (NEW parallel processing approach)
        Includes distributed locking to prevent duplicate processing
        """
        job_id = message.get("job_id")
        gcs_path = message.get("gcs_path")
        filename = message.get("filename")
        
        print(f"🎬 Video Processor received file: {filename} (job: {job_id})")
        
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
            self.process_video(db, job, gcs_path)
            
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
        Process all video files in a job sequentially (OLD approach for backward compatibility)
        """
        job_id = message.get("job_id")
        gcs_prefix = message.get("gcs_prefix")
        
        print(f"🎬 Video Processor received job (legacy): {job_id}")
        
        db = SessionLocal()
        try:
            # Get job from database
            job = db.query(models.ProcessingJob).filter(
                models.ProcessingJob.id == job_id
            ).first()
            
            if not job:
                print(f"Job {job_id} not found")
                return
            
            # List all video files in GCS prefix
            files = storage_manager.list_files(gcs_prefix)
            video_files = [f for f in files if f.lower().endswith(
                ('.mp4', '.avi', '.mov')
            )]
            
            print(f"Found {len(video_files)} video files to process")
            
            for file_path in video_files:
                try:
                    self.process_video(db, job, file_path)
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
                    traceback.print_exc()
            
            print(f"✅ Video processing completed for job {job_id}")
            
            # Check if all files have been processed
            self._check_job_completion(db, job)
            
        except Exception as e:
            print(f"Error in video processor: {e}")
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
    
    def format_timedelta(self, td):
        """
        Utility function to format timedelta objects (e.g 00:00:20.05)
        omitting microseconds and retaining milliseconds
        """
        result = str(td)
        try:
            result, ms = result.split(".")
        except ValueError:
            return (result + ".00").replace(":", "-")
        ms = int(ms)
        ms = round(ms / 1e4)
        return f"{result}.{ms:02}".replace(":", "-")
    
    def extract_frames(self, video_file_path: str, output_folder: str) -> list:
        """
        Extract frames from video at specified rate
        Returns list of frame file paths
        """
        print(f"🎞️  Extracting frames from video...")
        
        # Load the video clip
        video_clip = VideoFileClip(video_file_path)
        
        # Create output folder if it doesn't exist
        if not os.path.isdir(output_folder):
            os.makedirs(output_folder)
        
        # If the SAVING_FRAMES_PER_SECOND is above video FPS, then set it to FPS (as maximum)
        saving_frames_per_second = min(video_clip.fps, SAVING_FRAMES_PER_SECOND)
        
        # If SAVING_FRAMES_PER_SECOND is set to 0, step is 1/fps, else 1/SAVING_FRAMES_PER_SECOND
        step = 1 / video_clip.fps if saving_frames_per_second == 0 else 1 / saving_frames_per_second
        
        frame_paths = []
        
        # Iterate over each possible frame
        for current_duration in np.arange(0, video_clip.duration, step):
            # Format the file name and save it
            frame_duration_formatted = self.format_timedelta(timedelta(seconds=current_duration))
            frame_filename = os.path.join(output_folder, f"frame{frame_duration_formatted}.jpg")
            
            # Save the frame with the current duration
            video_clip.save_frame(frame_filename, current_duration)
            frame_paths.append(frame_filename)
        
        video_clip.close()
        
        print(f"✅ Extracted {len(frame_paths)} frames from video")
        return frame_paths
    
    def analyze_video_frames(self, frame_folder_path: str) -> str:
        """
        Analyze video frames using vision LLM
        Returns comprehensive analysis of the video content
        """
        print(f"🔍 Analyzing video frames with vision LLM...")
        
        # Prepare image content for LangChain
        chat_content = []
        images = sorted(glob.glob(f"{frame_folder_path}/*.jpg"))
        
        if not images:
            print(f"⚠️ No frames found in {frame_folder_path}")
            return "No frames available for analysis"
        
        print(f"📷 Processing {len(images)} frames...")
        
        # Encode all frames as base64 images
        for image_path in images:
            with open(image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
                content_dict = {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{encoded_string}"}
                }
                chat_content.append(content_dict)
        
        # Create prompt with system context for CCTV footage analysis
        prompt_with_multiple_images = ChatPromptTemplate.from_messages([
            ("system", """You are a policeman, analysing CCTV footages. Instead of a full video, you have frame captures from a CCTV video provided. 1 frame is captured every 3 seconds. Analyse these set of images and give an overall description of what the video contains from which these frame captures were done.

Focus on:
- People present (number, appearance, activities)
- Vehicles (types, colors, movements)
- Location characteristics
- Activities and events
- Timeline of events
- Any suspicious or noteworthy activities
- Overall scene description

Provide a comprehensive analysis that a law enforcement officer would find useful."""),
            HumanMessage(content=chat_content),
        ])
        
        # Invoke the LLM chain
        chain_with_multiple_images = prompt_with_multiple_images | self.vision_llm
        response = chain_with_multiple_images.invoke({})
        
        analysis = response.content
        print(f"✅ Video analysis completed: {len(analysis)} characters")
        
        return analysis
    
    def process_video(self, db, job, gcs_path: str):
        """
        Process a single video file
        
        Steps:
        1. Download video from GCS
        2. Extract frames at 0.3 fps (1 frame every ~3 seconds)
        3. Analyze frames using vision LLM
        4. Detect language and translate if Hindi
        5. Save analysis and translation to GCS
        6. Generate summary
        7. Create document record
        """
        print(f"🔄 Processing video: {gcs_path}")
        
        filename = os.path.basename(gcs_path)
        is_hindi = 'hindi' in filename.lower()
        
        # Download video file to temp
        suffix = os.path.splitext(gcs_path)[1]
        temp_video_file = storage_manager.download_to_temp(gcs_path, suffix=suffix)
        
        # Create temp directory for frames
        temp_frames_dir = tempfile.mkdtemp(prefix="video_frames_")
        
        try:
            # Step 1: Extract frames from video
            frame_paths = self.extract_frames(temp_video_file, temp_frames_dir)
            
            # Step 2: Analyze frames using vision LLM
            analysis = self.analyze_video_frames(temp_frames_dir)
            
            if not analysis or not analysis.strip():
                analysis = "[ No analysis available ]"
                print(f"⚠️ Empty analysis for {filename}")
            
            # Determine naming convention based on translation
            # == (two equal signs) for analysis + summary
            # === (three equal signs) for analysis + summary + translation
            equal_prefix = "===" if is_hindi else "=="
            
            # Save analysis to GCS with naming convention
            analysis_path = gcs_path + f'{equal_prefix}analysis.txt'
            storage_manager.upload_text(analysis, analysis_path)
            print(f"✅ Analysis saved: {len(analysis)} characters")
            
            # Step 3: Translation (if Hindi)
            translated_text_path = None
            final_text = analysis
            
            if is_hindi and analysis != "[ No analysis available ]":
                print(f"🌐 Translating analysis from Hindi...")
                try:
                    from document_processor import translate
                    
                    # Save analysis to temp file for translation
                    temp_trans = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8')
                    temp_trans.write(analysis)
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
                    
                    print(f"✅ Translation completed: {len(final_text)} characters")
                except Exception as e:
                    print(f"⚠️ Translation failed: {e}")
                    # Continue without translation
            
            # Step 4: Summarization
            print(f"📝 Generating summary...")
            summary = self.generate_summary(final_text)
            
            # Save summary to GCS with naming convention
            summary_path = gcs_path + f'{equal_prefix}summary.txt'
            storage_manager.upload_text(summary, summary_path)
            
        finally:
            # Cleanup temp files
            if os.path.exists(temp_video_file):
                os.unlink(temp_video_file)
            if os.path.exists(temp_frames_dir):
                shutil.rmtree(temp_frames_dir)
        
        # Step 5: Create document record
        document = models.Document(
            job_id=job.id,
            original_filename=filename,
            file_type=models.FileType.VIDEO,
            gcs_path=gcs_path,
            transcription_path=analysis_path,  # Store analysis in transcription_path
            translated_text_path=translated_text_path,
            summary_path=summary_path,
            summary_text=summary[:1000] if summary else ""
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        
        # Step 6: Vectorize the text
        print(f"🔢 Creating embeddings from video analysis...")
        try:
            from vector_store import vectorise_and_store_alloydb
            # Delete existing chunks for this document
            db.query(models.DocumentChunk).filter(
                models.DocumentChunk.document_id == document.id
            ).delete(synchronize_session=False)
            db.commit()
            # Vectorize the final text (translated if Hindi, original if English)
            vectorise_and_store_alloydb(db, document.id, final_text, summary)
            print(f"✅ Embeddings created for video analysis")
        except Exception as e:
            print(f"⚠️ Vectorization failed: {e}")
        
        # Step 7: Push to graph processor queue
        print(f"📊 Queuing for graph processing...")
        username = job.user.username if job.user else "unknown"
        redis_pubsub.push_to_queue(settings.REDIS_QUEUE_GRAPH, {
            "job_id": job.id,
            "document_id": document.id,
            "gcs_text_path": translated_text_path or analysis_path,
            "username": username
        })
        
        # Update job progress
        job.processed_files += 1
        db.commit()
        
        print(f"✅ Completed processing: {filename}")
    
    def generate_summary(self, text: str) -> str:
        """
        Generate summary of video analysis using Gemini (dev) or Gemma (production)
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
        
        # ===== PRODUCTION MODE: Use local LLM =====
        print(f"🔧 Using local LLM for summarization (PRODUCTION MODE)")
        try:
            from ollama import Client
            client = Client(host=settings.SUMMARY_LLM_URL)
            
            prompt = f"""Summarize the following video analysis in 200 words or less:

{text[:5000]}

Summary:"""
            
            response = client.chat(
                model=settings.SUMMARY_LLM_MODEL,
                messages=[{'role': 'user', 'content': prompt}],
            )
            return response['message']['content'].strip()
        except Exception as e:
            print(f"⚠️ Summary generation error: {e}")
            return "Summary generation failed"


def main():
    """Main entry point"""
    print("🚀 Starting Video Processor Service...")
    print(f"📡 Using Redis Queue for parallel processing")
    print(f"🎬 Frame extraction rate: {SAVING_FRAMES_PER_SECOND} fps (1 frame every ~{1/SAVING_FRAMES_PER_SECOND:.1f} seconds)")
    print(f"👂 Listening to queue: {settings.REDIS_QUEUE_VIDEO}")
    
    service = VideoProcessorService()
    
    # Listen to video queue (blocking)
    redis_pubsub.listen_queue(
        queue_name=settings.REDIS_QUEUE_VIDEO,
        callback=service.process_job
    )


if __name__ == "__main__":
    main()

