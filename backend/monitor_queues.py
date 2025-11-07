#!/usr/bin/env python3
"""
Monitor Redis queues in real-time to diagnose queue issues
"""
import sys
import time
from redis_pubsub import redis_pubsub
from config import settings

def monitor_queues():
    """Monitor all Redis queues continuously"""
    print("=" * 80)
    print("Redis Queue Monitor - Press Ctrl+C to stop")
    print("=" * 80)
    print()
    
    queues_to_monitor = [
        ("Document Queue", settings.REDIS_QUEUE_DOCUMENT),
        ("Audio Queue", settings.REDIS_QUEUE_AUDIO),
        ("Video Queue", settings.REDIS_QUEUE_VIDEO),
        ("Graph Queue", settings.REDIS_QUEUE_GRAPH),
    ]
    
    # Also check legacy channels for comparison
    channels_to_check = [
        ("Document Channel (legacy)", settings.REDIS_CHANNEL_DOCUMENT),
        ("Audio Channel (legacy)", settings.REDIS_CHANNEL_AUDIO),
        ("Video Channel (legacy)", settings.REDIS_CHANNEL_VIDEO),
        ("Graph Channel (legacy)", settings.REDIS_CHANNEL_GRAPH),
    ]
    
    iteration = 0
    try:
        while True:
            iteration += 1
            print(f"\n[{time.strftime('%H:%M:%S')}] Iteration {iteration}")
            print("-" * 80)
            
            # Monitor queues (using LLEN to get queue length)
            print("\nQUEUES (Redis LISTs):")
            for name, queue in queues_to_monitor:
                try:
                    length = redis_pubsub.redis_client.llen(queue)
                    print(f"  {name:25s} ({queue:20s}): {length:3d} messages")
                    
                    # If queue has messages, peek at them
                    if length > 0:
                        messages = redis_pubsub.redis_client.lrange(queue, 0, 2)
                        print(f"    └─ First message preview: {str(messages[0])[:100]}...")
                except Exception as e:
                    print(f"  {name:25s} ({queue:20s}): ERROR - {e}")
            
            # Check if any subscribers are listening to legacy channels
            print("\nCHANNELS (Pub/Sub - for debugging):")
            for name, channel in channels_to_check:
                try:
                    # PUBSUB NUMSUB returns number of subscribers
                    result = redis_pubsub.redis_client.pubsub_numsub(channel)
                    if result:
                        subscribers = result[0][1] if len(result) > 0 else 0
                        status = "ACTIVE" if subscribers > 0 else "no subscribers"
                        print(f"  {name:25s} ({channel:20s}): {status}")
                except Exception as e:
                    print(f"  {name:25s} ({channel:20s}): ERROR - {e}")
            
            # Sleep before next iteration
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\n\n" + "=" * 80)
        print("Monitoring stopped.")
        print("=" * 80)

if __name__ == "__main__":
    monitor_queues()
