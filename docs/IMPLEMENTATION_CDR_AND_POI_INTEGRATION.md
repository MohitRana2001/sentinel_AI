# CDR Processing and Person of Interest Integration

## Overview
This document describes the implementation of the following features:
1. Redis queue service for CDR (Call Detail Records) processing
2. Integration of Person of Interest (POI) with the suspects management
3. Joint tables for linking videos and CDR records to POI
4. Phone number matching in CDR data

## Implementation Date
November 14, 2025

---

## 1. CDR Redis Queue Service

### Purpose
Process CDR files (CSV/XLSX) asynchronously using Redis queues, similar to document, audio, and video processing.

### Changes Made

#### 1.1 New CDR Processor Service
**File**: `backend/processors/cdr_processor_service.py`

- Listens to Redis queue: `cdr_queue`
- Processes CDR files in parallel
- Tracks processing stages: `parsing` → `phone_matching` → `completed`
- Creates `CDRPOIMatch` records when phone numbers match POI records

**Progress Calculation for CDR**:
- Parsing: 33%
- Phone matching: 66%
- Completed: 100%

#### 1.2 Updated CDR Processor
**File**: `backend/cdr_processor.py`

Fixed the `process_cdr_file()` method to properly download files using `download_to_temp()` instead of the incorrect `download_file()` method.

#### 1.3 Updated Models
**File**: `backend/models.py`

Added status tracking fields to `CDRRecord`:
```python
status = Column(SQLEnum(JobStatus), default=JobStatus.QUEUED, nullable=False)
processing_stages = Column(JSON, default=dict)
current_stage = Column(String)
error_message = Column(Text)
started_at = Column(DateTime)
completed_at = Column(DateTime)
```

#### 1.4 Updated Upload Flow
**File**: `backend/main.py`

Changed from synchronous CDR processing to queue-based:
```python
# OLD: Synchronous processing
cdr_data = cdr_processor.process_cdr_file(gcs_path)
db.add(cdr_record)

# NEW: Queue-based processing
redis_pubsub.push_file_to_queue(job_id, gcs_path, filename, settings.REDIS_QUEUE_CDR)
```

#### 1.5 Updated Redis PubSub
**File**: `backend/redis_pubsub.py`

Added CDR progress stages:
```python
"cdr": {
    "starting": 0,
    "parsing": 33,
    "phone_matching": 66,
    "completed": 100
}
```

---

## 2. Person of Interest Integration

### Purpose
Replace the suspects table with PersonOfInterest integration, making name, phone number, and photo mandatory fields.

### Changes Made

#### 2.1 Updated PersonOfInterest Model
**File**: `backend/models.py`

Made fields mandatory:
```python
name = Column(String, index=True, nullable=False)
phone_number = Column(String, nullable=False, index=True)  # NEW: MANDATORY
photograph_base64 = Column(Text, nullable=False)  # MANDATORY
details = Column(JSONB, nullable=False, default=dict)  # Now optional, for extra fields
```

Added relationships to joint tables:
```python
video_detections = relationship("VideoPOIDetection", ...)
cdr_matches = relationship("CDRPOIMatch", ...)
```

#### 2.2 Updated Pydantic Schemas
**File**: `backend/main.py`

```python
class PersonOfInterestCreate(BaseModel):
    name: str  # MANDATORY
    phone_number: str  # MANDATORY
    photograph_base64: str  # MANDATORY
    details: Dict[str, Any] = {}  # OPTIONAL

class PersonOfInterestImport(BaseModel):
    persons: List[PersonOfInterestCreate]
```

#### 2.3 New Import Endpoint
**File**: `backend/main.py`

Added bulk import endpoint:
```
POST /api/v1/person-of-interest/import
```

This allows importing multiple POI records at once with validation for mandatory fields.

---

## 3. Joint Tables for Linking

### Purpose
Create database tables to track which suspects/POIs appear in videos and CDR records.

### Changes Made

#### 3.1 Video-POI Detection Table
**File**: `backend/models.py`

```python
class VideoPOIDetection(Base):
    __tablename__ = "video_poi_detections"
    
    document_id = Column(Integer, ForeignKey("documents.id"))  # Video
    poi_id = Column(Integer, ForeignKey("person_of_interest.id"))
    job_id = Column(String, ForeignKey("processing_jobs.id"))
    frames = Column(String)  # Comma-separated frame numbers: "15,42,89,127"
    confidence_scores = Column(JSON)
    detection_metadata = Column(JSON)
```

**Purpose**: Track which frames of a video contain which POI.

**Usage Example**:
- Video: `investigation_footage.mp4` (document_id: 123)
- POI: "John Doe" (poi_id: 5)
- Frames: "15,42,89,127" (POI detected in these frame numbers)

#### 3.2 CDR-POI Match Table
**File**: `backend/models.py`

```python
class CDRPOIMatch(Base):
    __tablename__ = "cdr_poi_matches"
    
    poi_id = Column(Integer, ForeignKey("person_of_interest.id"))
    job_id = Column(String, ForeignKey("processing_jobs.id"))
    phone_number = Column(String, index=True)
    cdr_record_data = Column(JSONB)  # The full CDR record
    matched_field = Column(String)  # Which field matched: "caller" or "called"
```

**Purpose**: Track which CDR records contain a POI's phone number.

**Usage Example**:
- POI: "John Doe" with phone: "9876543210"
- CDR Record: `{"caller": "9876543210", "called": "1234567890", "timestamp": "..."}`
- Matched Field: "caller"

---

## 4. Phone Number Matching

### Implementation
**File**: `backend/processors/cdr_processor_service.py`

The `_match_phone_numbers()` method:

1. **Extracts POI phone numbers** from the `person_of_interest` table
   - Looks in multiple possible keys: `phone`, `phone_number`, `mobile`, etc.
   - Normalizes phone numbers (removes spaces, dashes, parentheses)

2. **Scans CDR records** for matching phone numbers
   - Checks common CDR fields: `caller`, `called`, `calling_number`, `called_number`, `a_number`, `b_number`
   - Normalizes phone numbers from CDR records

3. **Creates match records** when a phone number is found
   - Stores the full CDR record as JSONB
   - Records which field matched (e.g., "caller" vs "called")

**Normalization**:
```python
def _normalize_phone(self, phone: str) -> str:
    # Remove all non-digit characters
    normalized = re.sub(r'\D', '', phone)
    # Return only if length >= 10
    return normalized if len(normalized) >= 10 else ""
```

---

## 5. Database Migration

### Migration Script
**File**: `backend/migrate_poi_and_cdr.py`

Run this script to update the database schema:
```bash
cd backend
python migrate_poi_and_cdr.py
```

**What it does**:
1. Adds mandatory fields to `person_of_interest` table
2. Adds status tracking fields to `cdr_records` table
3. Creates `video_poi_detections` table
4. Creates `cdr_poi_matches` table
5. Creates necessary indexes

---

## 6. Deployment

### Docker Services

#### 6.1 CDR Processor Service
**File**: `backend/Dockerfile.cdr_processor`

Build and run:
```bash
docker build -f Dockerfile.cdr_processor -t cdr-processor .
docker run --env-file .env cdr-processor
```

#### 6.2 Docker Compose
**File**: `docker-compose.yml` or `docker-compose.prod.yml`

Add the CDR processor service:
```yaml
cdr-processor:
  build:
    context: ./backend
    dockerfile: Dockerfile.cdr_processor
  environment:
    - REDIS_HOST=redis
    - ALLOYDB_HOST=db
  depends_on:
    - redis
    - db
```

---

## 7. API Changes

### New Endpoints

#### 7.1 Import Person of Interest
```
POST /api/v1/person-of-interest/import
Content-Type: application/json

{
  "persons": [
    {
      "name": "John Doe",
      "phone_number": "9876543210",
      "photograph_base64": "data:image/jpeg;base64,...",
      "details": {
        "address": "123 Main St",
        "occupation": "Engineer"
      }
    }
  ]
}
```

#### 7.2 Updated Create POI
```
POST /api/v1/person-of-interest
Content-Type: application/json

{
  "name": "John Doe",  // REQUIRED
  "phone_number": "9876543210",  // REQUIRED
  "photograph_base64": "data:image/jpeg;base64,...",  // REQUIRED
  "details": {  // OPTIONAL
    "address": "123 Main St"
  }
}
```

---

## 8. Frontend Changes Required

### 8.1 Suspect Management Component
**File**: `components/dashboard/person-of-interest-management.tsx`

**Changes needed**:
1. Update form to include mandatory fields:
   - Name (text input)
   - Phone Number (text input with validation)
   - Photo (file upload with base64 encoding)

2. Add import functionality:
   - File upload for bulk import (JSON/CSV)
   - Validation of mandatory fields before import

3. Integration with backend POI endpoints

### 8.2 Upload Page
When uploading files, the suspects can still be added, but they should now:
1. Be saved as PersonOfInterest records instead of Suspect records
2. Include mandatory validation for name, phone, and photo

---

## 9. Testing

### 9.1 CDR Processing Test

1. **Upload a CDR file** (CSV or XLSX):
```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -F "files=@test_cdr.csv" \
  -F "media_types=cdr" \
  -F "case_name=Test Case"
```

2. **Check processing status**:
- Monitor Redis queue: `LLEN cdr_queue`
- Check database: `SELECT * FROM cdr_records WHERE status='completed'`
- Check matches: `SELECT * FROM cdr_poi_matches`

### 9.2 POI Phone Matching Test

1. **Create a POI with phone number**:
```bash
curl -X POST http://localhost:8000/api/v1/person-of-interest \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Person",
    "phone_number": "9876543210",
    "photograph_base64": "...",
    "details": {}
  }'
```

2. **Upload CDR with matching phone**:
Upload a CDR CSV with phone "9876543210" in caller or called fields

3. **Verify match**:
```sql
SELECT * FROM cdr_poi_matches WHERE phone_number='9876543210';
```

---

## 10. Configuration

### Environment Variables
**File**: `.env` or `.env.local`

```bash
# Redis Queue for CDR
REDIS_QUEUE_CDR=cdr_queue

# Storage backend
STORAGE_BACKEND=gcs  # or 'local'
```

---

## 11. Troubleshooting

### Common Issues

#### Issue 1: StorageManager.download_file() missing argument
**Error**: `TypeError: StorageManager.download_file() missing 1 required positional argument: 'local_path'`

**Solution**: Updated `cdr_processor.py` to use `download_to_temp()` instead.

#### Issue 2: CDR not processing
**Symptoms**: CDR files uploaded but not processing

**Check**:
1. Is CDR processor service running? `docker ps | grep cdr-processor`
2. Are files being queued? `redis-cli LLEN cdr_queue`
3. Check service logs: `docker logs cdr-processor`

#### Issue 3: Phone numbers not matching
**Symptoms**: POI records exist but no CDR matches found

**Check**:
1. Phone number format in POI details (should be in a recognized key like `phone`, `phone_number`, `mobile`)
2. Phone number format in CDR records
3. Check normalization: both should have at least 10 digits after removing non-numeric characters

---

## 12. Future Enhancements

### Planned Features

1. **Face Recognition in Videos**
   - Implement `photograph_embedding` generation using face recognition models
   - Match video frames against POI photos
   - Populate `VideoPOIDetection` table automatically

2. **Advanced CDR Analysis**
   - Call duration analysis
   - Call frequency patterns
   - Network analysis (who calls whom)
   - Geographic location tracking (if CDR includes cell tower data)

3. **POI Search**
   - Semantic search using `details_embedding`
   - Photo search using `photograph_embedding`
   - Phone number fuzzy matching

4. **Frontend Dashboard**
   - Visualize POI connections in knowledge graph
   - Timeline view of CDR activities
   - Video playback with POI detection highlights

---

## Summary

This implementation provides:
- ✅ Asynchronous CDR processing with Redis queues
- ✅ Mandatory fields for Person of Interest (name, phone, photo)
- ✅ Phone number matching between CDR and POI
- ✅ Joint tables for tracking POI appearances in videos and CDR
- ✅ Progress tracking for CDR processing (33%, 66%, 100%)
- ✅ Bulk import for POI records

**Note**: The suspect table and related code still exist but should be deprecated in favor of PersonOfInterest. A future migration can remove the old suspect tables once all functionality is confirmed working.
