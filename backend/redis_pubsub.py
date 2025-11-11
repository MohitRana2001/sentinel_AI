import redis
import json
from typing import Dict, Any, Callable
from config import settings
import threading


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
    
    def push_file_to_queue(self, job_id: str, gcs_path: str, filename: str, queue_name: str) -> int:
        """Push file to queue for parallel processing by multiple workers"""
        message = {
            "job_id": job_id,
            "gcs_path": gcs_path,
            "filename": filename,
            "action": "process_file"
        }
        return self.push_to_queue(queue_name, message)
    
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

