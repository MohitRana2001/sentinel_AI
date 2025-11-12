# Artifact Status Tracking & Case Workflow - Implementation Guide

## Overview
This document explains the comprehensive refactoring of artifact status tracking and case-based workflow in the IB Bureau system.

---

## ✅ COMPLETED CHANGES

### 1. **Robust Artifact Status Tracking**

#### **Problem**
- Previously, artifacts (documents/audio/video) were marked as "completed" immediately after their main processing (e.g., document extraction, audio transcription)
- Graph processing happened asynchronously, but artifact status wasn't updated after graph completion
- This caused UI inconsistency: artifacts appeared "completed" before graphs were built

#### **Solution**
All artifact processors now follow a consistent status lifecycle:

```
QUEUED → PROCESSING (various stages) → awaiting_graph → COMPLETED (after graph)
```

**Processing Stages by Media Type:**

**Document:**
1. `extraction` - Text extraction from PDF/DOCX/TXT
2. `translation` - Translation if non-English
3. `summarization` - Summary generation
4. `embeddings` - Vector embedding creation
5. `awaiting_graph` - Waiting for graph processing
6. `graph_building` - Graph extraction (by graph processor)
7. `completed` - Fully done

**Audio:**
1. `transcription` - Audio to text conversion
2. `translation` - Translation if Hindi
3. `summarization` - Summary generation
4. `vectorization` - Vector embedding creation
5. `awaiting_graph` - Waiting for graph processing
6. `graph_building` - Graph extraction (by graph processor)
7. `completed` - Fully done

**Video:**
1. `frame_extraction` - Extract frames at 0.3 fps
2. `video_analysis` - Vision LLM analysis
3. `translation` - Translation if Hindi
4. `summarization` - Summary generation
5. `vectorization` - Vector embedding creation
6. `awaiting_graph` - Waiting for graph processing
7. `graph_building` - Graph extraction (by graph processor)
8. `completed` - Fully done

#### **Code Changes**

**File: `/backend/processors/audio_processor_service.py`**
- Added `doc_record` tracking with status updates
- Added `stage_times` dictionary to track timing for each stage
- Publish real-time status updates via Redis pub/sub
- Status remains `PROCESSING` with stage `awaiting_graph` after main processing
- Graph processor will mark as `COMPLETED`

**File: `/backend/processors/video_processor_service.py`**
- Same changes as audio processor
- Added frame extraction and video analysis stage tracking

**File: `/backend/processors/document_processor_service.py`**
- Already had status tracking, but updated to NOT mark as completed
- Changed final status from `completed` to `awaiting_graph`
- Graph processor will mark as `COMPLETED`

**File: `/backend/processors/graph_processor_service.py`**
- Now marks artifact as `COMPLETED` after graph building
- Adds `graph_building` timing to `processing_stages`
- Publishes final artifact completion status via Redis
- Job completion logic now checks for artifacts with `status=COMPLETED` instead of just checking for graph entities

### 2. **Mandatory Case Name**

#### **Problem**
- Case name was optional in upload endpoint
- No validation to ensure case-based grouping

#### **Solution**

**File: `/backend/main.py` (line ~666)**
```python
case_name: str = Form(...),  # MANDATORY: Case name for grouping jobs
```

Added validation:
```python
if not case_name or not case_name.strip():
    raise HTTPException(
        status_code=400,
        detail="Case name is required and cannot be empty"
    )
```

**Impact:**
- All new uploads MUST specify a case name
- Ensures proper case-based grouping and filtering
- Enables case extension and relationship tracking

---

## 📊 CASE WORKFLOW EXPLANATION

### What is a Case?

A **case** is a logical grouping of related uploads (jobs) that allows analysts to:
1. **Group related evidence** under a single investigation
2. **Extend existing cases** with new uploads
3. **Build cumulative knowledge graphs** across all artifacts in a case
4. **Track case-wide relationships** between entities, people, locations, etc.

### Case-Based Features

#### 1. **Creating a New Case**
When uploading files, specify a `case_name`:
```
POST /api/upload
{
  "case_name": "Gandhi_Murder_Investigation",
  "files": [...]
}
```

This creates a new job with:
- `case_name`: "Gandhi_Murder_Investigation"
- `parent_job_id`: null (first upload in case)

#### 2. **Extending an Existing Case**
To add new evidence to an existing case:
```
POST /api/upload
{
  "case_name": "Gandhi_Murder_Investigation",
  "parent_job_id": "manager/analyst/job-uuid-1",  // Optional: link to parent
  "files": [...]
}
```

**What Happens:**
- New job is created with same `case_name`
- If `parent_job_id` is provided, establishes parent-child relationship
- All documents/audio/video are processed independently
- Graphs are built for each artifact
- **Cross-document entity resolution** links entities across all documents in the case

#### 3. **Enhanced Summaries & Graphs**

**Entity Resolution Across Documents:**
When graph processor builds a graph for a new document in a case:

1. **Canonical Matching**: Entities are normalized (e.g., "John Smith" → "john-smith")
2. **Cross-Document Links**: If "john-smith" appears in multiple documents, creates `CROSS_DOC_MATCH` relationships
3. **Document Linking**: Documents that share entities get `SHARES_ENTITY` relationships in Neo4j

**Example:**
```
Case: "Drug_Trafficking_2024"

Upload 1 (CDR data):
  - Entity: "Suspect A" (phone: 9876543210)
  
Upload 2 (Surveillance report):
  - Entity: "Suspect A" (location: Mumbai)
  
Upload 3 (Audio intercept):
  - Entity: "Suspect A" (conversation about shipment)

Result:
  - All 3 documents linked via "Suspect A"
  - Knowledge graph shows:
    * Suspect A's phone number
    * Suspect A's locations
    * Suspect A's activities
    * Connections between documents
```

#### 4. **Case-Based Filtering (To Be Implemented)**

**Backend Endpoints:**
- `GET /api/cases` - List all cases
- `GET /api/cases/{case_name}/jobs` - Get all jobs in a case

**Frontend Components (To Be Updated):**
- Dashboard: Filter by case name
- Job History: Group by case, show parent-child relationships
- Results View: Show all artifacts in a case
- Graph View: Visualize case-wide entity relationships

---

## 🎯 HOW NEW UPLOADS RELATE TO PREVIOUS ARTIFACTS

### Relationship Types

1. **Case-Level Relationship**
   - All jobs with same `case_name` are part of the same investigation
   - Can query all jobs: `SELECT * FROM processing_jobs WHERE case_name = 'X'`

2. **Parent-Child Relationship**
   - `parent_job_id` field creates explicit lineage
   - Example: Initial upload → Follow-up uploads → Final evidence
   - Can traverse hierarchy: `job.child_jobs` / `job.parent_job`

3. **Entity-Level Relationship**
   - Stored in `graph_entities` and `graph_relationships` tables
   - `CROSS_DOC_MATCH` relationships link same entities across documents
   - AlloyDB query:
   ```sql
   SELECT ge1.entity_name, d1.original_filename, d2.original_filename
   FROM graph_relationships gr
   JOIN graph_entities ge1 ON gr.source_entity_id = ge1.entity_id
   JOIN graph_entities ge2 ON gr.target_entity_id = ge2.entity_id
   JOIN documents d1 ON ge1.document_id = d1.id
   JOIN documents d2 ON ge2.document_id = d2.id
   WHERE gr.relationship_type = 'CROSS_DOC_MATCH'
     AND d1.job_id IN (SELECT id FROM processing_jobs WHERE case_name = 'X')
   ```

4. **Neo4j Graph Relationships**
   - `User -[OWNS]-> Document`: Ownership tracking
   - `Document -[CONTAINS_ENTITY]-> Entity`: Document-entity links
   - `Document -[SHARES_ENTITY]-> Document`: Cross-document entity links
   - Entities within documents have their own relationships (extracted by LLM)

### Case Workflow Example

```
Case: "Organized_Crime_Mumbai_2024"

Timeline:
1. Day 1: Upload CDR data (suspect phone records)
   - Job ID: manager1/analyst1/uuid-1
   - Artifacts: 1 CSV file
   - Entities extracted: Suspect A, Suspect B, Phone numbers
   
2. Day 3: Upload surveillance photos
   - Job ID: manager1/analyst1/uuid-2
   - case_name: "Organized_Crime_Mumbai_2024"
   - parent_job_id: manager1/analyst1/uuid-1
   - Artifacts: 5 video files
   - Entities extracted: Suspect A, Suspect C, Location "Warehouse X"
   - Cross-doc links: Suspect A matched across CDR and video
   
3. Day 5: Upload interrogation transcripts
   - Job ID: manager1/analyst1/uuid-3
   - case_name: "Organized_Crime_Mumbai_2024"
   - parent_job_id: manager1/analyst1/uuid-2
   - Artifacts: 3 audio files
   - Entities extracted: Suspect A, Suspect B, Suspect D, "Warehouse X"
   - Cross-doc links:
     * Suspect A: CDR, Video, Audio
     * Suspect B: CDR, Audio
     * Warehouse X: Video, Audio
     
Knowledge Graph (Neo4j):
  - Suspect A appears in 3 documents (CDR, Video, Audio)
  - Suspect B appears in 2 documents (CDR, Audio)
  - Warehouse X mentioned in 2 documents (Video, Audio)
  - Document relationships visualized
  - Timeline reconstruction possible
```

---

## 🔄 REAL-TIME STATUS UPDATES

### Redis Pub/Sub Architecture

**Publishing:**
```python
redis_pubsub.publish_artifact_status(
    job_id=job.id,
    filename=filename,
    status="processing",
    current_stage="extraction",
    processing_stages={"extraction": 5.2, ...}
)
```

**Subscribing (Frontend):**
```javascript
// WebSocket or SSE connection to /api/jobs/{job_id}/status
{
  "type": "artifact_status",
  "job_id": "manager/analyst/uuid",
  "filename": "document.pdf",
  "status": "processing",
  "current_stage": "extraction",
  "processing_stages": {
    "extraction": 5.2,
    "translation": 8.1
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**UI Updates:**
- Progress bars show current stage
- Timing breakdown displayed per stage
- Real-time updates as each stage completes
- Final "completed" status only after graph processing

---

## 🐛 SUSPECTS TABLE RESOLUTION

### Issue
`PersonOfInterest` model was defined twice in `models.py`:
- Once active (lines 225-258)
- Once commented out (lines 290-324)

### Resolution Needed
**Action:** Remove the commented duplicate definition

```python
# Remove these lines from models.py (290-324):
# class PersonOfInterest(Base):
#     __tablename__ = "person_of_interest"
#     ...
```

**Verified:** The active definition is correct and includes:
- `details` JSONB field for flexible key-value storage
- `details_embedding` for semantic search
- `photograph_embedding` for image similarity
- Proper indexes for vector search

---

## 📝 REMAINING TASKS

### 1. **UI Updates**

#### Analyst Dashboard (`components/dashboard/analyst-dashboard.tsx`)
- [ ] Stack components vertically instead of grid layout
- [ ] Add case name filter dropdown
- [ ] Show case-based statistics

#### Job History
- [ ] Add case name column
- [ ] Group jobs by case
- [ ] Show parent-child relationships (tree view)
- [ ] Filter by case name

#### Results View
- [ ] Display case name prominently
- [ ] Show all artifacts in the same case
- [ ] Indicate cross-document entity matches

### 2. **Backend API Enhancements**

- [ ] `GET /api/cases/{case_name}/summary` - Aggregate summary across all jobs in case
- [ ] `GET /api/cases/{case_name}/entities` - All unique entities in case
- [ ] `GET /api/cases/{case_name}/timeline` - Chronological view of uploads
- [ ] `GET /api/cases/{case_name}/graph` - Combined graph data for case

### 3. **Graph Visualization**

- [ ] Neo4j graph view filtered by case
- [ ] Highlight cross-document entity links
- [ ] Show document-to-document relationships
- [ ] Interactive timeline of case events

### 4. **Migration Script**

For existing data without case names:
```sql
-- Assign default case names to existing jobs
UPDATE processing_jobs 
SET case_name = CONCAT('legacy_case_', id)
WHERE case_name IS NULL;
```

---

## 🧪 TESTING CHECKLIST

### Artifact Status Testing
- [ ] Upload document → verify status updates through all stages
- [ ] Upload audio → verify status updates through all stages
- [ ] Upload video → verify status updates through all stages
- [ ] Verify artifact marked "completed" only AFTER graph processing
- [ ] Check Redis pub/sub messages are published correctly

### Case Workflow Testing
- [ ] Create new case with upload
- [ ] Extend case with second upload (same case_name)
- [ ] Verify cross-document entity matching
- [ ] Check Neo4j graph has SHARES_ENTITY relationships
- [ ] Verify case filtering in API endpoints

### Mandatory Case Name Testing
- [ ] Upload without case_name → should fail with 400 error
- [ ] Upload with empty case_name → should fail with 400 error
- [ ] Upload with valid case_name → should succeed

---

## 🚀 DEPLOYMENT NOTES

### Database Changes
No schema migration needed - fields already exist:
- `processing_jobs.case_name` (already exists)
- `processing_jobs.parent_job_id` (already exists)
- `documents.status` (already exists)
- `documents.processing_stages` (already exists)
- `documents.current_stage` (already exists)

### Service Restart Required
After deploying code changes, restart:
1. Document Processor Service
2. Audio Processor Service
3. Video Processor Service
4. Graph Processor Service
5. Main FastAPI Backend

### Configuration
No new environment variables needed.

---

## 📊 PERFORMANCE IMPACT

### Positive Impacts
- More accurate job completion tracking
- Better user experience with real-time stage updates
- Enables case-based analytics and filtering

### Considerations
- Slight delay in marking jobs as "completed" (now waits for graph)
- Additional Redis pub/sub messages (minimal overhead)
- More complex status logic in processors

---

## 🔗 RELATED FILES

**Backend:**
- `/backend/processors/document_processor_service.py`
- `/backend/processors/audio_processor_service.py`
- `/backend/processors/video_processor_service.py`
- `/backend/processors/graph_processor_service.py`
- `/backend/main.py` (upload endpoint)
- `/backend/models.py` (ProcessingJob, Document models)
- `/backend/redis_pubsub.py` (status publishing)

**Frontend:**
- `/components/dashboard/analyst-dashboard.tsx` (needs vertical stacking)
- `/components/results/*` (needs case filtering)
- `/types/index.ts` (artifact status types)

**Documentation:**
- `/backend/migrations/add_artifact_status_and_case_name.py`
- `/backend/UPLOAD_FIX_SUMMARY.md`

---

## 💡 KEY TAKEAWAYS

1. **Artifact status is now accurate**: Only marked "completed" after full processing including graph
2. **Case name is mandatory**: Ensures proper grouping and enables case-based features
3. **Real-time updates**: UI can show exact processing stage for each artifact
4. **Cross-document linking**: Entities are automatically matched across documents in the same case
5. **Extensible design**: Easy to add more case-based features (analytics, combined summaries, etc.)

---

**Document Version:** 1.0  
**Last Updated:** 2024-01-15  
**Author:** AI Assistant (GitHub Copilot)
