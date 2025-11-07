# VM Integration Architecture Overview

## Introduction

This document provides a comprehensive overview of how the Document Processor and Graph Processor services are integrated into separate VMs within the Sentinel AI architecture. It serves as a high-level guide to understand the distributed system design and how the components interact.

## Architecture Diagram

```
                                    ┌─────────────────────────────────┐
                                    │      Users / Frontend           │
                                    │      (Next.js)                  │
                                    └─────────────┬───────────────────┘
                                                  │
                                                  │ HTTP/REST API
                                                  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         Main Application Server                           │
│                         (FastAPI Backend)                                 │
│                                                                            │
│  - User Authentication & RBAC                                             │
│  - File Upload Handler                                                    │
│  - Job Management                                                         │
│  - Chat / Query Interface                                                 │
│  - Graph Visualization API                                                │
└─────────┬──────────────────────────┬──────────────────┬──────────────────┘
          │                          │                  │
          │ Creates Jobs             │ Pushes to Queue  │ Stores Files
          ▼                          ▼                  ▼
┌──────────────────┐    ┌─────────────────────┐  ┌──────────────────────┐
│   AlloyDB        │    │      Redis          │  │  Cloud Storage       │
│   (PostgreSQL    │    │   (Message Queue)   │  │  (GCS / Network)     │
│    + pgvector)   │    │                     │  │                      │
│                  │    │  - document_queue   │  │  - Raw uploads       │
│  - Users         │    │  - graph_queue      │  │  - Extracted text    │
│  - Jobs          │    │  - audio_queue      │  │  - Summaries         │
│  - Documents     │    │  - video_queue      │  │  - Translations      │
│  - Chunks        │    │                     │  │                      │
│  - Embeddings    │    └─────────────────────┘  └──────────────────────┘
│  - Graph Meta    │              │                          │
└──────────────────┘              │                          │
          ▲                       │                          │
          │                       │ Pull Messages            │ Download Files
          │                       ▼                          │
          │         ┌─────────────────────────────┐         │
          │         │   DOCUMENT PROCESSOR VM     │◀────────┘
          │         │                             │
          │         │  Multiple Workers:          │
          │         │  - document_proc_1          │
          │         │  - document_proc_2          │
          │         │  - document_proc_3          │
          │         │                             │
          │         │  Tasks:                     │
          │         │  ✓ Text Extraction (OCR)    │
          │         │  ✓ Language Detection       │
          │         │  ✓ Translation              │
          │         │  ✓ Summarization (LLM)      │
          │         │  ✓ Embedding Generation     │
          │         │  ✓ Vector Storage           │
          └─────────┤                             │
                    │  Pushes to graph_queue      │
                    └─────────────┬───────────────┘
                                  │
                                  │ Queues processed docs
                                  ▼
                    ┌─────────────────────────────┐
                    │    GRAPH PROCESSOR VM       │
                    │                             │
                    │  Multiple Workers:          │
                    │  - graph_proc_1             │
                    │  - graph_proc_2             │
                    │  - graph_proc_3             │
                    │                             │
                    │  Tasks:                     │
                    │  ✓ Entity Extraction (LLM)  │
                    │  ✓ Relationship Detection   │
                    │  ✓ Graph Building           │
                    │  ✓ Entity Resolution        │
                    │  ✓ Cross-Doc Linking        │
                    │  ✓ Job Completion           │
                    └─────────────┬───────────────┘
                                  │
                                  │ Stores graph
                                  ▼
                    ┌─────────────────────────────┐
                    │        Neo4j                │
                    │    (Graph Database)         │
                    │                             │
                    │  - Entity Nodes             │
                    │  - Relationships            │
                    │  - Document Links           │
                    │  - User Links               │
                    └─────────────────────────────┘


                    ┌─────────────────────────────┐
                    │     LLM Servers             │
                    │     (Ollama)                │
                    │                             │
                    │  - Summary LLM (Gemma 1b)   │
                    │  - Graph LLM (Gemma 4b)     │
                    │  - Chat LLM (Gemma 1b)      │
                    │  - Embedding LLM            │
                    └─────────────────────────────┘
```

## System Components

### 1. Main Application Server

**Location**: Primary application server (VM or container)

**Responsibilities**:
- Handle user authentication and RBAC
- Accept file uploads via REST API
- Create processing jobs in AlloyDB
- Store raw files in cloud storage
- Push messages to Redis queues for processing
- Serve query/chat interface using vector search
- Provide graph visualization API by querying Neo4j
- Manage job status and results

**Technology Stack**:
- FastAPI (Python web framework)
- SQLAlchemy (ORM for database)
- Redis client for pub/sub
- GCS client for storage
- Neo4j driver for graph queries

**Does NOT**:
- Perform document processing (delegated to Document Processor VM)
- Extract entities or build graphs (delegated to Graph Processor VM)
- Run resource-intensive tasks (offloaded to worker VMs)

### 2. Document Processor VM

**Location**: Dedicated VM (can have multiple instances for scaling)

**Responsibilities**:
- Pull messages from `document_queue` in Redis
- Download raw files from cloud storage
- Extract text from PDFs, DOCX, TXT files using OCR
- Detect document language
- Translate non-English documents to English
- Generate document summaries using LLM
- Create text embeddings for semantic search
- Store chunks and embeddings in AlloyDB
- Upload processed text and summaries to storage
- Push completed documents to `graph_queue`

**Technology Stack**:
- Python with FastAPI dependencies
- Tesseract OCR for text extraction
- Docling for advanced PDF processing
- Ollama client for LLM summarization
- Redis client for queue management
- GCS/storage client for file operations

**Resource Requirements**:
- CPU: 4-8 cores
- RAM: 8-16 GB
- Disk: 50 GB
- Network: Good connectivity to Redis, AlloyDB, GCS, LLM servers

**Scaling Strategy**:
- Run multiple worker processes on same VM
- Run multiple VMs with workers
- Each worker independently pulls from queue
- Redis ensures no duplicate processing

### 3. Graph Processor VM

**Location**: Dedicated VM (can have multiple instances for scaling)

**Responsibilities**:
- Pull messages from `graph_queue` in Redis
- Download processed text from cloud storage
- Extract entities (people, orgs, locations, concepts) using LLM
- Identify relationships between entities
- Build knowledge graph in Neo4j
- Store graph metadata in AlloyDB for fast queries
- Perform entity resolution across documents
- Create cross-document entity links
- Mark jobs as COMPLETED when all docs processed

**Technology Stack**:
- Python with LangChain for graph building
- LangChain Neo4j integration
- Ollama client for LLM entity extraction
- Neo4j driver for graph storage
- Redis client for queue management

**Resource Requirements**:
- CPU: 4-8 cores (more beneficial than Document Processor)
- RAM: 16-32 GB (LLM inference is memory-intensive)
- Disk: 50 GB
- Network: Good connectivity to Redis, AlloyDB, Neo4j, LLM servers

**Scaling Strategy**:
- Run 2-4 worker processes (LLM is bottleneck)
- Use GPU-accelerated LLM for better throughput
- Each worker independently pulls from queue

### 4. Redis (Message Queue)

**Location**: Centralized server (can be on main app server or dedicated)

**Purpose**: 
- Coordinate work distribution between services
- Ensure fault tolerance and scalability

**Queues**:
- `document_queue`: Files to be processed (PDF, DOCX, TXT)
- `graph_queue`: Documents ready for entity extraction
- `audio_queue`: Audio files to be transcribed
- `video_queue`: Video files to be transcribed

**Advantages of Queue-Based Architecture**:
- **Decoupling**: Services can scale independently
- **Fault Tolerance**: If a worker crashes, message stays in queue
- **Load Balancing**: Multiple workers share the load automatically
- **Backpressure**: If downstream is slow, queue builds up (observable)
- **Priority**: Can implement priority queues if needed

### 5. AlloyDB / PostgreSQL

**Location**: Centralized database server

**Purpose**:
- Store all application data
- Provide vector search capabilities (pgvector extension)

**Tables**:
- `users`: User accounts with RBAC levels
- `processing_jobs`: Job metadata and status
- `documents`: Document metadata and file paths
- `document_chunks`: Text chunks for RAG
- `embeddings`: Vector embeddings for semantic search
- `graph_entities`: Entity metadata (name, type, properties)
- `graph_relationships`: Relationship metadata

**Why Both AlloyDB and Neo4j?**
- **AlloyDB**: Fast queries for document search, chunk retrieval, job status
- **Neo4j**: Optimized for complex graph traversals and visualization
- **Hybrid Approach**: Metadata in AlloyDB, graph structure in Neo4j

### 6. Neo4j (Graph Database)

**Location**: Dedicated server (can be Docker container or VM)

**Purpose**:
- Store knowledge graph for visualization
- Enable graph queries and traversals
- Support entity resolution across documents

**Node Types**:
- `Entity`: Extracted entities (Person, Organization, Location, etc.)
- `Document`: Document metadata nodes
- `User`: User nodes for ownership tracking

**Relationship Types**:
- `RELATED_TO`: Generic entity relationships
- `WORKS_AT`, `LOCATED_IN`, etc.: Specific entity relationships
- `CONTAINS_ENTITY`: Document to entity links
- `SHARES_ENTITY`: Cross-document entity links
- `OWNS`: User to document ownership

### 7. Cloud Storage (GCS / Network Storage)

**Location**: Google Cloud Storage bucket or network-mounted storage

**Purpose**:
- Store raw uploaded files
- Store processed artifacts (extracted text, summaries, translations)

**Directory Structure**:
```
uploads/
  ├── manager_username/
  │   └── analyst_username/
  │       └── job_uuid/
  │           ├── document1.pdf                 (raw upload)
  │           ├── document1--extracted.md       (extracted text)
  │           ├── document1--summary.txt        (summary)
  │           ├── document1---translated.md     (translation)
  │           ├── document2.docx                (raw upload)
  │           └── ...
```

**Access Pattern**:
- **Main App**: WRITE raw uploads, READ for serving to users
- **Document Processor**: READ raw files, WRITE processed artifacts
- **Graph Processor**: READ processed text only

### 8. LLM Servers (Ollama)

**Location**: Can be on same VMs or dedicated GPU servers

**Models**:
- **Summary LLM** (Gemma3:1b): Fast, lightweight summarization
- **Graph LLM** (Gemma3:4b): More capable entity extraction
- **Chat LLM** (Gemma3:1b): RAG-based Q&A
- **Embedding LLM** (EmbeddingGemma): Vector generation

**Why Separate Models?**
- **Performance**: Smaller models for simpler tasks (summarization)
- **Quality**: Larger models for complex tasks (entity extraction)
- **Resource Optimization**: Can run on different hardware

**Deployment Options**:
- CPU-only: Ollama on VMs with sufficient RAM
- GPU-accelerated: Ollama on GPU servers for faster inference

## Data Flow: Complete Pipeline

### Phase 1: Upload and Queue

1. User uploads files via frontend
2. Main App validates files and creates job in AlloyDB
3. Main App stores files in cloud storage (GCS)
4. Main App pushes file messages to Redis queues:
   - PDFs/DOCX/TXT → `document_queue`
   - Audio files → `audio_queue`
   - Video files → `video_queue`
5. Main App returns job_id to user

### Phase 2: Document Processing

1. **Document Processor worker** pulls message from `document_queue`
2. Worker downloads file from cloud storage
3. Worker extracts text:
   - PDF: Uses Docling with OCR (Tesseract)
   - DOCX: Uses python-docx
   - TXT: Direct read
4. Worker detects language using langid
5. If non-English, worker translates to English
6. Worker generates summary using Ollama LLM
7. Worker chunks text and generates embeddings
8. Worker stores chunks and embeddings in AlloyDB
9. Worker uploads processed text and summary to cloud storage
10. Worker creates/updates document record in AlloyDB
11. Worker pushes message to `graph_queue` with document_id
12. Worker updates job progress in AlloyDB

### Phase 3: Graph Processing

1. **Graph Processor worker** pulls message from `graph_queue`
2. Worker downloads processed text from cloud storage
3. Worker truncates text to 5000 chars (for LLM context limit)
4. Worker calls Ollama LLM to extract entities and relationships
5. Worker receives structured graph data (nodes + edges)
6. Worker stores graph in Neo4j:
   - Creates entity nodes with properties
   - Creates relationship edges
   - Links entities to document nodes
   - Links documents to user nodes
7. Worker stores graph metadata in AlloyDB for fast queries
8. Worker performs entity resolution:
   - Finds similar entities in other documents
   - Creates cross-document links
9. Worker checks if all documents in job are processed
10. If yes, worker marks job as COMPLETED in AlloyDB

### Phase 4: Querying and Visualization

1. User queries documents via chat interface
2. Main App performs vector search in AlloyDB
3. Main App retrieves relevant chunks
4. Main App uses LLM to generate answer with context
5. User requests graph visualization
6. Main App queries Neo4j for document entities and relationships
7. Main App returns graph data to frontend
8. Frontend renders interactive graph visualization

## Network Requirements

### Firewall Rules

**Main Application Server**:
- Inbound: 8000 (API), 3000 (Frontend - if on same server)
- Outbound: Redis (6379), AlloyDB (5432), Neo4j (7687), GCS (443), LLM servers (11434)

**Document Processor VM**:
- Inbound: None (worker doesn't accept connections)
- Outbound: Redis (6379), AlloyDB (5432), GCS (443), Summary LLM (11434), Embedding LLM (11434)

**Graph Processor VM**:
- Inbound: None (worker doesn't accept connections)
- Outbound: Redis (6379), AlloyDB (5432), Neo4j (7687), GCS (443), Graph LLM (11434)

**Redis Server**:
- Inbound: 6379 (from all VMs)
- Outbound: None typically

**AlloyDB Server**:
- Inbound: 5432 (from all VMs)
- Outbound: None typically

**Neo4j Server**:
- Inbound: 7687 (Bolt), 7474 (HTTP browser)
- Outbound: None typically

**LLM Servers**:
- Inbound: 11434 (from processor VMs)
- Outbound: None typically

### Internal Network Setup

**Recommended**: Use a private network (VPC) for all components:

```
Private Network: 10.0.0.0/16

- Main App:           10.0.1.10
- Redis:              10.0.2.10
- AlloyDB:            10.0.3.10
- Neo4j:              10.0.4.10
- Doc Processor 1:    10.0.5.10
- Doc Processor 2:    10.0.5.11
- Graph Processor 1:  10.0.6.10
- Graph Processor 2:  10.0.6.11
- Summary LLM:        10.0.7.10
- Graph LLM:          10.0.7.11
- Chat LLM:           10.0.7.12
- Embedding LLM:      10.0.7.13
```

**Benefits**:
- Low latency between services
- No exposure to public internet
- Simplified firewall rules
- Cost savings (no egress charges)

## Scaling Strategies

### Horizontal Scaling

**Document Processor VMs**:
- Add more VMs when document queue backs up
- Each VM can run 2-8 workers depending on CPU
- No coordination needed (queue handles distribution)
- Typical setup: 2-3 VMs with 4 workers each = 8-12 parallel processes

**Graph Processor VMs**:
- Add more VMs when graph queue backs up
- Fewer workers per VM (2-4) due to LLM memory requirements
- Consider GPU acceleration for better throughput
- Typical setup: 1-2 VMs with 2-3 workers each = 2-6 parallel processes

**Main Application**:
- Use load balancer (e.g., nginx) if serving many users
- Multiple FastAPI instances behind load balancer
- Stateless design allows easy horizontal scaling

### Vertical Scaling

**Document Processor VM**:
- Increase CPU for faster processing
- Increase RAM for more parallel workers
- 16-core, 32GB RAM VM can run 8-12 workers efficiently

**Graph Processor VM**:
- Increase RAM for LLM inference (most important)
- GPU dramatically improves speed (3-5x faster)
- 8-core, 32GB RAM + GPU is ideal

**LLM Servers**:
- GPU recommended for production
- CPU-only works but is slower (acceptable for moderate load)
- Consider cloud GPU instances (GCP T4, V100, A100)

### Auto-Scaling

**Monitoring Metrics**:
- Redis queue length (trigger scaling when > 100 messages)
- Worker CPU usage (scale up if consistently > 80%)
- Worker memory usage (scale up if consistently > 80%)
- Job processing latency (scale up if > SLA)

**Implementation**:
- Use Kubernetes for automatic scaling (if using containers)
- Use systemd + custom scripts for VM-based scaling
- Use cloud auto-scaling groups (GCP MIGs, AWS ASGs)

## Fault Tolerance and Reliability

### Component Failures

**Document Processor Crashes**:
- Systemd automatically restarts the service
- Message stays in Redis queue (not acknowledged)
- Another worker picks up the message
- Job continues processing

**Graph Processor Crashes**:
- Same recovery mechanism as Document Processor
- Neo4j transactions ensure data consistency
- Partial graphs are not committed

**Redis Failure**:
- Critical failure point (single point of failure)
- Solution: Redis Sentinel for automatic failover
- Or: Redis Cluster for high availability
- Messages in queue are persisted to disk (RDB/AOF)

**AlloyDB Failure**:
- Use AlloyDB replicas for read scaling
- Automatic failover to standby replica
- Point-in-time recovery available

**Neo4j Failure**:
- Graph visualization unavailable, but processing continues
- Neo4j clustering (Enterprise) for high availability
- Regular backups essential

**LLM Server Failure**:
- Workers retry with exponential backoff
- Queue messages remain until LLM recovers
- Consider multiple LLM instances behind load balancer

### Data Consistency

**Idempotency**:
- Document processing is idempotent (can be rerun safely)
- Graph processing checks for existing entities before creating
- AlloyDB uses UNIQUE constraints to prevent duplicates

**Transactions**:
- Database operations wrapped in transactions
- Failed transactions rolled back automatically
- Neo4j ensures atomicity of graph writes

## Monitoring and Observability

### Key Metrics to Monitor

**Queue Metrics**:
- Queue length for each queue
- Message processing rate
- Message age (time in queue)

**Worker Metrics**:
- CPU and memory usage per worker
- Processing time per document
- Success/failure rate
- Error rate and types

**Database Metrics**:
- Query latency
- Connection pool usage
- Disk usage
- Query throughput

**LLM Metrics**:
- Inference time per request
- Request queue depth
- Model memory usage
- GPU utilization (if applicable)

### Logging Strategy

**Centralized Logging**:
- All VMs send logs to central log aggregator (e.g., ELK stack, Loki)
- Structured logging (JSON format) for easy parsing
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

**Log Retention**:
- INFO logs: 7 days
- ERROR logs: 30 days
- DEBUG logs: 1 day (only in development)

### Alerting

**Critical Alerts** (immediate action):
- Redis down
- AlloyDB down
- Neo4j down
- Queue length > 1000 messages
- Error rate > 10%

**Warning Alerts** (investigate soon):
- Queue length > 100 messages for > 10 minutes
- Worker CPU > 90% for > 5 minutes
- Worker memory > 90% for > 5 minutes
- Processing latency > 2x normal

## Security Considerations

### Network Security

- All internal traffic on private network
- Only Main App exposed to internet (via load balancer)
- Firewall rules restrict VM-to-VM communication
- No SSH access from internet (use bastion host)

### Authentication

- Redis: Enable AUTH with strong password
- AlloyDB: Use strong database passwords
- Neo4j: Change default password immediately
- GCS: Use service account with minimal permissions

### Secrets Management

- Store secrets in `.env` files with restricted permissions (600)
- Use Google Secret Manager or HashiCorp Vault in production
- Rotate credentials regularly (quarterly recommended)
- Never commit secrets to Git

### Data Encryption

- AlloyDB: Enable encryption at rest
- GCS: Enable encryption at rest (default)
- Redis: Use TLS for connections in production
- Neo4j: Enable SSL/TLS for Bolt connections

## Cost Optimization

### Resource Optimization

**Right-Size VMs**:
- Don't over-provision CPU/RAM
- Monitor usage and adjust accordingly
- Use preemptible/spot instances for non-critical workers

**Storage Optimization**:
- Use lifecycle policies in GCS (delete old files)
- Compress old data
- Use cheaper storage classes for archival

**LLM Optimization**:
- Use quantized models (e.g., 4-bit quantization)
- Share LLM servers across services
- Use CPU for development, GPU for production

### Cost Breakdown Estimate

**For 1000 documents/day processing**:

- Main App VM (4 CPU, 16GB): $100/month
- Document Processor VM x2 (8 CPU, 16GB): $200/month
- Graph Processor VM x1 (8 CPU, 32GB): $150/month
- Redis VM (2 CPU, 8GB): $50/month
- AlloyDB (shared core): $100/month
- Neo4j VM (4 CPU, 16GB): $100/month
- LLM Server VM (8 CPU, 32GB): $150/month
- GCS Storage (100GB): $3/month
- Network egress: $20/month

**Total**: ~$873/month for self-hosted

**Managed Services Alternative**:
- Use Cloud Run for stateless services
- Use managed Redis (Cloud Memorystore)
- Use AlloyDB managed service
- Use managed Neo4j (Aura)

**Total with managed**: ~$1200-1500/month (easier management)

## Deployment Checklist

### Pre-Deployment

- [ ] All VMs provisioned with correct specs
- [ ] Private network configured
- [ ] Firewall rules set up
- [ ] DNS/hostnames configured
- [ ] Secrets generated and stored securely

### Main Application Deployment

- [ ] Code deployed
- [ ] Environment variables configured
- [ ] Database migrations run
- [ ] Static files built and deployed
- [ ] Service started and verified
- [ ] Health check endpoint responds

### Document Processor Deployment

- [ ] Code deployed on all VMs
- [ ] Tesseract and dependencies installed
- [ ] Environment variables configured
- [ ] Connectivity to Redis, AlloyDB, GCS verified
- [ ] Systemd service configured
- [ ] Multiple workers started
- [ ] Test document processed successfully

### Graph Processor Deployment

- [ ] Code deployed on all VMs
- [ ] Environment variables configured
- [ ] Connectivity to Redis, AlloyDB, Neo4j, GCS verified
- [ ] LLM server accessible
- [ ] Systemd service configured
- [ ] Multiple workers started
- [ ] Test graph created successfully

### Supporting Services

- [ ] Redis configured and secured
- [ ] AlloyDB set up with pgvector extension
- [ ] Neo4j configured and secured
- [ ] LLM models pulled and loaded
- [ ] GCS bucket created with proper permissions

### Monitoring Setup

- [ ] Logging aggregation configured
- [ ] Metrics collection set up (Prometheus/Grafana)
- [ ] Alerts configured
- [ ] Dashboards created
- [ ] On-call rotation defined

### Testing

- [ ] End-to-end test: Upload → Process → Graph → Query
- [ ] Load testing with multiple concurrent uploads
- [ ] Failure scenarios tested (kill workers, network issues)
- [ ] Performance benchmarks documented
- [ ] User acceptance testing completed

### Documentation

- [ ] Architecture diagram updated
- [ ] Runbooks created for common issues
- [ ] Deployment procedures documented
- [ ] Monitoring procedures documented
- [ ] Team trained on new architecture

## Conclusion

This distributed architecture provides:

1. **Scalability**: Each component scales independently
2. **Fault Tolerance**: Worker failures don't affect overall system
3. **Performance**: Parallel processing of documents and graphs
4. **Maintainability**: Clear separation of concerns
5. **Flexibility**: Easy to add new processors or modify existing ones

The queue-based design ensures reliable message delivery, while the specialized VMs optimize resource usage for different workloads.

**Next Steps**:
1. Follow the VM setup guides for Document and Graph Processors
2. Set up monitoring and alerting
3. Test the complete pipeline with sample data
4. Gradually increase load to verify scaling
5. Iterate on configuration based on observed performance

For detailed setup instructions, refer to:
- **VM_SETUP_DOCUMENT_PROCESSOR.md**: Step-by-step document processor setup
- **VM_SETUP_GRAPH_PROCESSOR.md**: Step-by-step graph processor setup
