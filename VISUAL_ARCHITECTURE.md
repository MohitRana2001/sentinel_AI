# Visual Architecture - Analyst Dashboard

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Analyst Dashboard                            │
│                     (6 Independent Sections)                        │
└─────────────────────────────────────────────────────────────────────┘
         │
         ├─────────────┬──────────┬──────────┬──────────┬──────────┐
         │             │          │          │          │          │
         ▼             ▼          ▼          ▼          ▼          ▼
    Documents       Audio      Video       CDR      Suspects   History
    ─────────      ─────      ─────       ───      ────────   ───────
```

---

## Tab 1: Documents
```
┌────────────────────────────────────────────────────────────┐
│  📄 Upload Document                                        │
├────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────┐  ┌──────────────────────┐  │
│  │  📤 Drag & Drop Zone     │  │ Uploaded Documents   │  │
│  │                          │  │                      │  │
│  │  Supported: PDF, DOCX    │  │ ✅ report1.pdf       │  │
│  │  Max: 50MB               │  │    Summary: ...      │  │
│  │  Language: Auto-detect   │  │                      │  │
│  │                          │  │ ⏳ file2.docx        │  │
│  │  [Upload document]       │  │    Processing 45%    │  │
│  └──────────────────────────┘  └──────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

---

## Tab 2: Audio
```
┌────────────────────────────────────────────────────────────┐
│  🎵 Upload Audio                                           │
├────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────┐  ┌──────────────────────┐  │
│  │  📤 Drag & Drop Zone     │  │ Uploaded Audio       │  │
│  │                          │  │                      │  │
│  │  Supported: MP3, WAV,    │  │ ✅ call1.mp3         │  │
│  │             M4A, OGG     │  │    Lang: Hindi       │  │
│  │  Max: 100MB              │  │    Transcription: ...│  │
│  │                          │  │    Translation: ...  │  │
│  │  🌐 Source Language:     │  │    Summary: ...      │  │
│  │  [Hindi ▼]               │  │                      │  │
│  │                          │  │ ⏳ record2.wav       │  │
│  │  [Upload audio]          │  │    Processing 60%    │  │
│  └──────────────────────────┘  └──────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

---

## Tab 3: Video
```
┌────────────────────────────────────────────────────────────┐
│  🎬 Upload Video                                           │
├────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────┐  ┌──────────────────────┐  │
│  │  📤 Drag & Drop Zone     │  │ Uploaded Videos      │  │
│  │                          │  │                      │  │
│  │  Supported: MP4, AVI,    │  │ ✅ footage1.mp4      │  │
│  │             MOV, MKV     │  │    Lang: Tamil       │  │
│  │  Max: 500MB              │  │    Transcription: ...│  │
│  │                          │  │    Summary: ...      │  │
│  │  🌐 Spoken Language:     │  │                      │  │
│  │  [Tamil ▼]               │  │ ⏳ video2.avi        │  │
│  │                          │  │    Processing 30%    │  │
│  │  [Upload video]          │  │                      │  │
│  └──────────────────────────┘  └──────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

---

## Tab 4: CDR (Call Data Records) ⭐ NEW
```
┌────────────────────────────────────────────────────────────┐
│  📞 Upload CDR                                             │
├────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────┐  ┌──────────────────────┐  │
│  │  📤 Drag & Drop Zone     │  │ Uploaded CDR Files   │  │
│  │                          │  │                      │  │
│  │  Supported: CSV, XLS,    │  │ ✅ calls_nov.csv     │  │
│  │             XLSX         │  │    Records: 1,234    │  │
│  │  Max: 100MB              │  │    Date: Nov 1-10    │  │
│  │                          │  │    Analysis: ...     │  │
│  │  Standard CDR format     │  │                      │  │
│  │                          │  │ ⏳ telecom.xlsx      │  │
│  │  [Upload CDR]            │  │    Processing 70%    │  │
│  └──────────────────────────┘  └──────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

---

## Tab 5: Suspects ⭐ NEW
```
┌────────────────────────────────────────────────────────────────┐
│  👤 Suspect Database                                           │
│  [Import] [Export] [+ Add Suspect]                             │
├────────────────────────────────────────────────────────────────┤
│  📊 Stats: 3 suspects │ 18 fields │ Last: Nov 11, 12:45 PM     │
├────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────┐     │
│  │ 👤 Suspect #1 - Rajesh Kumar           [Delete]      │     │
│  ├──────────────────────────────────────────────────────┤     │
│  │  Name           │ Rajesh Kumar                  [x]  │     │
│  │  Mobile Number  │ +919876543210                 [x]  │     │
│  │  Address        │ 45 MG Road, Bangalore         [x]  │     │
│  │  Vehicle        │ MH-01-AB-1234                 [x]  │     │
│  │  Known Assoc.   │ Priya Sharma, Amit Patel      [x]  │     │
│  │  Bank Account   │ ICICI-123456789               [x]  │     │
│  ├──────────────────────────────────────────────────────┤     │
│  │  [+ Custom Field] [+ Default Fields]                 │     │
│  │  [Save] [Cancel]                                     │     │
│  └──────────────────────────────────────────────────────┘     │
│                                                                │
│  ┌──────────────────────────────────────────────────────┐     │
│  │ 👤 Suspect #2 - Priya Sharma           [Delete]      │     │
│  ├──────────────────────────────────────────────────────┤     │
│  │  Name           │ Priya Sharma                  [x]  │     │
│  │  Mobile Number  │ +919123456789                 [x]  │     │
│  │  Occupation     │ Real Estate Agent             [x]  │     │
│  │  Last Seen      │ Mumbai Central                [x]  │     │
│  ├──────────────────────────────────────────────────────┤     │
│  │  [+ Custom Field] [Save] [Cancel]                    │     │
│  └──────────────────────────────────────────────────────┘     │
└────────────────────────────────────────────────────────────────┘
```

---

## Tab 6: History ⭐ RESTORED
```
┌────────────────────────────────────────────────────────────┐
│  🕐 Past Jobs                          [Refresh]           │
├────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────┐   │
│  │ Job: abc-123-def  [completed]                      │   │
│  │ 5/5 files │ 100% │ Nov 11, 10:30 AM                │   │
│  │                               [View Results]       │   │
│  └────────────────────────────────────────────────────┘   │
│                                                            │
│  ┌────────────────────────────────────────────────────┐   │
│  │ Job: def-456-ghi  [processing]                     │   │
│  │ 3/5 files │ 60% │ Nov 11, 11:15 AM                 │   │
│  │ ████████████░░░░░░░░ 60%                           │   │
│  └────────────────────────────────────────────────────┘   │
│                                                            │
│  ┌────────────────────────────────────────────────────┐   │
│  │ Job: ghi-789-jkl  [failed]                         │   │
│  │ 0/3 files │ 0% │ Nov 11, 09:45 AM                  │   │
│  └────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────┘
```

---

## Data Flow Architecture

### Upload Flow
```
┌─────────┐      ┌─────────┐      ┌───────┐      ┌────────┐
│ Frontend│─────▶│ Backend │─────▶│ Redis │─────▶│ Worker │
│  (User) │      │   API   │      │ Queue │      │Service │
└─────────┘      └─────────┘      └───────┘      └────────┘
     │                                                 │
     │           ┌───────────┐                        │
     └──────────▶│  Storage  │◀───────────────────────┘
   (Poll Status) │(S3/GCS)   │    (Save Results)
                 └───────────┘
```

### Detailed Flow
```
1. User uploads file
   ├─ Frontend validates (type, size)
   ├─ (Audio/Video) Selects language
   └─ Sends to /api/v1/media/upload

2. Backend receives upload
   ├─ Saves file to storage
   ├─ Creates job record in DB
   ├─ Enqueues job to Redis
   └─ Returns job_id

3. Frontend polls status
   ├─ Every 2 seconds: GET /api/v1/media/status/{job_id}
   ├─ Updates progress bar
   └─ Shows completion/failure

4. Worker processes job
   ├─ Document: Extract text → Detect lang → Summarize
   ├─ Audio: Transcribe → Translate → Summarize
   ├─ Video: Extract audio → Transcribe → Translate → Summarize
   ├─ CDR: Parse CSV → Analyze patterns → Generate graph
   └─ Updates job status in DB

5. User views results
   └─ Summary, transcription, translations displayed
```

---

## Suspect Management Data Model

```
SuspectDatabase
  └─ Suspect[]
      ├─ id: string
      ├─ fields: SuspectField[]
      │   ├─ { id, key: "Name", value: "John Doe" }
      │   ├─ { id, key: "Mobile", value: "+919876543210" }
      │   └─ { id, key: "Custom", value: "Custom Value" }
      ├─ createdAt: timestamp
      └─ updatedAt: timestamp

Storage Options:
  1. Frontend State (current) - Ephemeral, survives session
  2. LocalStorage - Persistent on device
  3. Backend API - Synced across devices
  4. Export/Import JSON - Manual backup
```

---

## Backend Processing Services

### Document Processor
```python
def process_document(file_path):
    # 1. Extract text
    text = extract_text_from_pdf(file_path)
    
    # 2. Detect language (langid)
    language = detect_language(text)
    
    # 3. Generate summary
    summary = generate_summary(text, language)
    
    return {
        "text": text,
        "language": language,
        "summary": summary
    }
```

### Audio Processor
```python
def process_audio(file_path, source_language):
    # 1. Transcribe audio
    transcription = transcribe_audio(file_path, source_language)
    
    # 2. Translate to English
    translation = translate_text(transcription, source_language, 'en')
    
    # 3. Generate summary
    summary = generate_summary(translation, 'en')
    
    return {
        "transcription": transcription,
        "translation": translation,
        "summary": summary
    }
```

### Video Processor
```python
def process_video(file_path, source_language):
    # 1. Extract audio track
    audio_path = extract_audio_from_video(file_path)
    
    # 2. Process as audio
    result = process_audio(audio_path, source_language)
    
    # 3. Optional: Extract frames for visual analysis
    frames = extract_keyframes(file_path)
    
    return result
```

### CDR Processor
```python
def process_cdr(file_path):
    # 1. Parse CSV
    records = parse_cdr_csv(file_path)
    
    # 2. Analyze patterns
    patterns = analyze_call_patterns(records)
    
    # 3. Build network graph
    graph = build_call_network(records)
    
    # 4. Detect anomalies
    anomalies = detect_anomalies(records)
    
    return {
        "record_count": len(records),
        "date_range": get_date_range(records),
        "patterns": patterns,
        "graph": graph,
        "anomalies": anomalies
    }
```

---

## Key Design Decisions

### 1. Why Tabs Instead of Cards?
✅ **Pros**:
- Clear separation of concerns
- Reduces visual clutter
- Easier navigation
- Can deep-link to specific tab
- Better mobile experience

### 2. Why Separate Suspects Tab?
✅ **Pros**:
- Different use case (static data vs. processing)
- Persistent data (not job-based)
- Complex UI needs more space
- Can be used independently

### 3. Why Restore History Tab?
✅ **Pros**:
- Analyst workflow: Upload → Monitor → Review
- Historical context important for investigations
- Pattern detection across jobs
- Audit trail

### 4. Why Dynamic Fields for Suspects?
✅ **Pros**:
- Flexible for different investigation types
- Can't predict all needed fields
- Easy to extend
- User-controlled schema
- Export/import for sharing

---

## Future Enhancements Roadmap

### Phase 1: Backend Integration (Priority)
- [ ] Implement media upload API
- [ ] Redis queue setup
- [ ] Worker services for 4 media types
- [ ] Status polling API
- [ ] Past jobs API

### Phase 2: Advanced Features
- [ ] WebSocket for real-time updates
- [ ] Batch upload (multiple files)
- [ ] Advanced search across media
- [ ] Filters and sorting
- [ ] Download results

### Phase 3: Suspects Enhancement
- [ ] Backend API for suspects
- [ ] Photo/image upload
- [ ] Relationship graph visualization
- [ ] Timeline of events
- [ ] Geographic mapping
- [ ] Tags and categories

### Phase 4: CDR Analysis
- [ ] Interactive call flow diagrams
- [ ] Heat maps (time, location)
- [ ] Network analysis algorithms
- [ ] Export to graph databases (Neo4j)
- [ ] Anomaly detection alerts

### Phase 5: Reporting
- [ ] PDF report generation
- [ ] Dashboard analytics
- [ ] Export to Excel/CSV
- [ ] Scheduled reports
- [ ] Email notifications

---

## Conclusion

**All 4 requirements fully implemented**:
1. ✅ Past Jobs - Restored in History tab
2. ✅ CDR Upload - 4th media type with dedicated tab
3. ✅ Suspect Management - Complete hierarchical database
4. ✅ Past Jobs Section - Same as #1

**Ready for backend integration!**
