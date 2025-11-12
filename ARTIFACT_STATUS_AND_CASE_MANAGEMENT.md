# Real-Time Per-Artifact Status & Case Management - Implementation Guide

## Overview

This implementation adds two major features to the IB Bureau application:

1. **Real-time per-artifact status tracking** - Each uploaded file (artifact) now has its own status, timing, and progress tracking
2. **Case management** - Group related uploads into cases and extend cases with new documents over time

## Changes Summary

### Backend Changes

#### 1. Database Models (`backend/models.py`)

**ProcessingJob Model:**
- Added `case_name` (String) - Optional case identifier for grouping jobs
- Added `parent_job_id` (String, ForeignKey) - Links to parent job when extending a case
- Added `child_jobs` relationship - Tracks jobs that extend this case

**Document Model:**
- Added `status` (JobStatus enum) - Per-artifact processing status
- Added `processing_stages` (JSON) - Timing for each processing stage (extraction, translation, summarization, embeddings)
- Added `current_stage` (String) - Current processing stage
- Added `error_message` (Text) - Artifact-specific error messages
- Added `started_at` (DateTime) - When processing started for this artifact
- Added `completed_at` (DateTime) - When processing completed for this artifact

#### 2. Redis Pub/Sub (`backend/redis_pubsub.py`)

Added new methods:
- `publish_artifact_status()` - Publish per-artifact status updates to job-specific channels
- `publish_job_status()` - Publish job-level status updates

These methods enable real-time status broadcasting to the frontend.

#### 3. API Endpoints (`backend/main.py`)

**Updated Endpoints:**

`POST /api/v1/upload`:
- Added `case_name` parameter (Form field, optional)
- Added `parent_job_id` parameter (Form field, optional)
- Stores case information in job record

`GET /api/v1/jobs/{job_id}/status`:
- Now returns `artifacts` array with per-artifact status
- Each artifact includes: id, filename, file_type, status, current_stage, processing_stages, started_at, completed_at, error_message
- Returns `case_name` and `parent_job_id` fields

**New Endpoints:**

`GET /api/v1/cases`:
- Returns list of all unique case names for current user

`GET /api/v1/cases/{case_name}/jobs`:
- Returns all jobs associated with a specific case
- Respects RBAC (analysts see their jobs, managers see their analysts' jobs)

#### 4. Document Processor (`backend/processors/document_processor_service.py`)

- Creates Document record at start of processing with `status='processing'`
- Tracks timing for each stage: extraction, translation, summarization, embeddings
- Updates `current_stage` and `processing_stages` as it progresses
- Publishes status updates to Redis after each stage
- Sets `status='completed'` or `status='failed'` with final timing on completion

### Frontend Changes

#### 1. Types (`types/index.ts`)

**New/Updated Types:**
```typescript
interface MediaItem {
  // ... existing fields ...
  startedAt?: string
  completedAt?: string
  errorMessage?: string
  processingStages?: Record<string, number>  // Stage timing in seconds
}

interface JobStatusResponse {
  job_id: string
  status: ProcessingStatus
  case_name?: string
  parent_job_id?: string
  artifacts: ArtifactStatus[]  // NEW: Per-artifact details
  // ... other fields ...
}

interface ArtifactStatus {
  id: number
  filename: string
  file_type: string
  status: ProcessingStatus
  current_stage?: string
  processing_stages?: Record<string, number>
  started_at?: string
  completed_at?: string
  error_message?: string
}
```

#### 2. API Client (`lib/api-client.ts`)

**Updated:**
- `uploadDocuments()` - Now accepts optional `caseName` and `parentJobId` parameters

**New Methods:**
- `getCases()` - Fetch all cases
- `getCaseJobs(caseName)` - Fetch jobs for a specific case

#### 3. Auth Context (`context/auth-context.tsx`)

**Updated:**
- `pollJobStatus()` - Now processes `artifacts` array from status endpoint
- Updates each MediaItem based on its corresponding artifact status
- Provides real-time per-artifact status updates
- `uploadJob()` - Now accepts `caseName` and `parentJobId` parameters

#### 4. Unified Upload Component (`components/upload/unified-upload.tsx`)

**New UI Elements:**
- Case Management section with toggle between "New Case" and "Existing Case"
- Input field for new case name
- Dropdown to select from existing cases
- Help text explaining case functionality

**Functionality:**
- Loads existing cases on mount using `apiClient.getCases()`
- Allows user to create new case or add to existing
- Passes case name to upload handler

#### 5. Analyst Dashboard (`components/dashboard/analyst-dashboard.tsx`)

**Updated:**
- "Recent Uploads" section now shows per-artifact status badges
- Displays processing stage timing (e.g., "extraction: 5.2s", "summarization: 12.3s")
- Shows current stage with animated spinner for in-progress artifacts
- Total timing calculation displayed for completed artifacts

### Database Migration

Run the migration script to add new columns:

```bash
cd backend
python migrations/add_artifact_status_and_case_name.py
```

The migration adds:
1. `case_name` and `parent_job_id` to `processing_jobs` table
2. Index on `case_name` for faster lookups
3. Status tracking columns to `documents` table:
   - `status`, `processing_stages`, `current_stage`
   - `error_message`, `started_at`, `completed_at`

## Usage Examples

### 1. Create a New Case

```typescript
// Upload files with a new case name
await uploadJob(
  { files: filesArray, suspects: suspectsArray },
  "Operation Phoenix",  // case name
  undefined  // no parent job
);
```

### 2. Add Documents to Existing Case

```typescript
// Extend an existing case with new documents
await uploadJob(
  { files: newFiles, suspects: [] },
  "Operation Phoenix",  // same case name
  undefined  // optional: could specify parent_job_id
);
```

### 3. Monitor Per-Artifact Status

The frontend now automatically displays:
- Each artifact's individual status (queued, processing, completed, failed)
- Current processing stage (extraction, translation, summarization, etc.)
- Time taken for each stage as badges
- Total processing time

## Real-Time Status Flow

```
1. User uploads files
   ↓
2. Backend creates Job + Document records (status='queued')
   ↓
3. Worker picks up file, updates Document (status='processing')
   ↓
4. Worker publishes status after each stage:
   - extraction complete (5.2s)
   - translation complete (8.7s)
   - summarization complete (12.3s)
   - embeddings complete (15.1s)
   ↓
5. Frontend polls /jobs/{id}/status every 2s
   ↓
6. Frontend updates UI with per-artifact status
   ↓
7. Document marked completed (status='completed')
   Frontend shows total time and all stage timings
```

## API Response Examples

### Job Status Response (with per-artifact status)

```json
{
  "job_id": "manager1/analyst1/uuid",
  "status": "processing",
  "case_name": "Operation Phoenix",
  "parent_job_id": null,
  "total_files": 3,
  "processed_files": 2,
  "progress_percentage": 66.67,
  "artifacts": [
    {
      "id": 123,
      "filename": "report.pdf",
      "file_type": "document",
      "status": "completed",
      "current_stage": "completed",
      "processing_stages": {
        "extraction": 5.2,
        "summarization": 12.3,
        "embeddings": 8.5
      },
      "started_at": "2025-11-12T10:00:00Z",
      "completed_at": "2025-11-12T10:00:26Z",
      "error_message": null
    },
    {
      "id": 124,
      "filename": "interview.mp3",
      "file_type": "audio",
      "status": "processing",
      "current_stage": "transcription",
      "processing_stages": {
        "extraction": 15.8
      },
      "started_at": "2025-11-12T10:00:05Z",
      "completed_at": null,
      "error_message": null
    },
    {
      "id": 125,
      "filename": "surveillance.mp4",
      "file_type": "video",
      "status": "queued",
      "current_stage": null,
      "processing_stages": {},
      "started_at": null,
      "completed_at": null,
      "error_message": null
    }
  ]
}
```

### Cases List Response

```json
{
  "cases": [
    "Operation Phoenix",
    "Case 2024-001",
    "Mumbai Inquiry"
  ]
}
```

### Case Jobs Response

```json
{
  "case_name": "Operation Phoenix",
  "jobs": [
    {
      "job_id": "manager1/analyst1/uuid-1",
      "status": "completed",
      "total_files": 5,
      "processed_files": 5,
      "parent_job_id": null,
      "created_at": "2025-11-10T14:30:00Z",
      "completed_at": "2025-11-10T14:35:00Z"
    },
    {
      "job_id": "manager1/analyst1/uuid-2",
      "status": "completed",
      "total_files": 3,
      "processed_files": 3,
      "parent_job_id": "manager1/analyst1/uuid-1",
      "created_at": "2025-11-12T10:00:00Z",
      "completed_at": "2025-11-12T10:02:00Z"
    }
  ]
}
```

## Benefits

### For Users:
1. **Real-time visibility** - See exactly what stage each file is in
2. **Performance insights** - Know which stages take longest
3. **Better organization** - Group related documents into cases
4. **Incremental investigation** - Add documents to cases as investigation progresses
5. **Error isolation** - If one file fails, others continue processing

### For Developers:
1. **Granular monitoring** - Track performance at artifact level
2. **Better debugging** - Know exactly where processing failed
3. **Scalability** - Each artifact processed independently
4. **Audit trail** - Complete timing and status history per artifact

## Testing Checklist

- [ ] Run database migration successfully
- [ ] Upload single file - verify per-artifact status updates
- [ ] Upload multiple files - verify each tracks independently
- [ ] Create new case - verify case appears in cases list
- [ ] Add files to existing case - verify they're grouped
- [ ] Verify timing badges display correctly in UI
- [ ] Test error handling - one file fails, others continue
- [ ] Verify RBAC - analysts see their cases, managers see analysts' cases
- [ ] Test polling - status updates every 2 seconds
- [ ] Verify graph building includes all case documents

## Future Enhancements

1. **Case summary generation** - Combine summaries from all jobs in a case
2. **Case timeline view** - Visualize all uploads/updates in a case chronologically
3. **Case comparison** - Compare entities/relationships across cases
4. **Artifact filtering** - Filter by status, file type, processing time
5. **Notification system** - Alert when specific artifacts complete or fail
6. **Performance analytics** - Dashboard showing average times per stage
7. **Batch operations** - Reprocess all artifacts in a case with updated parameters

## Troubleshooting

### Issue: Artifacts stuck in "queued" state
**Solution:** Check that worker services are running and consuming from Redis queues

### Issue: Status not updating in real-time
**Solution:** Verify Redis connection and check browser console for polling errors

### Issue: Case name not appearing
**Solution:** Ensure migration ran successfully and case_name field exists in database

### Issue: Timing data missing
**Solution:** Check that worker is calling `publish_artifact_status()` after each stage

## File Reference

### Backend Files Modified:
- `backend/models.py` - Database models
- `backend/redis_pubsub.py` - Redis pub/sub methods
- `backend/main.py` - API endpoints
- `backend/processors/document_processor_service.py` - Per-artifact status tracking

### Backend Files Created:
- `backend/migrations/add_artifact_status_and_case_name.py` - Database migration

### Frontend Files Modified:
- `types/index.ts` - TypeScript types
- `lib/api-client.ts` - API client methods
- `context/auth-context.tsx` - Status polling and upload
- `components/upload/unified-upload.tsx` - Case management UI
- `components/dashboard/analyst-dashboard.tsx` - Status display

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review API response examples for expected data structure
3. Verify database migration completed successfully
4. Check worker logs for stage timing and status updates
