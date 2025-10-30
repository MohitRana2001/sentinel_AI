"""
Redis Pub/Sub utilities for inter-service communication
"""
import redis
import json
from typing import Dict, Any, Callable
from config import settings
import threading


class RedisPubSub:
    """Redis Pub/Sub handler for processor communication"""
    
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
        """
        Publish message to Redis channel
        
        Args:
            channel: Channel name
            message: Message dict to publish
            
        Returns:
            Number of subscribers that received the message
        """
        message_json = json.dumps(message)
        return self.redis_client.publish(channel, message_json)
    
    def publish_job(self, job_id: str, gcs_prefix: str, channel: str) -> int:
        """
        Publish job information to processor channel
        
        Args:
            job_id: Job ID
            gcs_prefix: GCS prefix where files are stored
            channel: Target channel (document_processor, audio_processor, video_processor)
            
        Returns:
            Number of subscribers
        """
        message = {
            "job_id": job_id,
            "gcs_prefix": gcs_prefix,
            "action": "process"
        }
        return self.publish(channel, message)
    
    def subscribe(self, channel: str):
        """Subscribe to a channel"""
        self.pubsub.subscribe(channel)
    
    def listen(self, channel: str, callback: Callable[[Dict[str, Any]], None]):
        """
        Listen to channel and execute callback on messages
        
        Args:
            channel: Channel name
            callback: Function to call with message dict
        """
        self.subscribe(channel)
        
        print(f"🎧 Listening to channel: {channel}")
        
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
        """
        Listen to channel in a separate thread
        
        Args:
            channel: Channel name
            callback: Function to call with message dict
        """
        thread = threading.Thread(
            target=self.listen,
            args=(channel, callback),
            daemon=True
        )
        thread.start()
        return thread
    
    def unsubscribe(self, channel: str):
        """Unsubscribe from channel"""
        self.pubsub.unsubscribe(channel)
    
    def close(self):
        """Close Redis connection"""
        self.pubsub.close()
        self.redis_client.close()


# Singleton instance
redis_pubsub = RedisPubSub()

