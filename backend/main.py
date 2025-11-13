from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, Query, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
import uuid
from langchain_ollama import OllamaEmbeddings
import json

import enum
from pydantic import BaseModel, EmailStr
from datetime import datetime
from security import get_password_hash 

from config import settings
from database import get_db, init_db
import models
from models import RBACLevel 

# Import new configurable storage system
from storage_config import storage_manager
from redis_pubsub import redis_pubsub
from vector_store import VectorStore
from cdr_processor import cdr_processor
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

# --- START: PYDANTIC MODELS FOR USER MANAGEMENT ---
class ManagerCreate(BaseModel):
    """Data model for Admin to create a Manager."""
    email: EmailStr
    username: str
    password: str

class AnalystCreate(BaseModel):
    """Data model for Admin/Manager to create an Analyst."""
    email: EmailStr
    username: str
    password: str
    manager_id: int

class AnalystCreateByManager(BaseModel):
    """Data model for Manager to create an Analyst (manager_id is implicit)."""
    email: EmailStr
    username: str
    password: str

class AdminSignUp(BaseModel):
    """Data model for the first admin sign-up."""
    email: EmailStr
    username: str
    password: str
    secret_key: str

class UserOut(BaseModel):
    """Data model for returning user info (safely, without password)."""
    id: int
    email: str
    username: str
    rbac_level: RBACLevel
    manager_id: Optional[int] = None
    created_by: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

class AnalystWithManager(BaseModel):
    """Analyst with manager information."""
    id: int
    email: str
    username: str
    manager_id: Optional[int]
    manager_email: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ManagerWithAnalysts(BaseModel):
    """Manager with their analysts."""
    id: int
    email: str
    username: str
    created_at: datetime
    analysts: List[UserOut] = []

    class Config:
        from_attributes = True

class ReassignAnalyst(BaseModel):
    """Data model to reassign analyst to a different manager."""
    new_manager_id: int

class JobWithAnalyst(BaseModel):
    """Job with analyst information for manager view."""
    job_id: str
    analyst_email: str
    analyst_username: str
    status: str
    total_files: int
    processed_files: int
    created_at: datetime
    progress_percentage: float

class PersonOfInterestCreate(BaseModel):
    name: str
    details: Dict[str, Any]
    photograph_base64: Optional[str] = None
# --- END: PYDANTIC MODELS ---


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
            url = settings.NEO4J_URI,
            username = settings.NEO4J_USERNAME,
            password = settings.NEO4J_PASSWORD,
            database = settings.NEO4J_DATABASE
        )
    except Exception as e:
        print(f"Failed to connect to Neo4j in main.py: {e}")
        graph = None
else:
    print("Neo4j is not installed, graph API will not function.")
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
    print("Registered Routes")
    for route in app.routes:
        print(route.path)


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

def get_poi_embedding_model():
    """
    Returns the Ollama embedding model for vectorizing PoI details.
    Using the same model as document processor.
    """
    return OllamaEmbeddings(
        model="embeddinggemma:latest",
        # Assuming Ollama runs on port 11434 on the configured host
        # base_url=f"http://{settings.CHAT_LLM_HOST}:11434"
        base_url="http://127.0.0.1:11434"  
    )

def get_photo_embedding(base64_str: str) -> List[float]:
    """
    Placeholder for generating vision embeddings from a base64 image.
    TODO: Shounak to provide the vision model logic here.
    """
    # Returning a zero-vector of dimension 1024 as a placeholder
    return [0.0] * 1024

# --- START: USER MANAGEMENT ENDPOINTS ---

@app.post(f"{settings.API_PREFIX}/admin/signup", response_model=UserOut)
async def signup_admin(
    user_in: AdminSignUp,
    db: Session = Depends(get_db)
):
    """
    Create the first Admin user. Requires a secret key from server settings.
    This is a one-time operation.
    """
    if user_in.secret_key != settings.ADMIN_SIGNUP_SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret key")

    admin_exists = db.query(models.User).filter(
        models.User.rbac_level == models.RBACLevel.ADMIN
    ).first()
    
    if admin_exists:
        raise HTTPException(status_code=400, detail="An admin account already exists")
        
    existing_user = db.query(models.User).filter(
        models.User.email == user_in.email
    ).first()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_admin = models.User(
        email=user_in.email,
        username=user_in.username,
        hashed_password=get_password_hash(user_in.password),
        rbac_level=models.RBACLevel.ADMIN
    )
    
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    
    return new_admin


@app.post(f"{settings.API_PREFIX}/admin/managers", response_model=UserOut)
async def admin_create_manager(
    user_in: ManagerCreate,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_super_admin)
):
    """Admin endpoint to create a new Manager."""
    existing_user = db.query(models.User).filter(
        models.User.email == user_in.email
    ).first()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    new_manager = models.User(
        email=user_in.email,
        username=user_in.username,
        hashed_password=get_password_hash(user_in.password),
        rbac_level=models.RBACLevel.MANAGER,
        created_by=admin_user.id
    )
    
    db.add(new_manager)
    db.commit()
    db.refresh(new_manager)
    
    return new_manager


@app.get(f"{settings.API_PREFIX}/admin/managers", response_model=List[ManagerWithAnalysts])
async def admin_list_managers(
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_super_admin)
):
    """Admin endpoint to list all managers with their analysts."""
    managers = db.query(models.User).filter(
        models.User.rbac_level == models.RBACLevel.MANAGER
    ).all()
    
    result = []
    for manager in managers:
        manager_data = ManagerWithAnalysts(
            id=manager.id,
            email=manager.email,
            username=manager.username,
            created_at=manager.created_at,
            analysts=[UserOut.from_orm(a) for a in manager.analysts]
        )
        result.append(manager_data)
    
    return result


@app.delete(f"{settings.API_PREFIX}/admin/managers/{{manager_id}}")
async def admin_delete_manager(
    manager_id: int,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_super_admin)
):
    """Admin endpoint to delete a manager."""
    manager = db.query(models.User).filter(
        models.User.id == manager_id,
        models.User.rbac_level == models.RBACLevel.MANAGER
    ).first()
    
    if not manager:
        raise HTTPException(status_code=404, detail="Manager not found")
    
    # Check if manager has analysts
    if manager.analysts:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete manager with {len(manager.analysts)} analyst(s). Reassign or delete analysts first."
        )
    
    db.delete(manager)
    db.commit()
    
    return {"message": f"Manager {manager.email} deleted successfully"}


@app.post(f"{settings.API_PREFIX}/admin/analysts", response_model=UserOut)
async def admin_create_analyst(
    user_in: AnalystCreate,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_super_admin)
):
    """Admin endpoint to create a new Analyst and assign to a manager."""
    existing_user = db.query(models.User).filter(
        models.User.email == user_in.email
    ).first()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Verify manager exists
    manager = db.query(models.User).filter(
        models.User.id == user_in.manager_id,
        models.User.rbac_level == models.RBACLevel.MANAGER
    ).first()
    
    if not manager:
        raise HTTPException(status_code=404, detail="Manager not found")
        
    new_analyst = models.User(
        email=user_in.email,
        username=user_in.username,
        hashed_password=get_password_hash(user_in.password),
        rbac_level=models.RBACLevel.ANALYST,
        manager_id=user_in.manager_id,
        created_by=admin_user.id
    )
    
    db.add(new_analyst)
    db.commit()
    db.refresh(new_analyst)
    
    return new_analyst


@app.get(f"{settings.API_PREFIX}/admin/analysts", response_model=List[AnalystWithManager])
async def admin_list_analysts(
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_super_admin)
):
    """Admin endpoint to list all analysts with their manager info."""
    analysts = db.query(models.User).filter(
        models.User.rbac_level == models.RBACLevel.ANALYST
    ).all()
    
    result = []
    for analyst in analysts:
        manager_email = None
        if analyst.manager_id:
            manager = db.query(models.User).filter(models.User.id == analyst.manager_id).first()
            if manager:
                manager_email = manager.email
        
        result.append(AnalystWithManager(
            id=analyst.id,
            email=analyst.email,
            username=analyst.username,
            manager_id=analyst.manager_id,
            manager_email=manager_email,
            created_at=analyst.created_at
        ))
    
    return result


@app.put(f"{settings.API_PREFIX}/admin/analysts/{{analyst_id}}/manager", response_model=UserOut)
async def admin_reassign_analyst(
    analyst_id: int,
    reassign_data: ReassignAnalyst,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_super_admin)
):
    """Admin endpoint to reassign an analyst to a different manager."""
    analyst = db.query(models.User).filter(
        models.User.id == analyst_id,
        models.User.rbac_level == models.RBACLevel.ANALYST
    ).first()
    
    if not analyst:
        raise HTTPException(status_code=404, detail="Analyst not found")
    
    new_manager = db.query(models.User).filter(
        models.User.id == reassign_data.new_manager_id,
        models.User.rbac_level == models.RBACLevel.MANAGER
    ).first()
    
    if not new_manager:
        raise HTTPException(status_code=404, detail="New manager not found")
    
    analyst.manager_id = reassign_data.new_manager_id
    db.commit()
    db.refresh(analyst)
    
    return analyst


@app.delete(f"{settings.API_PREFIX}/admin/analysts/{{analyst_id}}")
async def admin_delete_analyst(
    analyst_id: int,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_super_admin)
):
    """Admin endpoint to delete an analyst."""
    analyst = db.query(models.User).filter(
        models.User.id == analyst_id,
        models.User.rbac_level == models.RBACLevel.ANALYST
    ).first()
    
    if not analyst:
        raise HTTPException(status_code=404, detail="Analyst not found")
    
    db.delete(analyst)
    db.commit()
    
    return {"message": f"Analyst {analyst.email} deleted successfully"}


@app.post(f"{settings.API_PREFIX}/manager/analysts", response_model=UserOut)
async def manager_create_analyst(
    user_in: AnalystCreateByManager,
    db: Session = Depends(get_db),
    manager_user: models.User = Depends(get_manager)
):
    """Manager endpoint to create a new Analyst under themselves."""
    existing_user = db.query(models.User).filter(
        models.User.email == user_in.email
    ).first()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    new_analyst = models.User(
        email=user_in.email,
        username=user_in.username,
        hashed_password=get_password_hash(user_in.password),
        rbac_level=models.RBACLevel.ANALYST,
        manager_id=manager_user.id,
        created_by=manager_user.id
    )
    
    db.add(new_analyst)
    db.commit()
    db.refresh(new_analyst)
    
    return new_analyst


@app.get(f"{settings.API_PREFIX}/manager/analysts", response_model=List[UserOut])
async def manager_list_analysts(
    db: Session = Depends(get_db),
    manager_user: models.User = Depends(get_manager)
):
    """Manager endpoint to list their analysts."""
    return [UserOut.from_orm(a) for a in manager_user.analysts]


@app.delete(f"{settings.API_PREFIX}/manager/analysts/{{analyst_id}}")
async def manager_delete_analyst(
    analyst_id: int,
    db: Session = Depends(get_db),
    manager_user: models.User = Depends(get_manager)
):
    """Manager endpoint to delete one of their analysts."""
    analyst = db.query(models.User).filter(
        models.User.id == analyst_id,
        models.User.rbac_level == models.RBACLevel.ANALYST,
        models.User.manager_id == manager_user.id
    ).first()
    
    if not analyst:
        raise HTTPException(status_code=404, detail="Analyst not found or not managed by you")
    
    db.delete(analyst)
    db.commit()
    
    return {"message": f"Analyst {analyst.email} deleted successfully"}


@app.get(f"{settings.API_PREFIX}/manager/jobs", response_model=List[JobWithAnalyst])
async def manager_get_jobs(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    manager_user: models.User = Depends(get_manager)
):
    """Manager endpoint to get all jobs from their analysts."""
    query = db.query(models.ProcessingJob).order_by(
        models.ProcessingJob.created_at.desc()
    )
    query = filter_jobs_scope(query, manager_user)
    jobs = query.limit(limit).offset(offset).all()
    
    result = []
    for job in jobs:
        analyst = job.user
        progress = (job.processed_files / job.total_files * 100) if job.total_files > 0 else 0
        
        result.append(JobWithAnalyst(
            job_id=job.id,
            analyst_email=analyst.email,
            analyst_username=analyst.username,
            status=job.status.value,
            total_files=job.total_files,
            processed_files=job.processed_files,
            created_at=job.created_at,
            progress_percentage=round(progress, 2)
        ))
    
    return result


@app.get(f"{settings.API_PREFIX}/analyst/jobs")
async def analyst_get_jobs(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Analyst endpoint to get their own jobs."""
    if current_user.rbac_level != models.RBACLevel.ANALYST:
        raise HTTPException(status_code=403, detail="Analyst access required")
    
    query = db.query(models.ProcessingJob).filter(
        models.ProcessingJob.user_id == current_user.id
    ).order_by(models.ProcessingJob.created_at.desc())
    
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

# --- END: USER MANAGEMENT ENDPOINTS ---

@app.post(f"{settings.API_PREFIX}/person-of-interest")
async def create_person_of_interest(
    poi_in: PersonOfInterestCreate,
    db: Session = Depends(get_db),
    #current_user: models.User = Depends(get_current_user)
):
    """Creates a new Person of Interest with embeddings."""
    
    print(f"Creating PoI: {poi_in.name}")
    
    # 1. Generate Text Embedding for the JSON details
    details_str = json.dumps(poi_in.details)
    
    try:
        embed_model = get_poi_embedding_model()
        details_embedding = embed_model.embed_query(details_str)
        print(f"Generated text embedding of length: {len(details_embedding)}")
    except Exception as e:
        print(f"Error generating text embedding: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate text embedding: {str(e)}")

    # 2. Generate Photo Embedding
    photo_embedding = None
    if poi_in.photograph_base64:
        try:
            photo_embedding = get_photo_embedding(poi_in.photograph_base64)
            print(f"Generated photo embedding of length: {len(photo_embedding)}")
        except Exception as e:
            print(f"Error generating photo embedding: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to generate photo embedding: {str(e)}")

    # 3. Save to Database
    new_poi = models.PersonOfInterest(
        name=poi_in.name,
        details=poi_in.details,
        photograph_base64=poi_in.photograph_base64,
        details_embedding=details_embedding,
        photograph_embedding=photo_embedding
    )
    
    db.add(new_poi)
    db.commit()
    db.refresh(new_poi)
    
    return {"id": new_poi.id, "name": new_poi.name, "message": "Person of Interest created successfully"}

@app.post(f"{settings.API_PREFIX}/upload")
async def upload_documents(
    files: List[UploadFile] = File(...),
    media_types: List[str] = Form(default=[]),
    languages: List[str] = Form(default=[]),
    suspects: str = Form(default="[]"),
    case_name: str = Form(...),  # MANDATORY: Case name for grouping jobs
    parent_job_id: str = Form(default=None),  # NEW: Parent job ID for extending cases
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Validate case_name is provided and non-empty
    if not case_name or not case_name.strip():
        raise HTTPException(
            status_code=400,
            detail="Case name is required and cannot be empty"
        )
    
    # Parse suspects from JSON string
    try:
        suspects_data = json.loads(suspects) if suspects else []
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Invalid suspects JSON format"
        )
    
    # Validation checks
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
    
    # RBAC check: Only analysts and managers can upload
    if current_user.rbac_level == models.RBACLevel.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Admin users cannot upload documents. Only managers and analysts can upload."
        )
    
    # Generate job_id in format: manager_username/analyst_username/uuid
    job_uuid = str(uuid.uuid4())
    
    if current_user.rbac_level == models.RBACLevel.ANALYST:
        # For analysts, get their manager's email
        if not current_user.manager_id:
            raise HTTPException(
                status_code=400,
                detail="Analyst must be assigned to a manager before uploading"
            )
        
        manager = db.query(models.User).filter(
            models.User.id == current_user.manager_id
        ).first()
        
        if not manager:
            raise HTTPException(
                status_code=400,
                detail="Manager not found. Contact admin to assign you to a manager."
            )
        
        job_id = f"{manager.username}/{current_user.username}/{job_uuid}"
    
    elif current_user.rbac_level == models.RBACLevel.MANAGER:
        # For managers uploading, use their username for both manager and analyst parts
        job_id = f"{current_user.username}/{current_user.username}/{job_uuid}"
    
    else:
        raise HTTPException(
            status_code=403,
            detail="Invalid user role for document upload"
        )
    
    gcs_prefix = f"uploads/{job_id}/"
    
    print(f"Starting upload for job {job_id}: {len(files)} files")
    
    filenames = []
    file_types = []
    file_languages = []
    
    # Use provided media_types if available, otherwise infer from extension
    for idx, file in enumerate(files):
        try:
            gcs_path = f"{gcs_prefix}{file.filename}"
            storage_manager.upload_file(file.file, gcs_path)
            filenames.append(file.filename)
            
            # Determine file type from media_types if provided, otherwise from extension
            if idx < len(media_types) and media_types[idx]:
                file_type = media_types[idx]
            else:
                ext = file.filename.split('.')[-1].lower()
                if ext in ['pdf', 'docx', 'txt']:
                    file_type = 'document'
                elif ext in ['mp3', 'wav', 'm4a']:
                    file_type = 'audio'
                elif ext in ['mp4', 'avi', 'mov']:
                    file_type = 'video'
                elif ext in ['csv', 'xlsx']:
                    file_type = 'cdr'
                else:
                    file_type = 'document'
            
            file_types.append(file_type)
            
            # Get language if provided
            if idx < len(languages) and languages[idx]:
                file_languages.append(languages[idx])
            else:
                file_languages.append(None)
            
            print(f"Uploaded: {file.filename} to {gcs_path} (type: {file_type})")
        except Exception as e:
            print(f"Error uploading {file.filename}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload {file.filename}: {str(e)}"
            )
    
    job = models.ProcessingJob(
        id=job_id,
        user_id=current_user.id,
        gcs_prefix=gcs_prefix,
        original_filenames=filenames,
        file_types=file_types,
        total_files=len(files),
        status=models.JobStatus.QUEUED,
        case_name=case_name,  # NEW: Store case name
        parent_job_id=parent_job_id  # NEW: Link to parent job if extending case
    )
    
    db.add(job)
    db.commit()
    db.refresh(job)
    
    # Save suspects to database
    for suspect_data in suspects_data:
        suspect = models.Suspect(
            id=suspect_data.get('id', str(uuid.uuid4())),
            job_id=job_id,
            fields=suspect_data.get('fields', [])
        )
        db.add(suspect)
    
    if suspects_data:
        db.commit()
        print(f"Saved {len(suspects_data)} suspects for job {job_id}")
    
    cdr_files_processed = 0
    for idx, (filename, file_type) in enumerate(zip(filenames, file_types)):
        if file_type == 'cdr':
            try:
                gcs_path = f"{gcs_prefix}{filename}"
                print(f"Processing CDR file: {filename}")
                
                # Download and convert CDR to JSONB
                cdr_data = cdr_processor.process_cdr_file(gcs_path)
                cdr_processor.validate_cdr_data(cdr_data)
                
                # Save CDR record to database
                cdr_record = models.CDRRecord(
                    job_id=job_id,
                    original_filename=filename,
                    file_path=gcs_path,
                    data=cdr_data,
                    record_count=len(cdr_data)
                )
                db.add(cdr_record)
                db.commit()
                
                cdr_files_processed += 1
                job.processed_files += 1
                db.commit()
                
                print(f"✅ CDR file processed: {filename} ({len(cdr_data)} records)")
            except Exception as e:
                print(f"❌ Error processing CDR file {filename}: {e}")
                job.error_message = f"CDR processing error: {str(e)}"
                db.commit()
    
    # Push per-file messages to Redis queues for true parallel processing
    # Each file gets its own message in a queue, distributed to available workers
    messages_queued = 0
    for idx, (filename, file_type) in enumerate(zip(filenames, file_types)):
        gcs_path = f"{gcs_prefix}{filename}"
        
        # Prepare metadata with language if available
        metadata = {}
        if idx < len(file_languages) and file_languages[idx]:
            metadata['language'] = file_languages[idx]
        
        if file_type == 'document':
            redis_pubsub.push_file_to_queue(job_id, gcs_path, filename, settings.REDIS_QUEUE_DOCUMENT, metadata)
            messages_queued += 1
        elif file_type == 'audio':
            redis_pubsub.push_file_to_queue(job_id, gcs_path, filename, settings.REDIS_QUEUE_AUDIO, metadata)
            messages_queued += 1
        elif file_type == 'video':
            redis_pubsub.push_file_to_queue(job_id, gcs_path, filename, settings.REDIS_QUEUE_VIDEO, metadata)
            messages_queued += 1
        # CDR files are processed synchronously above, no queue needed
    
    print(f"Job {job_id} created: {messages_queued} queued, {cdr_files_processed} CDR processed")
    
    return {
        "job_id": job_id,
        "status": "queued",
        "total_files": len(files),
        "suspects_count": len(suspects_data),
        "cdr_processed": cdr_files_processed,
        "message": f"Successfully uploaded {len(files)} files and {len(suspects_data)} suspects. Processing started."
    }

@app.get(f"{settings.API_PREFIX}/cases")
async def get_cases(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get all unique case names for the current user (or their analysts if manager)
    """
    query = db.query(models.ProcessingJob.case_name).filter(
        models.ProcessingJob.case_name.isnot(None)
    ).distinct()
    
    query = filter_jobs_scope(query, current_user)
    
    cases = [row[0] for row in query.all()]
    
    return {
        "cases": cases
    }


@app.get(f"{settings.API_PREFIX}/cases/{{case_name}}/jobs")
async def get_case_jobs(
    case_name: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get all jobs for a specific case
    """
    query = db.query(models.ProcessingJob).filter(
        models.ProcessingJob.case_name == case_name
    ).order_by(models.ProcessingJob.created_at.desc())
    
    query = filter_jobs_scope(query, current_user)
    jobs = query.all()
    
    return {
        "case_name": case_name,
        "jobs": [
            {
                "job_id": job.id,
                "status": job.status.value,
                "total_files": job.total_files,
                "processed_files": job.processed_files,
                "parent_job_id": job.parent_job_id,
                "created_at": job.created_at.isoformat(),
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            }
            for job in jobs
        ]
    }


@app.get(f"{settings.API_PREFIX}/jobs/{{job_id:path}}/status")
async def get_job_status(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
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
    
    # Get per-artifact status
    documents = db.query(models.Document).filter(
        models.Document.job_id == job_id
    ).all()
    
    artifacts = []
    total_artifact_progress = 0.0
    
    for doc in documents:
        # Calculate progress for this artifact using the same logic as Redis pub/sub
        artifact_progress = redis_pubsub._calculate_progress(
            current_stage=doc.current_stage,
            processing_stages=doc.processing_stages,
            file_type=doc.file_type.value if doc.file_type else None,
            status=doc.status.value if doc.status else "queued"
        )
        
        total_artifact_progress += artifact_progress
        
        artifacts.append({
            "id": doc.id,
            "filename": doc.original_filename,
            "file_type": doc.file_type.value,
            "status": doc.status.value if doc.status else "queued",
            "current_stage": doc.current_stage,
            "processing_stages": doc.processing_stages or {},
            "progress": artifact_progress,  # Per-artifact progress
            "started_at": doc.started_at.isoformat() if doc.started_at else None,
            "completed_at": doc.completed_at.isoformat() if doc.completed_at else None,
            "error_message": doc.error_message
        })
    
    # Calculate overall job progress as average of all artifacts
    progress_percentage = 0.0
    if len(documents) > 0:
        progress_percentage = total_artifact_progress / len(documents)
    elif job.total_files > 0:
        # Fallback to old calculation if no documents yet
        progress_percentage = (job.processed_files / job.total_files) * 100
    
    return {
        "job_id": job.id,
        "status": job.status.value,
        "case_name": job.case_name,
        "parent_job_id": job.parent_job_id,
        "total_files": job.total_files,
        "processed_files": job.processed_files,
        "progress_percentage": round(progress_percentage, 2),
        "current_stage": job.current_stage,
        "processing_stages": job.processing_stages or {},
        "artifacts": artifacts,  # NEW: Per-artifact status
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "error_message": job.error_message
    }


@app.get(f"{settings.API_PREFIX}/jobs/{{job_id:path}}/results")
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
            content = storage_manager.download_text(document.summary_path)
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
        content = storage_manager.download_text(text_path)
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
        content = storage_manager.download_text(document.translated_text_path)
    except:
        raise HTTPException(500, "Failed to retrieve translation")
    
    return {
        "document_id": document.id,
        "filename": document.original_filename,
        "content": content,
        "content_type": "translation"
    }

@app.get(f"{settings.API_PREFIX}/jobs/{{job_id:path}}/graph")
async def get_job_graph(
    job_id: str,
    document_ids: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get combined knowledge graph from Neo4j for all documents in a job"""
    
    print(f"📊 GET /graph called for job: {job_id}")
    
    # 1. Check access (same as before)
    job = db.query(models.ProcessingJob).filter(
        models.ProcessingJob.id == job_id
    ).first()
    
    if not job:
        raise HTTPException(404, "Job not found")
    if not user_has_job_access(current_user, job):
        raise HTTPException(403, "Insufficient permissions")
    if not graph:
        raise HTTPException(500, "Graph database is not connected")

    # 2. Get document IDs (same as before)
    if document_ids:
        selected_ids = [int(id.strip()) for id in document_ids.split(',') if id.strip()]
        doc_ids = db.query(models.Document.id).filter(
            models.Document.job_id == job_id,
            models.Document.id.in_(selected_ids)
        ).all()
    else:
        doc_ids = db.query(models.Document.id).filter(
            models.Document.job_id == job_id
        ).all()
    
    document_ids_list = [str(doc_id[0]) for doc_id in doc_ids]
    
    if not document_ids_list:
        return {"nodes": [], "relationships": []}

    # 3. ✅ UPDATED QUERY - Return labels directly in Cypher
    nodes_query = """
    MATCH (n)
    WHERE n.document_id IN $doc_ids
      AND NOT 'Document' IN labels(n)
      AND NOT 'User' IN labels(n)
    RETURN n.id as id, 
           CASE 
             WHEN size(labels(n)) > 1 THEN labels(n)[1]
             ELSE labels(n)[0]
           END as type,
           labels(n) as all_labels,
           properties(n) as properties
    """
    
    relationships_query = """
    MATCH (n)-[r]->(m)
    WHERE n.document_id IN $doc_ids
      AND m.document_id IN $doc_ids
      AND NOT 'Document' IN labels(n)
      AND NOT 'User' IN labels(n)
      AND NOT 'Document' IN labels(m)
      AND NOT 'User' IN labels(m)
    RETURN n.id as source_id,
           m.id as target_id,
           type(r) as rel_type,
           properties(r) as rel_properties
    """
    
    try:
        print(f"Fetching nodes...")
        nodes_result = graph.query(nodes_query, params={"doc_ids": document_ids_list})
        
        print(f"Fetching relationships...")
        rels_result = graph.query(relationships_query, params={"doc_ids": document_ids_list})
        
        print(f"Query successful")
        print(f"Nodes: {len(nodes_result)} records")
        print(f"Relationships: {len(rels_result)} records")
        
    except Exception as e:
        print(f"Neo4j query failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Graph query failed: {str(e)}")

    # 4. UPDATED PROCESSING - Use data from Cypher directly
    nodes = {}
    relationships = []
    
    # Process nodes - data is already extracted by Cypher
    for record in nodes_result:
        try:
            node_id = record.get("id")
            node_type = record.get("type")
            node_props = record.get("properties", {})
            all_labels = record.get("all_labels", [])
            
            if node_id:
                nodes[node_id] = {
                    "id": node_id,
                    "label": node_id,
                    "type": node_type if node_type else "Entity",
                    "properties": node_props if isinstance(node_props, dict) else {}
                }
                
                # Debug: print each node type
                print(f"Node: {node_id} -> Type: {node_type} (Labels: {all_labels})")
                
        except Exception as e:
            print(f"Error processing node: {e}")
            traceback.print_exc()
            continue
    
    # Process relationships - data is already extracted by Cypher
    for record in rels_result:
        try:
            source_id = record.get("source_id")
            target_id = record.get("target_id")
            rel_type = record.get("rel_type")
            rel_props = record.get("rel_properties", {})
            
            if source_id and target_id:
                relationships.append({
                    "source": source_id,
                    "target": target_id,
                    "type": rel_type if rel_type else "RELATED",
                    "properties": rel_props if isinstance(rel_props, dict) else {}
                })
        except Exception as e:
            print(f"Error processing relationship: {e}")
            continue
    
    # Count unique types for debugging
    unique_types = set(node["type"] for node in nodes.values())
    print(f"\nReturning {len(nodes)} nodes and {len(relationships)} relationships")
    print(f"Unique node types: {unique_types}")
    
    # Print sample data
    if nodes:
        sample_node = list(nodes.values())[0]
        print(f"📝 Sample node: {sample_node}")
    if relationships:
        print(f"📝 Sample relationship: {relationships[0]}")
    
    return {
        "nodes": list(nodes.values()),
        "relationships": relationships
    }
    
@app.post(f"{settings.API_PREFIX}/chat")
async def chat_with_documents(
    message: str,
    job_id: Optional[str] = None,
    document_ids: Optional[str] = None,  # comma-separated document IDs
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # (Your original code...)
    if not message:
        raise HTTPException(400, "Message is required")
    
    vector_store = VectorStore(db)
    
    # Parse document IDs if provided
    doc_id_list = None
    if document_ids:
        try:
            doc_id_list = [int(id.strip()) for id in document_ids.split(',') if id.strip()]
        except ValueError:
            raise HTTPException(400, "Invalid document_ids format")
    
    try:
        if job_id:
            job = db.query(models.ProcessingJob).filter(models.ProcessingJob.id == job_id).first()
            if not job:
                raise HTTPException(404, "Job not found")
            if not user_has_job_access(current_user, job):
                raise HTTPException(status_code=403, detail="Insufficient permissions for this job")

        # Verify access to selected documents if specified
        if doc_id_list:
            for doc_id in doc_id_list:
                document = db.query(models.Document).filter(models.Document.id == doc_id).first()
                if not document:
                    raise HTTPException(404, f"Document {doc_id} not found")
                if not user_has_document_access(current_user, document):
                    raise HTTPException(status_code=403, detail=f"Insufficient permissions for document {doc_id}")

        results = vector_store.similarity_search(
            query=message,
            k=8,
            document_ids=doc_id_list,
            job_id=job_id,
            user=current_user
        )

        context = "\n\n".join([r["chunk_text"][:800] for r in results[:5]])
        
        # ===== LOCAL DEV MODE: Use Gemini if configured =====
        if settings.USE_GEMINI_FOR_DEV and settings.GEMINI_API_KEY:
            try:
                print("Using Gemini for chat (LOCAL DEV MODE)")
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
                        "document_ids": document_ids if document_ids else "N/A",
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
                print(f"Gemini chat error, falling back to Ollama: {agent_error}")
                import traceback
                traceback.print_exc()

        # ===== PRODUCTION MODE: Use Ollama/Gemma =====
        print("🔧 Using Ollama for chat (PRODUCTION MODE)")
        try:
            from ollama import Client
            ollama_client = Client(host=f"http://{settings.CHAT_LLM_HOST}:{settings.CHAT_LLM_PORT}")
            
            # Prepare context from chunks
            context_with_sources = []
            for idx, r in enumerate(results[:5]):
                chunk_preview = r["chunk_text"][:800]
                context_with_sources.append(f"[Source {idx+1}]\n{chunk_preview}")
            
            full_context = "\n\n".join(context_with_sources)
            
            # Create RAG prompt
            prompt = f"""You are a helpful assistant analyzing documents. Based on the following document excerpts, answer the      user's question accurately and concisely.

Document Excerpts:
{full_context}

User Question: {message}

Please provide a clear and informative answer based only on the information in the excerpts above. If the answer is not in the excerpts, say so."""
            
            # Call Ollama
            response = ollama_client.chat(
                model=settings.CHAT_LLM_MODEL,
                messages=[{
                    'role': 'user',
                    'content': prompt,
                }],
            )
            
            response_text = response['message']['content']
            
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
                "mode": f"ollama-{settings.CHAT_LLM_MODEL}"
            }
        except Exception as ollama_error:
            print(f"Ollama chat error: {ollama_error}")
            import traceback
            traceback.print_exc()
            
            # Final fallback: return context only
            return {
                "response": f"Based on the document excerpts:\n\n{context}\n\n(Chat LLM unavailable)",
                "sources": results[:5],
                "mode": "context-only"
            }
    except Exception as e:
        print(f"Chat error: {e}")
        raise HTTPException(500, f"Chat failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )