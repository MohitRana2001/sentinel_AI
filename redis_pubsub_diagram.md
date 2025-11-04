# Redis Pub/Sub Flow in Sentinel AI

```mermaid
flowchart LR
    subgraph Frontend
        F[Next.js UI]
    end

    subgraph Backend
        B[(FastAPI /upload)]
        JP[Processing Job Record<br/>AlloyDB]
    end

    subgraph Redis["Redis Pub/Sub"]
        Q1[(document_processor)]
        Q2[(audio_processor)]
        Q3[(video_processor)]
        Qg[(graph_processor)]
    end

    subgraph Workers
        D[Document Processor<br/>(OCR/Translate/Summarise)]
        A[Audio/Video Processor]
        AV[Graph Processor<br/>(Entity Extraction)]
    end

    subgraph Storage
        GCS[(GCS / Local Storage)]
        DB[(AlloyDB + pgvector)]
        NEO[(Neo4j)]
    end

    F -->|uploads files| B
    B -->|store raw files| GCS
    B -->|create job| JP
    B -->|publish job| Q1
    B -->|publish job| Q2
    B -->|publish job| Q3

    D -->|download prefix| GCS
    D -->|write summaries/chunks| GCS
    D -->|store metadata| DB
    D -->|publish text prefix| Qg

    A -->|optional transcription| GCS
    A -->|store transcript| DB
    A -->|publish text prefix| Qg

    AV -->|download text| GCS
    AV -->|write graph nodes| DB
    AV -->|write relationships| NEO
```

**Flow summary**

1. The React UI posts files to `POST /api/v1/upload`. The backend writes them to the configured storage (GCS or the local fallback) and records a job in AlloyDB.
2. The backend publishes one message per channel (`document_processor`, `audio_processor`, `video_processor`) describing the job ID and storage prefix.
3. Each worker subscribes to its channel via Redis Pub/Sub, downloads the files it is responsible for, generates artefacts, stores results in AlloyDB/GCS, and republishes additional work onto the `graph_processor` channel if needed.
4. The Graph Processor consumes messages from `graph_processor`, extracts entities/relationships, pushes them into Neo4j and AlloyDB, and the frontend later visualises them via the `/jobs/{job_id}/graph` endpoint.
