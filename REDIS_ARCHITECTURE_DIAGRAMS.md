# Redis Architecture Diagrams

## Current vs Proposed Architecture

### Current Architecture (Without DLQ)

```
┌──────────────┐
│   Frontend   │
│   (Upload)   │
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│  FastAPI Backend │
│  POST /upload    │
└────┬─────────────┘
     │
     ├─────► GCS/Storage (save files)
     ├─────► AlloyDB (create job record)
     │
     ▼
┌──────────────────┐
│  Redis Queue     │
│  (document_queue)│
└────┬─────────────┘
     │
     ▼
┌──────────────────┐
│ Worker Process   │
│ (Processor)      │
└────┬─────────────┘
     │
     ├─ Success ──► Store in DB
     │
     └─ Failure ──► ❌ MESSAGE LOST!
```

**Problem**: When processing fails, the message is lost forever.

---

### Proposed Architecture (With DLQ)

```
┌──────────────┐
│   Frontend   │
│   (Upload)   │
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│  FastAPI Backend │
│  POST /upload    │
└────┬─────────────┘
     │
     ├─────► GCS/Storage (save files)
     ├─────► AlloyDB (create job record)
     │
     ▼
┌──────────────────────────────────────────┐
│              Redis Server                 │
├──────────────────────────────────────────┤
│                                           │
│  Work Queues:                             │
│  • document_queue ◄───────┐               │
│  • audio_queue            │               │
│  • video_queue            │               │
│  • graph_queue            │               │
│                           │               │
│  Retry Queues (ZSET):     │ Requeue       │
│  • document_retry ────────┤ (when ready)  │
│  • audio_retry            │               │
│  • video_retry            │               │
│  • graph_retry            │               │
│                           │               │
│  Dead Letter Queues:      │               │
│  • document_dlq           │               │
│  • audio_dlq              │               │
│  • video_dlq              │               │
│  • graph_dlq              │               │
│                           │               │
└───────────────────────────┼───────────────┘
                            │
        ┌───────────────────┴──────────────┐
        │                                  │
        ▼                                  ▼
┌──────────────────┐            ┌──────────────────┐
│ Worker Process   │            │  Retry Worker    │
│ (Processor)      │            │  (Background)    │
└────┬─────────────┘            └──────────────────┘
     │
     ├─ Success ──► Store in DB ✅
     │
     └─ Failure ───┐
                   │
                   ├─ Retry < 3 ──► Push to retry_queue
                   │                 (exponential backoff)
                   │
                   └─ Retry = 3 ──► Push to DLQ
                                     (manual review)
```

**Benefits**: 
- No lost messages
- Automatic retries with backoff
- Manual recovery for persistent failures

---

## DLQ Flow Detail

```
┌─────────────────────────────────────────────────────────┐
│                    Processing Flow                       │
└─────────────────────────────────────────────────────────┘

  ┌──────────────────┐
  │  Message arrives │
  │  from queue      │
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐
  │  Try to process  │
  │  document/audio  │
  │  /video/graph    │
  └────┬─────┬───────┘
       │     │
   Success  Failure
       │     │
       ▼     ▼
   ┌────┐  ┌──────────────────────┐
   │ DB │  │ Catch Exception      │
   │ ✅ │  │ - error message      │
   └────┘  │ - stack trace        │
           │ - retry count        │
           └────┬─────────────────┘
                │
                ▼
           ┌─────────────┐
           │ retry_count │
           │  < MAX (3)? │
           └─┬─────────┬─┘
             │         │
            Yes       No
             │         │
             ▼         ▼
    ┌────────────┐  ┌─────────────┐
    │Push to     │  │ Push to DLQ │
    │Retry Queue │  │ (permanent) │
    │            │  └──────┬──────┘
    │Score: now+│         │
    │  backoff  │         │
    └─────┬──────┘         │
          │                │
          │                ▼
          │      ┌──────────────────┐
          │      │ Store metadata:  │
          │      │ - job_id         │
          │      │ - filename       │
          │      │ - error_message  │
          │      │ - stack_trace    │
          │      │ - retry_count    │
          │      │ - timestamps     │
          │      └──────────────────┘
          │
          ▼
    ┌─────────────┐
    │Retry Worker │◄───┐
    │(Background) │    │
    │             │    │
    │Checks every │    │
    │10 seconds   │    │
    └─────┬───────┘    │
          │            │
          ▼            │
    ┌──────────────┐   │
    │ Get messages │   │
    │ with score   │   │
    │ <= now()     │   │
    └─────┬────────┘   │
          │            │
          ▼            │
    ┌──────────────┐   │
    │ Requeue to   │───┘
    │ original     │ (increment retry_count)
    │ work queue   │
    └──────────────┘
```

---

## Caching Architecture

### Without Caching (Current)

```
┌─────────────┐
│  Frontend   │
│  Request    │
└──────┬──────┘
       │
       │ Every request...
       │
       ▼
┌──────────────────┐
│  FastAPI Backend │
└──────┬───────────┘
       │
       ├──► Query AlloyDB (user data)
       │    - 10-50ms per query
       │
       ├──► Query AlloyDB (job status)
       │    - Polled every 2-5 seconds
       │    - Excessive DB load
       │
       ├──► Fetch from GCS (summaries)
       │    - 50-200ms per fetch
       │    - API costs
       │
       ├──► Query pgvector (search)
       │    - 100-500ms per search
       │    - Expensive computation
       │
       └──► Query Neo4j (graphs)
            - 200-1000ms per query
            - Complex Cypher queries

Total: 360-1750ms per request
```

### With Caching (Proposed)

```
┌─────────────┐
│  Frontend   │
│  Request    │
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│  FastAPI Backend │
└──────┬───────────┘
       │
       ▼
┌─────────────────────────────────────┐
│           Redis Cache                │
├─────────────────────────────────────┤
│                                      │
│ user:{user_id}                       │
│ ├─ TTL: 15 min                       │
│ └─ Hit rate: ~95%                    │
│                                      │
│ job:status:{job_id}                  │
│ ├─ TTL: 5 sec                        │
│ └─ Hit rate: ~90%                    │
│                                      │
│ doc:summary:{doc_id}                 │
│ ├─ TTL: 1 hour                       │
│ └─ Hit rate: ~85%                    │
│                                      │
│ vector:search:{hash}                 │
│ ├─ TTL: 30 min                       │
│ └─ Hit rate: ~70%                    │
│                                      │
│ graph:{job_id}:{hash}                │
│ ├─ TTL: 10 min                       │
│ └─ Hit rate: ~75%                    │
│                                      │
└──────┬──────────────────┬───────────┘
       │                  │
    Cache Hit        Cache Miss
       │                  │
       ▼                  ▼
   ┌────────┐      ┌─────────────┐
   │ Return │      │ Query DB/   │
   │ ~1ms   │      │ Storage/etc │
   └────────┘      └──────┬──────┘
                          │
                          ▼
                   ┌─────────────┐
                   │ Store in    │
                   │ Cache       │
                   └─────────────┘

Cache Hit: ~1ms
Cache Miss: 360-1750ms (same as before)

With 85% hit rate:
Average: (0.85 × 1ms) + (0.15 × 500ms) = 75.85ms
Improvement: 85-95% faster!
```

---

## Cache Invalidation Flow

```
┌────────────────────────────────────────────────────────┐
│                Data Modification Events                 │
└────────────────────────────────────────────────────────┘

Event: User Created/Updated/Deleted
  │
  ▼
┌──────────────────────┐
│ Invalidate Cache:    │
│ • user:{user_id}     │
│ • user:rbac:{id}     │
│ • users:managers     │
│ • users:analysts:*   │
└──────────────────────┘


Event: Job Status Changed
  │
  ▼
┌──────────────────────┐
│ Invalidate Cache:    │
│ • job:status:{id}    │
│ • job:progress:{id}  │
└──────────────────────┘


Event: Document Processed
  │
  ▼
┌──────────────────────┐
│ Invalidate Cache:    │
│ • doc:summary:{id}   │
│ • doc:trans:{id}     │
│ • vector:search:*    │
└──────────────────────┘


Event: Graph Entity Added
  │
  ▼
┌──────────────────────┐
│ Invalidate Cache:    │
│ • graph:{job_id}:*   │
└──────────────────────┘
```

---

## Redis Key Structure

```
Redis Database (DB 0)
│
├── Work Distribution (LIST)
│   ├── document_queue          [job1, job2, job3, ...]
│   ├── audio_queue             [job4, job5, ...]
│   ├── video_queue             [job6, ...]
│   └── graph_queue             [job7, job8, ...]
│
├── Retry Management (SORTED SET - score = timestamp)
│   ├── document_retry          {msg1: 1699285200, msg2: 1699285260, ...}
│   ├── audio_retry             {msg3: 1699285320, ...}
│   ├── video_retry             {msg4: 1699285380, ...}
│   └── graph_retry             {msg5: 1699285440, ...}
│
├── Dead Letter Queues (LIST)
│   ├── document_dlq            [failed_msg1, failed_msg2, ...]
│   ├── audio_dlq               [failed_msg3, ...]
│   ├── video_dlq               [failed_msg4, ...]
│   └── graph_dlq               [failed_msg5, ...]
│
├── DLQ Metadata (HASH)
│   └── dlq:metadata:{job_id}:{filename}
│       ├── original_queue: "document_queue"
│       ├── failure_count: "3"
│       ├── first_failure_time: "2025-11-06T10:00:00Z"
│       ├── last_failure_time: "2025-11-06T10:30:00Z"
│       ├── error_message: "Connection timeout..."
│       └── stack_trace: "Traceback..."
│
├── Cache - User Data (STRING with JSON)
│   ├── user:{user_id}                    TTL: 900s
│   │   └── {"id": 1, "email": "...", "rbac_level": "analyst", ...}
│   │
│   └── user:rbac:{user_id}               TTL: 900s
│       └── {"rbac_level": "analyst", "can_upload": true, ...}
│
├── Cache - Job Data (STRING with JSON)
│   ├── job:status:{job_id}               TTL: 5s
│   │   └── {"job_id": "...", "status": "processing", "progress": 45.2, ...}
│   │
│   └── job:progress:{job_id}             TTL: 5s
│       └── {"processed": 5, "total": 10, "percentage": 50.0}
│
├── Cache - Document Data (STRING with JSON)
│   ├── doc:summary:{document_id}         TTL: 3600s
│   │   └── {"document_id": 123, "content": "Summary text...", ...}
│   │
│   ├── doc:transcription:{document_id}   TTL: 3600s
│   │   └── {"document_id": 123, "content": "Transcript...", ...}
│   │
│   └── doc:translation:{document_id}     TTL: 3600s
│       └── {"document_id": 123, "content": "Translation...", ...}
│
├── Cache - Vector Search (STRING with JSON)
│   └── vector:search:{md5_hash}:{job_id} TTL: 1800s
│       └── [{"chunk_text": "...", "score": 0.95, ...}, ...]
│
├── Cache - Graph Data (STRING with JSON)
│   └── graph:{job_id}:{doc_ids_hash}     TTL: 600s
│       └── {"nodes": [...], "relationships": [...]}
│
└── Cache - User Lists (STRING with JSON)
    ├── users:managers                     TTL: 300s
    │   └── [{"id": 1, "email": "...", "analysts": [...]}, ...]
    │
    └── users:analysts:{manager_id}        TTL: 300s
        └── [{"id": 2, "email": "...", ...}, ...]
```

---

## Performance Comparison

### Database Query Load

**Without Caching:**
```
Requests per second: 100
DB queries per request: 3 (average)
Total DB queries/sec: 300

Daily DB queries: 300 × 86,400 = 25,920,000
```

**With Caching (85% hit rate):**
```
Requests per second: 100
Cache hits: 85
Cache misses: 15
DB queries from misses: 15 × 3 = 45
Total DB queries/sec: 45

Daily DB queries: 45 × 86,400 = 3,888,000

Reduction: 85% fewer queries!
```

### Response Times

| Endpoint | Without Cache | With Cache | Improvement |
|----------|---------------|------------|-------------|
| Get User | 20ms | 1ms | 95% faster |
| Job Status | 15ms | 1ms | 93% faster |
| Document Summary | 150ms | 2ms | 99% faster |
| Vector Search | 500ms | 5ms | 99% faster |
| Knowledge Graph | 800ms | 10ms | 99% faster |

### Cost Savings

**Storage Backend (GCS) API Calls:**
- Current: 10,000 calls/day for summaries
- With cache: 1,500 calls/day (85% cached)
- Savings: $8.50/day × 30 = $255/month

**Database Connection Pool:**
- Current: Need 50 connections
- With cache: Need 10 connections
- Cost reduction: 80%

---

## Monitoring Dashboard Layout

```
┌─────────────────────────────────────────────────────────────┐
│                     Redis Monitoring                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  DLQ Statistics                                               │
│  ┌─────────────┬──────┬─────────────────┬───────────────┐   │
│  │ Queue       │ Size │ Avg Retry Count │ Top Error     │   │
│  ├─────────────┼──────┼─────────────────┼───────────────┤   │
│  │ document_dlq│  12  │      2.3        │ Storage timeout│   │
│  │ audio_dlq   │   3  │      2.0        │ FFmpeg error  │   │
│  │ video_dlq   │   1  │      3.0        │ Memory error  │   │
│  │ graph_dlq   │   7  │      2.8        │ Neo4j timeout │   │
│  └─────────────┴──────┴─────────────────┴───────────────┘   │
│                                                               │
│  Retry Queue Status                                           │
│  ┌─────────────┬──────────┬────────────────────┐            │
│  │ Queue       │ Pending  │ Next Retry In      │            │
│  ├─────────────┼──────────┼────────────────────┤            │
│  │ doc_retry   │    5     │   2 min 30 sec     │            │
│  │ audio_retry │    2     │   5 min 15 sec     │            │
│  │ video_retry │    1     │   10 min 20 sec    │            │
│  │ graph_retry │    3     │   1 min 45 sec     │            │
│  └─────────────┴──────────┴────────────────────┘            │
│                                                               │
│  Cache Performance                                            │
│  ┌────────────────────┬──────────┬──────────┬──────────┐    │
│  │ Cache Type         │ Hit Rate │ Requests │ Avg TTL  │    │
│  ├────────────────────┼──────────┼──────────┼──────────┤    │
│  │ User Auth          │   95%    │  10,234  │  850s    │    │
│  │ Job Status         │   90%    │  25,678  │  4s      │    │
│  │ Document Summary   │   85%    │   5,432  │  3200s   │    │
│  │ Vector Search      │   70%    │   1,234  │  1500s   │    │
│  │ Knowledge Graph    │   75%    │     876  │  550s    │    │
│  └────────────────────┴──────────┴──────────┴──────────┘    │
│                                                               │
│  Overall Redis Health                                         │
│  • Memory Used: 125 MB / 512 MB (24%)                        │
│  • Total Keys: 12,450                                         │
│  • Operations/sec: 1,234                                      │
│  • Connection Count: 45                                       │
│  • Eviction Rate: 0.02%                                       │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Priority Matrix

```
┌──────────────────────────────────────────────────────────┐
│               Impact vs Effort Matrix                     │
│                                                           │
│  High Impact                                              │
│  ▲                                                        │
│  │    ┌─────────────────┐      ┌──────────────┐         │
│  │    │ User Auth Cache │      │   DLQ Core   │         │
│  │    │   (Implement    │      │ (Implement   │         │
│  │    │    First!)      │      │   First!)    │         │
│  │    └─────────────────┘      └──────────────┘         │
│  │                                                        │
│  │    ┌─────────────────┐      ┌──────────────┐         │
│  │    │ Job Status      │      │ Retry Worker │         │
│  │    │ Cache           │      │              │         │
│  │    └─────────────────┘      └──────────────┘         │
│  │                                                        │
│  │    ┌─────────────────┐                                │
│  │    │ Document        │      ┌──────────────┐         │
│  │    │ Summary Cache   │      │ DLQ Admin UI │         │
│  │    └─────────────────┘      └──────────────┘         │
│  │                                                        │
│  │    ┌─────────────────┐                                │
│  │    │ Vector Search   │      ┌──────────────┐         │
│  │    │ Cache           │      │ Cache        │         │
│  │    └─────────────────┘      │ Monitoring   │         │
│  │                              └──────────────┘         │
│  │                                                        │
│  │    ┌─────────────────┐                                │
│  │    │ Graph Cache     │                                │
│  │    └─────────────────┘                                │
│  │                                                        │
│  └────────────────────────────────────────────────────► │
│         Low Effort                          High Effort  │
│                                                           │
└──────────────────────────────────────────────────────────┘

Week 1: DLQ Core + User Auth Cache
Week 2: Retry Worker + Job Status Cache + Document Cache
Week 3: Vector Search Cache + Graph Cache + Monitoring
```

---

## Summary

### Key Metrics to Track

**DLQ:**
- Messages in DLQ (target: <50)
- Retry success rate (target: >90%)
- Average retries before success (target: <2)
- Time to resolve DLQ messages (target: <24 hours)

**Caching:**
- Overall cache hit rate (target: >80%)
- Response time improvement (target: >70% faster)
- Database query reduction (target: >80%)
- Storage API call reduction (target: >80%)

### Success Criteria

✅ **DLQ**: Zero lost jobs, <5% permanent failures  
✅ **Caching**: >80% hit rate, >70% faster responses  
✅ **Cost**: 80% reduction in database load  
✅ **Scalability**: Handle 10x traffic with same resources  

---

**For detailed implementation, see:**
- REDIS_DLQ_AND_CACHE_IMPLEMENTATION_GUIDE.md
- REDIS_IMPLEMENTATION_QUICK_START.md
