"""
Media Upload Routes
Handles document, audio, video, and CDR uploads
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Optional
import os
import uuid
from pathlib import Path
from datetime import datetime

router = APIRouter(prefix="/media", tags=["media"])

# Supported languages from document_processor.py
SUPPORTED_LANGUAGES = {
    'hi', 'bn', 'pa', 'gu', 'kn', 'ml', 'mr', 'ta', 'te', 'zh', 'en'
}

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@router.post("/upload")
async def upload_media(
    file: UploadFile = File(...),
    media_type: str = Form(...),
    language: Optional[str] = Form(None)
):
    """
    Upload document, audio, video, or CDR file
    
    - **document**: Auto-detects language using langid
    - **audio/video**: Requires language parameter for transcription
    - **cdr**: Call Data Record processing
    """
    
    # Validate media type
    if media_type not in ['document', 'audio', 'video', 'cdr']:
        raise HTTPException(status_code=400, detail=f"Invalid media_type: {media_type}")
    
    # Validate language for audio/video
    if media_type in ['audio', 'video']:
        if not language:
            raise HTTPException(
                status_code=400,
                detail=f"Language required for {media_type}. Supported: {', '.join(SUPPORTED_LANGUAGES)}"
            )
        if language not in SUPPORTED_LANGUAGES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported language: {language}. Supported: {', '.join(SUPPORTED_LANGUAGES)}"
            )
    
    # Generate unique IDs
    media_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    
    # Create media type specific directory
    media_dir = UPLOAD_DIR / media_type
    media_dir.mkdir(exist_ok=True)
    
    # Save file
    file_extension = Path(file.filename).suffix
    file_path = media_dir / f"{media_id}{file_extension}"
    
    try:
        # Read and save file
        content = await file.read()
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        print(f"✅ Saved {media_type} file: {file_path}")
        print(f"   Original: {file.filename}")
        print(f"   Size: {len(content) / 1024 / 1024:.2f} MB")
        if language:
            print(f"   Language: {language}")
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save file: {str(e)}"
        )
    
    # TODO: Enqueue job to Redis for background processing
    # For now, just return success response
    
    # Prepare job data for future Redis implementation
    job_data = {
        "media_id": media_id,
        "job_id": job_id,
        "file_path": str(file_path),
        "media_type": media_type,
        "original_filename": file.filename,
        "file_size": len(content),
        "created_at": datetime.utcnow().isoformat(),
    }
    
    if language:
        job_data["language"] = language
    
    print(f"📋 Job data prepared: {job_data}")
    print(f"⚠️  Note: Redis queue not implemented yet. File saved but not processed.")
    
    return JSONResponse({
        "media_id": media_id,
        "job_id": job_id,
        "status": "queued",
        "message": f"{media_type.capitalize()} uploaded successfully (queued for processing)"
    }, status_code=202)


@router.get("/status/{job_id}")
async def get_media_status(job_id: str):
    """
    Get processing status of media
    
    TODO: Implement actual job status lookup from Redis/Database
    """
    
    # For now, return mock status
    # In production, this should query Redis or database
    
    print(f"📊 Status check for job: {job_id}")
    print(f"⚠️  Note: Returning mock data. Implement actual status lookup.")
    
    # Mock response - replace with actual implementation
    return {
        "status": "processing",
        "progress": 45,
        "message": "Processing in progress (mock data)"
    }


# Example of what the full implementation should look like:
"""
from services.queue_service import QueueService

@router.post("/upload")
async def upload_media(...):
    # ... save file ...
    
    # Enqueue job to Redis
    job_id = await QueueService.add_media_job(job_data)
    
    return { "job_id": job_id, ... }

@router.get("/status/{job_id}")
async def get_media_status(job_id: str):
    # Query job status from Redis/Database
    status = await QueueService.get_job_status(job_id)
    return status
"""
