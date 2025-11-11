# Quick Reference: Analyst Dashboard Changes

## Overview
```
┌─────────────────────────────────────────────────────────────┐
│                    Analyst Dashboard                         │
├─────────────────────────────────────────────────────────────┤
│  [Documents] [Audio] [Video] [CDR] [Suspects] [History]    │
└─────────────────────────────────────────────────────────────┘
```

## 1. Documents Tab
- **Upload**: PDF, DOCX (max 50MB)
- **Language**: Auto-detected ✨
- **Output**: Summary

## 2. Audio Tab
- **Upload**: MP3, WAV, M4A, OGG (max 100MB)
- **Language**: Required dropdown (11 languages) 🌐
- **Output**: Transcription + Translation + Summary

## 3. Video Tab
- **Upload**: MP4, AVI, MOV, MKV (max 500MB)
- **Language**: Required dropdown (11 languages) 🌐
- **Output**: Transcription + Translation + Summary

## 4. CDR Tab ⭐ NEW
- **Upload**: CSV, XLS, XLSX (max 100MB)
- **Language**: N/A
- **Output**: Call pattern analysis + Network graph

## 5. Suspects Tab ⭐ NEW
```
┌─────────────────────────────────────────┐
│  Suspect #1 - John Doe        [Delete]  │
├─────────────────────────────────────────┤
│  Name          │ John Doe        [x]    │
│  Address       │ 123 Main St     [x]    │
│  Mobile        │ +919876543210   [x]    │
│  [Custom Key]  │ [Custom Value]  [x]    │
├─────────────────────────────────────────┤
│  [+ Custom Field] [+ Default Fields]    │
│  [Save] [Cancel]                        │
└─────────────────────────────────────────┘
```

**Features**:
- ➕ Add unlimited suspects
- ➕ Add unlimited fields per suspect
- 🗑️ Remove any field (including defaults)
- 💾 Export to JSON
- 📥 Import from JSON
- 📊 Statistics: Total suspects, Total fields, Last updated

**Default Fields** (optional):
- Name, Address, Mobile Number, Email, DOB, Occupation

## 6. History Tab ⭐ RESTORED
```
┌────────────────────────────────────────────┐
│  Job ID: abc-123  [completed]             │
│  5/5 files • 100% • Nov 11, 10:30 AM      │
│                        [View Results]      │
├────────────────────────────────────────────┤
│  Job ID: def-456  [processing]            │
│  3/5 files • 60% • Nov 11, 11:15 AM       │
└────────────────────────────────────────────┘
```

---

## Supported Languages (Audio/Video)
1. 🇮🇳 Hindi (hi)
2. 🇮🇳 Bengali (bn)
3. 🇮🇳 Punjabi (pa)
4. 🇮🇳 Gujarati (gu)
5. 🇮🇳 Kannada (kn)
6. 🇮🇳 Malayalam (ml)
7. 🇮🇳 Marathi (mr)
8. 🇮🇳 Tamil (ta)
9. 🇮🇳 Telugu (te)
10. 🇨🇳 Chinese (zh)
11. 🇬🇧 English (en)

---

## File Summary

### New Files Created
1. `/components/ui/tabs.tsx` - Tab navigation
2. `/components/ui/select.tsx` - Language dropdown
3. `/components/ui/label.tsx` - Form labels
4. `/hooks/use-toast.ts` - Toast notifications
5. `/components/upload/media-upload-card.tsx` - Reusable upload component
6. `/components/dashboard/analyst-dashboard.tsx` - Main dashboard (REPLACED)
7. `/components/dashboard/suspect-management.tsx` - Suspect database ⭐ NEW

### Modified Files
1. `/types/index.ts` - Added MediaType, CDR, Suspect types
2. `/context/auth-context.tsx` - Added uploadMedia, mediaItems, polling
3. `/components/dashboard/dashboard-page.tsx` - Simplified routing

---

## Usage Examples

### Upload Document
1. Click "Documents" tab
2. Drag PDF file or click browse
3. Click "Upload document"
4. Wait for processing (auto-polls every 2s)
5. View summary when complete

### Upload Audio (Hindi)
1. Click "Audio" tab
2. Drag MP3 file
3. **Select "Hindi" from dropdown** ⚠️ Required
4. Click "Upload audio"
5. View transcription + translation + summary

### Add Suspect
1. Click "Suspects" tab
2. Click "Add Suspect"
3. Click "Add Default Fields" (or "Add Custom Field")
4. Fill in values:
   - Name: "Rajesh Kumar"
   - Mobile: "+919876543210"
   - Address: "45 MG Road, Bangalore"
5. Add custom field: "Known Associates" → "Priya Sharma"
6. Click "Save Changes"
7. (Optional) Click "Export" to download JSON

### View Past Jobs
1. Click "History" tab
2. View list of all jobs
3. Click "View Results" on completed jobs
4. Click "Refresh" to reload

---

## Quick Stats

| Feature | Count |
|---------|-------|
| Total Tabs | 6 |
| Media Types | 4 (Document, Audio, Video, CDR) |
| Supported Languages | 11 |
| Max File Sizes | 50MB-500MB |
| New Components | 7 |

---

## Status Indicators

| Status | Color | Icon |
|--------|-------|------|
| Queued | 🟡 Yellow | ⏱️ Clock |
| Processing | 🔵 Blue | ⏳ Spinner |
| Completed | 🟢 Green | ✅ Check |
| Failed | 🔴 Red | ❌ X |

---

## Backend Requirements

### Endpoints Needed
1. `POST /api/v1/media/upload` - Upload any media
2. `GET /api/v1/media/status/{job_id}` - Poll status
3. `GET /api/v1/analyst/jobs` - Get past jobs

### Processing Services Needed
1. **Document Processor** - Extract text, detect language, summarize
2. **Audio Processor** - Transcribe (with language), translate, summarize
3. **Video Processor** - Extract audio → transcribe → translate → summarize
4. **CDR Processor** - Parse CSV, analyze patterns, generate graph

---

## Next Steps for Development

### Priority 1: Backend Implementation
- [ ] Create `/api/v1/media/upload` endpoint
- [ ] Implement Redis queue with BullMQ
- [ ] Create worker services for each media type
- [ ] Add status polling endpoint

### Priority 2: Database
- [ ] Create `media_items` table
- [ ] Create `suspects` table (optional - currently frontend only)
- [ ] Create `jobs` table for history

### Priority 3: Enhancements
- [ ] WebSocket for real-time updates
- [ ] Batch upload support
- [ ] Advanced search
- [ ] Export reports

---

## Testing Checklist

- [ ] Upload PDF document
- [ ] Upload audio with Hindi language
- [ ] Upload video with Tamil language
- [ ] Upload CDR CSV file
- [ ] Add suspect with default fields
- [ ] Add suspect with custom fields
- [ ] Remove field from suspect
- [ ] Delete suspect
- [ ] Export suspects to JSON
- [ ] Import suspects from JSON
- [ ] View past jobs
- [ ] Refresh past jobs
- [ ] Switch between tabs
- [ ] Check mobile responsiveness
