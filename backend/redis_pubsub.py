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
        Calculate progress percentage based on completed stages
        
        Stage order by file type:
        - document: extraction, translation, summarization, embeddings, graph_building
        - audio: transcription, translation, summarization, vectorization, graph_building
        - video: frame_extraction, video_analysis, translation, summarization, vectorization, graph_building
        """
        if status == "completed":
            return 100
        
        if status == "failed":
            return 0
        
        if not current_stage:
            return 0
        
        # Define stage orders for each file type
        stage_orders = {
            "document": ["starting", "extraction", "translation", "summarization", "embeddings", "awaiting_graph", "graph_building", "completed"],
            "audio": ["starting", "transcription", "translation", "summarization", "vectorization", "awaiting_graph", "graph_building", "completed"],
            "video": ["starting", "frame_extraction", "video_analysis", "translation", "summarization", "vectorization", "awaiting_graph", "graph_building", "completed"]
        }
        
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
        
        stages = stage_orders.get(file_type, stage_orders["document"])
        
        # Count completed stages (stages that have timing in processing_stages)
        completed_count = 0
        if processing_stages:
            completed_count = len(processing_stages)
        
        # Add 1 for current stage if not yet in completed stages
        if current_stage and current_stage not in (processing_stages or {}):
            completed_count += 1
        
        # Calculate percentage
        total_stages = len(stages) - 1  # Exclude "starting"
        if total_stages == 0:
            return 0
        
        progress = int((completed_count / total_stages) * 100)
        return min(progress, 99)  # Cap at 99% until truly completed
    
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
    
    def unsubscribe(self, channel: str):
        self.pubsub.unsubscribe(channel)
    
    def close(self):
        self.pubsub.close()
        self.redis_client.close()


# Singleton instance
redis_pubsub = RedisPubSub()

