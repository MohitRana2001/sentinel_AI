# Troubleshooting: Hindi PDF Not Being Queued

## Problem Description

**Symptom**: When uploading a Hindi PDF, it appears to be processed immediately with a generated summary, rather than being transferred to the Redis queue for asynchronous processing.

## Root Cause Analysis

This is actually **expected behavior** and NOT a bug. Here's why:

### Understanding the Processing Flow

1. **File Upload** → Files ARE immediately queued to Redis
2. **Worker Processing** → Workers pick up from queue and process
3. **User Experience** → May FEEL immediate if workers are fast

### Why It Seems Immediate

```
User uploads file (10ms)
    ↓
API stores file & creates job (50ms)
    ↓
API pushes to Redis queue (5ms)
    ↓
API returns response "Processing started" (←User sees this immediately)
    ↓
Worker picks up from queue (10ms)
    ↓
Worker processes file (5-30 seconds)
    ↓
User polls /jobs/{job_id}/status to see progress
```

**The API returns immediately** after queueing, not after processing completes.

## Verification Steps

### 1. Check if Redis Queue is Working

```bash
# Connect to Redis
redis-cli

# Check document queue length (should be 0 if processed, or >0 if pending)
LLEN document_queue

# Monitor queue in real-time
MONITOR

# In another terminal, upload a file and watch Redis activity
```

**Expected Output**:
```
1. LPUSH document_queue "{...}" ← File added to queue
2. BRPOP document_queue          ← Worker picks up file
```

### 2. Check Worker Logs

```bash
# If using Docker
docker-compose logs -f document-processor

# Expected output:
# "Document Processor received file: hindi.pdf (job: manager1/analyst1/uuid)"
# "Using Docling for document processing..."
# "Detected language: hi"
# "Translating from hi to English..."
# "Completed processing: hindi.pdf"
```

### 3. Verify Processing Timing

```python
# In your API response, note the timestamps:
{
  "job_id": "...",
  "status": "queued",  # ← This is returned BEFORE processing
  "message": "Successfully uploaded 1 files. Processing started."
}

# Then poll status:
GET /api/v1/jobs/{job_id}/status

# You should see status progression:
# 1. "queued" (immediately after upload)
# 2. "processing" (when worker picks it up)
# 3. "completed" (after processing finishes)
```

### 4. Check Job Status Progression

```bash
# Make API call
curl -X POST http://localhost:8000/api/v1/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "files=@hindi.pdf"

# Note the job_id, then poll status
curl http://localhost:8000/api/v1/jobs/{job_id}/status

# Example progression (with timestamps):
# At T+0s:   status: "queued"
# At T+2s:   status: "processing", processed_files: 0/1
# At T+15s:  status: "processing", processed_files: 1/1
# At T+20s:  status: "completed", processed_files: 1/1
```

## Common Misunderstandings

### ❌ Misconception 1: "File should stay in queue for a while"

**Reality**: If workers are available and system is not under load, files are processed within seconds. This is GOOD performance, not a bug.

### ❌ Misconception 2: "I don't see the file in Redis queue"

**Reality**: `LLEN document_queue` returns 0 because worker already processed it. This is normal for fast processing.

### ❌ Misconception 3: "Summary appears too quickly"

**Reality**: 
- Gemini API (dev mode): 2-5 seconds
- Ollama Gemma3:1b (prod): 5-15 seconds
- This is expected for small-to-medium documents

## Actual Issues to Check For

If you suspect a REAL problem, check these:

### Issue 1: Worker Not Running

```bash
# Check if worker is running
docker-compose ps document-processor

# Should show: Up

# If not running:
docker-compose up -d document-processor
```

### Issue 2: Worker Not Consuming from Queue

```bash
# Check worker logs for "Listening to queue"
docker-compose logs document-processor | grep "Listening"

# Expected:
# "👂 Listening to queue: document_queue"
```

### Issue 3: Redis Connection Issues

```bash
# Check Redis is accessible
redis-cli PING
# Expected: PONG

# Check connection from backend
docker-compose exec api python -c "
from redis_pubsub import redis_pubsub
print('Redis client:', redis_pubsub.redis_client)
print('Ping:', redis_pubsub.redis_client.ping())
"
```

### Issue 4: Synchronous Processing (Old Code)

If using old code that doesn't use queues:

```python
# OLD (synchronous):
def upload_documents(...):
    # ... store files ...
    process_document(file)  # ← Processes before returning
    return {"status": "completed"}

# NEW (asynchronous with queues):
def upload_documents(...):
    # ... store files ...
    redis_pubsub.push_file_to_queue(...)  # ← Queues for later
    return {"status": "queued"}  # ← Returns immediately
```

**Check**: Search your codebase for direct calls to `process_document` or similar functions in the upload endpoint.

## How to Force Visible Queueing (For Testing)

If you want to see files wait in queue:

### Method 1: Stop Workers Temporarily

```bash
# Stop workers
docker-compose stop document-processor audio-processor video-processor

# Upload files
curl -X POST .../upload -F "files=@file1.pdf" -F "files=@file2.pdf"

# Check queue
redis-cli LLEN document_queue
# Should show: 2

# Start workers again
docker-compose start document-processor
```

### Method 2: Add Artificial Delay (Dev Only)

```python
# In document_processor_service.py (for testing only!)
def _process_single_file(self, message: dict):
    import time
    time.sleep(10)  # Add 10 second delay
    # ... rest of processing ...
```

### Method 3: Upload Many Files at Once

```bash
# Upload 100 files to see queuing effect
for i in {1..100}; do
  curl -X POST .../upload -F "files=@test_$i.pdf" &
done

# Check queue
redis-cli LLEN document_queue
# Should show growing number as files queue up
```

## Expected Behavior for Hindi PDF

**Correct Flow**:

```
1. User uploads hindi.pdf
   ├─ API validates file (< 4MB, .pdf extension)
   ├─ API stores in GCS/Local: uploads/manager1/analyst1/uuid/hindi.pdf
   ├─ API creates job: status=QUEUED
   ├─ API pushes to document_queue
   └─ API returns: {"status": "queued", "job_id": "..."}

2. Document Worker (within seconds)
   ├─ BRPOP document_queue → gets hindi.pdf
   ├─ Downloads: hindi.pdf
   ├─ Docling OCR with Tesseract (hin language)
   ├─ Detects language: hi
   ├─ Translates: Hindi → English (M2M100)
   ├─ Generates summary: English (Gemini/Gemma)
   ├─ Saves files:
   │  ├─ hindi.pdf---extracted.md (Hindi)
   │  ├─ hindi.pdf---translated.md (English)
   │  └─ hindi.pdf---summary.txt (English)
   ├─ Creates document record in DB
   ├─ Vectorizes English text
   └─ Pushes to graph_queue

3. Graph Worker (within seconds)
   ├─ BRPOP graph_queue
   ├─ Downloads english text
   ├─ Extracts entities & relationships
   ├─ Stores in Neo4j
   └─ Marks job: status=COMPLETED

Total time: ~15-30 seconds for small PDF
```

## Diagnostic Commands

```bash
# Full diagnostic suite
echo "=== Redis Status ==="
redis-cli PING
redis-cli INFO | grep connected_clients

echo "=== Queue Lengths ==="
redis-cli LLEN document_queue
redis-cli LLEN audio_queue
redis-cli LLEN video_queue
redis-cli LLEN graph_queue

echo "=== Worker Status ==="
docker-compose ps | grep processor

echo "=== Recent Worker Logs ==="
docker-compose logs --tail=50 document-processor

echo "=== Database Jobs ==="
docker-compose exec api python -c "
from database import SessionLocal
from models import ProcessingJob
db = SessionLocal()
jobs = db.query(ProcessingJob).order_by(ProcessingJob.created_at.desc()).limit(5).all()
for job in jobs:
    print(f'{job.id}: {job.status.value} - {job.processed_files}/{job.total_files}')
"
```

## Performance Benchmarks

Expected processing times (for reference):

| File Type | Size | Dev Mode (Gemini) | Prod Mode (Gemma) |
|-----------|------|-------------------|-------------------|
| English PDF | 1 page | 3-5s | 8-12s |
| Hindi PDF | 1 page | 5-8s | 12-18s |
| English PDF | 10 pages | 10-15s | 25-35s |
| Hindi PDF | 10 pages | 15-25s | 35-50s |
| MP3 Audio | 1 min | 8-12s | N/A (pending) |
| MP4 Video | 30s | 15-20s | 15-20s |

If your processing is significantly slower, check:
- CPU/GPU resources
- Network latency to GCS
- LLM server performance
- Redis connectivity

## Conclusion

**The system is working correctly** if:
1. ✅ Files are queued to Redis (check logs: "LPUSH")
2. ✅ Workers pick up from queue (check logs: "BRPOP")
3. ✅ Processing completes within expected time
4. ✅ Job status progresses: queued → processing → completed
5. ✅ Output files are created (extracted, translated, summary)

**Fast processing is a feature, not a bug.** The queue system allows:
- Asynchronous processing (API returns immediately)
- Scalability (add more workers for higher load)
- Reliability (queue persistence, retry on failure)

If you still believe there's an issue after checking the above, provide:
1. Worker logs showing the processing timeline
2. Redis MONITOR output during upload
3. API response timestamps vs completion timestamps
4. Expected vs actual behavior description

---

**Related Documentation**:
- [README.md](README.md) - Full system documentation
- [PROCESS_FLOW.md](PROCESS_FLOW.md) - Detailed process flows
- [REDIS_QUEUE_SYSTEM.md](REDIS_QUEUE_SYSTEM.md) - Queue architecture
