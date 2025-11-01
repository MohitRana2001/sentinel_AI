from fastapi import FastAPI, File, UploadFile, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from sqlalchemy.orm import Session
import uuid

import enum
from pydantic import BaseModel, EmailStr
from datetime import datetime
from security import get_password_hash 

from config import settings
from database import get_db, init_db
import models
from models import RBACLevel 

from gcs_storage import gcs_storage
from redis_pubsub import redis_pubsub
from vector_store import VectorStore
try:
    from langchain_neo4j import Neo4jGraph
except Exception:
    Neo4jGraph = None
from agents.google_agent import GoogleDocAgent
from routes.auth import router as auth_router
from security import get_current_user
from rbac import (
    filter_documents_scope,
    filter_jobs_scope,
    user_has_document_access,
    user_has_job_access,
)

# --- START: NEW PYDANTIC MODELS FOR USER CREATION ---
class AssignableRole(str, enum.Enum):
    MANAGER = "manager"
    ANALYST = "analyst"

class UserCreate(BaseModel):
    """Data model for Admin to create a new user."""
    username: EmailStr
    password: str
    role: AssignableRole

class AnalystCreate(BaseModel):
    """Data model for Manager to create an Analyst."""
    username: EmailStr
    password: str

class AdminSignUp(BaseModel):
    """Data model for the first admin sign-up."""
    username: EmailStr
    password: str
    secret_key: str  # The special key from your settings

class UserOut(BaseModel):
    """Data model for returning user info (safely, without password)."""
    id: int
    username: EmailStr
    role: RBACLevel
    created_at: datetime

    class Config:
        orm_mode = True
# --- END: NEW PYDANTIC MODELS ---


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
    # allow_origins=settings.CORS_ORIGINS,
    allow_origins=["*"], # allowing all for now
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)

if Neo4jGraph:
    try:
        graph = Neo4jGraph(
            url = settings.Neo4j_URI,
            username = settings.Neo4j_USERNAME,
            password = settings.Neo4j_PASSWORD,
            database = settings.NEo4j_DATABASE
        )
    except Exception as e:
        print(f"❌ Failed to connect to Neo4j in main.py: {e}")
        graph = None
    else:
        print("⚠️ Neo4j is not installed, graph API will not function.")
        graph = None

# --- START: NEW SECURITY DEPENDENCIES FOR ADMIN & MANAGER ---
def get_super_admin(current_user: models.User = Depends(get_current_user)):
    """
    Dependency to check if the current user is a Super Admin.
    """
    if current_user.rbac_level != models.RBACLevel.ADMIN: 
        raise HTTPException(
            status_code=403, 
            detail="Not authorized: Super admin access required."
        )
    return current_user

def get_manager(current_user: models.User = Depends(get_current_user)):
    """
    Dependency to check if the current user is a Manager.
    """
    if current_user.rbac_level != models.RBACLevel.MANAGER: 
        raise HTTPException(
            status_code=403, 
            detail="Not authorized: Manager access required."
        )
    return current_user
# --- END: NEW SECURITY DEPENDENCIES ---


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()
    print("Database initialized")
    print(f"API running at {settings.API_HOST}:{settings.API_PORT}")
    print(f"Docs available at {settings.API_PREFIX}/docs")


@app.get("/")
async def root():
    return {
        "message": "Sentinel AI API",
        "version": "1.0.0",
        "docs": f"{settings.API_PREFIX}/docs",
        "status": "operational"
    }


@app.get(f"{settings.API_PREFIX}/health")
async def health_check():
    return {
        "status": "healthy",
        "upload_limits": {
            "max_files": settings.MAX_UPLOAD_FILES,
            "max_size_mb": settings.MAX_FILE_SIZE_MB
        }
    }


@app.get(f"{settings.API_PREFIX}/config")
async def get_config():
    return {
        "max_upload_files": settings.MAX_UPLOAD_FILES,
        "max_file_size_mb": settings.MAX_FILE_SIZE_MB,
        "allowed_extensions": settings.allowed_extensions_list,
        "rbac_levels": settings.RBAC_LEVELS
    }


# --- START: NEW ENDPOINTS FOR USER SIGNUP & CREATION ---

@app.post(f"{settings.API_PREFIX}/signup/admin", response_model=UserOut)
async def signup_admin_user(
    user_in: AdminSignUp,
    db: Session = Depends(get_db)
):
    """
    Create the first Super Admin user.
    This requires a secret key from the server settings.
    """
    
    # 1. CRITICAL: Check the secret key
    if user_in.secret_key != settings.ADMIN_SIGNUP_SECRET:
        raise HTTPException(
            status_code=403,
            detail="Invalid secret key. Not authorized."
        )

    # 2. Check if an admin already exists (makes it one-time use)
    admin_exists = db.query(models.User).filter(
        models.User.rbac_level == models.RBACLevel.ADMIN
    ).first()
    
    if admin_exists:
        raise HTTPException(
            status_code=400,
            detail="An admin account already exists."
        )
        
    # 3. Check if this specific username is taken
    existing_user = db.query(models.User).filter(
        models.User.username == user_in.username
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Username (email) already registered."
        )

    # 4. Hash the password
    hashed_password = get_password_hash(user_in.password)
    
    # 5. Create the new admin user
    new_admin = models.User(
        username=user_in.username,
        hashed_password=hashed_password,
        rbac_level=models.RBACLevel.ADMIN # Hardcode the role to ADMIN
    )
    
    # 6. Save to database
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    
    return new_admin


@app.post(f"{settings.API_PREFIX}/admin/create-user", response_model=UserOut)
async def admin_create_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_super_admin) # Locks endpoint
):
    """
    Super Admin endpoint to create a new Manager or Analyst.
    """
    existing_user = db.query(models.User).filter(
        models.User.username == user_in.username
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Username (email) already registered."
        )
        
    hashed_password = get_password_hash(user_in.password)
    
    new_user = models.User(
        username=user_in.username,
        hashed_password=hashed_password,
        rbac_level=user_in.role
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user


@app.post(f"{settings.API_PREFIX}/manager/create-analyst", response_model=UserOut)
async def manager_create_analyst(
    user_in: AnalystCreate,
    db: Session = Depends(get_db),
    manager_user: models.User = Depends(get_manager) # Locks endpoint
):
    """
    Manager-only endpoint to create a new Analyst.
    """
    existing_user = db.query(models.User).filter(
        models.User.username == user_in.username
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Username (email) already registered."
        )
        
    hashed_password = get_password_hash(user_in.password)
    
    new_user = models.User(
        username=user_in.username,
        hashed_password=hashed_password,
        rbac_level=models.RBACLevel.ANALYST # Role is hardcoded
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user

# --- END: NEW ENDPOINTS FOR USER SIGNUP & CREATION ---



@app.post(f"{settings.API_PREFIX}/upload")
async def upload_documents(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # (Your original code...)
    if len(files) > settings.MAX_UPLOAD_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {settings.MAX_UPLOAD_FILES} files allowed per upload"
        )
    
    for file in files:
        file_ext = '.' + file.filename.split('.')[-1].lower() if '.' in file.filename else ''
        if file_ext not in settings.allowed_extensions_list:
            raise HTTPException(
                status_code=400,
                detail=f"File type {file_ext} not allowed. Allowed: {', '.join(settings.allowed_extensions_list)}"
            )
        
        file.file.seek(0, 2)
        size = file.file.tell()
        file.file.seek(0)
        
        if size > settings.max_file_size_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"File '{file.filename}' exceeds {settings.MAX_FILE_SIZE_MB}MB limit (size: {size / 1024 / 1024:.2f}MB)"
            )
    
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

    job_id = str(uuid.uuid4())
    gcs_prefix = f"uploads/{job_id}/"
    
    print(f"Starting upload for job {job_id}: {len(files)} files")
    
    filenames = []
    file_types = []
    
    for file in files:
        try:
            gcs_path = f"{gcs_prefix}{file.filename}"
            gcs_storage.upload_file(file.file, gcs_path)
            filenames.append(file.filename)
            
            ext = file.filename.split('.')[-1].lower()
            if ext in ['pdf', 'docx', 'txt']:
                file_types.append('document')
            elif ext in ['mp3', 'wav', 'm4a']:
                file_types.append('audio')
            elif ext in ['mp4', 'avi', 'mov']:
                file_types.append('video')
            else:
                file_types.append('document')
            
            print(f"Uploaded: {file.filename} to {gcs_path}")
        except Exception as e:
            print(f"Error uploading {file.filename}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload {file.filename}: {str(e)}"
            )
    
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
    
    redis_pubsub.publish_job(job_id, gcs_prefix, settings.REDIS_CHANNEL_DOCUMENT)
    
    if 'audio' in file_types:
        redis_pubsub.publish_job(job_id, gcs_prefix, settings.REDIS_CHANNEL_AUDIO)
    if 'video' in file_types:
        redis_pubsub.publish_job(job_id, gcs_prefix, settings.REDIS_CHANNEL_VIDEO)
    
    print(f"Job {job_id} created and queued for processing")
    
    return {
        "job_id": job_id,
        "status": "queued",
        "total_files": len(files),
        "message": f"Successfully uploaded {len(files)} files. Processing started."
    }

@app.get(f"{settings.API_PREFIX}/jobs/{{job_id}}/status")
async def get_job_status(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # (Your original code...)
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
    # (Your original code...)
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
    # (Your original code...)
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



@app.get(f"{settings.API_PREFIX}/documents/{{document_id}}/summary")
async def get_document_summary(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # (Your original code...)
    document = db.query(models.Document).filter(
        models.Document.id == document_id
    ).first()
    
    if not document:
        raise HTTPException(404, "Document not found")

    if not user_has_document_access(current_user, document):
        raise HTTPException(status_code=403, detail="Insufficient permissions for this document")
    
    if document.summary_text:
        content = document.summary_text
    elif document.summary_path:
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
    # (Your original code...)
    document = db.query(models.Document).filter(
        models.Document.id == document_id
    ).first()
    
    if not document:
        raise HTTPException(404, "Document not found")

    if not user_has_document_access(current_user, document):
        raise HTTPException(status_code=403, detail="Insufficient permissions for this document")
    
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
    # (Your original code...)
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

@app.get(f"{settings.API_PREFIX}/jobs/{{job_id}}/graph")
async def get_job_graph(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get combined knowledge graph from Neo4j for all documents in a job"""
    
    # 1. Check if job exists and user has access (from SQL)
    job = db.query(models.ProcessingJob).filter(
        models.ProcessingJob.id == job_id
    ).first()
    
    if not job:
        raise HTTPException(404, "Job not found")

    if not user_has_job_access(current_user, job):
        raise HTTPException(status_code=403, detail="Insufficient permissions for this job")
    
    if not graph:
        raise HTTPException(500, "Graph database is not connected")

    # 2. Get all document IDs for this job (from SQL)
    doc_ids = db.query(models.Document.id).filter(
        models.Document.job_id == job_id
    ).all()
    
    # Convert list of tuples to list of strings
    document_ids_list = [str(doc_id[0]) for doc_id in doc_ids]

    if not document_ids_list:
        return {"nodes": [], "relationships": []} # No documents, empty graph

    # 3. Query Neo4j for nodes and relationships matching these document IDs
    cypher_query = """
    MATCH (n)
    WHERE n.document_id IN $doc_ids
    OPTIONAL MATCH (n)-[r]-(m)
    WHERE m.document_id IN $doc_ids
    RETURN n, r, m
    """
    
    try:
        result = graph.query(cypher_query, params={"doc_ids": document_ids_list})
    except Exception as e:
        print(f"❌ Neo4j query failed: {e}")
        raise HTTPException(500, f"Graph query failed: {str(e)}")

    # 4. Format the Neo4j results into the JSON your frontend expects
    nodes = {}
    relationships = set()

    for record in result:
        node_n = record["n"]
        rel = record["r"]
        node_m = record["m"]

        if node_n:
            nodes[node_n.get("id")] = {
                "id": node_n.get("id"),
                "label": node_n.get("id"), # Use 'id' for label
                "type": list(node_n.labels)[0] if node_n.labels else "Node",
                "properties": dict(node_n)
            }
        
        if node_m:
            nodes[node_m.get("id")] = {
                "id": node_m.get("id"),
                "label": node_m.get("id"),
                "type": list(node_m.labels)[0] if node_m.labels else "Node",
                "properties": dict(node_m)
            }

        if rel:
            relationships.add((
                rel.start_node.get("id"), 
                rel.end_node.get("id"),
                rel.type,
                tuple(rel.properties.items())
            ))

    return {
        "nodes": list(nodes.values()),
        "relationships": [
            {
                "source": source_id,
                "target": target_id,
                "type": rel_type,
                "properties": dict(props)
            }
            for (source_id, target_id, rel_type, props) in relationships
        ]
    }


@app.post(f"{settings.API_PREFIX}/chat")
async def chat_with_documents(
    message: str,
    job_id: Optional[str] = None,
    document_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # (Your original code...)
    if not message:
        raise HTTPException(400, "Message is required")
    
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
            if not job_id:
                job_id = document.job_id

        results = vector_store.similarity_search(
            query=message,
            k=8,
            document_id=document_id,
            job_id=job_id,
            user=current_user
        )

        context = "\n\n".join([r["chunk_text"][:800] for r in results[:5]])
        
        if settings.GEMINI_API_KEY:
            try:
                agent = GoogleDocAgent(api_key=settings.GEMINI_API_KEY, model=settings.GOOGLE_CHAT_MODEL)
                
                enriched_chunks = []
                for r in results[:8]:
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
                    include_static_refs=False
                )
                
                display_sources = []
                for r in results[:5]:
                    display_sources.append({
                        "chunk_text": r["chunk_text"][:500],
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