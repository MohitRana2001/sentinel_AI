from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, ForeignKey, Enum as SQLEnum, Float, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from datetime import datetime
import enum
from database import Base
from pgvector.sqlalchemy import Vector


class RBACLevel(str, enum.Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    ANALYST = "analyst"


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FileType(str, enum.Enum):
    DOCUMENT = "document"
    AUDIO = "audio"
    VIDEO = "video"
    IMAGE = "image"


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    
    # RBAC - Role-based access control
    rbac_level = Column(SQLEnum(RBACLevel), default=RBACLevel.ANALYST, nullable=False)
    
    # Manager-Analyst relationship
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    jobs = relationship("ProcessingJob", back_populates="user", foreign_keys="ProcessingJob.user_id")
    
    # Self-referential relationships for manager-analyst hierarchy
    analysts = relationship("User", back_populates="manager", foreign_keys=[manager_id])
    manager = relationship("User", back_populates="analysts", foreign_keys=[manager_id], remote_side=[id],)
    
    # Track who created this user
    creator = relationship("User", foreign_keys=[created_by], remote_side=[id])


class ProcessingJob(Base):
    """Processing job model with format: manager_username/analyst_username/job_uuid"""
    __tablename__ = "processing_jobs"
    
    id = Column(String, primary_key=True, index=True)  # Format: manager_username/analyst_username/uuid
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    status = Column(SQLEnum(JobStatus), default=JobStatus.QUEUED, nullable=False)
    
    # Case Management - allows grouping and extending cases
    case_name = Column(String, index=True, nullable=True)  # Case identifier to group related uploads
    parent_job_id = Column(String, ForeignKey("processing_jobs.id"), nullable=True)  # Reference to parent job if extending case
    
    gcs_prefix = Column(String, nullable=False)
    
    original_filenames = Column(JSON)
    file_types = Column(JSON)  # Types of files (document/audio/video)
    total_files = Column(Integer, default=0)
    processed_files = Column(Integer, default=0)
    
    # Timing information for each processing stage
    processing_stages = Column(JSON, default=dict)  # {"document_processing": 12.5, "graph_building": 8.3, ...}
    current_stage = Column(String)  # Current processing stage
    
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    error_message = Column(Text)
    
    user = relationship("User", back_populates="jobs", foreign_keys=[user_id])
    documents = relationship("Document", back_populates="job")
    
    # Self-referential for case extensions
    child_jobs = relationship("ProcessingJob", backref="parent_job", remote_side=[id], foreign_keys=[parent_job_id])
    
    def parse_job_id(self):
        """Parse job_id to extract manager_username, analyst_username, and job_uuid"""
        parts = self.id.split("/")
        if len(parts) == 3:
            return {
                "manager_username": parts[0],
                "analyst_username": parts[1],
                "job_uuid": parts[2]
            }
        return None


class Document(Base):
    """Document model - represents individual processed files"""
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("job_id", "original_filename", name="uq_job_document"),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, ForeignKey("processing_jobs.id"), nullable=False)
    
    original_filename = Column(String, nullable=False)
    file_type = Column(SQLEnum(FileType), nullable=False)
    gcs_path = Column(String, nullable=False)  # Original file path in GCS
    
    extracted_text_path = Column(String)
    translated_text_path = Column(String)
    summary_path = Column(String)
    transcription_path = Column(String)  # For audio/video files
    
    # Summary text (cached for quick access)
    summary_text = Column(Text)
    
    # Per-artifact status and timing tracking
    status = Column(SQLEnum(JobStatus), default=JobStatus.QUEUED, nullable=False)
    processing_stages = Column(JSON, default=dict)  # {"extraction": 5.2, "summarization": 3.1, ...}
    current_stage = Column(String)  # Current processing stage for this artifact
    error_message = Column(Text)  # Error message specific to this artifact
    
    started_at = Column(DateTime)  # When processing started for this artifact
    completed_at = Column(DateTime)  # When processing completed for this artifact
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    job = relationship("ProcessingJob", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document")
    graph_entities = relationship("GraphEntity", back_populates="document")


class DocumentChunk(Base):
    """Document chunks with vector embeddings stored in AlloyDB"""
    __tablename__ = "document_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    
    # Chunk information
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    
    # Vector embedding (pgvector)
    embedding = Column(Vector(768))  # Gemma embedding dimension
    
    chunk_metadata = Column("metadata", JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    document = relationship("Document", back_populates="chunks")

    # similarity search
    __table_args__ = (
        Index(
            "ix_document_chunks_embedding",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100}
        ),
    )


class GraphEntity(Base):
    """Graph entities extracted from documents"""
    __tablename__ = "graph_entities"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    
    entity_id = Column(String, unique=True, index=True, nullable=False)  # Neo4j node ID or unique identifier
    entity_name = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    properties = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    document = relationship("Document", back_populates="graph_entities")


class GraphRelationship(Base):
    __tablename__ = "graph_relationships"
    
    id = Column(Integer, primary_key=True, index=True)
    
    source_entity_id = Column(String, ForeignKey("graph_entities.entity_id"), nullable=False)
    target_entity_id = Column(String, ForeignKey("graph_entities.entity_id"), nullable=False)
    relationship_type = Column(String, nullable=False)
    properties = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class ActivityLog(Base):
    __tablename__ = "activity_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    activity_type = Column(String, nullable=False)  # upload, query, view_graph, etc.
    details = Column(JSON)
    
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


# --- PERSON OF INTEREST MODELS ---

EMBEDDING_GEMMA_DIM = 768 
PHOTO_VECTOR_DIM = 1024 

class PersonOfInterest(Base):
    __tablename__ = "person_of_interest"

    id = Column(Integer, primary_key=True, index=True)
    
    name = Column(String, index=True, nullable=False)
    
    # Stores arbitrary key-value pairs (e.g., "Names": [...], "Status": "Gangster")
    details = Column(JSONB, nullable=False)
    
    photograph_base64 = Column(Text, nullable=True)
    
    # Vectors
    details_embedding = Column(Vector(EMBEDDING_GEMMA_DIM))
    photograph_embedding = Column(Vector(PHOTO_VECTOR_DIM))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index(
            "ix_poi_details_embedding",
            "details_embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100}
        ),
        Index(
            "ix_poi_photo_embedding",
            "photograph_embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100}
        ),
    )

class CDRRecord(Base):
    """CDR (Call Data Records) stored as JSONB"""
    __tablename__ = "cdr_records"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, ForeignKey("processing_jobs.id"), nullable=False, index=True)
    
    # Original file information
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)  # GCS path to original file
    
    # CDR data in JSONB format (array of call records)
    data = Column(JSONB, nullable=False)  # [{"caller": "...", "called": "...", "timestamp": "...", ...}, ...]
    
    # Metadata
    record_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    job = relationship("ProcessingJob", backref="cdr_records")
    
    __table_args__ = (
        Index("ix_cdr_job_id", "job_id"),
    )


EMBEDDING_GEMMA_DIM = 768 

PHOTO_VECTOR_DIM = 1024
