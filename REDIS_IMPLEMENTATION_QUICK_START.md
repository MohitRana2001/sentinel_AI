# Redis DLQ & Caching - Quick Start Guide

## 🚀 Quick Implementation Summary

### DLQ (Dead Letter Queue)

#### What to Add:

**1. Configuration (`backend/config.py`)**
```python
# DLQ Queues
REDIS_DLQ_DOCUMENT: str = "document_dlq"
REDIS_DLQ_AUDIO: str = "audio_dlq"
REDIS_DLQ_VIDEO: str = "video_dlq"
REDIS_DLQ_GRAPH: str = "graph_dlq"

# Retry Queues
REDIS_RETRY_DOCUMENT: str = "document_retry"
REDIS_RETRY_AUDIO: str = "audio_retry"
REDIS_RETRY_VIDEO: str = "video_retry"
REDIS_RETRY_GRAPH: str = "graph_retry"

# Settings
MAX_RETRY_ATTEMPTS: int = 3
RETRY_BACKOFF_BASE_SECONDS: int = 60
DLQ_RETENTION_DAYS: int = 7
```

**2. Enhanced Redis PubSub (`backend/redis_pubsub.py`)**
Add methods:
- `push_to_dlq()` - Push failed messages to DLQ
- `push_to_retry_queue()` - Push to retry with backoff
- `get_ready_retries()` - Get messages ready to retry
- `get_dlq_count()` - Get DLQ size
- `get_dlq_messages()` - View DLQ messages
- `requeue_from_dlq()` - Move message back to processing

**3. Update Processor Services**
Wrap processing logic in try-catch:
```python
try:
    self.process_document(db, job, gcs_path)
except Exception as e:
    if retry_count < MAX_RETRY_ATTEMPTS:
        redis_pubsub.push_to_retry_queue(...)
    else:
        redis_pubsub.push_to_dlq(...)
```

**4. Create Retry Worker (`backend/retry_worker_service.py`)**
Background service that:
- Monitors retry queues every 10 seconds
- Requeues messages when retry time is reached
- Implements exponential backoff

**5. Add DLQ API Endpoints (`backend/main.py`)**
- `GET /admin/dlq/stats` - View DLQ counts
- `GET /admin/dlq/{queue_name}` - View messages
- `POST /admin/dlq/{queue_name}/requeue/{index}` - Requeue message

---

### Caching Strategy

#### Priority Areas to Cache:

**HIGH PRIORITY**
1. **User Authentication** - Cache user data for 15 mins
   - Key: `user:{user_id}`
   - Reduces DB queries by ~80%

2. **Job Status** - Cache for 5 seconds
   - Key: `job:status:{job_id}`
   - Reduces DB load from frequent polling

3. **Document Summaries** - Cache for 1 hour
   - Key: `doc:summary:{document_id}`
   - Eliminates storage backend calls

**MEDIUM PRIORITY**
4. **Vector Search Results** - Cache for 30 mins
   - Key: `vector:search:{hash(query)}:{job_id}`
   - Reduces expensive vector computations

5. **Knowledge Graphs** - Cache for 10 mins
   - Key: `graph:{job_id}:{doc_ids_hash}`
   - Reduces Neo4j query load

**LOW PRIORITY**
6. **User Lists** - Cache for 5 mins
   - Key: `users:managers`, `users:analysts:{manager_id}`
   - Faster admin dashboard

#### What to Add:

**1. Cache Helper (`backend/cache.py`)**
Create RedisCache class with methods:
- `get(key)` - Get from cache
- `set(key, value, ttl)` - Set with TTL
- `delete(key)` - Remove from cache
- `delete_pattern(pattern)` - Bulk delete
- `@cache_result()` - Decorator for caching
- `get_or_set()` - Get or compute and cache

**2. Update API Endpoints**
Add caching to:
- `get_current_user()` in `security.py`
- `get_job_status()` in `main.py`
- `get_document_summary()` in `main.py`
- `get_document_transcription()` in `main.py`
- `chat_with_documents()` in `main.py`
- `get_job_graph()` in `main.py`

**3. Cache Invalidation**
Invalidate cache when data changes:
```python
# User changes
cache.delete(f"user:{user_id}")

# Job updates
cache.delete(f"job:status:{job_id}")

# Document changes
cache.delete(f"doc:summary:{document_id}")

# Graph updates
cache.delete_pattern(f"graph:{job_id}:*")
```

**4. Monitoring Endpoints**
- `GET /admin/cache/stats` - Cache hit rate, memory usage
- `DELETE /admin/cache/clear` - Clear cache (admin only)

---

## 📊 Expected Performance Improvements

### DLQ
- ✅ **Zero lost jobs** from transient failures
- ✅ **Automatic retry** with exponential backoff
- ✅ **Full error visibility** for debugging
- ✅ **Manual recovery** for permanent failures

### Caching
- ✅ **80-90% reduction** in database queries
- ✅ **70-80% reduction** in storage API calls
- ✅ **50-70% faster** response times
- ✅ **5-10x improvement** in concurrent request handling

---

## 🔧 Environment Variables

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

---

## 📝 Implementation Checklist

### DLQ Implementation
- [ ] Update `config.py` with DLQ settings
- [ ] Add DLQ methods to `redis_pubsub.py`
- [ ] Update document processor with error handling
- [ ] Update audio processor with error handling
- [ ] Update video processor with error handling
- [ ] Update graph processor with error handling
- [ ] Create `retry_worker_service.py`
- [ ] Add DLQ API endpoints to `main.py`
- [ ] Create Dockerfile for retry worker
- [ ] Update docker-compose.yml
- [ ] Test failure scenarios
- [ ] Document DLQ operations

### Caching Implementation
- [ ] Create `cache.py` helper class
- [ ] Update `config.py` with cache settings
- [ ] Add caching to `get_current_user()`
- [ ] Add caching to `get_job_status()`
- [ ] Add caching to `get_document_summary()`
- [ ] Add caching to `get_document_transcription()`
- [ ] Add caching to `chat_with_documents()`
- [ ] Add caching to `get_job_graph()`
- [ ] Implement cache invalidation logic
- [ ] Add cache monitoring endpoints
- [ ] Load test and measure improvements
- [ ] Document caching strategy

---

## 🎯 Redis Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         Redis Server                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Work Queues (LIST):                                         │
│  ├─ document_queue                                           │
│  ├─ audio_queue                                              │
│  ├─ video_queue                                              │
│  └─ graph_queue                                              │
│                                                               │
│  Retry Queues (SORTED SET):                                  │
│  ├─ document_retry (timestamp-based)                         │
│  ├─ audio_retry                                              │
│  ├─ video_retry                                              │
│  └─ graph_retry                                              │
│                                                               │
│  Dead Letter Queues (LIST):                                  │
│  ├─ document_dlq                                             │
│  ├─ audio_dlq                                                │
│  ├─ video_dlq                                                │
│  └─ graph_dlq                                                │
│                                                               │
│  DLQ Metadata (HASH):                                        │
│  └─ dlq:metadata:{job_id}:{filename}                         │
│                                                               │
│  Cache (STRING/HASH):                                        │
│  ├─ user:{user_id}                                           │
│  ├─ job:status:{job_id}                                      │
│  ├─ doc:summary:{document_id}                                │
│  ├─ vector:search:{hash}                                     │
│  └─ graph:{job_id}:{doc_ids_hash}                            │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 💡 Tips & Best Practices

### DLQ
1. **Monitor DLQ daily** - Don't let messages pile up
2. **Analyze error patterns** - Fix root causes
3. **Set retention limits** - Clean up old messages
4. **Alert on DLQ growth** - Detect systemic issues early
5. **Test retry logic** - Ensure backoff works correctly

### Caching
1. **Start with high-priority items** - Biggest impact first
2. **Monitor hit rates** - Aim for >80%
3. **Set appropriate TTLs** - Balance freshness vs load
4. **Invalidate on changes** - Keep cache consistent
5. **Use compression for large data** - Save memory
6. **Plan for cache failures** - Graceful degradation

---

## 🔍 Monitoring Dashboards

### DLQ Metrics
- Total messages in each DLQ
- Retry queue sizes
- Failure rates by queue
- Top error messages
- Average retry count
- DLQ processing time

### Cache Metrics
- Hit rate (should be >80%)
- Miss rate
- Memory usage
- Key count
- Eviction rate
- Average TTL
- Top cached keys

---

## 📚 For Detailed Implementation

See: **REDIS_DLQ_AND_CACHE_IMPLEMENTATION_GUIDE.md**

This guide contains:
- Complete code examples
- Detailed architecture diagrams
- Step-by-step implementation
- Full API documentation
- Testing strategies
- Troubleshooting guide
