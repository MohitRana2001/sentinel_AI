"""
Sentinel AI - FastAPI Backend
Main API server for document intelligence platform
"""
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from sqlalchemy.orm import Session
import uuid

from config import settings
from database import get_db, init_db
import models
from gcs_storage import gcs_storage
from redis_pubsub import redis_pubsub
from vector_store import VectorStore
from agents.google_agent import GoogleDocAgent
from routes.auth import router as auth_router
from security import get_current_user
from rbac import (
    filter_documents_scope,
    filter_jobs_scope,
    user_has_document_access,
    user_has_job_access,
)

app = FastAPI(
    title="Sentinel AI API",
    description="Document Intelligence Platform with RBAC and Knowledge Graphs",
    version="1.0.0",
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()
    print("✅ Database initialized")
    print(f"📡 API running at {settings.API_HOST}:{settings.API_PORT}")
    print(f"📚 Docs available at {settings.API_PREFIX}/docs")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Sentinel AI API",
        "version": "1.0.0",
        "docs": f"{settings.API_PREFIX}/docs",
        "status": "operational"
    }


@app.get(f"{settings.API_PREFIX}/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "upload_limits": {
            "max_files": settings.MAX_UPLOAD_FILES,
            "max_size_mb": settings.MAX_FILE_SIZE_MB
        }
    }


@app.get(f"{settings.API_PREFIX}/config")
async def get_config():
    """Get public configuration"""
    return {
        "max_upload_files": settings.MAX_UPLOAD_FILES,
        "max_file_size_mb": settings.MAX_FILE_SIZE_MB,
        "allowed_extensions": settings.allowed_extensions_list,
        "rbac_levels": settings.RBAC_LEVELS
    }


# ==================== UPLOAD ENDPOINTS ====================

@app.post(f"{settings.API_PREFIX}/upload")
async def upload_documents(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Upload documents for processing
    
    Validates:
    - Number of files (MAX_UPLOAD_FILES)
    - File size (MAX_FILE_SIZE_MB)
    - File extensions (ALLOWED_EXTENSIONS)
    """
    # Validate number of files
    if len(files) > settings.MAX_UPLOAD_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {settings.MAX_UPLOAD_FILES} files allowed per upload"
        )
    
    # Validate file extensions and sizes
    for file in files:
        # Check extension
        file_ext = '.' + file.filename.split('.')[-1].lower() if '.' in file.filename else ''
        if file_ext not in settings.allowed_extensions_list:
            raise HTTPException(
                status_code=400,
                detail=f"File type {file_ext} not allowed. Allowed: {', '.join(settings.allowed_extensions_list)}"
            )
        
        # Check size
        file.file.seek(0, 2)
        size = file.file.tell()
        file.file.seek(0)
        
        if size > settings.max_file_size_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"File '{file.filename}' exceeds {settings.MAX_FILE_SIZE_MB}MB limit (size: {size / 1024 / 1024:.2f}MB)"
            )
    
    # Ensure RBAC scope assignments exist for the user
    if current_user.rbac_level == models.RBACLevel.STATION:
        if not all([current_user.station_id, current_user.district_id, current_user.state_id]):
            raise HTTPException(
                status_code=400,
                detail="Station-level accounts require station_id, district_id, and state_id assignments before uploading.",
            )
    elif current_user.rbac_level == models.RBACLevel.DISTRICT:
        if not all([current_user.district_id, current_user.state_id]):
            raise HTTPException(
                status_code=400,
                detail="District-level accounts require district_id and state_id assignments before uploading.",
            )
    elif current_user.rbac_level == models.RBACLevel.STATE and not current_user.state_id:
        raise HTTPException(
            status_code=400,
            detail="State-level accounts require a state_id assignment before uploading.",
        )

    # Create job
    job_id = str(uuid.uuid4())
    gcs_prefix = f"uploads/{job_id}/"
    
    print(f"📤 Starting upload for job {job_id}: {len(files)} files")
    
    # Upload files to GCS
    filenames = []
    file_types = []
    
    for file in files:
        try:
            gcs_path = f"{gcs_prefix}{file.filename}"
            gcs_storage.upload_file(file.file, gcs_path)
            filenames.append(file.filename)
            
            # Determine file type
            ext = file.filename.split('.')[-1].lower()
            if ext in ['pdf', 'docx', 'txt']:
                file_types.append('document')
            elif ext in ['mp3', 'wav', 'm4a']:
                file_types.append('audio')
            elif ext in ['mp4', 'avi', 'mov']:
                file_types.append('video')
            else:
                file_types.append('document')
            
            print(f"✅ Uploaded: {file.filename} to {gcs_path}")
        except Exception as e:
            print(f"❌ Error uploading {file.filename}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload {file.filename}: {str(e)}"
            )
    
    # Create job in database
    # For demo, using default RBAC values - in production, get from authenticated user
    job = models.ProcessingJob(
        id=job_id,
        user_id=current_user.id,
        rbac_level=current_user.rbac_level,
        station_id=current_user.station_id,
        district_id=current_user.district_id,
        state_id=current_user.state_id,
        gcs_prefix=gcs_prefix,
        original_filenames=filenames,
        file_types=file_types,
        total_files=len(files),
        status=models.JobStatus.QUEUED
    )
    
    db.add(job)
    db.commit()
    db.refresh(job)
    
    # Publish to Redis Pub/Sub for processing
    redis_pubsub.publish_job(job_id, gcs_prefix, settings.REDIS_CHANNEL_DOCUMENT)
    
    # Also publish to audio/video channels if applicable
    if 'audio' in file_types:
        redis_pubsub.publish_job(job_id, gcs_prefix, settings.REDIS_CHANNEL_AUDIO)
    if 'video' in file_types:
        redis_pubsub.publish_job(job_id, gcs_prefix, settings.REDIS_CHANNEL_VIDEO)
    
    print(f"✅ Job {job_id} created and queued for processing")
    
    return {
        "job_id": job_id,
        "status": "queued",
        "total_files": len(files),
        "message": f"Successfully uploaded {len(files)} files. Processing started."
    }


# ==================== JOB STATUS ENDPOINTS ====================

@app.get(f"{settings.API_PREFIX}/jobs/{{job_id}}/status")
async def get_job_status(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get job processing status"""
    job = db.query(models.ProcessingJob).filter(
        models.ProcessingJob.id == job_id
    ).first()
    
    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )

    if not user_has_job_access(current_user, job):
        raise HTTPException(status_code=403, detail="Insufficient permissions for this job")
    
    progress_percentage = 0.0
    if job.total_files > 0:
        progress_percentage = (job.processed_files / job.total_files) * 100
    
    return {
        "job_id": job.id,
        "status": job.status.value,
        "total_files": job.total_files,
        "processed_files": job.processed_files,
        "progress_percentage": round(progress_percentage, 2),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "error_message": job.error_message
    }


@app.get(f"{settings.API_PREFIX}/jobs/{{job_id}}/results")
async def get_job_results(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get job results including all processed documents"""
    job = db.query(models.ProcessingJob).filter(
        models.ProcessingJob.id == job_id
    ).first()
    
    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )

    if not user_has_job_access(current_user, job):
        raise HTTPException(status_code=403, detail="Insufficient permissions for this job")
    
    # Get all documents for this job
    documents_query = db.query(models.Document).filter(
        models.Document.job_id == job_id
    )
    documents = filter_documents_scope(documents_query, current_user).all()
    
    return {
        "job_id": job.id,
        "status": job.status.value,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "documents": [
            {
                "id": doc.id,
                "filename": doc.original_filename,
                "file_type": doc.file_type.value,
                "summary": doc.summary_text,
                "created_at": doc.created_at.isoformat()
            }
            for doc in documents
        ]
    }


@app.get(f"{settings.API_PREFIX}/jobs")
async def get_user_jobs(
    limit: int = 10,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get all jobs (paginated)"""
    query = db.query(models.ProcessingJob).order_by(
        models.ProcessingJob.created_at.desc()
    )
    query = filter_jobs_scope(query, current_user)
    jobs = query.limit(limit).offset(offset).all()
    
    return [
        {
            "job_id": job.id,
            "status": job.status.value,
            "total_files": job.total_files,
            "processed_files": job.processed_files,
            "created_at": job.created_at.isoformat(),
            "progress_percentage": (job.processed_files / job.total_files * 100) if job.total_files > 0 else 0
        }
        for job in jobs
    ]


# ==================== DOCUMENT CONTENT ENDPOINTS ====================

@app.get(f"{settings.API_PREFIX}/documents/{{document_id}}/summary")
async def get_document_summary(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get document summary"""
    document = db.query(models.Document).filter(
        models.Document.id == document_id
    ).first()
    
    if not document:
        raise HTTPException(404, "Document not found")

    if not user_has_document_access(current_user, document):
        raise HTTPException(status_code=403, detail="Insufficient permissions for this document")
    
    # If summary is stored in database
    if document.summary_text:
        content = document.summary_text
    elif document.summary_path:
        # Download from GCS
        try:
            content = gcs_storage.download_text(document.summary_path)
        except:
            content = "Summary not available"
    else:
        content = "Summary not yet generated"
    
    return {
        "document_id": document.id,
        "filename": document.original_filename,
        "content": content,
        "content_type": "summary"
    }


@app.get(f"{settings.API_PREFIX}/documents/{{document_id}}/transcription")
async def get_document_transcription(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get document transcription (extracted text from documents or audio transcription)"""
    document = db.query(models.Document).filter(
        models.Document.id == document_id
    ).first()
    
    if not document:
        raise HTTPException(404, "Document not found")

    if not user_has_document_access(current_user, document):
        raise HTTPException(status_code=403, detail="Insufficient permissions for this document")
    
    # For audio/video files, use transcription_path
    # For documents (PDF/TXT), use extracted_text_path
    text_path = None
    if document.file_type in [models.FileType.AUDIO, models.FileType.VIDEO]:
        text_path = document.transcription_path
    else:
        text_path = document.extracted_text_path
    
    if not text_path:
        raise HTTPException(404, "Transcription not available for this document")
    
    try:
        content = gcs_storage.download_text(text_path)
    except Exception as e:
        print(f"❌ Error retrieving transcription: {e}")
        raise HTTPException(500, f"Failed to retrieve transcription: {str(e)}")
    
    return {
        "document_id": document.id,
        "filename": document.original_filename,
        "content": content,
        "content_type": "transcription"
    }


@app.get(f"{settings.API_PREFIX}/documents/{{document_id}}/translation")
async def get_document_translation(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get document translation"""
    document = db.query(models.Document).filter(
        models.Document.id == document_id
    ).first()
    
    if not document:
        raise HTTPException(404, "Document not found")

    if not user_has_document_access(current_user, document):
        raise HTTPException(status_code=403, detail="Insufficient permissions for this document")
    
    if not document.translated_text_path:
        raise HTTPException(404, "Translation not available for this document")
    
    try:
        content = gcs_storage.download_text(document.translated_text_path)
    except:
        raise HTTPException(500, "Failed to retrieve translation")
    
    return {
        "document_id": document.id,
        "filename": document.original_filename,
        "content": content,
        "content_type": "translation"
    }


# ==================== GRAPH ENDPOINTS ====================

@app.get(f"{settings.API_PREFIX}/jobs/{{job_id}}/graph")
async def get_job_graph(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get combined knowledge graph for all documents in a job"""
    job = db.query(models.ProcessingJob).filter(
        models.ProcessingJob.id == job_id
    ).first()
    
    if not job:
        raise HTTPException(404, "Job not found")

    if not user_has_job_access(current_user, job):
        raise HTTPException(status_code=403, detail="Insufficient permissions for this job")
    
    # Get all graph entities and relationships for this job
    entities = db.query(models.GraphEntity).join(
        models.Document
    ).filter(
        models.Document.job_id == job_id
    ).all()
    
    relationships = db.query(models.GraphRelationship).join(
        models.GraphEntity, models.GraphRelationship.source_entity_id == models.GraphEntity.entity_id
    ).join(
        models.Document, models.GraphEntity.document_id == models.Document.id
    ).filter(
        models.Document.job_id == job_id
    ).all()
    
    return {
        "nodes": [
            {
                "id": entity.entity_id,
                "label": entity.entity_name,
                "type": entity.entity_type,
                "properties": entity.properties
            }
            for entity in entities
        ],
        "relationships": [
            {
                "source": rel.source_entity_id,
                "target": rel.target_entity_id,
                "type": rel.relationship_type,
                "properties": rel.properties
            }
            for rel in relationships
        ]
    }


# ==================== CHAT/RAG ENDPOINT ====================

@app.post(f"{settings.API_PREFIX}/chat")
async def chat_with_documents(
    message: str,
    job_id: Optional[str] = None,
    document_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Chat with documents using RAG (Retrieval Augmented Generation)
    """
    if not message:
        raise HTTPException(400, "Message is required")
    
    # Use vector store for similarity search
    vector_store = VectorStore(db)
    
    try:
        if job_id:
            job = db.query(models.ProcessingJob).filter(models.ProcessingJob.id == job_id).first()
            if not job:
                raise HTTPException(404, "Job not found")
            if not user_has_job_access(current_user, job):
                raise HTTPException(status_code=403, detail="Insufficient permissions for this job")

        if document_id:
            document = db.query(models.Document).filter(models.Document.id == document_id).first()
            if not document:
                raise HTTPException(404, "Document not found")
            if not user_has_document_access(current_user, document):
                raise HTTPException(status_code=403, detail="Insufficient permissions for this document")
            # If job_id not provided, limit search to document's job scope for consistency
            if not job_id:
                job_id = document.job_id

        # Search for similar chunks - increased to 8 for better context
        results = vector_store.similarity_search(
            query=message,
            k=8,
            document_id=document_id,
            job_id=job_id,
            user=current_user
        )

        # Format context from search results
        context = "\n\n".join([r["chunk_text"][:800] for r in results[:5]])
        
        # Use Google Agent for better responses (if API key present)
        if settings.GEMINI_API_KEY:
            try:
                agent = GoogleDocAgent(api_key=settings.GEMINI_API_KEY, model=settings.GOOGLE_CHAT_MODEL)
                
                # Pass top 8 relevant chunks with more complete text (up to 1500 chars per chunk)
                # This provides better context for the agent to generate accurate responses
                enriched_chunks = []
                for r in results[:8]:
                    # Keep more text for better context (up to 1500 chars)
                    chunk_text = r["chunk_text"][:1500] if len(r["chunk_text"]) > 1500 else r["chunk_text"]
                    enriched_chunks.append({
                        "chunk_text": chunk_text,
                        "document_id": r.get("document_id"),
                        "chunk_index": r.get("chunk_index"),
                        "metadata": r.get("metadata", {})
                    })
                
                response_text = agent.generate(
                    question=message,
                    chunks=enriched_chunks,
                    metadata={
                        "job_id": job_id or "N/A",
                        "document_id": str(document_id) if document_id else "N/A",
                    },
                    include_static_refs=False  # Explicitly disable static refs to avoid token limit issues
                )
                
                # Return top 5 sources to frontend (with truncated text for display)
                display_sources = []
                for r in results[:5]:
                    display_sources.append({
                        "chunk_text": r["chunk_text"][:500],  # Truncate for UI display
                        "document_id": r.get("document_id"),
                        "chunk_index": r.get("chunk_index"),
                        "metadata": r.get("metadata", {})
                    })
                
                return {
                    "response": response_text,
                    "sources": display_sources,
                    "mode": f"google-{settings.GOOGLE_CHAT_MODEL}"
                }
            except Exception as agent_error:
                print(f"⚠️  Google agent error: {agent_error}")
                import traceback
                traceback.print_exc()
                # Fall through to basic response

        # Fallback: return context-based response
        return {
            "response": f"Based on the document excerpts:\n\n{context}\n\n(Note: For better chat responses, configure GEMINI_API_KEY)",
            "sources": results[:5],
            "mode": "context-only"
        }
    except Exception as e:
        print(f"❌ Chat error: {e}")
        raise HTTPException(500, f"Chat failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )
