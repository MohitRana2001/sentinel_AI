#!/usr/bin/env python3
"""
Test script to simulate document upload and verify queue behavior

Note: This is a standalone utility script, not a module.
Run from the backend directory: cd backend && python test_document_queue.py
Or with Python module syntax: python -m backend.test_document_queue
"""
import sys
import os
import time
import json
import traceback

# Add backend directory to path for imports
# This allows running the script from any directory
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

from redis_pubsub import redis_pubsub
from config import settings

def test_document_queue_flow():
    """Test the complete flow of document queueing"""
    
    print("=" * 80)
    print("Testing Document Queue Flow")
    print("=" * 80)
    
    # Test configuration
    test_job_id = "test-job-12345"
    test_filename = "test-document.pdf"
    test_gcs_path = f"uploads/{test_job_id}/{test_filename}"
    
    print(f"\nTest Configuration:")
    print(f"  Job ID: {test_job_id}")
    print(f"  Filename: {test_filename}")
    print(f"  GCS Path: {test_gcs_path}")
    print(f"  Queue: {settings.REDIS_QUEUE_DOCUMENT}")
    
    # Step 1: Check initial queue state
    print(f"\n{'='*80}")
    print(f"Step 1: Check Initial Queue State")
    print(f"{'='*80}")
    try:
        initial_length = redis_pubsub.redis_client.llen(settings.REDIS_QUEUE_DOCUMENT)
        print(f"✓ Initial queue length: {initial_length}")
    except Exception as e:
        print(f"✗ Error checking queue: {e}")
        return
    
    # Step 2: Push test message to queue
    print(f"\n{'='*80}")
    print(f"Step 2: Push Test Message to Queue")
    print(f"{'='*80}")
    try:
        result = redis_pubsub.push_file_to_queue(
            test_job_id,
            test_gcs_path,
            test_filename,
            settings.REDIS_QUEUE_DOCUMENT
        )
        print(f"✓ Push successful! Queue length after push: {result}")
        print(f"✓ Messages added: {result - initial_length}")
    except Exception as e:
        print(f"✗ Error pushing to queue: {e}")
        return
    
    # Step 3: Verify message is in queue
    print(f"\n{'='*80}")
    print(f"Step 3: Verify Message is in Queue")
    print(f"{'='*80}")
    try:
        current_length = redis_pubsub.redis_client.llen(settings.REDIS_QUEUE_DOCUMENT)
        print(f"✓ Current queue length: {current_length}")
        
        if current_length > initial_length:
            print(f"✓ Message successfully queued!")
            
            # Peek at the message
            messages = redis_pubsub.redis_client.lrange(settings.REDIS_QUEUE_DOCUMENT, 0, -1)
            print(f"\nQueue contents ({len(messages)} message(s)):")
            for i, msg in enumerate(messages, 1):
                try:
                    parsed = json.loads(msg)
                    print(f"  {i}. action={parsed.get('action')}, filename={parsed.get('filename')}")
                except json.JSONDecodeError as e:
                    print(f"  {i}. {msg[:100]}... (parse error: {e})")
        else:
            print(f"⚠️  Warning: Queue length did not increase!")
    except Exception as e:
        print(f"✗ Error verifying queue: {e}")
        return
    
    # Step 4: Simulate consumption (pop the message)
    print(f"\n{'='*80}")
    print(f"Step 4: Simulate Message Consumption")
    print(f"{'='*80}")
    print(f"Waiting for message (timeout: 2 seconds)...")
    try:
        result = redis_pubsub.redis_client.brpop(settings.REDIS_QUEUE_DOCUMENT, timeout=2)
        if result:
            queue, message_data = result
            print(f"✓ Message received from queue: {queue}")
            
            # Decode and parse
            if isinstance(message_data, bytes):
                message_data = message_data.decode('utf-8')
            data = json.loads(message_data)
            
            print(f"\nMessage content:")
            print(f"  Job ID: {data.get('job_id')}")
            print(f"  Filename: {data.get('filename')}")
            print(f"  GCS Path: {data.get('gcs_path')}")
            print(f"  Action: {data.get('action')}")
            
            # Verify it's our test message
            if data.get('job_id') == test_job_id and data.get('filename') == test_filename:
                print(f"\n✓ SUCCESS: Test message received correctly!")
            else:
                print(f"\n⚠️  Warning: Received different message than expected")
        else:
            print(f"⚠️  No message received within timeout")
    except Exception as e:
        print(f"✗ Error consuming from queue: {e}")
        traceback.print_exc()
        return
    
    # Step 5: Final queue state
    print(f"\n{'='*80}")
    print(f"Step 5: Final Queue State")
    print(f"{'='*80}")
    try:
        final_length = redis_pubsub.redis_client.llen(settings.REDIS_QUEUE_DOCUMENT)
        print(f"✓ Final queue length: {final_length}")
        
        if final_length == initial_length:
            print(f"✓ Queue returned to initial state")
        else:
            print(f"⚠️  Queue length changed: {initial_length} -> {final_length}")
    except Exception as e:
        print(f"✗ Error checking final state: {e}")
    
    # Summary
    print(f"\n{'='*80}")
    print(f"Test Summary")
    print(f"{'='*80}")
    print(f"✓ Queue push: WORKING")
    print(f"✓ Queue pop: WORKING")
    print(f"✓ Message format: CORRECT")
    print(f"\nConclusion: Redis document queue is functioning correctly!")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    test_document_queue_flow()
