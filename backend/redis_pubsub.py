import redis
import json
from typing import Dict, Any, Callable, Optional
from config import settings
import threading
from datetime import datetime
from datetime import datetime


class RedisPubSub:
    
    def __init__(self):
        # Create Redis connection
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
            decode_responses=True
        )
        self.pubsub = self.redis_client.pubsub()
    
    def publish(self, channel: str, message: Dict[str, Any]) -> int:

        message_json = json.dumps(message)
        return self.redis_client.publish(channel, message_json)
    
    def publish_job(self, job_id: str, gcs_prefix: str, channel: str) -> int:
        """Publish job-level message (for backward compatibility)"""
        message = {
            "job_id": job_id,
            "gcs_prefix": gcs_prefix,
            "action": "process"
        }
        return self.publish(channel, message)
    
    def publish_file(self, job_id: str, gcs_path: str, filename: str, channel: str) -> int:
        """Publish file-level message for parallel processing"""
        message = {
            "job_id": job_id,
            "gcs_path": gcs_path,
            "filename": filename,
            "action": "process_file"
        }
        return self.publish(channel, message)
    
    def push_to_queue(self, queue_name: str, message: Dict[str, Any]) -> int:
        """Push message to Redis queue (LIST) for work distribution"""
        message_json = json.dumps(message)
        return self.redis_client.lpush(queue_name, message_json)
    
    def push_file_to_queue(self, job_id: str, gcs_path: str, filename: str, queue_name: str, message_metadata: Optional[Dict[str, Any]] = None) -> int:
        """Push file to queue for parallel processing by multiple workers"""
        message = {
            "job_id": job_id,
            "gcs_path": gcs_path,
            "filename": filename,
            "action": "process_file",
            "metadata": message_metadata or {}
        }
        return self.push_to_queue(queue_name, message)
    
    def publish_artifact_status(self, job_id: str, filename: str, status: str, 
                                 current_stage: Optional[str] = None,
                                 processing_stages: Optional[Dict[str, float]] = None,
                                 error_message: Optional[str] = None,
                                 file_type: Optional[str] = None) -> int:
        """
        Publish per-artifact status update to a job-specific channel
        This allows real-time UI updates for individual files
        
        Progress is calculated based on completed stages out of total stages for the file type
        """
        # Calculate progress percentage based on completed stages
        progress_percent = self._calculate_progress(current_stage, processing_stages, file_type, status)
        
        channel = f"job_status:{job_id}"
        message = {
            "type": "artifact_status",
            "job_id": job_id,
            "filename": filename,
            "status": status,
            "current_stage": current_stage,
            "processing_stages": processing_stages or {},
            "progress_percent": progress_percent,
            "error_message": error_message,
            "timestamp": datetime.now().isoformat()
        }
        return self.publish(channel, message)
    
    @staticmethod
    def _calculate_progress(current_stage: Optional[str], 
                           processing_stages: Optional[Dict[str, float]], 
                           file_type: Optional[str],
                           status: str) -> int:
        """
        Calculate progress percentage based on current stage position in the pipeline
        
        Stage order by file type (translation is optional):
        - document: extraction → summarization → embeddings → graph_building → completed
        - audio: transcription → summarization → vectorization → graph_building → completed
        - video: frame_extraction → video_analysis → summarization → vectorization → graph_building → completed
        - cdr: parsing → phone_matching → completed
        
        Translation stage is optional and doesn't count in progress calculation
        """
        # Debug logging
        print(f"🔍 Progress Calculation - status: {status}, current_stage: {current_stage}, file_type: {file_type}")
        print(f"   processing_stages: {processing_stages}")
        
        if status == "completed":
            print(f"   ✅ Status is completed, returning 100%")
            return 100
        
        if status == "failed":
            print(f"   ❌ Status is failed, returning 0%")
            return 0
        
        if not current_stage:
            print(f"   ⚠️ No current_stage, returning 0%")
            return 0
        
        # Determine file type from processing stages if not provided
        if not file_type:
            if processing_stages:
                if "extraction" in processing_stages or "embeddings" in processing_stages:
                    file_type = "document"
                elif "transcription" in processing_stages:
                    file_type = "audio"
                elif "frame_extraction" in processing_stages or "video_analysis" in processing_stages:
                    file_type = "video"
            
            # Default to document if still unknown
            if not file_type:
                file_type = "document"
        
        # Define core stages (excluding optional translation) with their progress weights
        # Each stage represents equal progress (100 / number_of_core_stages)
        # Core stages for document/audio: extraction/transcription, summarization, embeddings/vectorization, awaiting_graph, graph_building, completed = 6 stages
        # Core stages for video: frame_extraction, video_analysis, summarization, vectorization, awaiting_graph, graph_building, completed = 7 stages
        # Core stages for CDR: parsing, phone_matching, completed = 3 stages
        stage_progress = {
            "document": {
                "starting": 0,
                "extraction": 16,        # 1/6 ≈ 16.67%
                "translation": 33,       # Optional, same as summarization
                "summarization": 33,     # 2/6 ≈ 33.33%
                "embeddings": 50,        # 3/6 = 50%
                "awaiting_graph": 66,    # 4/6 ≈ 66.67%
                "graph_building": 83,    # 5/6 ≈ 83.33%
                "completed": 100         # 6/6 = 100%
            },
            "audio": {
                "starting": 0,
                "transcription": 16,     # 1/6 ≈ 16.67%
                "translation": 33,       # Optional, same as summarization
                "summarization": 33,     # 2/6 ≈ 33.33%
                "vectorization": 50,     # 3/6 = 50%
                "awaiting_graph": 66,    # 4/6 ≈ 66.67%
                "graph_building": 83,    # 5/6 ≈ 83.33%
                "completed": 100         # 6/6 = 100%
            },
            "video": {
                "starting": 0,
                "frame_extraction": 14,  # 1/7 ≈ 14.29%
                "video_analysis": 28,    # 2/7 ≈ 28.57%
                "translation": 42,       # Optional, same as summarization
                "summarization": 42,     # 3/7 ≈ 42.86%
                "vectorization": 57,     # 4/7 ≈ 57.14%
                "awaiting_graph": 71,    # 5/7 ≈ 71.43%
                "graph_building": 85,    # 6/7 ≈ 85.71%
                "completed": 100         # 7/7 = 100%
            },
            "cdr": {
                "starting": 0,
                "parsing": 33,           # 1/3 ≈ 33.33%
                "phone_matching": 66,    # 2/3 ≈ 66.67%
                "completed": 100         # 3/3 = 100%
            }
        }
        
        # Get progress map for file type
        progress_map = stage_progress.get(file_type, stage_progress["document"])
        
        # Get progress for current stage
        progress = progress_map.get(current_stage, 0)
        
        # If stage not found in map, try to estimate based on completed stages count
        if progress == 0 and current_stage != "starting":
            # Count unique completed stages (excluding translation which is optional)
            completed_count = 0
            if processing_stages:
                for stage in processing_stages.keys():
                    if stage != "translation":  # Don't count optional translation
                        completed_count += 1
            
            # Add current stage if not in completed
            if current_stage not in (processing_stages or {}):
                completed_count += 1
            
            # Estimate progress: each core stage is roughly equal
            if file_type == "video":
                total_core_stages = 7  # video has more stages
            elif file_type == "cdr":
                total_core_stages = 3  # CDR has fewer stages
            else:
                total_core_stages = 6  # document and audio
            
            progress = int((completed_count / total_core_stages) * 100)
        
        # Cap at 99% until truly completed
        return min(int(progress), 99) if status != "completed" else 100
    
    def publish_job_status(self, job_id: str, status: str, 
                           current_stage: Optional[str] = None,
                           processed_files: Optional[int] = None,
                           total_files: Optional[int] = None) -> int:
        """
        Publish job-level status update
        """
        channel = f"job_status:{job_id}"
        message = {
            "type": "job_status",
            "job_id": job_id,
            "status": status,
            "current_stage": current_stage,
            "processed_files": processed_files,
            "total_files": total_files,
            "timestamp": datetime.now().isoformat()
        }
        return self.publish(channel, message)
    
    def subscribe(self, channel: str):
        self.pubsub.subscribe(channel)
    
    def listen(self, channel: str, callback: Callable[[Dict[str, Any]], None]):
        
        self.subscribe(channel)
        
        print(f"Listening to channel: {channel}")
        
        for message in self.pubsub.listen():
            if message['type'] == 'message':
                try:
                    data = json.loads(message['data'])
                    callback(data)
                except json.JSONDecodeError as e:
                    print(f"Error decoding message: {e}")
                except Exception as e:
                    print(f"Error processing message: {e}")
    
    def listen_async(self, channel: str, callback: Callable[[Dict[str, Any]], None]):

        thread = threading.Thread(
            target=self.listen,
            args=(channel, callback),
            daemon=True
        )
        thread.start()
        return thread
    
    def listen_queue(self, queue_name: str, callback: Callable[[Dict[str, Any]], None]):
        """
        Listen to Redis queue (blocking pop) for work distribution
        Each message is consumed by only ONE worker (true parallelism)
        """
        print(f"Listening to queue: {queue_name}")
        
        while True:
            try:
                # BRPOP: Block until message available, pop from right
                # Returns: (queue_name, message) or None after timeout
                result = self.redis_client.brpop(queue_name, timeout=1)
                
                if result:
                    queue, message_data = result
                    try:
                        # Decode if bytes
                        if isinstance(message_data, bytes):
                            message_data = message_data.decode('utf-8')
                        
                        data = json.loads(message_data)
                        callback(data)
                    except json.JSONDecodeError as e:
                        print(f"Error decoding message: {e}")
                    except Exception as e:
                        print(f"Error processing message: {e}")
                        import traceback
                        traceback.print_exc()
            except KeyboardInterrupt:
                print("\nShutting down worker...")
                break
            except Exception as e:
                print(f"Error in queue listener: {e}")
                import time
                time.sleep(1)  # Avoid tight loop on errors
    
    def subscribe_to_queue(self, queue_name: str, callback: Callable[[Dict[str, Any]], None]):
        """Alias for listen_queue for consistency"""
        self.listen_queue(queue_name, callback)
    
    def unsubscribe(self, channel: str):
        self.pubsub.unsubscribe(channel)
    
    def close(self):
        self.pubsub.close()
        self.redis_client.close()


# Singleton instance
redis_pubsub = RedisPubSub()

