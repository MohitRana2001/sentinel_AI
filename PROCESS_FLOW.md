# Sentinel AI - Detailed Process Flow Documentation

This document provides comprehensive process flow diagrams and explanations for all processing scenarios in Sentinel AI.

## Table of Contents

- [Document Processing Flows](#document-processing-flows)
- [Audio Processing Flows](#audio-processing-flows)
- [Video Processing Flows](#video-processing-flows)
- [Graph Processing Flow](#graph-processing-flow)
- [Model Selection Decision Trees](#model-selection-decision-trees)
- [Error Handling Flows](#error-handling-flows)

## Document Processing Flows

### English PDF Processing

```mermaid
flowchart TD
    Start([User uploads English PDF]) --> Validate[Validate file size & type]
    Validate --> Store[Store in GCS/Local]
    Store --> CreateJob[Create ProcessingJob<br/>status=QUEUED]
    CreateJob --> PushQueue[Push to document_queue]
    
    PushQueue --> Worker[Document Worker picks up]
    Worker --> Download[Download PDF]
    Download --> Docling[Docling OCR Processing]
    Docling --> |Uses Tesseract| ExtractText[Extract text with layout]
    ExtractText --> DetectLang[Language Detection<br/>langid.classify]
    DetectLang --> |en detected| NoTranslation[Skip translation]
    NoTranslation --> Summary[Generate Summary<br/>Gemini/Gemma3:1b]
    Summary --> SaveFiles[Save files:<br/>--extracted.md<br/>--summary.txt]
    SaveFiles --> CreateDoc[Create Document record in DB]
    CreateDoc --> Vectorize[Chunk & Vectorize text<br/>EmbeddingGemma]
    Vectorize --> SaveChunks[Save chunks to AlloyDB]
    SaveChunks --> QueueGraph[Push to graph_queue]
    QueueGraph --> UpdateJob[Update job.processed_files]
    UpdateJob --> End([Processing Complete])
```

### Hindi PDF Processing

```mermaid
flowchart TD
    Start([User uploads Hindi PDF]) --> Validate[Validate file size & type]
    Validate --> Store[Store in GCS/Local]
    Store --> CreateJob[Create ProcessingJob<br/>status=QUEUED]
    CreateJob --> PushQueue[Push to document_queue]
    
    PushQueue --> Worker[Document Worker picks up]
    Worker --> Download[Download PDF]
    Download --> Docling[Docling OCR Processing]
    Docling --> |Tesseract with hin| ExtractText[Extract Hindi text]
    ExtractText --> DetectLang[Language Detection<br/>langid.classify]
    DetectLang --> |hi detected| TranslateJSON[JSON-based Translation]
    TranslateJSON --> |M2M100 hi→en| TranslatedText[English text]
    TranslatedText --> Summary[Generate Summary<br/>Gemini/Gemma3:1b<br/>on English text]
    Summary --> SaveFiles[Save files:<br/>---extracted.md Hindi<br/>---translated.md English<br/>---summary.txt English]
    SaveFiles --> CreateDoc[Create Document record]
    CreateDoc --> Vectorize[Vectorize English text<br/>EmbeddingGemma]
    Vectorize --> SaveChunks[Save chunks to AlloyDB]
    SaveChunks --> QueueGraph[Push translated text<br/>to graph_queue]
    QueueGraph --> UpdateJob[Update job.processed_files]
    UpdateJob --> End([Processing Complete])
```

### TXT File Processing

```mermaid
flowchart TD
    Start([User uploads TXT file]) --> Validate[Validate file size & type]
    Validate --> Store[Store in GCS/Local]
    Store --> CreateJob[Create ProcessingJob<br/>status=QUEUED]
    CreateJob --> PushQueue[Push to document_queue]
    
    PushQueue --> Worker[Document Worker picks up]
    Worker --> Download[Download TXT]
    Download --> ReadFile[Read file<br/>UTF-8→Latin-1→CP1252]
    ReadFile --> DetectLang[Language Detection<br/>langid.classify]
    
    DetectLang --> IsEnglish{English?}
    IsEnglish --> |Yes| NoTranslation[Skip translation]
    IsEnglish --> |No| Translate[M2M100 Translation]
    
    Translate --> TranslatedText[English text]
    NoTranslation --> Summary[Generate Summary]
    TranslatedText --> Summary
    
    Summary --> SaveFiles[Save files with<br/>--/--- naming]
    SaveFiles --> CreateDoc[Create Document record]
    CreateDoc --> Vectorize[Vectorize text]
    Vectorize --> SaveChunks[Save chunks]
    SaveChunks --> QueueGraph[Push to graph_queue]
    QueueGraph --> UpdateJob[Update job.processed_files]
    UpdateJob --> End([Processing Complete])
```

### DOCX File Processing

```mermaid
flowchart TD
    Start([User uploads DOCX]) --> Validate[Validate file size & type]
    Validate --> Store[Store in GCS/Local]
    Store --> CreateJob[Create ProcessingJob<br/>status=QUEUED]
    CreateJob --> PushQueue[Push to document_queue]
    
    PushQueue --> Worker[Document Worker picks up]
    Worker --> Download[Download DOCX]
    Download --> Docling[Docling Document Processing]
    Docling --> ExtractText[Extract text with formatting]
    ExtractText --> DetectLang[Language Detection]
    
    DetectLang --> IsEnglish{English?}
    IsEnglish --> |Yes| NoTranslation[Skip translation]
    IsEnglish --> |No| TranslateJSON[JSON-based Translation<br/>Preserves structure]
    
    TranslateJSON --> TranslatedMD[Translated Markdown]
    NoTranslation --> Summary[Generate Summary]
    TranslatedMD --> Summary
    
    Summary --> SaveFiles[Save files:<br/>Extracted MD<br/>Translated MD if needed<br/>Summary TXT]
    SaveFiles --> CreateDoc[Create Document record]
    CreateDoc --> Vectorize[Vectorize text]
    Vectorize --> SaveChunks[Save chunks]
    SaveChunks --> QueueGraph[Push to graph_queue]
    QueueGraph --> UpdateJob[Update job.processed_files]
    UpdateJob --> End([Processing Complete])
```

## Audio Processing Flows

### English Audio Processing (Dev Mode)

```mermaid
flowchart TD
    Start([User uploads English MP3]) --> Validate[Validate file size & type]
    Validate --> Store[Store in GCS/Local]
    Store --> CreateJob[Create ProcessingJob<br/>status=QUEUED]
    CreateJob --> PushQueue[Push to audio_queue]
    
    PushQueue --> Worker[Audio Worker picks up]
    Worker --> Download[Download MP3]
    Download --> CheckMode{Dev Mode?}
    CheckMode --> |Yes<br/>USE_GEMINI_FOR_DEV=true| GeminiTranscribe[Google Gemini 2.0 Flash<br/>Audio Transcription]
    CheckMode --> |No| GemmaTranscribe[Gemma3:12b Multimodal<br/>Transcription TODO]
    
    GeminiTranscribe --> Transcription[English transcription text]
    GemmaTranscribe --> Transcription
    
    Transcription --> CheckFilename{Filename<br/>contains 'hindi'?}
    CheckFilename --> |No| NoTranslation[Skip translation]
    CheckFilename --> |Yes| Translate[M2M100 Translation]
    
    NoTranslation --> Summary[Generate Summary<br/>Gemini/Gemma3:1b]
    Translate --> Summary
    
    Summary --> SaveFiles[Save files:<br/>==transcription.txt<br/>==summary.txt]
    SaveFiles --> CreateDoc[Create Document record<br/>type=AUDIO]
    CreateDoc --> Vectorize[Vectorize transcription]
    Vectorize --> SaveChunks[Save chunks to AlloyDB]
    SaveChunks --> QueueGraph[Push to graph_queue]
    QueueGraph --> UpdateJob[Update job.processed_files]
    UpdateJob --> End([Processing Complete])
```

### Hindi Audio Processing (Dev Mode)

```mermaid
flowchart TD
    Start([User uploads hindi_audio.mp3]) --> Validate[Validate file size & type]
    Validate --> Store[Store in GCS/Local]
    Store --> CreateJob[Create ProcessingJob<br/>status=QUEUED]
    CreateJob --> PushQueue[Push to audio_queue]
    
    PushQueue --> Worker[Audio Worker picks up]
    Worker --> Download[Download MP3]
    Download --> GeminiTranscribe[Google Gemini 2.0 Flash<br/>Audio Transcription<br/>with Hindi prompt]
    
    GeminiTranscribe --> HindiTranscription[Hindi transcription text]
    HindiTranscription --> CheckFilename{Filename<br/>contains 'hindi'?}
    CheckFilename --> |Yes| Translate[M2M100 Translation<br/>Hindi → English]
    
    Translate --> EnglishText[English text]
    EnglishText --> Summary[Generate English Summary<br/>Gemini/Gemma3:1b]
    
    Summary --> SaveFiles[Save files:<br/>===transcription.txt Hindi<br/>===translated.txt English<br/>===summary.txt English]
    SaveFiles --> CreateDoc[Create Document record<br/>type=AUDIO]
    CreateDoc --> Vectorize[Vectorize English text<br/>for searchability]
    Vectorize --> SaveChunks[Save chunks to AlloyDB]
    SaveChunks --> QueueGraph[Push translated text<br/>to graph_queue]
    QueueGraph --> UpdateJob[Update job.processed_files]
    UpdateJob --> End([Processing Complete])
```

### Audio Processing (Production Mode)

```mermaid
flowchart TD
    Start([Audio file uploaded]) --> Validate[Validate file size & type]
    Validate --> Store[Store in GCS/Local]
    Store --> CreateJob[Create ProcessingJob]
    CreateJob --> PushQueue[Push to audio_queue]
    
    PushQueue --> Worker[Audio Worker picks up]
    Worker --> Download[Download audio]
    Download --> CheckMode{Dev Mode?}
    CheckMode --> |No| GemmaCheck[Gemma3:12b Multimodal]
    GemmaCheck --> |Not Implemented| Placeholder[Return placeholder text:<br/>'Audio transcription pending']
    
    CheckMode --> |Yes| GeminiAPI[Use Gemini API]
    GeminiAPI --> Transcription[Get transcription]
    Transcription --> Process[Continue normal flow]
    
    Placeholder --> SavePlaceholder[Save placeholder<br/>as transcription]
    SavePlaceholder --> CreateDoc[Create Document record]
    CreateDoc --> End([Partial Complete<br/>Awaiting implementation])
```

## Video Processing Flows

### English Video Processing

```mermaid
flowchart TD
    Start([User uploads surveillance.mp4]) --> Validate[Validate file size & type]
    Validate --> Store[Store in GCS/Local]
    Store --> CreateJob[Create ProcessingJob<br/>status=QUEUED]
    CreateJob --> PushQueue[Push to video_queue]
    
    PushQueue --> Worker[Video Worker picks up]
    Worker --> Download[Download MP4]
    Download --> ExtractFrames[Extract frames at 0.3 fps<br/>1 frame every ~3 seconds<br/>using MoviePy]
    
    ExtractFrames --> Frames[JPEG frames saved<br/>to temp directory]
    Frames --> EncodeFrames[Base64 encode all frames]
    EncodeFrames --> VisionLLM[Gemma3:4b Vision LLM<br/>via LangChain]
    
    VisionLLM --> |CCTV analysis prompt| Analysis[Detailed analysis:<br/>• People & activities<br/>• Vehicles<br/>• Timeline<br/>• Suspicious events]
    
    Analysis --> CheckFilename{Filename<br/>contains 'hindi'?}
    CheckFilename --> |No| NoTranslation[Skip translation]
    CheckFilename --> |Yes| Translate[M2M100 Translation]
    
    NoTranslation --> Summary[Generate Summary]
    Translate --> Summary
    
    Summary --> SaveFiles[Save files:<br/>==analysis.txt<br/>==summary.txt]
    SaveFiles --> CleanupFrames[Delete temp frames]
    CleanupFrames --> CreateDoc[Create Document record<br/>type=VIDEO]
    CreateDoc --> Vectorize[Vectorize analysis text]
    Vectorize --> SaveChunks[Save chunks to AlloyDB]
    SaveChunks --> QueueGraph[Push to graph_queue]
    QueueGraph --> UpdateJob[Update job.processed_files]
    UpdateJob --> End([Processing Complete])
```

### Hindi Video Processing

```mermaid
flowchart TD
    Start([User uploads hindi_cctv.mp4]) --> Validate[Validate file size & type]
    Validate --> Store[Store in GCS/Local]
    Store --> CreateJob[Create ProcessingJob<br/>status=QUEUED]
    CreateJob --> PushQueue[Push to video_queue]
    
    PushQueue --> Worker[Video Worker picks up]
    Worker --> Download[Download MP4]
    Download --> ExtractFrames[Extract frames at 0.3 fps<br/>MoviePy]
    
    ExtractFrames --> Frames[JPEG frames]
    Frames --> EncodeFrames[Base64 encode frames]
    EncodeFrames --> VisionLLM[Gemma3:4b Vision LLM<br/>CCTV analysis prompt]
    
    VisionLLM --> Analysis[Analysis in English<br/>Vision models output English]
    
    Analysis --> CheckFilename{Filename<br/>contains 'hindi'?}
    CheckFilename --> |Yes| Translate[Apply M2M100 Translation<br/>if needed for audio overlay]
    
    Translate --> TranslatedAnalysis[Translated analysis]
    TranslatedAnalysis --> Summary[Generate English Summary]
    
    Summary --> SaveFiles[Save files:<br/>===analysis.txt<br/>===translated.txt if applicable<br/>===summary.txt]
    SaveFiles --> CleanupFrames[Delete temp frames]
    CleanupFrames --> CreateDoc[Create Document record<br/>type=VIDEO]
    CreateDoc --> Vectorize[Vectorize analysis]
    Vectorize --> SaveChunks[Save chunks]
    SaveChunks --> QueueGraph[Push to graph_queue]
    QueueGraph --> UpdateJob[Update job.processed_files]
    UpdateJob --> End([Processing Complete])
```

## Graph Processing Flow

### Knowledge Graph Extraction

```mermaid
flowchart TD
    Start([Document/Audio/Video<br/>processing complete]) --> PushMsg[Push message to graph_queue:<br/>job_id, document_id,<br/>text_path, username]
    
    PushMsg --> GraphWorker[Graph Worker picks up]
    GraphWorker --> DownloadText[Download text file<br/>Prefer translated/English version]
    
    DownloadText --> CheckText{Text<br/>available?}
    CheckText --> |No| Skip[Log error & skip<br/>Document processor likely failed]
    CheckText --> |Yes| TruncateText[Truncate to 5000 chars<br/>for efficiency]
    
    TruncateText --> LangChain[Create LangChain Document<br/>with metadata]
    LangChain --> LLMTransform[LLMGraphTransformer<br/>Gemma3:4b via vLLM]
    
    LLMTransform --> ExtractEntities[Extract Entities:<br/>• Person<br/>• Organization<br/>• Location<br/>• Event<br/>• etc.]
    
    ExtractEntities --> ExtractRels[Extract Relationships:<br/>• WORKS_FOR<br/>• LOCATED_IN<br/>• PARTICIPATED_IN<br/>• etc.]
    
    ExtractRels --> CreateNodes[Create/Merge Nodes in Neo4j:<br/>• Canonical ID generation<br/>• Property normalization]
    
    CreateNodes --> CreateRels[Create Relationships in Neo4j:<br/>• Link entities<br/>• Add metadata]
    
    CreateRels --> LinkDoc[Create Document node<br/>Link via CONTAINS_ENTITY]
    LinkDoc --> LinkUser[Link User node<br/>via OWNS relationship]
    
    LinkUser --> CheckCompletion{All documents<br/>in job have graphs?}
    CheckCompletion --> |No| Continue[Keep job as PROCESSING]
    CheckCompletion --> |Yes| MarkComplete[Mark job as COMPLETED<br/>Set completed_at timestamp]
    
    MarkComplete --> End([Graph Processing Complete])
    Continue --> End
    Skip --> End
```

### Graph Node Structure

```mermaid
graph LR
    User([User Node<br/>username: analyst1]) -->|OWNS| Doc([Document Node<br/>document_id: 123<br/>filename: report.pdf])
    
    Doc -->|CONTAINS_ENTITY| Person1([Person Node<br/>name: John Doe<br/>id: john-doe])
    Doc -->|CONTAINS_ENTITY| Org1([Organization Node<br/>name: ABC Corp<br/>id: abc-corp])
    Doc -->|CONTAINS_ENTITY| Loc1([Location Node<br/>name: Mumbai<br/>id: mumbai])
    
    Person1 -->|WORKS_FOR| Org1
    Org1 -->|LOCATED_IN| Loc1
    Person1 -->|LOCATED_IN| Loc1
```

## Model Selection Decision Trees

### Summarization Model Selection

```mermaid
flowchart TD
    Start([Need to generate summary]) --> CheckEnv{USE_GEMINI_FOR_DEV<br/>environment variable}
    
    CheckEnv --> |true| CheckKey{GEMINI_API_KEY<br/>exists?}
    CheckKey --> |Yes| UseGemini[Use Google Gemini API<br/>gemini-2.0-flash-exp]
    CheckKey --> |No| LogWarning[Log: Gemini configured<br/>but key missing]
    
    CheckEnv --> |false| UseOllama[Use Ollama<br/>Gemma3:1b]
    LogWarning --> UseOllama
    
    UseGemini --> GeminiCall[Call Gemini API:<br/>GoogleDocAgent.generate_summary]
    GeminiCall --> CheckSuccess{API call<br/>successful?}
    CheckSuccess --> |Yes| ReturnSummary([Return summary])
    CheckSuccess --> |No| FallbackOllama[Fallback to Ollama]
    
    UseOllama --> OllamaCall[Call Ollama:<br/>Client.chat with gemma3:1b]
    OllamaCall --> OllamaSuccess{Call<br/>successful?}
    OllamaSuccess --> |Yes| ReturnSummary
    OllamaSuccess --> |No| ReturnError([Return error message])
    
    FallbackOllama --> OllamaCall
```

### Transcription Model Selection

```mermaid
flowchart TD
    Start([Need to transcribe audio]) --> CheckEnv{USE_GEMINI_FOR_DEV}
    
    CheckEnv --> |true| CheckKey{GEMINI_API_KEY<br/>exists?}
    CheckKey --> |Yes| UseGemini[Use Google Gemini 2.0 Flash<br/>Multimodal API]
    CheckKey --> |No| LogWarning[Log: Gemini configured<br/>but key missing]
    
    CheckEnv --> |false| CheckGemma{Gemma3:12b<br/>multimodal available?}
    LogWarning --> CheckGemma
    
    CheckGemma --> |Yes| UseGemma[Use Gemma3:12b<br/>Local inference]
    CheckGemma --> |No| ReturnPlaceholder[Return placeholder:<br/>'Transcription pending']
    
    UseGemini --> UploadAudio[Upload audio to Gemini]
    UploadAudio --> SetPrompt[Set language hint:<br/>Hindi/English]
    SetPrompt --> GeminiGenerate[Generate transcription]
    GeminiGenerate --> CleanupGemini[Delete uploaded file]
    CleanupGemini --> ReturnTranscription([Return transcription])
    
    UseGemma --> |Not yet implemented| ReturnPlaceholder
    ReturnPlaceholder --> CreateDocPartial([Create document<br/>with placeholder])
```

### Chat Model Selection

```mermaid
flowchart TD
    Start([User sends chat message]) --> VectorSearch[Perform vector similarity search<br/>EmbeddingGemma]
    
    VectorSearch --> GetChunks[Retrieve top 8 relevant chunks<br/>Filter by user access]
    GetChunks --> CheckEnv{USE_GEMINI_FOR_DEV}
    
    CheckEnv --> |true| CheckKey{GEMINI_API_KEY<br/>exists?}
    CheckKey --> |Yes| UseGemini[Use Google Gemini<br/>GoogleDocAgent.generate]
    CheckKey --> |No| LogWarning[Log: Gemini configured<br/>but key missing]
    
    CheckEnv --> |false| UseOllama[Use Ollama<br/>Gemma3:1b Chat Model]
    LogWarning --> UseOllama
    
    UseGemini --> PrepareGemini[Prepare chunks with metadata:<br/>document_id, chunk_index]
    PrepareGemini --> GeminiGenerate[Generate response<br/>with references]
    GeminiGenerate --> ReturnResponse([Return response<br/>with sources])
    
    UseOllama --> PrepareContext[Prepare context:<br/>Source 1, Source 2, ...]
    PrepareContext --> OllamaRAG[Create RAG prompt]
    OllamaRAG --> OllamaGenerate[Generate response]
    OllamaGenerate --> CheckSuccess{Success?}
    CheckSuccess --> |Yes| ReturnResponse
    CheckSuccess --> |No| FallbackContext[Return context only]
    FallbackContext --> ReturnResponse
```

## Error Handling Flows

### Document Processing Error Handling

```mermaid
flowchart TD
    Start([Document Worker<br/>receives message]) --> TryProcess{Try processing}
    
    TryProcess --> DownloadFail{Download<br/>failed?}
    DownloadFail --> |Yes| LogError1[Log: File not found in storage]
    LogError1 --> SkipFile[Skip file<br/>Don't fail entire job]
    
    DownloadFail --> |No| OCRFail{OCR/Extraction<br/>failed?}
    OCRFail --> |Yes| LogError2[Log: OCR failed<br/>Check Tesseract/Docling]
    LogError2 --> CheckCritical{Critical<br/>error?}
    CheckCritical --> |Yes| SkipFile
    CheckCritical --> |No| RetryOCR[Retry with fallback]
    
    OCRFail --> |No| EmptyText{Extracted text<br/>empty?}
    EmptyText --> |Yes| LogError3[Log: Empty text extracted<br/>Possible image-only PDF]
    LogError3 --> RaiseError[Raise ValueError]
    RaiseError --> SkipFile
    
    EmptyText --> |No| TranslateFail{Translation<br/>failed?}
    TranslateFail --> |Yes| LogError4[Log: Translation error]
    LogError4 --> UseOriginal[Use original text<br/>Continue without translation]
    
    TranslateFail --> |No| SummaryFail{Summary<br/>generation failed?}
    SummaryFail --> |Yes| LogError5[Log: Summary generation failed]
    LogError5 --> UseFallback[Use fallback summary:<br/>'Summary generation failed']
    
    SummaryFail --> |No| Success[Process completed successfully]
    
    UseOriginal --> Success
    UseFallback --> Success
    Success --> SaveResults[Save all results]
    SaveResults --> UpdateJob[Update job progress]
    
    SkipFile --> CheckRemaining{Other files<br/>remaining?}
    CheckRemaining --> |Yes| ContinueJob[Continue job<br/>status=PROCESSING]
    CheckRemaining --> |No| MarkPartial[Mark job as COMPLETED<br/>with some failures]
    
    UpdateJob --> End([Worker continues<br/>to next message])
    ContinueJob --> End
    MarkPartial --> End
```

### Graph Processing Error Handling

```mermaid
flowchart TD
    Start([Graph Worker<br/>receives message]) --> TryDownload{Try download<br/>text file}
    
    TryDownload --> DownloadFail{Download<br/>failed?}
    DownloadFail --> |Yes| LogError1[Log: Text file not found<br/>Document processor likely failed]
    LogError1 --> Skip[Skip graph processing<br/>for this document]
    
    DownloadFail --> |No| EmptyText{Text<br/>empty?}
    EmptyText --> |Yes| LogError2[Log: Empty text file]
    LogError2 --> Skip
    
    EmptyText --> |No| TryExtract{Try entity<br/>extraction}
    TryExtract --> ExtractFail{LLM extraction<br/>failed?}
    ExtractFail --> |Yes| CheckLLM[Check LLM service]
    CheckLLM --> LogError3[Log: LLM unavailable<br/>or timeout]
    LogError3 --> Skip
    
    ExtractFail --> |No| EmptyGraph{No entities<br/>extracted?}
    EmptyGraph --> |Yes| LogWarning[Log: No entities found<br/>Text may be too short]
    LogWarning --> CreateEmptyDoc[Create Document node only<br/>No entities]
    
    EmptyGraph --> |No| TryNeo4j{Try Neo4j<br/>storage}
    TryNeo4j --> Neo4jFail{Neo4j<br/>connection failed?}
    Neo4jFail --> |Yes| LogError4[Log: Neo4j unavailable]
    LogError4 --> SaveLocal[Save graph data locally<br/>for later retry]
    
    Neo4jFail --> |No| Success[Graph created successfully]
    
    Success --> CheckJobComplete{All documents<br/>in job processed?}
    CreateEmptyDoc --> CheckJobComplete
    
    CheckJobComplete --> |Yes| MarkComplete[Mark job as COMPLETED]
    CheckJobComplete --> |No| KeepProcessing[Keep job as PROCESSING]
    
    Skip --> End([Continue to next message])
    SaveLocal --> End
    MarkComplete --> End
    KeepProcessing --> End
```

### Redis Queue Error Handling

```mermaid
flowchart TD
    Start([Worker listens<br/>to queue]) --> TryPop{Try BRPOP<br/>from queue}
    
    TryPop --> Timeout{Timeout<br/>after 1s?}
    Timeout --> |Yes| Continue[Continue listening<br/>No error]
    
    Timeout --> |No| GotMessage[Message received]
    GotMessage --> TryDecode{Try JSON<br/>decode}
    
    TryDecode --> DecodeFail{Decode<br/>failed?}
    DecodeFail --> |Yes| LogError1[Log: Invalid JSON in message]
    LogError1 --> DiscardMessage[Discard message<br/>Continue to next]
    
    DecodeFail --> |No| TryCallback{Try callback<br/>function}
    TryCallback --> CallbackFail{Callback<br/>raised exception?}
    CallbackFail --> |Yes| LogError2[Log: Processing error]
    LogError2 --> PrintTraceback[Print full traceback]
    PrintTraceback --> DiscardMessage
    
    CallbackFail --> |No| Success[Message processed<br/>successfully]
    
    Success --> Continue
    DiscardMessage --> Continue
    Continue --> TryPop
    
    TryPop --> ConnectionFail{Redis<br/>connection lost?}
    ConnectionFail --> |Yes| LogError3[Log: Redis connection error]
    LogError3 --> Wait[Sleep 1 second]
    Wait --> TryPop
```

## Performance Optimization Flows

### Parallel Processing with Multiple Workers

```mermaid
sequenceDiagram
    participant API
    participant Redis
    participant Worker1 as Document Worker 1
    participant Worker2 as Document Worker 2
    participant Worker3 as Document Worker 3
    participant DB as AlloyDB

    API->>Redis: LPUSH file1.pdf to document_queue
    API->>Redis: LPUSH file2.pdf to document_queue
    API->>Redis: LPUSH file3.pdf to document_queue
    
    par Worker 1 Processing
        Worker1->>Redis: BRPOP document_queue
        Redis-->>Worker1: file1.pdf
        Worker1->>Worker1: Process file1.pdf
        Worker1->>DB: Check if already processed
        DB-->>Worker1: Not processed
        Worker1->>Worker1: Extract, translate, summarize
        Worker1->>DB: Save document record
    and Worker 2 Processing
        Worker2->>Redis: BRPOP document_queue
        Redis-->>Worker2: file2.pdf
        Worker2->>Worker2: Process file2.pdf
        Worker2->>DB: Check if already processed
        DB-->>Worker2: Not processed
        Worker2->>Worker2: Extract, translate, summarize
        Worker2->>DB: Save document record
    and Worker 3 Processing
        Worker3->>Redis: BRPOP document_queue
        Redis-->>Worker3: file3.pdf
        Worker3->>Worker3: Process file3.pdf
        Worker3->>DB: Check if already processed
        DB-->>Worker3: Not processed
        Worker3->>Worker3: Extract, translate, summarize
        Worker3->>DB: Save document record
    end
    
    Note over Worker1,Worker3: All workers process in parallel<br/>Each file processed by ONE worker
```

### Distributed Locking Mechanism

```mermaid
flowchart TD
    Start([Worker receives<br/>file message]) --> QueryDB[Query database:<br/>SELECT * FROM documents<br/>WHERE job_id=X AND filename=Y]
    
    QueryDB --> Exists{Document<br/>exists?}
    Exists --> |No| CreateRecord[INSERT INTO documents<br/>with basic info]
    Exists --> |Yes| CheckStatus{Has summary_path?}
    
    CheckStatus --> |Yes| AlreadyDone[Log: Already processed<br/>by another worker]
    AlreadyDone --> Skip([Skip processing<br/>Return immediately])
    
    CheckStatus --> |No| UpdateRecord[UPDATE document<br/>continue processing]
    CreateRecord --> Process[Process file:<br/>Extract, translate, summarize]
    UpdateRecord --> Process
    
    Process --> SaveResults[Save results:<br/>• extracted_text_path<br/>• translated_text_path<br/>• summary_path<br/>• summary_text]
    
    SaveResults --> Commit[COMMIT transaction]
    Commit --> End([Processing complete<br/>Worker continues])
```

## Summary of Key Differences

### File Naming Conventions Summary

| Scenario | Extracted | Translated | Summary | Example |
|----------|-----------|------------|---------|---------|
| **Document (English)** | `--extracted.md` | - | `--summary.txt` | `report--extracted.md` |
| **Document (Hindi)** | `---extracted.md` | `---translated.md` | `---summary.txt` | `hindi---extracted.md` |
| **Audio (English)** | `==transcription.txt` | - | `==summary.txt` | `audio.mp3==transcription.txt` |
| **Audio (Hindi)** | `===transcription.txt` | `===translated.txt` | `===summary.txt` | `hindi.mp3===transcription.txt` |
| **Video (English)** | `==analysis.txt` | - | `==summary.txt` | `cctv.mp4==analysis.txt` |
| **Video (Hindi)** | `===analysis.txt` | `===translated.txt` | `===summary.txt` | `hindi.mp4===analysis.txt` |

### Model Usage Summary

| Task | Dev Mode | Production Mode |
|------|----------|-----------------|
| **Document Summary** | Google Gemini 2.0 Flash | Ollama Gemma3:1b |
| **Audio Transcription** | Google Gemini 2.0 Flash | Gemma3:12b multimodal (pending) |
| **Video Analysis** | Gemma3:4b Vision (LangChain) | Gemma3:4b Vision (LangChain) |
| **Chat/Q&A** | Google Gemini 2.0 Flash | Ollama Gemma3:1b |
| **Knowledge Graph** | Gemma3:4b (vLLM) | Gemma3:4b (vLLM) |
| **Translation** | M2M100 (dl-translate) | M2M100 (dl-translate) |
| **Embeddings** | EmbeddingGemma (Ollama) | EmbeddingGemma (Ollama) |

---

**Last Updated**: 2025-11-06  
**Version**: 1.0.0
