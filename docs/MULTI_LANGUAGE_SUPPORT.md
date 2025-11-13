# Multi-Language Support for Audio and Video Processing

## Date: November 14, 2025

## Overview
Updated audio and video processing services to support multiple languages beyond Hindi. The system now uses language metadata passed from the upload endpoint instead of checking filenames.

---

## Changes Made

### 1. Audio Processor Service
**File**: `backend/processors/audio_processor_service.py`

#### What Changed:
- ✅ Now extracts `language` from message metadata
- ✅ Supports all major Indian languages + English
- ✅ Uses language parameter instead of filename checking
- ✅ Updated transcription function with language mapping

#### Language Support Added:
- Hindi (hi/hindi)
- Bengali (bn/bengali)
- Punjabi (pa/punjabi)
- Gujarati (gu/gujarati)
- Kannada (kn/kannada)
- Malayalam (ml/malayalam)
- Marathi (mr/marathi)
- Tamil (ta/tamil)
- Telugu (te/telugu)
- English (en/english)

#### Code Changes:

**Before**:
```python
def _process_single_file(self, message: dict):
    filename = message.get("filename")
    is_hindi = 'hindi' in filename.lower()
    
def process_audio(self, db, job, gcs_path: str):
    is_hindi = 'hindi' in filename.lower()
    
def transcribe_audio(self, file_path: str, filename: str, is_hindi: bool = False):
    lang_hint = "Hindi (Devanagari script)" if is_hindi else "English"
```

**After**:
```python
def _process_single_file(self, message: dict):
    metadata = message.get("metadata", {})
    language = metadata.get("language", None)
    self.process_audio(db, job, gcs_path, language)
    
def process_audio(self, db, job, gcs_path: str, language: str = None):
    if language:
        needs_translation = language.lower() != 'en'
        source_language = language
    else:
        # Backward compatibility: check filename
        is_hindi = 'hindi' in filename.lower()
        needs_translation = is_hindi
        source_language = 'hindi' if is_hindi else 'english'
    
def transcribe_audio(self, file_path: str, filename: str, language: str = "english"):
    language_hints = {
        'hi': 'Hindi (Devanagari script)',
        'bn': 'Bengali (Bangla script)',
        # ... all languages mapped
    }
    lang_hint = language_hints.get(language.lower(), 'English')
```

### 2. Video Processor Service
**File**: `backend/processors/video_processor_service.py`

#### What Changed:
- ✅ Now extracts `language` from message metadata
- ✅ Uses language parameter for translation decisions
- ✅ Backward compatible with filename-based detection

#### Code Changes:

**Before**:
```python
def _process_single_file(self, message: dict):
    filename = message.get("filename")
    
def process_video(self, db, job, gcs_path: str):
    is_hindi = 'hindi' in filename.lower()
    equal_prefix = "===" if is_hindi else "=="
    if is_hindi and analysis != "[ No analysis available ]":
        print(f"Translating analysis from Hindi...")
```

**After**:
```python
def _process_single_file(self, message: dict):
    metadata = message.get("metadata", {})
    language = metadata.get("language", None)
    self.process_video(db, job, gcs_path, language)
    
def process_video(self, db, job, gcs_path: str, language: str = None):
    if language:
        needs_translation = language.lower() != 'en'
        source_language = language
    else:
        # Backward compatibility
        is_hindi = 'hindi' in filename.lower()
        needs_translation = is_hindi
        source_language = 'hindi' if is_hindi else 'english'
    
    equal_prefix = "===" if needs_translation else "=="
    if needs_translation and analysis != "[ No analysis available ]":
        print(f"Translating analysis from {source_language} to English...")
```

---

## How It Works

### Upload Flow:

1. **User uploads file** with language specified:
   ```bash
   POST /api/v1/upload
   files: audio.mp3
   media_types: audio
   languages: hindi  # ← Language specified
   ```

2. **Backend queues file** with metadata:
   ```python
   metadata = {'language': 'hindi'}
   redis_pubsub.push_file_to_queue(
       job_id, gcs_path, filename, 
       settings.REDIS_QUEUE_AUDIO, 
       metadata  # ← Language passed here
   )
   ```

3. **Processor receives** message with language:
   ```python
   {
       "job_id": "...",
       "gcs_path": "...",
       "filename": "audio.mp3",
       "action": "process_file",
       "metadata": {
           "language": "hindi"  # ← Language available here
       }
   }
   ```

4. **Processor uses language** for:
   - Transcription prompts (Gemini/Gemma)
   - Translation decisions
   - File naming conventions

---

## Backward Compatibility

The changes maintain backward compatibility:

### If language is provided:
```python
metadata = {'language': 'bengali'}
# Uses 'bengali' for transcription and translation
```

### If language is NOT provided:
```python
metadata = {}
# Falls back to filename checking:
# - If 'hindi' in filename → treat as Hindi
# - Otherwise → treat as English
```

---

## File Naming Convention

The naming convention remains the same:

### Two Equal Signs (==):
- Used for: English or transcription-only files
- Files created:
  - `audio.mp3==transcription.txt`
  - `audio.mp3==summary.txt`

### Three Equal Signs (===):
- Used for: Non-English files requiring translation
- Files created:
  - `audio.mp3===transcription.txt` (original language)
  - `audio.mp3===translated.txt` (English translation)
  - `audio.mp3===summary.txt` (summary of translated text)

---

## Language Code Mapping

The system accepts both ISO codes and full language names:

| ISO Code | Full Name | Script |
|----------|-----------|--------|
| hi | hindi | Devanagari |
| bn | bengali | Bangla |
| pa | punjabi | Gurmukhi |
| gu | gujarati | Gujarati |
| kn | kannada | Kannada |
| ml | malayalam | Malayalam |
| mr | marathi | Devanagari |
| ta | tamil | Tamil |
| te | telugu | Telugu |
| en | english | Latin |

---

## Testing

### Test 1: Upload Hindi Audio
```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -F "files=@audio_hindi.mp3" \
  -F "media_types=audio" \
  -F "languages=hindi" \
  -F "case_name=Test" \
  -H "Authorization: Bearer TOKEN"
```

**Expected**:
- Transcription uses: "Hindi (Devanagari script)"
- Translation: Yes
- Files: `===transcription.txt`, `===translated.txt`, `===summary.txt`

### Test 2: Upload Bengali Video
```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -F "files=@video_bengali.mp4" \
  -F "media_types=video" \
  -F "languages=bengali" \
  -F "case_name=Test" \
  -H "Authorization: Bearer TOKEN"
```

**Expected**:
- Analysis in Bengali context
- Translation: Yes (Bengali → English)
- Files: `===analysis.txt`, `===translated.txt`, `===summary.txt`

### Test 3: Upload English Audio (Backward Compatible)
```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -F "files=@audio_english.mp3" \
  -F "media_types=audio" \
  -F "case_name=Test" \
  -H "Authorization: Bearer TOKEN"
```

**Expected**:
- No language specified → defaults to English
- Translation: No
- Files: `==transcription.txt`, `==summary.txt`

---

## Frontend Changes Needed

### Upload Form
The frontend should allow users to select language:

```tsx
<select name="language">
  <option value="en">English</option>
  <option value="hi">Hindi</option>
  <option value="bn">Bengali</option>
  <option value="pa">Punjabi</option>
  <option value="gu">Gujarati</option>
  <option value="kn">Kannada</option>
  <option value="ml">Malayalam</option>
  <option value="mr">Marathi</option>
  <option value="ta">Tamil</option>
  <option value="te">Telugu</option>
</select>
```

### API Call
```javascript
const formData = new FormData();
formData.append('files', audioFile);
formData.append('media_types', 'audio');
formData.append('languages', selectedLanguage); // ← Add language
formData.append('case_name', caseName);

await fetch('/api/v1/upload', {
  method: 'POST',
  body: formData,
  headers: { 'Authorization': `Bearer ${token}` }
});
```

---

## Benefits

1. **Multi-Language Support**: 
   - No longer limited to Hindi
   - Supports all major Indian languages
   - Easy to add more languages

2. **Better User Experience**:
   - Users explicitly select language
   - No reliance on filename conventions
   - Clear language identification

3. **Backward Compatible**:
   - Old uploads still work (filename-based)
   - No breaking changes
   - Gradual migration path

4. **Maintainable**:
   - Centralized language mapping
   - Easy to add new languages
   - Clear code structure

---

## Future Enhancements

1. **Automatic Language Detection**:
   - Use Gemini/AI to detect language from audio/video
   - Fallback when user doesn't specify

2. **Language-Specific Prompts**:
   - Optimize transcription prompts per language
   - Better accuracy for specific scripts

3. **Multi-Language Output**:
   - Option to keep original language summary
   - Side-by-side original + English

4. **Language Confidence Scores**:
   - Track confidence in language detection
   - Alert if mismatch detected

---

## Summary

✅ **Audio Processor**: Now supports all major Indian languages  
✅ **Video Processor**: Language-aware analysis and translation  
✅ **Backward Compatible**: Old filename-based detection still works  
✅ **Metadata-Driven**: Uses language from upload metadata  
✅ **Easy to Extend**: Simple to add new languages  

**Next Steps**:
1. Update frontend to include language selector
2. Test with various language audio/video files
3. Monitor translation quality per language
4. Consider automatic language detection
