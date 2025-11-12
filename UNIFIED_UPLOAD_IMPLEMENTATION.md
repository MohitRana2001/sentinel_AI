# Unified Upload Implementation Summary

## Overview
This document summarizes the architectural changes made to support unified job uploads where multiple artifact types (documents, audio, video, CDR) and suspects can be uploaded together in a single job.

## Changes Made

### 1. Backend Models (`backend/models.py`)
✅ **Added Suspect Model**
```python
class Suspect(Base):
    """Suspects linked to processing jobs"""
    __tablename__ = "suspects"
    
    id = Column(String, primary_key=True, index=True)  # UUID from frontend
    job_id = Column(String, ForeignKey("processing_jobs.id"), nullable=False)
    fields = Column(JSON, nullable=False)  # Array of {id, key, value}
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    job = relationship("ProcessingJob", backref="suspects")
```

### 2. Backend Upload Endpoint (`backend/main.py`)
✅ **Updated upload endpoint to:**
- Import `json` module and `Form` from FastAPI
- Accept arrays of `media_types` and `languages` via `Form()`
- Accept suspects data as JSON string via `Form(None)`
- Process each file with its corresponding media type and language
- Save suspects to database linked to the job
- Return suspects count in the response

**Key Changes:**
```python
@app.post(f"{settings.API_PREFIX}/upload")
async def upload_documents(
    files: List[UploadFile] = File(...),
    media_types: List[str] = Form([]),      # List of media types (one per file)
    languages: List[str] = Form([]),         # List of languages (one per file)
    suspects: Optional[str] = Form(None),    # JSON string of suspects data
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
```

### 3. Backend Job Results Endpoint (`backend/main.py`)
✅ **Updated to include suspects:**
- Query suspects from database for the job
- Return suspects array in the response

```python
suspects_query = db.query(models.Suspect).filter(
    models.Suspect.job_id == job_id
)
suspects = suspects_query.all()

return {
    # ... existing fields ...
    "suspects": [
        {
            "id": suspect.id,
            "fields": suspect.fields,
            "created_at": suspect.created_at.isoformat(),
            "updated_at": suspect.updated_at.isoformat()
        }
        for suspect in suspects
    ]
}
```

### 4. Backend Jobs List Endpoint (`backend/main.py`)
✅ **Added suspects count to job listing:**
```python
suspects_count = db.query(models.Suspect).filter(
    models.Suspect.job_id == job.id
).count()

result.append({
    # ... existing fields ...
    "suspects_count": suspects_count,
})
```

### 5. Frontend Analyst Dashboard (`components/dashboard/analyst-dashboard.tsx`)
✅ **Updated to:**
- Import `useRouter` from Next.js
- Add `handleViewResults` function to navigate to results page
- Display suspects count in job cards
- Make "View Results" button functional
- Auto-refresh jobs when History tab is opened (already implemented)

**Key Changes:**
```tsx
const router = useRouter();

const handleViewResults = (jobId: string) => {
  router.push(`/results?jobId=${encodeURIComponent(jobId)}`);
};

// In job card:
{job.suspects_count > 0 && (
  <span className="flex items-center gap-1">
    <Users className="h-3 w-3" />
    {job.suspects_count} suspect(s)
  </span>
)}

<Button 
  variant="outline"
  onClick={() => handleViewResults(job.job_id)}
>
  View Results
</Button>
```

### 6. Frontend API Client (`lib/api-client.ts`)
✅ **Updated JobResults interface to include suspects:**
```typescript
interface JobResults {
  // ... existing fields ...
  suspects: Array<{
    id: string
    fields: Array<{
      id: string
      key: string
      value: string
    }>
    created_at: string
    updated_at: string
  }>
}
```

## Features Implemented

### ✅ 1. Unified Upload
- Users can now upload multiple files of different types in a single job
- Each file can have its own media type (document, audio, video, CDR)
- Audio and video files can have language specified for transcription
- All files in a job are processed in parallel by appropriate workers

### ✅ 2. Suspects Integration
- Suspects are uploaded together with files in the same job
- Suspects data is stored in the database with proper job linking
- Suspects are returned when fetching job results
- Suspects count is displayed in job history

### ✅ 3. History Tab Auto-Refresh
- History tab automatically refreshes jobs when opened
- "Refresh" button allows manual refresh
- Jobs display suspects count if any suspects are linked

### ✅ 4. View Results Functionality
- "View Results" button now navigates to results page
- Job ID is passed as URL parameter
- Results page can display both documents and suspects

## How It Works

### Upload Flow:
1. User adds multiple files of different types via unified upload component
2. User manages suspects in the Suspects tab
3. User clicks "Upload" - all files and suspects are sent to backend
4. Backend creates a single job with all files
5. Backend saves all suspects linked to the job
6. Backend queues each file to the appropriate processor (document/audio/video/CDR)
7. Workers process files in parallel
8. Results are available once all files are processed

### Data Flow:
```
Frontend (UnifiedUpload) 
  → FormData with files, media_types, languages, suspects
    → Backend (/upload)
      → Create ProcessingJob
      → Save Suspects to DB
      → Queue files to Redis
        → Workers process files
          → Results stored in DB
            → Frontend fetches results (/jobs/{job_id}/results)
```

## Database Schema

### Suspects Table:
```sql
CREATE TABLE suspects (
    id VARCHAR PRIMARY KEY,
    job_id VARCHAR REFERENCES processing_jobs(id),
    fields JSON NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

## Testing Checklist

- [ ] Upload multiple files of different types in one job
- [ ] Upload with suspects attached
- [ ] Verify suspects are saved to database
- [ ] Check job history shows suspects count
- [ ] Click "View Results" and verify navigation works
- [ ] Verify job results endpoint returns suspects
- [ ] Test auto-refresh on History tab
- [ ] Test manual refresh button
- [ ] Verify files are processed by correct workers
- [ ] Check progress tracking for mixed media types

## Next Steps

1. **Restart Backend**: The database will auto-create the suspects table on startup
   ```bash
   cd backend
   python main.py
   ```

2. **Test Upload Flow**: 
   - Add multiple files (document + audio + video)
   - Add suspects in the Suspects tab
   - Upload and verify all artifacts are linked to one job

3. **Verify Database**:
   - Check that suspects table is created
   - Verify suspects are saved with correct job_id

4. **Test Results Page**:
   - Navigate to results page from history
   - Verify suspects are displayed alongside documents

## Notes

- The Suspect model is flexible with JSON fields for custom key-value pairs
- Each job can have multiple suspects
- Suspects are always associated with a job (cannot exist independently)
- The unified upload maintains backward compatibility with existing media processing
