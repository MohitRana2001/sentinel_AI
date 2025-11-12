# Quick Reference: Unified Upload Architecture

## 🎯 Key Concepts

**Unified Job** = Multiple files (different types) + Suspects in a single processing job

**Media Types:**
- `document` - PDF, DOCX, TXT
- `audio` - MP3, WAV, M4A, OGG (requires language)
- `video` - MP4, AVI, MOV, MKV (requires language)
- `cdr` - CSV, XLS, XLSX

## 📊 Data Models

### Suspect
```typescript
{
  id: string                    // UUID
  fields: SuspectField[]        // [{ id, key, value }]
  createdAt: string
  updatedAt: string
}
```

### FileWithMetadata
```typescript
{
  file: File
  mediaType: 'document' | 'audio' | 'video' | 'cdr'
  language?: string             // Required for audio/video
}
```

### UploadJob
```typescript
{
  files: FileWithMetadata[]
  suspects: Suspect[]
}
```

## 🔌 API Endpoints

### Upload Files + Suspects
```http
POST /api/v1/upload
Content-Type: multipart/form-data

files: [File, File, File]
media_types: ['document', 'audio', 'video']
languages: ['', 'hi', 'en']
suspects: '[{"id":"123","fields":[...]}]'

Response:
{
  "job_id": "manager/analyst/uuid",
  "status": "queued",
  "total_files": 3,
  "suspects_count": 2,
  "message": "Successfully uploaded 3 files and 2 suspects..."
}
```

### Get Job Results
```http
GET /api/v1/jobs/{job_id}/results

Response:
{
  "job_id": "...",
  "status": "completed",
  "documents": [...],
  "suspects": [
    {
      "id": "123",
      "fields": [{"id":"1", "key":"name", "value":"John"}],
      "created_at": "...",
      "updated_at": "..."
    }
  ]
}
```

### List Jobs
```http
GET /api/v1/jobs?limit=10&offset=0

Response:
[
  {
    "job_id": "...",
    "total_files": 3,
    "processed_files": 3,
    "suspects_count": 2,  // NEW
    "progress_percentage": 100,
    "status": "completed"
  }
]
```

## 🎨 Frontend Components

### UnifiedUpload
```tsx
<UnifiedUpload 
  onUpload={handleUpload} 
  suspects={suspects}  // From dashboard state
/>
```

**Usage:**
```tsx
const handleUpload = async (files: FileWithMetadata[], suspects: Suspect[]) => {
  await uploadJob({ files, suspects });
};
```

### AnalystDashboard Tabs
```tsx
<Tabs value={activeTab} onValueChange={setActiveTab}>
  <TabsList>
    <TabsTrigger value="upload">Upload</TabsTrigger>
    <TabsTrigger value="suspects">Suspects</TabsTrigger>
    <TabsTrigger value="history">History</TabsTrigger>
  </TabsList>
  
  <TabsContent value="upload">
    <UnifiedUpload onUpload={handleUpload} suspects={suspects} />
  </TabsContent>
  
  <TabsContent value="suspects">
    <SuspectManagement suspects={suspects} onSuspectsChange={setSuspects} />
  </TabsContent>
  
  <TabsContent value="history">
    {/* Auto-refreshes when opened */}
  </TabsContent>
</Tabs>
```

## 🔄 Upload Flow

```
1. User adds files:
   - Click "Add Document" → Select PDFs
   - Click "Add Audio" → Select MP3s → Choose language
   - Click "Add Video" → Select MP4s → Choose language

2. Files stored in state:
   [
     { file: File, mediaType: 'document', language: undefined },
     { file: File, mediaType: 'audio', language: 'hi' },
     { file: File, mediaType: 'video', language: 'en' }
   ]

3. User clicks "Upload X File(s) + Y Suspect(s)"

4. uploadJob() creates FormData:
   formData.append('files', file1)
   formData.append('files', file2)
   formData.append('media_types', 'document')
   formData.append('media_types', 'audio')
   formData.append('languages', '')
   formData.append('languages', 'hi')
   formData.append('suspects', JSON.stringify(suspects))

5. Backend receives FormData:
   - Creates single ProcessingJob
   - Saves all Suspects to DB
   - Queues each file to appropriate worker

6. Workers process in parallel:
   - Document → document_queue → Document Processor
   - Audio → audio_queue → Audio Processor
   - Video → video_queue → Video Processor

7. Results available via /jobs/{job_id}/results
```

## 💾 Database Schema

### suspects table
```sql
CREATE TABLE suspects (
    id VARCHAR PRIMARY KEY,
    job_id VARCHAR NOT NULL,
    fields JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES processing_jobs(id)
);
```

### Query Examples
```sql
-- Get suspects for a job
SELECT * FROM suspects WHERE job_id = 'manager/analyst/uuid';

-- Count suspects per job
SELECT job_id, COUNT(*) as suspect_count 
FROM suspects 
GROUP BY job_id;

-- Get jobs with suspects
SELECT pj.*, COUNT(s.id) as suspect_count
FROM processing_jobs pj
LEFT JOIN suspects s ON s.job_id = pj.id
GROUP BY pj.id;
```

## 🔧 Common Tasks

### Add a new media type
1. Update `MediaType` in `types/index.ts`
2. Add to `MEDIA_TYPE_CONFIG` in `unified-upload.tsx`
3. Add queue constant in `config.py`
4. Update file type detection in `main.py`
5. Create processor service
6. Add worker to docker-compose

### Debug upload issues
```python
# Backend logs
print(f"Files: {len(files)}")
print(f"Media types: {media_types}")
print(f"Languages: {languages}")
print(f"Suspects: {suspects_data}")
```

```tsx
// Frontend logs
console.log('Files to upload:', files);
console.log('Suspects:', suspects);
console.log('FormData:', Array.from(formData.entries()));
```

### Test upload manually
```bash
# Create test suspects JSON
echo '[{"id":"test-1","fields":[{"id":"1","key":"name","value":"Test User"}]}]' > suspects.json

# Upload
curl -X POST http://localhost:8000/api/v1/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "files=@test.pdf" \
  -F "files=@test.mp3" \
  -F "media_types=document" \
  -F "media_types=audio" \
  -F "languages=" \
  -F "languages=hi" \
  -F "suspects=$(cat suspects.json)"
```

## 🐛 Troubleshooting

### "Language parameter required"
Audio/video files must have language specified.
```tsx
// Fix:
<Select onValueChange={(lang) => updateLanguage(index, lang)}>
```

### Suspects not saved
Check JSON parsing in backend:
```python
try:
    suspects_data = json.loads(suspects)
except Exception as e:
    print(f"Error parsing suspects: {e}")
```

### History not refreshing
Verify useEffect dependency:
```tsx
useEffect(() => {
  if (activeTab === 'history') {
    loadPastJobs();
  }
}, [activeTab]);  // Must include activeTab
```

### View Results not working
Check router import:
```tsx
import { useRouter } from "next/navigation";  // Not "next/router"!
```

## 📝 Code Snippets

### Backend: Save suspects
```python
for suspect_data in suspects_data:
    suspect = models.Suspect(
        id=suspect_data.get('id', str(uuid.uuid4())),
        job_id=job_id,
        fields=suspect_data.get('fields', [])
    )
    db.add(suspect)
db.commit()
```

### Frontend: Build FormData
```tsx
const formData = new FormData();
job.files.forEach((fileWithMeta) => {
  formData.append('files', fileWithMeta.file);
  formData.append('media_types', fileWithMeta.mediaType);
  formData.append('languages', fileWithMeta.language || '');
});
if (job.suspects.length > 0) {
  formData.append('suspects', JSON.stringify(job.suspects));
}
```

### Query suspects count
```python
suspects_count = db.query(models.Suspect).filter(
    models.Suspect.job_id == job.id
).count()
```

## 📚 Related Documentation

- `UNIFIED_UPLOAD_IMPLEMENTATION.md` - Full implementation details
- `MIGRATION_GUIDE.md` - Deployment guide
- `COMPLETION_SUMMARY.md` - What was changed and why
- Backend API docs: `http://localhost:8000/api/v1/docs`

## 🚀 Quick Start

1. Start backend: `cd backend && python main.py`
2. Start frontend: `npm run dev`
3. Login as analyst
4. Go to Suspects tab → Add suspects
5. Go to Upload tab → Add mixed media files
6. Click Upload
7. Go to History tab → See job with suspects count
8. Click "View Results" when complete

---

**Last Updated:** Check git log for latest changes
**Questions?** Review the implementation docs or check backend logs
