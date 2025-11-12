# Backend Upload Fix - Summary

## Issue
Frontend was calling `POST /api/v1/media/upload` but the backend had `POST /api/v1/upload`.

## Solution
**Option Chosen**: Extend the existing `/upload` endpoint instead of creating a new one.

## Changes Made

### 1. Updated `redis_pubsub.py`

**Method**: `push_file_to_queue()`

**Before**:
```python
def push_file_to_queue(self, job_id: str, gcs_path: str, filename: str, queue_name: str) -> int:
    message = {
        "job_id": job_id,
        "gcs_path": gcs_path,
        "filename": filename,
        "action": "process_file"
    }
    return self.push_to_queue(queue_name, message)
```

**After**:
```python
def push_file_to_queue(self, job_id: str, gcs_path: str, filename: str, queue_name: str, metadata: Dict[str, Any] = None) -> int:
    message = {
        "job_id": job_id,
        "gcs_path": gcs_path,
        "filename": filename,
        "action": "process_file"
    }
    # Merge additional metadata if provided
    if metadata:
        message.update(metadata)
    return self.push_to_queue(queue_name, message)
```

**Change**: Added optional `metadata` parameter to pass language and other info to workers.

---

### 2. Updated `config.py`

**Added**:
```python
REDIS_QUEUE_CDR: str = "cdr_queue"  # NEW: CDR (Call Data Records) queue
```

**Updated allowed extensions**:
```python
ALLOWED_EXTENSIONS: str = os.getenv(
    "ALLOWED_EXTENSIONS", 
    ".pdf,.docx,.txt,.mp3,.wav,.mp4,.avi,.mov,.csv,.xls,.xlsx"  # Added .csv, .xls, .xlsx
)
```

---

### 3. Already Updated `main.py`

The `/upload` endpoint already has:

```python
@app.post(f"{settings.API_PREFIX}/upload")
async def upload_documents(
    files: List[UploadFile] = File(...),
    media_type: Optional[str] = None,  # 'document', 'audio', 'video', 'cdr'
    language: Optional[str] = None,     # For audio/video transcription
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
```

**Features**:
- ✅ Accepts `media_type` parameter ('document', 'audio', 'video', 'cdr')
- ✅ Accepts `language` parameter (required for audio/video)
- ✅ Validates language for audio/video
- ✅ Routes to appropriate Redis queue
- ✅ Passes language metadata to workers

---

### 4. Updated Frontend `auth-context.tsx`

**Changed endpoint URL**:
```typescript
// Before
const response = await fetch(`${API_BASE_URL}/media/upload`, {

// After
const response = await fetch(`${API_BASE_URL}/upload`, {
```

**Changed response parsing**:
```typescript
// Before
const { media_id, job_id, status } = await response.json();

// After
const { job_id } = await response.json();
```

---

## How It Works Now

### Upload Flow

```
1. User uploads file in frontend
   ↓
2. Frontend sends to: POST /api/v1/upload
   - files: File[]
   - media_type: 'document' | 'audio' | 'video' | 'cdr'
   - language: 'hi' | 'en' | ... (if audio/video)
   ↓
3. Backend validates:
   - File size < MAX_FILE_SIZE_MB
   - File extension allowed
   - Language required for audio/video
   ↓
4. Backend uploads to storage (GCS/Local)
   ↓
5. Backend creates ProcessingJob in DB
   ↓
6. Backend pushes to Redis queue with metadata:
   - document_queue → { job_id, gcs_path, filename }
   - audio_queue → { job_id, gcs_path, filename, language: "hi" }
   - video_queue → { job_id, gcs_path, filename, language: "ta" }
   - cdr_queue → { job_id, gcs_path, filename }
   ↓
7. Backend returns: { job_id }
   ↓
8. Frontend polls: GET /api/v1/jobs/{job_id}/status
   ↓
9. Worker processes file from queue
   ↓
10. Frontend shows results
```

---

## Media Type Routing

| Media Type | Queue | Metadata | Worker Service |
|------------|-------|----------|----------------|
| `document` | `document_queue` | - | `document_processor_service` |
| `audio` | `audio_queue` | `{ language: "hi" }` | `audio_processor_service` |
| `video` | `video_queue` | `{ language: "ta" }` | `video_processor_service` |
| `cdr` | `cdr_queue` | - | `cdr_processor_service` (TBD) |

---

## Testing

### Test Document Upload
```bash
curl -X POST "http://localhost:8000/api/v1/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "files=@test.pdf" \
  -F "media_type=document"
```

### Test Audio Upload
```bash
curl -X POST "http://localhost:8000/api/v1/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "files=@audio.mp3" \
  -F "media_type=audio" \
  -F "language=hi"
```

### Test Video Upload
```bash
curl -X POST "http://localhost:8000/api/v1/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "files=@video.mp4" \
  -F "media_type=video" \
  -F "language=ta"
```

### Test CDR Upload
```bash
curl -X POST "http://localhost:8000/api/v1/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "files=@calls.csv" \
  -F "media_type=cdr"
```

---

## Worker Updates Needed

Workers need to check for `language` in the message metadata:

### Example: `audio_processor_service.py`

```python
def process_message(message: dict):
    job_id = message.get("job_id")
    gcs_path = message.get("gcs_path")
    filename = message.get("filename")
    language = message.get("language")  # NEW: Get language from metadata
    
    if not language:
        # Fallback or error
        language = "hi"  # Default
    
    # Process audio with specified language
    transcription = transcribe_audio(gcs_path, language)
    # ...
```

---

## Summary

✅ **Fixed**: TypeError in `push_file_to_queue()` - added `metadata` parameter
✅ **Added**: CDR queue configuration
✅ **Updated**: Allowed file extensions to include CSV, XLS, XLSX
✅ **Updated**: Frontend to use `/upload` endpoint
✅ **Ready**: Backend can now accept document, audio, video, and CDR uploads with language metadata

**Next Step**: Test the upload flow end-to-end!
