# Migration Guide: Unified Upload & Suspects

## Prerequisites
- Backend server stopped
- Database access (PostgreSQL/AlloyDB or SQLite)

## Step 1: Update Backend Code
The following files have been updated:
- ✅ `backend/models.py` - Added Suspect model
- ✅ `backend/main.py` - Updated upload endpoint, added suspects support

## Step 2: Restart Backend
The database migration will happen automatically on startup via `init_db()`:

```bash
cd backend
python main.py
```

**Expected Output:**
```
✅ pgvector extension enabled
✅ Database tables created
Database initialized
API running at 0.0.0.0:8000
Docs available at /api/v1/docs
```

The `suspects` table will be created automatically.

## Step 3: Verify Database Schema

### PostgreSQL/AlloyDB:
```sql
-- Check suspects table exists
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' AND table_name = 'suspects';

-- Verify columns
\d suspects
```

### SQLite:
```bash
sqlite3 backend/sentinel_dev.db
.schema suspects
```

**Expected Schema:**
```sql
CREATE TABLE suspects (
    id VARCHAR NOT NULL, 
    job_id VARCHAR NOT NULL, 
    fields JSON NOT NULL, 
    created_at TIMESTAMP, 
    updated_at TIMESTAMP, 
    PRIMARY KEY (id), 
    FOREIGN KEY(job_id) REFERENCES processing_jobs (id)
)
```

## Step 4: Test Upload Flow

### 1. Login to the application
```
http://localhost:3000
```

### 2. Navigate to Dashboard
- Click on "Dashboard" (Analyst view)

### 3. Add Suspects
- Click on "Suspects" tab
- Click "Add Suspect"
- Fill in fields (e.g., Name, Age, Location)
- Click "Save Suspect"

### 4. Upload Files
- Click on "Upload" tab
- Click "Add Document" and select a PDF
- Click "Add Audio" and select an MP3 (choose language)
- Click "Add Video" and select an MP4 (choose language)
- Verify suspects count is shown: "2 Suspect(s) will be included in this job"
- Click "Upload X File(s) + Y Suspect(s)"

### 5. Check Job Status
- Click on "History" tab (should auto-refresh)
- Verify job appears with:
  - File count (e.g., "3/3 files")
  - Suspects count (e.g., "2 suspect(s)")
  - Status badge
  - Progress percentage

### 6. View Results
- Wait for job to complete
- Click "View Results" button
- Verify navigation to results page with job ID in URL

## Step 5: Verify Backend API

### Test upload endpoint:
```bash
curl -X POST "http://localhost:8000/api/v1/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "files=@test.pdf" \
  -F "media_types=document" \
  -F "languages=" \
  -F 'suspects=[{"id":"123","fields":[{"id":"1","key":"name","value":"John Doe"}]}]'
```

**Expected Response:**
```json
{
  "job_id": "manager/analyst/uuid",
  "status": "queued",
  "total_files": 1,
  "suspects_count": 1,
  "message": "Successfully uploaded 1 files and 1 suspects. Processing started."
}
```

### Test job results endpoint:
```bash
curl -X GET "http://localhost:8000/api/v1/jobs/JOB_ID/results" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected Response:**
```json
{
  "job_id": "manager/analyst/uuid",
  "status": "completed",
  "completed_at": "2024-01-01T00:00:00",
  "documents": [
    {
      "id": 1,
      "filename": "test.pdf",
      "file_type": "document",
      "summary": "...",
      "created_at": "2024-01-01T00:00:00"
    }
  ],
  "suspects": [
    {
      "id": "123",
      "fields": [
        {"id": "1", "key": "name", "value": "John Doe"}
      ],
      "created_at": "2024-01-01T00:00:00",
      "updated_at": "2024-01-01T00:00:00"
    }
  ]
}
```

## Troubleshooting

### Issue: Suspects table not created
**Solution:** Manually create the table:
```sql
CREATE TABLE suspects (
    id VARCHAR PRIMARY KEY,
    job_id VARCHAR NOT NULL,
    fields JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES processing_jobs(id)
);

CREATE INDEX idx_suspects_job_id ON suspects(job_id);
```

### Issue: Upload fails with "language parameter required"
**Solution:** Ensure language is specified for audio/video files in the frontend.

### Issue: Suspects not appearing in job results
**Solution:** 
1. Check suspects are in the database:
   ```sql
   SELECT * FROM suspects WHERE job_id = 'YOUR_JOB_ID';
   ```
2. Verify the job_id matches exactly
3. Check backend logs for errors

### Issue: "View Results" button doesn't work
**Solution:** 
1. Check browser console for errors
2. Verify `useRouter` is imported from `next/navigation`
3. Ensure results page exists at `/app/results/page.tsx`

## Rollback Plan

If issues occur, you can rollback by:

1. **Drop suspects table:**
   ```sql
   DROP TABLE IF EXISTS suspects;
   ```

2. **Revert backend files:**
   ```bash
   git checkout HEAD~1 backend/models.py backend/main.py
   ```

3. **Restart backend:**
   ```bash
   python backend/main.py
   ```

## Production Deployment

### 1. Database Backup
```bash
# PostgreSQL
pg_dump -h HOST -U USER -d DATABASE > backup_before_migration.sql

# SQLite
cp backend/sentinel_dev.db backend/sentinel_dev.db.backup
```

### 2. Deploy Backend
```bash
# Pull latest code
git pull origin main

# Restart backend service
systemctl restart sentinel-backend
# OR
docker-compose restart backend
```

### 3. Verify Migration
```bash
# Check suspects table
psql -h HOST -U USER -d DATABASE -c "\d suspects"

# Check backend logs
tail -f /var/log/sentinel-backend.log
```

### 4. Deploy Frontend
```bash
# Build and deploy
npm run build
npm run start
# OR
docker-compose restart frontend
```

## Post-Migration Validation

- [ ] Suspects table created successfully
- [ ] Upload endpoint accepts multiple media types
- [ ] Upload endpoint accepts suspects data
- [ ] Suspects are saved to database
- [ ] Job results include suspects
- [ ] Job list shows suspects count
- [ ] History tab auto-refreshes
- [ ] View Results button works
- [ ] Results page displays suspects

## Support

If you encounter issues:
1. Check backend logs: `tail -f backend/logs/app.log`
2. Check database connections
3. Verify Redis is running (for job queues)
4. Review the full implementation summary: `UNIFIED_UPLOAD_IMPLEMENTATION.md`
