# Fixing the 404 Error - Backend Setup Guide

## Error Explanation

```
POST http://localhost:8000/api/v1/media/upload 404 (Not Found)
```

**What this means**: 
- ✅ Frontend is working correctly
- ✅ Frontend is making the right API call
- ❌ Backend endpoint doesn't exist yet
- ❌ Backend server needs the `/media/upload` route

---

## Solution: 3-Step Setup

### Step 1: Register the Media Router (DONE ✅)

I've already added the media upload endpoint for you:

**File**: `/backend/routes/media.py`
**Registered in**: `/backend/main.py` (line 29-30, 135)

---

### Step 2: Start the Backend Server

```bash
cd /home/mohitrana/ib-bureau/backend
python main.py
```

Or if using uvicorn directly:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Expected output**:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

### Step 3: Test the Upload

1. **Start Backend** (in terminal 1):
   ```bash
   cd backend
   python main.py
   ```

2. **Start Frontend** (in terminal 2):
   ```bash
   npm run dev
   ```

3. **Open Browser**: http://localhost:3000/dashboard

4. **Upload a file** in any tab (Document/Audio/Video/CDR)

5. **Check Backend Logs** - You should see:
   ```
   ✅ Saved document file: uploads/document/abc-123.pdf
      Original: myfile.pdf
      Size: 2.34 MB
   📋 Job data prepared: {...}
   ⚠️  Note: Redis queue not implemented yet. File saved but not processed.
   ```

---

## Current Implementation Status

### ✅ What Works Now

1. **File Upload**
   - Receives file from frontend
   - Validates media type (document/audio/video/cdr)
   - Validates language (for audio/video)
   - Saves file to `uploads/{media_type}/` directory
   - Returns `media_id` and `job_id`

2. **Status Endpoint**
   - Returns mock status (for now)
   - Endpoint: `GET /api/v1/media/status/{job_id}`

### ⚠️ What's Not Implemented Yet

1. **Background Processing**
   - Redis queue not set up
   - Worker services not running
   - Files are saved but not processed

2. **Actual Job Status**
   - Currently returns mock data
   - Need to implement Redis/database lookup

3. **Result Generation**
   - No summary generation
   - No transcription
   - No translation

---

## Next Steps: Full Implementation

### Phase 1: Basic Queue Setup

#### 1. Install Redis Dependencies
```bash
cd backend
pip install redis bullmq ioredis
```

#### 2. Start Redis Server
```bash
# Using Docker
docker run -d -p 6379:6379 redis:7-alpine

# Or install locally
sudo apt-get install redis-server
redis-server
```

#### 3. Create Queue Service
Create `/backend/services/queue_service.py`:

```python
from redis import Redis
from rq import Queue
import json

redis_conn = Redis(host='localhost', port=6379, db=0)
media_queue = Queue('media-processing', connection=redis_conn)

def enqueue_media_job(job_data):
    """Add job to processing queue"""
    job = media_queue.enqueue(
        'workers.media_processor.process_media',
        job_data,
        job_timeout='30m'
    )
    return job.id

def get_job_status(job_id):
    """Get job status from queue"""
    job = media_queue.fetch_job(job_id)
    if not job:
        return None
    
    return {
        'status': job.get_status(),
        'progress': job.meta.get('progress', 0),
        'result': job.result
    }
```

#### 4. Update Media Route
```python
from services.queue_service import enqueue_media_job

@router.post("/upload")
async def upload_media(...):
    # ... save file ...
    
    # Enqueue job
    job_id = enqueue_media_job(job_data)
    
    return {"job_id": job_id, ...}
```

#### 5. Create Worker
Create `/backend/workers/media_processor.py`:

```python
def process_media(job_data):
    media_type = job_data['media_type']
    
    if media_type == 'document':
        return process_document(job_data)
    elif media_type == 'audio':
        return process_audio(job_data)
    elif media_type == 'video':
        return process_video(job_data)
    elif media_type == 'cdr':
        return process_cdr(job_data)
```

#### 6. Start Worker
```bash
rq worker media-processing
```

---

### Phase 2: Integrate Existing Processors

Your existing processors are already there! Just need to wire them up:

#### Document Processing
```python
# backend/workers/document_worker.py
from document_processor import process_document_with_docling

def process_document(job_data):
    file_path = job_data['file_path']
    
    # Use your existing function!
    text, metadata, language = process_document_with_docling(
        file_path,
        lang=None  # Auto-detect
    )
    
    # Generate summary using Gemini
    from gemini_client import generate_summary
    summary = generate_summary(text)
    
    return {
        'text': text,
        'language': language,
        'summary': summary,
        'metadata': metadata
    }
```

#### Audio Processing
```python
# backend/workers/audio_worker.py
from processors.audio_processor_service import process_audio_file

def process_audio(job_data):
    file_path = job_data['file_path']
    language = job_data['language']
    
    # Use your existing service!
    result = process_audio_file(file_path, language)
    
    return {
        'transcription': result['transcription'],
        'translation': result['translation'],
        'summary': result['summary']
    }
```

#### Video Processing
```python
# backend/workers/video_worker.py
from processors.video_processor_service import process_video_file

def process_video(job_data):
    file_path = job_data['file_path']
    language = job_data['language']
    
    # Use your existing service!
    result = process_video_file(file_path, language)
    
    return {
        'transcription': result['transcription'],
        'translation': result['translation'],
        'summary': result['summary']
    }
```

---

## Quick Test Without Redis (Current Setup)

For now, you can test the frontend without full backend:

### Option A: Use Mock Backend

The current implementation saves files and returns success. Frontend will poll for status but won't get real updates.

**What you'll see**:
- ✅ File uploads successfully
- ✅ Gets `job_id` 
- ⏳ Status shows "processing" indefinitely
- ❌ No actual processing happens

### Option B: Fake Success Response

Modify `/backend/routes/media.py` to simulate completion:

```python
@router.get("/status/{job_id}")
async def get_media_status(job_id: str):
    # Simulate completed job
    return {
        "status": "completed",
        "progress": 100,
        "summary": "This is a mock summary. File was uploaded but not actually processed.",
        "transcription": "Mock transcription text...",
    }
```

This will make the frontend show "completed" status with fake data.

---

## Testing Checklist

### Frontend Testing (No Backend Needed)
- [x] UI components render
- [x] File selection works
- [x] Language dropdown works (audio/video)
- [x] Drag & drop works
- [x] Validation works (file type, size)
- [x] Tab navigation works
- [x] Suspect management works

### Backend Testing (After Setup)
- [ ] Backend starts without errors
- [ ] `/api/v1/media/upload` endpoint exists (200/202)
- [ ] File saves to `uploads/` directory
- [ ] Returns valid `job_id` and `media_id`
- [ ] `/api/v1/media/status/{job_id}` returns data
- [ ] CORS allows requests from frontend

### End-to-End Testing (After Full Setup)
- [ ] Upload document → file saved
- [ ] Upload audio → file saved → transcribed
- [ ] Upload video → file saved → transcribed
- [ ] Upload CDR → file saved → analyzed
- [ ] Status updates in real-time
- [ ] Results display in frontend

---

## Common Issues & Solutions

### Issue 1: Port Already in Use
```bash
Error: Address already in use
```
**Solution**:
```bash
# Find process using port 8000
lsof -i :8000

# Kill it
kill -9 <PID>

# Or use different port
uvicorn main:app --port 8001
```

### Issue 2: CORS Error
```
Access to fetch at 'http://localhost:8000' from origin 'http://localhost:3000' has been blocked by CORS
```
**Solution**: Already handled in `main.py` (line 125-131):
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Issue 3: Import Errors
```
ImportError: No module named 'routes.media'
```
**Solution**:
```bash
cd backend
pip install -r requirements.txt
```

### Issue 4: File Upload Size Limit
```
413 Payload Too Large
```
**Solution**: Add to `main.py`:
```python
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware import Middleware
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI()

# Increase upload size limit
app.add_middleware(
    BaseHTTPMiddleware,
    max_upload_size=500 * 1024 * 1024  # 500 MB
)
```

---

## Summary

**Current Status**: 
- ✅ Frontend: 100% complete
- ⚠️ Backend: Basic endpoint created (files upload, but not processed)
- ❌ Redis Queue: Not implemented yet
- ❌ Workers: Not running

**To Fix 404 Error**:
1. Start backend server: `cd backend && python main.py`
2. Backend should now respond (files save, but don't process)

**For Full Functionality**:
1. Set up Redis
2. Create queue service
3. Create worker processes
4. Wire up your existing document/audio/video processors

**Recommended Next Step**: 
Start the backend server first to test file uploads, then implement Redis queue for actual processing.
