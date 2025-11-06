# Redis DLQ (Dead Letter Queue) and Caching Implementation Guide

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [DLQ Implementation](#dlq-implementation)
3. [Caching Strategy](#caching-strategy)
4. [Implementation Steps](#implementation-steps)
5. [Code Examples](#code-examples)
6. [Monitoring and Maintenance](#monitoring-and-maintenance)

---

## Executive Summary

This document provides a comprehensive guide for implementing:
1. **Dead Letter Queue (DLQ)** using Redis for handling failed processing jobs
2. **Caching strategies** using Redis to optimize application performance and reduce API calls

### Benefits
- **Reliability**: Failed jobs are captured and can be retried or analyzed
- **Performance**: Reduced database queries and API calls through intelligent caching
- **Scalability**: Better resource utilization and faster response times
- **Cost Efficiency**: Reduced compute costs through caching frequently accessed data

---

## DLQ Implementation

### Overview
A Dead Letter Queue (DLQ) captures messages that fail to process successfully after multiple retry attempts. This prevents loss of work and provides a mechanism for manual review and reprocessing.

### Current Architecture
Currently, the application uses Redis for work distribution:
- **Redis Queues**: `document_queue`, `audio_queue`, `video_queue`, `graph_queue`
- **Processing Flow**: Jobs → Redis Queue → Worker Processing → Database Storage
- **Problem**: When processing fails, messages are lost

### Proposed DLQ Architecture

```
┌─────────────┐
│ Main Queue  │
│ (e.g., doc) │
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│  Worker Process  │
│                  │
│  Try Process     │◄────┐
│                  │     │
└────┬─────────┬───┘     │
     │         │         │
  Success    Failure     │
     │         │         │
     ▼         ▼         │
┌────────┐ ┌─────────┐  │
│  DB    │ │   DLQ   │  │ Retry
│ Update │ │ (Redis) │  │ Logic
└────────┘ └────┬────┘  │
                │        │
                └────────┘
                (Max Retries)
                    │
                    ▼
           ┌─────────────────┐
           │ DLQ Permanent   │
           │ (Requires Manual│
           │  Intervention)  │
           └─────────────────┘
```

### DLQ Components

#### 1. **Dead Letter Queues**
Create dedicated DLQ for each processing queue:
- `document_dlq` - For failed document processing
- `audio_dlq` - For failed audio processing
- `video_dlq` - For failed video processing
- `graph_dlq` - For failed graph processing

#### 2. **Retry Queues**
Implement retry queues with exponential backoff:
- `document_retry` - Retry queue for documents
- `audio_retry` - Retry queue for audio
- `video_retry` - Retry queue for video
- `graph_retry` - Retry queue for graph

#### 3. **Metadata Storage**
Store failure metadata in Redis hashes:
```
Key: dlq:metadata:{job_id}:{filename}
Fields:
  - original_queue: document_queue
  - failure_count: 3
  - first_failure_time: 2025-11-06T10:00:00Z
  - last_failure_time: 2025-11-06T10:30:00Z
  - error_message: Connection timeout to storage backend
  - stack_trace: ...
  - retry_count: 2
```

### Implementation Details

#### Configuration (config.py)
```python
# DLQ Configuration
REDIS_DLQ_DOCUMENT: str = "document_dlq"
REDIS_DLQ_AUDIO: str = "audio_dlq"
REDIS_DLQ_VIDEO: str = "video_dlq"
REDIS_DLQ_GRAPH: str = "graph_dlq"

# Retry Configuration
REDIS_RETRY_DOCUMENT: str = "document_retry"
REDIS_RETRY_AUDIO: str = "audio_retry"
REDIS_RETRY_VIDEO: str = "video_retry"
REDIS_RETRY_GRAPH: str = "graph_retry"

# DLQ Settings
MAX_RETRY_ATTEMPTS: int = int(os.getenv("MAX_RETRY_ATTEMPTS", "3"))
RETRY_BACKOFF_BASE_SECONDS: int = int(os.getenv("RETRY_BACKOFF_BASE_SECONDS", "60"))
DLQ_RETENTION_DAYS: int = int(os.getenv("DLQ_RETENTION_DAYS", "7"))
```

#### Enhanced RedisPubSub Class
Add DLQ-specific methods to `redis_pubsub.py`:

```python
def push_to_dlq(self, dlq_name: str, message: Dict[str, Any], error: str, stack_trace: str = None) -> int:
    """Push failed message to Dead Letter Queue with metadata"""
    # Add failure metadata
    enriched_message = {
        **message,
        "dlq_metadata": {
            "failure_time": datetime.now(timezone.utc).isoformat(),
            "error_message": error,
            "stack_trace": stack_trace,
            "original_queue": message.get("original_queue", "unknown")
        }
    }
    
    # Store in DLQ
    message_json = json.dumps(enriched_message)
    result = self.redis_client.lpush(dlq_name, message_json)
    
    # Store metadata separately for easy querying
    job_id = message.get("job_id")
    filename = message.get("filename", "unknown")
    metadata_key = f"dlq:metadata:{job_id}:{filename}"
    
    self.redis_client.hset(metadata_key, mapping={
        "original_queue": message.get("original_queue", "unknown"),
        "failure_count": "1",
        "first_failure_time": datetime.now(timezone.utc).isoformat(),
        "last_failure_time": datetime.now(timezone.utc).isoformat(),
        "error_message": error,
        "stack_trace": stack_trace or "",
        "message": message_json
    })
    
    # Set expiration on metadata (DLQ_RETENTION_DAYS)
    self.redis_client.expire(metadata_key, settings.DLQ_RETENTION_DAYS * 86400)
    
    return result

def push_to_retry_queue(self, retry_queue: str, message: Dict[str, Any], retry_count: int, 
                       original_queue: str) -> int:
    """Push message to retry queue with backoff"""
    # Calculate delay using exponential backoff
    delay_seconds = settings.RETRY_BACKOFF_BASE_SECONDS * (2 ** (retry_count - 1))
    retry_at = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
    
    enriched_message = {
        **message,
        "retry_metadata": {
            "retry_count": retry_count,
            "retry_at": retry_at.isoformat(),
            "original_queue": original_queue
        }
    }
    
    message_json = json.dumps(enriched_message)
    
    # Use Redis sorted set for delayed retry
    # Score is Unix timestamp when to retry
    return self.redis_client.zadd(retry_queue, {message_json: retry_at.timestamp()})

def get_ready_retries(self, retry_queue: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Get messages from retry queue that are ready to be retried"""
    now = datetime.now(timezone.utc).timestamp()
    
    # Get messages with score <= now (ready to retry)
    messages = self.redis_client.zrangebyscore(retry_queue, 0, now, start=0, num=limit)
    
    # Remove from retry queue
    if messages:
        self.redis_client.zremrangebyscore(retry_queue, 0, now)
    
    # Parse JSON messages
    parsed_messages = []
    for msg in messages:
        try:
            if isinstance(msg, bytes):
                msg = msg.decode('utf-8')
            parsed_messages.append(json.loads(msg))
        except json.JSONDecodeError as e:
            print(f"❌ Error decoding retry message: {e}")
    
    return parsed_messages

def get_dlq_count(self, dlq_name: str) -> int:
    """Get count of messages in DLQ"""
    return self.redis_client.llen(dlq_name)

def get_dlq_messages(self, dlq_name: str, start: int = 0, end: int = -1) -> List[Dict[str, Any]]:
    """Get messages from DLQ for inspection"""
    messages = self.redis_client.lrange(dlq_name, start, end)
    
    parsed_messages = []
    for msg in messages:
        try:
            if isinstance(msg, bytes):
                msg = msg.decode('utf-8')
            parsed_messages.append(json.loads(msg))
        except json.JSONDecodeError as e:
            print(f"❌ Error decoding DLQ message: {e}")
    
    return parsed_messages

def requeue_from_dlq(self, dlq_name: str, target_queue: str, message_index: int = 0) -> bool:
    """Move a message from DLQ back to processing queue"""
    # Get message from DLQ by index
    messages = self.redis_client.lrange(dlq_name, message_index, message_index)
    
    if not messages:
        return False
    
    message = messages[0]
    
    # Remove from DLQ
    self.redis_client.lrem(dlq_name, 1, message)
    
    # Push to target queue
    self.redis_client.lpush(target_queue, message)
    
    return True
```

#### Enhanced Processor Service
Modify processor services (e.g., `document_processor_service.py`) to handle failures:

```python
def _process_single_file(self, message: dict):
    job_id = message.get("job_id")
    gcs_path = message.get("gcs_path")
    filename = message.get("filename")
    retry_count = message.get("retry_metadata", {}).get("retry_count", 0)
    original_queue = message.get("retry_metadata", {}).get("original_queue", settings.REDIS_QUEUE_DOCUMENT)
    
    print(f"📄 Document Processor received file: {filename} (job: {job_id}, retry: {retry_count})")
    
    db = SessionLocal()
    try:
        # ... existing processing logic ...
        
        self.process_document(db, job, gcs_path)
        self._check_job_completion(db, job)
        print(f"✅ Completed processing: {filename}")
        
    except Exception as e:
        error_msg = str(e)
        stack_trace = traceback.format_exc()
        print(f"❌ Error processing file {filename}: {error_msg}")
        print(stack_trace)
        
        # Handle retry logic
        if retry_count < settings.MAX_RETRY_ATTEMPTS:
            # Push to retry queue
            print(f"🔄 Pushing {filename} to retry queue (attempt {retry_count + 1}/{settings.MAX_RETRY_ATTEMPTS})")
            message["original_queue"] = original_queue
            redis_pubsub.push_to_retry_queue(
                settings.REDIS_RETRY_DOCUMENT,
                message,
                retry_count + 1,
                original_queue
            )
        else:
            # Max retries reached, push to DLQ
            print(f"💀 Max retries reached for {filename}, pushing to DLQ")
            message["original_queue"] = original_queue
            redis_pubsub.push_to_dlq(
                settings.REDIS_DLQ_DOCUMENT,
                message,
                error_msg,
                stack_trace
            )
            
            # Update job status
            try:
                job.error_message = f"Failed to process {filename}: {error_msg}"
                db.commit()
            except:
                pass
    finally:
        db.close()
```

#### Retry Worker Service
Create a new retry worker service (`retry_worker_service.py`):

```python
import time
from redis_pubsub import redis_pubsub
from config import settings

class RetryWorkerService:
    """
    Background service that monitors retry queues and resubmits
    messages when their retry time is reached
    """
    
    def __init__(self):
        self.retry_queues = [
            (settings.REDIS_RETRY_DOCUMENT, settings.REDIS_QUEUE_DOCUMENT),
            (settings.REDIS_RETRY_AUDIO, settings.REDIS_QUEUE_AUDIO),
            (settings.REDIS_RETRY_VIDEO, settings.REDIS_QUEUE_VIDEO),
            (settings.REDIS_RETRY_GRAPH, settings.REDIS_QUEUE_GRAPH),
        ]
    
    def run(self):
        print("🔄 Retry Worker Service started")
        
        while True:
            try:
                for retry_queue, target_queue in self.retry_queues:
                    # Get messages ready to retry
                    messages = redis_pubsub.get_ready_retries(retry_queue, limit=100)
                    
                    if messages:
                        print(f"🔄 Found {len(messages)} messages ready to retry from {retry_queue}")
                        
                        for msg in messages:
                            # Remove retry metadata and push to original queue
                            msg.pop("retry_metadata", None)
                            redis_pubsub.push_to_queue(target_queue, msg)
                            
                            filename = msg.get("filename", "unknown")
                            retry_count = msg.get("retry_metadata", {}).get("retry_count", 0)
                            print(f"   ↻ Requeued {filename} (retry #{retry_count})")
                
                # Check every 10 seconds
                time.sleep(10)
                
            except KeyboardInterrupt:
                print("\n👋 Retry Worker shutting down...")
                break
            except Exception as e:
                print(f"❌ Error in retry worker: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(10)

if __name__ == "__main__":
    service = RetryWorkerService()
    service.run()
```

#### API Endpoints for DLQ Management
Add to `main.py`:

```python
@app.get(f"{settings.API_PREFIX}/admin/dlq/stats")
async def get_dlq_stats(
    admin_user: models.User = Depends(get_super_admin)
):
    """Get statistics about DLQ"""
    return {
        "document_dlq": redis_pubsub.get_dlq_count(settings.REDIS_DLQ_DOCUMENT),
        "audio_dlq": redis_pubsub.get_dlq_count(settings.REDIS_DLQ_AUDIO),
        "video_dlq": redis_pubsub.get_dlq_count(settings.REDIS_DLQ_VIDEO),
        "graph_dlq": redis_pubsub.get_dlq_count(settings.REDIS_DLQ_GRAPH),
    }

@app.get(f"{settings.API_PREFIX}/admin/dlq/{{queue_name}}")
async def get_dlq_messages(
    queue_name: str,
    limit: int = 50,
    admin_user: models.User = Depends(get_super_admin)
):
    """Get messages from a specific DLQ"""
    dlq_map = {
        "document": settings.REDIS_DLQ_DOCUMENT,
        "audio": settings.REDIS_DLQ_AUDIO,
        "video": settings.REDIS_DLQ_VIDEO,
        "graph": settings.REDIS_DLQ_GRAPH,
    }
    
    dlq_name = dlq_map.get(queue_name)
    if not dlq_name:
        raise HTTPException(404, "DLQ not found")
    
    messages = redis_pubsub.get_dlq_messages(dlq_name, 0, limit - 1)
    return {
        "queue": queue_name,
        "count": len(messages),
        "messages": messages
    }

@app.post(f"{settings.API_PREFIX}/admin/dlq/{{queue_name}}/requeue/{{message_index}}")
async def requeue_dlq_message(
    queue_name: str,
    message_index: int,
    admin_user: models.User = Depends(get_super_admin)
):
    """Requeue a message from DLQ back to processing queue"""
    dlq_map = {
        "document": (settings.REDIS_DLQ_DOCUMENT, settings.REDIS_QUEUE_DOCUMENT),
        "audio": (settings.REDIS_DLQ_AUDIO, settings.REDIS_QUEUE_AUDIO),
        "video": (settings.REDIS_DLQ_VIDEO, settings.REDIS_QUEUE_VIDEO),
        "graph": (settings.REDIS_DLQ_GRAPH, settings.REDIS_QUEUE_GRAPH),
    }
    
    queues = dlq_map.get(queue_name)
    if not queues:
        raise HTTPException(404, "DLQ not found")
    
    dlq_name, target_queue = queues
    success = redis_pubsub.requeue_from_dlq(dlq_name, target_queue, message_index)
    
    if not success:
        raise HTTPException(404, "Message not found in DLQ")
    
    return {"message": "Message requeued successfully"}
```

---

## Caching Strategy

### Overview
Implement intelligent caching to reduce database queries, API calls, and improve response times.

### Cache Candidates Analysis

#### 1. **User Authentication & Session Data** (HIGH PRIORITY)
**Current Issue**: Every API request validates the JWT token and queries the database for user details.

**Cache Strategy**:
- Cache user objects by user ID
- Cache user RBAC permissions
- TTL: 15 minutes (900 seconds)

**Benefits**:
- Reduce database queries by ~80% for authenticated requests
- Faster authentication checks
- Reduced database load

**Implementation**:
```python
# Cache key pattern: user:{user_id}
# Cache key pattern: user:rbac:{user_id}
```

#### 2. **Job Status & Progress** (HIGH PRIORITY)
**Current Issue**: Frontend polls job status frequently (every 2-5 seconds), causing excessive database queries.

**Cache Strategy**:
- Cache job status and progress data
- TTL: 5 seconds (reduces DB load while keeping data fresh)
- Invalidate cache when job status changes

**Benefits**:
- Reduce database queries by ~90% for status polling
- Faster response times for job status endpoint
- Better user experience with quicker updates

**Implementation**:
```python
# Cache key pattern: job:status:{job_id}
# Cache key pattern: job:progress:{job_id}
```

#### 3. **Document Summaries & Transcriptions** (HIGH PRIORITY)
**Current Issue**: Document summaries and transcriptions are fetched from storage backend on every request.

**Cache Strategy**:
- Cache document summaries (can be large, use compression)
- Cache transcriptions for audio/video files
- TTL: 1 hour (3600 seconds) - these rarely change

**Benefits**:
- Eliminate storage backend calls for frequently accessed documents
- Reduce GCS/storage API costs
- Faster response times

**Implementation**:
```python
# Cache key pattern: doc:summary:{document_id}
# Cache key pattern: doc:transcription:{document_id}
# Cache key pattern: doc:translation:{document_id}
```

#### 4. **Vector Search Results** (MEDIUM PRIORITY)
**Current Issue**: Same chat queries result in identical vector searches.

**Cache Strategy**:
- Cache vector search results by query hash
- TTL: 30 minutes (1800 seconds)
- Cache invalidated when new documents are added to job

**Benefits**:
- Reduce expensive vector similarity computations
- Faster chat responses for common queries
- Reduced database load

**Implementation**:
```python
# Cache key pattern: vector:search:{hash(query)}:{job_id}
# Use MD5 hash of query + filters as cache key
```

#### 5. **Knowledge Graph Data** (MEDIUM PRIORITY)
**Current Issue**: Neo4j queries for graphs can be expensive and slow.

**Cache Strategy**:
- Cache graph node and relationship data per job
- TTL: 10 minutes (600 seconds)
- Invalidate when graph is updated

**Benefits**:
- Reduce Neo4j query load
- Faster graph visualization
- Better scalability

**Implementation**:
```python
# Cache key pattern: graph:{job_id}
# Cache key pattern: graph:partial:{job_id}:{document_ids_hash}
```

#### 6. **Configuration & Settings** (LOW PRIORITY)
**Current Issue**: Application settings and configuration are read from environment/file repeatedly.

**Cache Strategy**:
- Cache application configuration at startup
- Cache rarely changing metadata (allowed extensions, limits, etc.)
- TTL: 1 hour or until application restart

**Benefits**:
- Marginal performance improvement
- Reduced file system access

**Implementation**:
```python
# Cache key pattern: config:app
# Cache key pattern: config:rbac_levels
```

#### 7. **User Lists (Managers, Analysts)** (LOW PRIORITY)
**Current Issue**: Admin/Manager views query full user lists on every page load.

**Cache Strategy**:
- Cache manager list with their analysts
- Cache analyst list
- TTL: 5 minutes (300 seconds)
- Invalidate when user is created/deleted/modified

**Benefits**:
- Faster admin dashboard loading
- Reduced database queries

**Implementation**:
```python
# Cache key pattern: users:managers
# Cache key pattern: users:analysts:{manager_id}
```

### Cache Implementation Details

#### Redis Cache Helper Class
Create `backend/cache.py`:

```python
import json
import hashlib
from typing import Any, Optional, Callable
from datetime import timedelta
from redis import Redis
from config import settings
import functools

class RedisCache:
    """
    Redis-based caching helper with automatic serialization,
    TTL management, and cache invalidation
    """
    
    def __init__(self):
        self.redis_client = Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
            decode_responses=False  # We'll handle encoding/decoding
        )
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache, returns None if not found"""
        try:
            value = self.redis_client.get(key)
            if value is None:
                return None
            
            # Deserialize
            if isinstance(value, bytes):
                value = value.decode('utf-8')
            
            return json.loads(value)
        except Exception as e:
            print(f"⚠️ Cache get error for key {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in cache with TTL in seconds"""
        try:
            # Serialize
            serialized = json.dumps(value)
            
            # Set with expiration
            return self.redis_client.setex(key, ttl, serialized)
        except Exception as e:
            print(f"⚠️ Cache set error for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            return self.redis_client.delete(key) > 0
        except Exception as e:
            print(f"⚠️ Cache delete error for key {key}: {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern (e.g., 'user:*')"""
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            print(f"⚠️ Cache delete pattern error for {pattern}: {e}")
            return 0
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            return self.redis_client.exists(key) > 0
        except Exception as e:
            print(f"⚠️ Cache exists error for key {key}: {e}")
            return False
    
    def increment(self, key: str, amount: int = 1) -> int:
        """Increment a counter"""
        try:
            return self.redis_client.incrby(key, amount)
        except Exception as e:
            print(f"⚠️ Cache increment error for key {key}: {e}")
            return 0
    
    def cache_result(self, key_prefix: str, ttl: int = 300):
        """
        Decorator to cache function results
        
        Usage:
            @cache.cache_result("user", ttl=900)
            def get_user(user_id: int):
                # Expensive operation
                return user_data
        """
        def decorator(func: Callable):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Build cache key from function args
                key_parts = [key_prefix]
                key_parts.extend([str(arg) for arg in args])
                key_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])
                cache_key = ":".join(key_parts)
                
                # Try to get from cache
                cached = self.get(cache_key)
                if cached is not None:
                    print(f"✅ Cache hit: {cache_key}")
                    return cached
                
                # Execute function
                print(f"❌ Cache miss: {cache_key}")
                result = func(*args, **kwargs)
                
                # Store in cache
                self.set(cache_key, result, ttl)
                
                return result
            
            return wrapper
        return decorator
    
    def get_or_set(self, key: str, factory: Callable, ttl: int = 300) -> Any:
        """
        Get value from cache, or compute and cache it if not present
        
        Usage:
            value = cache.get_or_set(
                "user:123",
                lambda: db.query(User).get(123),
                ttl=900
            )
        """
        cached = self.get(key)
        if cached is not None:
            return cached
        
        # Compute value
        value = factory()
        
        # Store in cache
        if value is not None:
            self.set(key, value, ttl)
        
        return value
    
    def hash_key(self, *parts) -> str:
        """Create a hash-based cache key from parts"""
        combined = ":".join([str(p) for p in parts])
        return hashlib.md5(combined.encode()).hexdigest()

# Singleton instance
cache = RedisCache()
```

#### Caching in API Endpoints

**Example 1: User Authentication Caching**
Modify `security.py`:

```python
from cache import cache

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> models.User:
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: int = payload.get("sub")
        
        if user_id is None:
            raise credentials_exception
        
        # Try to get user from cache
        cache_key = f"user:{user_id}"
        cached_user_data = cache.get(cache_key)
        
        if cached_user_data:
            # Reconstruct user object from cached data
            user = models.User(**cached_user_data)
            return user
        
        # Cache miss - query database
        user = db.query(models.User).filter(models.User.id == user_id).first()
        
        if user is None:
            raise credentials_exception
        
        # Cache user data (serialize to dict)
        user_data = {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "rbac_level": user.rbac_level.value,
            "manager_id": user.manager_id,
            "created_by": user.created_by,
        }
        cache.set(cache_key, user_data, ttl=900)  # 15 minutes
        
        return user
        
    except JWTError:
        raise credentials_exception
```

**Example 2: Job Status Caching**
Modify `main.py`:

```python
from cache import cache

@app.get(f"{settings.API_PREFIX}/jobs/{{job_id:path}}/status")
async def get_job_status(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Try cache first
    cache_key = f"job:status:{job_id}"
    cached_status = cache.get(cache_key)
    
    if cached_status:
        # Verify user still has access (lightweight check)
        if user_has_job_access_by_id(current_user, job_id):
            return cached_status
    
    # Cache miss or access changed - query database
    job = db.query(models.ProcessingJob).filter(
        models.ProcessingJob.id == job_id
    ).first()
    
    if not job:
        raise HTTPException(404, "Job not found")
    
    if not user_has_job_access(current_user, job):
        raise HTTPException(403, "Insufficient permissions for this job")
    
    progress_percentage = 0.0
    if job.total_files > 0:
        progress_percentage = (job.processed_files / job.total_files) * 100
    
    result = {
        "job_id": job.id,
        "status": job.status.value,
        "total_files": job.total_files,
        "processed_files": job.processed_files,
        "progress_percentage": round(progress_percentage, 2),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "error_message": job.error_message
    }
    
    # Cache for 5 seconds (balance between freshness and load)
    cache.set(cache_key, result, ttl=5)
    
    return result
```

**Example 3: Document Summary Caching**
Modify `main.py`:

```python
from cache import cache

@app.get(f"{settings.API_PREFIX}/documents/{{document_id}}/summary")
async def get_document_summary(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Try cache first
    cache_key = f"doc:summary:{document_id}"
    cached_summary = cache.get(cache_key)
    
    if cached_summary:
        return cached_summary
    
    # Cache miss - query database and storage
    document = db.query(models.Document).filter(
        models.Document.id == document_id
    ).first()
    
    if not document:
        raise HTTPException(404, "Document not found")
    
    if not user_has_document_access(current_user, document):
        raise HTTPException(403, "Insufficient permissions for this document")
    
    if document.summary_text:
        content = document.summary_text
    elif document.summary_path:
        try:
            content = storage_manager.download_text(document.summary_path)
        except:
            content = "Summary not available"
    else:
        content = "Summary not yet generated"
    
    result = {
        "document_id": document.id,
        "filename": document.original_filename,
        "content": content,
        "content_type": "summary"
    }
    
    # Cache for 1 hour (summaries don't change)
    cache.set(cache_key, result, ttl=3600)
    
    return result
```

**Example 4: Vector Search Caching**
Modify `main.py`:

```python
from cache import cache
import hashlib

@app.post(f"{settings.API_PREFIX}/chat")
async def chat_with_documents(
    message: str,
    job_id: Optional[str] = None,
    document_ids: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if not message:
        raise HTTPException(400, "Message is required")
    
    # Create cache key from query parameters
    cache_key_parts = [message, job_id or "all", document_ids or "all"]
    cache_key_hash = hashlib.md5(":".join(cache_key_parts).encode()).hexdigest()
    cache_key = f"vector:search:{cache_key_hash}"
    
    # Try to get cached search results
    cached_results = cache.get(cache_key)
    
    if cached_results:
        print(f"✅ Using cached vector search results")
        results = cached_results
    else:
        print(f"❌ Cache miss, performing vector search")
        
        # Parse document IDs if provided
        doc_id_list = None
        if document_ids:
            try:
                doc_id_list = [int(id.strip()) for id in document_ids.split(',') if id.strip()]
            except ValueError:
                raise HTTPException(400, "Invalid document_ids format")
        
        # Access control checks...
        if job_id:
            job = db.query(models.ProcessingJob).filter(models.ProcessingJob.id == job_id).first()
            if not job:
                raise HTTPException(404, "Job not found")
            if not user_has_job_access(current_user, job):
                raise HTTPException(403, "Insufficient permissions for this job")
        
        # Perform vector search
        vector_store = VectorStore(db)
        results = vector_store.similarity_search(
            query=message,
            k=8,
            document_ids=doc_id_list,
            job_id=job_id,
            user=current_user
        )
        
        # Cache results for 30 minutes
        cache.set(cache_key, results, ttl=1800)
    
    # Generate response using cached or fresh results
    context = "\n\n".join([r["chunk_text"][:800] for r in results[:5]])
    
    # ... rest of chat logic ...
```

**Example 5: Knowledge Graph Caching**
Modify `main.py`:

```python
from cache import cache
import hashlib

@app.get(f"{settings.API_PREFIX}/jobs/{{job_id:path}}/graph")
async def get_job_graph(
    job_id: str,
    document_ids: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get combined knowledge graph from Neo4j with caching"""
    
    # Check job access
    job = db.query(models.ProcessingJob).filter(
        models.ProcessingJob.id == job_id
    ).first()
    
    if not job:
        raise HTTPException(404, "Job not found")
    
    if not user_has_job_access(current_user, job):
        raise HTTPException(403, "Insufficient permissions for this job")
    
    if not graph:
        raise HTTPException(500, "Graph database is not connected")
    
    # Create cache key
    doc_ids_hash = hashlib.md5((document_ids or "all").encode()).hexdigest()
    cache_key = f"graph:{job_id}:{doc_ids_hash}"
    
    # Try cache
    cached_graph = cache.get(cache_key)
    if cached_graph:
        print(f"✅ Using cached graph data")
        return cached_graph
    
    print(f"❌ Cache miss, querying Neo4j")
    
    # Get document IDs
    if document_ids:
        try:
            selected_ids = [int(id.strip()) for id in document_ids.split(',') if id.strip()]
        except ValueError:
            raise HTTPException(400, "Invalid document_ids format")
        
        doc_ids = db.query(models.Document.id).filter(
            models.Document.job_id == job_id,
            models.Document.id.in_(selected_ids)
        ).all()
    else:
        doc_ids = db.query(models.Document.id).filter(
            models.Document.job_id == job_id
        ).all()
    
    document_ids_list = [str(doc_id[0]) for doc_id in doc_ids]
    
    if not document_ids_list:
        return {"nodes": [], "relationships": []}
    
    # Query Neo4j (existing logic)
    cypher_query = """
    // ... existing Cypher query ...
    """
    
    try:
        result = graph.query(cypher_query, params={"doc_ids": document_ids_list})
    except Exception as e:
        print(f"❌ Neo4j query failed: {e}")
        raise HTTPException(500, f"Graph query failed: {str(e)}")
    
    # Format results (existing logic)
    nodes = {}
    relationships = set()
    
    # ... existing formatting logic ...
    
    graph_data = {
        "nodes": list(nodes.values()),
        "relationships": [
            {
                "source": source_id,
                "target": target_id,
                "type": rel_type,
                "properties": dict(props)
            }
            for (source_id, target_id, rel_type, props) in relationships
        ]
    }
    
    # Cache for 10 minutes
    cache.set(cache_key, graph_data, ttl=600)
    
    return graph_data
```

#### Cache Invalidation Strategy

**When to Invalidate Cache:**

1. **User Cache** - Invalidate when:
   - User updates their profile
   - User permissions change
   - User is deleted

```python
def invalidate_user_cache(user_id: int):
    cache.delete(f"user:{user_id}")
    cache.delete(f"user:rbac:{user_id}")
```

2. **Job Cache** - Invalidate when:
   - Job status changes
   - Job progress updates
   - Job completes or fails

```python
def invalidate_job_cache(job_id: str):
    cache.delete(f"job:status:{job_id}")
    cache.delete(f"job:progress:{job_id}")
```

3. **Document Cache** - Invalidate when:
   - Document is updated (rare)
   - Document is deleted

```python
def invalidate_document_cache(document_id: int):
    cache.delete(f"doc:summary:{document_id}")
    cache.delete(f"doc:transcription:{document_id}")
    cache.delete(f"doc:translation:{document_id}")
```

4. **Graph Cache** - Invalidate when:
   - New entities are added to job
   - Graph relationships are updated

```python
def invalidate_graph_cache(job_id: str):
    cache.delete_pattern(f"graph:{job_id}:*")
```

5. **Vector Search Cache** - Invalidate when:
   - New documents are added to job
   - Document chunks are updated

```python
def invalidate_vector_search_cache(job_id: str):
    cache.delete_pattern(f"vector:search:*:{job_id}:*")
```

#### Cache Monitoring

Add cache monitoring endpoints:

```python
@app.get(f"{settings.API_PREFIX}/admin/cache/stats")
async def get_cache_stats(
    admin_user: models.User = Depends(get_super_admin)
):
    """Get Redis cache statistics"""
    info = cache.redis_client.info("stats")
    memory = cache.redis_client.info("memory")
    
    return {
        "total_connections": info.get("total_connections_received"),
        "total_commands": info.get("total_commands_processed"),
        "keyspace_hits": info.get("keyspace_hits"),
        "keyspace_misses": info.get("keyspace_misses"),
        "hit_rate": info.get("keyspace_hits") / (info.get("keyspace_hits") + info.get("keyspace_misses")) * 100 if (info.get("keyspace_hits") + info.get("keyspace_misses")) > 0 else 0,
        "used_memory_human": memory.get("used_memory_human"),
        "used_memory_peak_human": memory.get("used_memory_peak_human"),
    }

@app.delete(f"{settings.API_PREFIX}/admin/cache/clear")
async def clear_cache(
    pattern: Optional[str] = None,
    admin_user: models.User = Depends(get_super_admin)
):
    """Clear cache (all or by pattern)"""
    if pattern:
        deleted = cache.delete_pattern(pattern)
        return {"message": f"Cleared {deleted} keys matching pattern: {pattern}"}
    else:
        cache.redis_client.flushdb()
        return {"message": "Cleared all cache"}
```

---

## Implementation Steps

### Phase 1: DLQ Implementation (Week 1)

1. **Day 1-2: Configuration and Redis Enhancement**
   - Update `config.py` with DLQ settings
   - Enhance `redis_pubsub.py` with DLQ methods
   - Add unit tests for DLQ functionality

2. **Day 3-4: Processor Service Updates**
   - Update all processor services with error handling
   - Implement retry logic in processor services
   - Test failure scenarios

3. **Day 5: Retry Worker Service**
   - Implement retry worker service
   - Create Docker container for retry worker
   - Test retry mechanism end-to-end

4. **Day 6-7: API Endpoints and Testing**
   - Add DLQ management endpoints
   - Create admin UI components for DLQ monitoring
   - Integration testing and documentation

### Phase 2: Caching Implementation (Week 2)

1. **Day 1-2: Cache Infrastructure**
   - Create `cache.py` helper class
   - Add cache configuration to `config.py`
   - Write cache unit tests

2. **Day 3-4: High Priority Caching**
   - Implement user authentication caching
   - Implement job status caching
   - Implement document summary caching
   - Measure performance improvements

3. **Day 5: Medium Priority Caching**
   - Implement vector search caching
   - Implement knowledge graph caching
   - Test cache invalidation

4. **Day 6-7: Monitoring and Optimization**
   - Add cache monitoring endpoints
   - Add cache statistics to admin dashboard
   - Performance testing and optimization
   - Documentation

---

## Code Examples

### Example 1: Enhanced Processor with DLQ

```python
# backend/processors/document_processor_service.py

from redis_pubsub import redis_pubsub
from config import settings
import traceback

class DocumentProcessorService:
    
    def _process_single_file(self, message: dict):
        job_id = message.get("job_id")
        gcs_path = message.get("gcs_path")
        filename = message.get("filename")
        retry_count = message.get("retry_metadata", {}).get("retry_count", 0)
        
        db = SessionLocal()
        try:
            # Process document
            job = db.query(models.ProcessingJob).filter(
                models.ProcessingJob.id == job_id
            ).first()
            
            if not job:
                raise ValueError(f"Job {job_id} not found")
            
            self.process_document(db, job, gcs_path)
            print(f"✅ Successfully processed: {filename}")
            
        except Exception as e:
            error_msg = str(e)
            stack_trace = traceback.format_exc()
            print(f"❌ Error processing {filename}: {error_msg}")
            
            # Retry logic
            if retry_count < settings.MAX_RETRY_ATTEMPTS:
                # Push to retry queue with exponential backoff
                print(f"🔄 Retry {retry_count + 1}/{settings.MAX_RETRY_ATTEMPTS} for {filename}")
                message["original_queue"] = settings.REDIS_QUEUE_DOCUMENT
                redis_pubsub.push_to_retry_queue(
                    settings.REDIS_RETRY_DOCUMENT,
                    message,
                    retry_count + 1,
                    settings.REDIS_QUEUE_DOCUMENT
                )
            else:
                # Max retries reached - DLQ
                print(f"💀 Max retries exceeded for {filename}, moving to DLQ")
                message["original_queue"] = settings.REDIS_QUEUE_DOCUMENT
                redis_pubsub.push_to_dlq(
                    settings.REDIS_DLQ_DOCUMENT,
                    message,
                    error_msg,
                    stack_trace
                )
        finally:
            db.close()
```

### Example 2: Using Cache Decorator

```python
# backend/services/user_service.py

from cache import cache
from database import SessionLocal
import models

class UserService:
    
    @cache.cache_result("user:details", ttl=900)
    def get_user_details(self, user_id: int):
        """Get user details with 15-minute cache"""
        db = SessionLocal()
        try:
            user = db.query(models.User).filter(models.User.id == user_id).first()
            if not user:
                return None
            
            return {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "rbac_level": user.rbac_level.value,
                "manager_id": user.manager_id,
            }
        finally:
            db.close()
    
    @cache.cache_result("user:rbac", ttl=900)
    def get_user_permissions(self, user_id: int):
        """Get user RBAC permissions with 15-minute cache"""
        db = SessionLocal()
        try:
            user = db.query(models.User).filter(models.User.id == user_id).first()
            if not user:
                return None
            
            return {
                "rbac_level": user.rbac_level.value,
                "can_upload": user.rbac_level in [models.RBACLevel.ANALYST, models.RBACLevel.MANAGER],
                "can_manage_users": user.rbac_level in [models.RBACLevel.ADMIN, models.RBACLevel.MANAGER],
                "manager_id": user.manager_id,
            }
        finally:
            db.close()
```

### Example 3: Cache with Automatic Invalidation

```python
# backend/services/job_service.py

from cache import cache
from database import SessionLocal
import models

class JobService:
    
    def update_job_status(self, job_id: str, status: models.JobStatus):
        """Update job status and invalidate cache"""
        db = SessionLocal()
        try:
            job = db.query(models.ProcessingJob).filter(
                models.ProcessingJob.id == job_id
            ).first()
            
            if job:
                job.status = status
                db.commit()
                
                # Invalidate cache
                cache.delete(f"job:status:{job_id}")
                cache.delete(f"job:progress:{job_id}")
                
                print(f"✅ Job {job_id} status updated to {status.value}")
        finally:
            db.close()
    
    def increment_processed_files(self, job_id: str):
        """Increment processed files count and invalidate cache"""
        db = SessionLocal()
        try:
            job = db.query(models.ProcessingJob).filter(
                models.ProcessingJob.id == job_id
            ).first()
            
            if job:
                job.processed_files += 1
                db.commit()
                
                # Invalidate cache
                cache.delete(f"job:status:{job_id}")
                cache.delete(f"job:progress:{job_id}")
        finally:
            db.close()
```

---

## Monitoring and Maintenance

### DLQ Monitoring

1. **Daily Checks**
   - Monitor DLQ counts
   - Review error patterns
   - Identify systemic issues

2. **Weekly Reviews**
   - Analyze failure trends
   - Update retry logic if needed
   - Clean up old DLQ messages

3. **Alerts**
   - Alert when DLQ count exceeds threshold
   - Alert when retry queue grows too large
   - Alert on repeated failures for same error type

### Cache Monitoring

1. **Real-time Metrics**
   - Cache hit rate (target: >80%)
   - Memory usage
   - Eviction rate
   - Key count

2. **Performance Metrics**
   - Response time improvements
   - Database query reduction
   - API call reduction

3. **Health Checks**
   - Redis connection status
   - Cache operations success rate
   - TTL effectiveness

### Environment Variables

Add to `.env`:

```bash
# DLQ Configuration
MAX_RETRY_ATTEMPTS=3
RETRY_BACKOFF_BASE_SECONDS=60
DLQ_RETENTION_DAYS=7

# Cache Configuration
CACHE_ENABLED=true
CACHE_DEFAULT_TTL=300
CACHE_USER_TTL=900
CACHE_JOB_STATUS_TTL=5
CACHE_DOCUMENT_TTL=3600
CACHE_VECTOR_SEARCH_TTL=1800
CACHE_GRAPH_TTL=600
```

### Docker Compose Updates

Add retry worker service:

```yaml
  retry-worker:
    build:
      context: ./backend
      dockerfile: Dockerfile.retry_worker
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - MAX_RETRY_ATTEMPTS=3
      - RETRY_BACKOFF_BASE_SECONDS=60
    depends_on:
      - redis
    restart: unless-stopped
```

---

## Summary

### DLQ Benefits
✅ **Reliability**: No more lost jobs due to transient failures  
✅ **Observability**: Clear visibility into what's failing and why  
✅ **Recoverability**: Ability to reprocess failed jobs  
✅ **Debugging**: Detailed error information for troubleshooting  

### Caching Benefits
✅ **Performance**: 80-90% reduction in database queries  
✅ **Scalability**: Better handling of concurrent requests  
✅ **Cost**: Reduced storage backend API calls  
✅ **User Experience**: Faster response times  

### Implementation Timeline
- **Week 1**: DLQ implementation and testing
- **Week 2**: Caching implementation and optimization
- **Week 3**: Monitoring, documentation, and fine-tuning

### Next Steps
1. Review this implementation guide
2. Set up development environment with Redis
3. Implement Phase 1 (DLQ)
4. Test DLQ thoroughly
5. Implement Phase 2 (Caching)
6. Monitor and optimize

---

**Document Version**: 1.0  
**Last Updated**: 2025-11-06  
**Author**: Sentinel AI Development Team
