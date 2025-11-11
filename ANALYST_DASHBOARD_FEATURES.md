# Analyst Dashboard - Complete Feature Set

## Overview
The Analyst Dashboard now includes **6 main sections** with comprehensive functionality for intelligence gathering and analysis.

---

## 1. Documents Tab 📄

### Features
- Upload PDF, DOCX files (max 50MB)
- **Automatic language detection** using langid
- No manual language selection needed
- Real-time processing status
- Summary generation

### Use Case
Upload investigation reports, legal documents, case files for automated analysis.

---

## 2. Audio Tab 🎵

### Features
- Upload MP3, WAV, M4A, OGG files (max 100MB)
- **Required language selection** from dropdown
- Transcription in source language
- Translation to English
- Summary generation

### Supported Languages
All 11 languages from `document_processor.py`:
- Hindi (hi), Bengali (bn), Punjabi (pa)
- Gujarati (gu), Kannada (kn), Malayalam (ml)
- Marathi (mr), Tamil (ta), Telugu (te)
- Chinese Simplified (zh), English (en)

### Use Case
Upload intercepted calls, voice recordings, interviews for transcription and analysis.

---

## 3. Video Tab 🎬

### Features
- Upload MP4, AVI, MOV, MKV files (max 500MB)
- **Required language selection** from dropdown
- Audio extraction → Transcription
- Translation to English
- Summary generation

### Use Case
Upload surveillance footage, interrogation videos, CCTV recordings with audio for analysis.

---

## 4. CDR Tab 📞 (NEW)

### Features
- Upload CSV, XLS, XLSX files (max 100MB)
- Standard telecom CDR format
- Call pattern analysis
- Network mapping
- Frequency analysis

### Expected CDR Format
```csv
caller_number,receiver_number,call_time,duration,location,cell_tower_id
+919876543210,+919123456789,2024-11-11 10:30:00,120,Mumbai,TOWER_001
```

### Use Case
Upload call data records for link analysis, pattern detection, and network visualization.

---

## 5. Suspects Tab 👤 (NEW)

### Features

#### Dynamic Field Management
- **Add unlimited suspects**
- **Customizable fields** - add/remove any field
- **Default fields provided**: Name, Address, Mobile Number, Email, DOB, Occupation
- **All fields removable** - complete flexibility

#### Hierarchical Structure
```
Suspect #1
  ├── Field: Name → "John Doe"
  ├── Field: Address → "123 Main St"
  ├── Field: Mobile → "+919876543210"
  ├── Field: Known Associates → "Jane Smith, Bob Johnson"
  └── Field: [Custom] → [Custom Value]
```

#### Operations
- **Add Suspect**: Creates new suspect card
- **Add Custom Field**: Add any key-value pair
- **Add Default Fields**: Quickly add standard fields
- **Remove Field**: Delete any field (including defaults)
- **Delete Suspect**: Remove entire suspect record
- **Save Changes**: Persist modifications
- **Cancel**: Discard unsaved changes

#### Import/Export
- **Export**: Download all suspects as JSON
- **Import**: Upload previously exported JSON file
- **Format**:
```json
{
  "suspects": [
    {
      "id": "suspect-1699123456",
      "fields": [
        { "id": "field-1", "key": "Name", "value": "John Doe" },
        { "id": "field-2", "key": "Mobile Number", "value": "+919876543210" }
      ],
      "createdAt": "2024-11-11T10:30:00.000Z",
      "updatedAt": "2024-11-11T12:45:00.000Z"
    }
  ]
}
```

### Use Case Examples

#### Example 1: Basic Suspect
```
Suspect #1
  Name: Rajesh Kumar
  Address: 45 MG Road, Bangalore
  Mobile Number: +919876543210
  Email: rajesh.k@example.com
  Occupation: Business Owner
```

#### Example 2: Extended Details
```
Suspect #2
  Name: Priya Sharma
  Alias: PS, Priya S
  Mobile Number: +919123456789
  Alternate Mobile: +919987654321
  Email: priya@example.com
  Address: 78 Park Street, Kolkata
  Known Associates: Rajesh Kumar, Amit Patel
  Vehicle Number: MH-01-AB-1234
  Bank Account: ICICI-123456789
  Last Known Location: Mumbai Central
  Date of Birth: 1985-03-15
  Occupation: Real Estate Agent
  Criminal Record: None
  Notes: Frequent caller to suspect #1
```

### Statistics Dashboard
- **Total Suspects**: Count of all suspects
- **Total Fields**: Sum of all fields across suspects
- **Last Updated**: Most recent modification timestamp

---

## 6. History Tab 🕐 (RESTORED)

### Features
- **Past Jobs List**: All previous processing jobs
- **Job Details**:
  - Job ID (code format)
  - Status badge (completed, processing, failed, queued)
  - File count (processed/total)
  - Progress percentage
  - Created timestamp (IST timezone)
- **Actions**:
  - View Results (for completed jobs)
  - Refresh list
- **Auto-load**: Loads on dashboard mount

### Use Case
Track processing history, revisit old analyses, monitor job progress.

---

## Technical Architecture

### Component Structure
```
AnalystDashboard
├── MediaUploadCard (Documents, Audio, Video, CDR)
│   ├── Drag & Drop Zone
│   ├── Language Selector (conditional)
│   └── Upload Button
├── SuspectManagement
│   ├── SuspectCard[]
│   │   ├── Field Editor
│   │   └── Action Buttons
│   ├── Import/Export
│   └── Statistics
└── PastJobsList
    └── JobCard[]
```

### Data Flow

#### Upload Flow
```
User selects file
  → Validates (type, size)
  → (Audio/Video) Selects language
  → Upload to /api/v1/media/upload
  → Receives job_id
  → Adds to mediaItems state
  → Polls /api/v1/media/status/{job_id}
  → Updates status/progress every 2s
  → Displays summary on completion
```

#### Suspect Management Flow
```
Add Suspect
  → Create suspect card
  → Add fields (custom or default)
  → Edit key-value pairs
  → Remove unwanted fields
  → Save changes
  → Export to JSON (optional)
```

---

## State Management

### Auth Context State
```typescript
{
  mediaItems: MediaItem[] // All uploaded media
  uploadMedia: (file, type, lang?) => Promise<void>
  // ... other auth state
}
```

### Local Component State
```typescript
// Analyst Dashboard
{
  activeTab: 'document' | 'audio' | 'video' | 'cdr' | 'suspects' | 'history'
  uploading: { document: bool, audio: bool, video: bool, cdr: bool }
  pastJobs: Job[]
  loadingJobs: boolean
}

// Suspect Management
{
  suspects: Suspect[]
}

// Each Suspect
{
  fields: SuspectField[]
  isEditing: boolean
}
```

---

## API Endpoints Required

### Media Upload
```
POST /api/v1/media/upload
- Body: FormData { file, media_type, language? }
- Response: { media_id, job_id, status }
```

### Job Status
```
GET /api/v1/media/status/{job_id}
- Response: { status, progress, summary?, transcription? }
```

### Past Jobs
```
GET /api/v1/analyst/jobs?limit=15&offset=0
- Response: Job[]
```

---

## File Validations

| Media Type | Formats | Max Size | Language |
|------------|---------|----------|----------|
| Document | PDF, DOCX | 50 MB | Auto-detect |
| Audio | MP3, WAV, M4A, OGG | 100 MB | Required |
| Video | MP4, AVI, MOV, MKV | 500 MB | Required |
| CDR | CSV, XLS, XLSX | 100 MB | N/A |

---

## UI Components Used

- **Tabs**: `@radix-ui/react-tabs`
- **Select**: `@radix-ui/react-select`
- **Label**: `@radix-ui/react-label`
- **Card, Button, Input**: Custom components
- **Icons**: `lucide-react`
- **Toast**: Custom hook

---

## Keyboard Shortcuts (Suggested)

- `Ctrl+1-6`: Switch tabs
- `Ctrl+S`: Save suspect changes
- `Ctrl+N`: Add new suspect
- `Ctrl+F`: Add new field
- `Esc`: Cancel editing

---

## Mobile Responsiveness

- **Desktop**: 2-column grid (upload + list)
- **Tablet**: Stacked layout
- **Mobile**: Single column, scrollable tabs

---

## Security Considerations

### Data Privacy
- Suspects data stored in component state (not persisted by default)
- Export requires explicit user action
- Import validates JSON structure
- No automatic cloud sync

### File Upload
- Client-side validation before upload
- Server-side validation required
- File type whitelisting
- Size limits enforced

---

## Future Enhancements

### Suspects Tab
- [ ] Database persistence
- [ ] Photo upload for suspects
- [ ] Relationship mapping (graphs)
- [ ] Timeline of events
- [ ] Search and filter
- [ ] Tags/categories
- [ ] Bulk import from CSV

### CDR Tab
- [ ] Visual call flow diagram
- [ ] Heat map of call patterns
- [ ] Geographic visualization
- [ ] Anomaly detection
- [ ] Export to Neo4j graph

### General
- [ ] WebSocket for real-time updates (replace polling)
- [ ] Batch upload (multiple files)
- [ ] Advanced search across all media
- [ ] AI-powered insights dashboard
- [ ] PDF report generation

---

## Summary of Changes from Previous Version

### ✅ Restored
1. **Past Jobs Section** - Now in dedicated "History" tab

### ➕ Added
1. **CDR Upload Tab** - 4th media type for call data records
2. **Suspects Management Tab** - Complete suspect database with dynamic fields
3. **6-tab Navigation** - Document, Audio, Video, CDR, Suspects, History

### 🔧 Enhanced
1. **Flexible Field System** - Add/remove any field in suspects
2. **Default Field Templates** - Quick start with common fields
3. **Import/Export** - JSON-based data portability
4. **Statistics Dashboard** - Overview of suspect database

### 📋 Maintained
1. All existing upload functionality
2. Language selection for audio/video
3. Auto-detection for documents
4. Progress tracking
5. Status indicators

---

## Questions Answered

### Q1: Have you removed past jobs?
**A**: Yes, but now **RESTORED** in a dedicated "History" tab with the same functionality.

### Q2: Add CDR component?
**A**: ✅ **DONE** - 4th tab added for Call Data Record uploads (CSV/XLS/XLSX format).

### Q3: Suspect details form with dynamic fields?
**A**: ✅ **DONE** - Complete suspect management system with:
- Unlimited suspects
- Fully customizable fields (add/remove any key-value)
- Default field templates
- Hierarchical structure
- Import/Export capability

### Q4: Bring back past jobs?
**A**: ✅ **DONE** - Restored in "History" tab with all original features.

---

## Installation

Already installed dependencies:
```bash
npm install @radix-ui/react-tabs @radix-ui/react-select @radix-ui/react-label --legacy-peer-deps
```

No additional packages needed!
