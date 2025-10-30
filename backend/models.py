"""
Database models for Sentinel AI with RBAC support
"""
from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, ForeignKey, Enum as SQLEnum, Float, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import ARRAY
from datetime import datetime
import enum
from database import Base
from pgvector.sqlalchemy import Vector


class RBACLevel(str, enum.Enum):
    """RBAC hierarchy levels"""
    STATION = "station"
    DISTRICT = "district"
    STATE = "state"


class JobStatus(str, enum.Enum):
    """Job processing status"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FileType(str, enum.Enum):
    """File types"""
    DOCUMENT = "document"
    AUDIO = "audio"
    VIDEO = "video"
    IMAGE = "image"


class User(Base):
    """User model with RBAC"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    
    # RBAC
    rbac_level = Column(SQLEnum(RBACLevel), default=RBACLevel.STATION, nullable=False)
    station_id = Column(String, index=True)
    district_id = Column(String, index=True)
    state_id = Column(String, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    jobs = relationship("ProcessingJob", back_populates="user")


class ProcessingJob(Base):
    """Processing job model"""
    __tablename__ = "processing_jobs"
    
    id = Column(String, primary_key=True, index=True)  # UUID
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # RBAC - Inherit from user
    rbac_level = Column(SQLEnum(RBACLevel), nullable=False)
    station_id = Column(String, index=True)
    district_id = Column(String, index=True)
    state_id = Column(String, index=True)
    
    status = Column(SQLEnum(JobStatus), default=JobStatus.QUEUED, nullable=False)
    
    # GCS Information
    gcs_prefix = Column(String, nullable=False)
    
    # File information
    original_filenames = Column(JSON)
    file_types = Column(JSON)  # Types of files (document/audio/video)
    total_files = Column(Integer, default=0)
    processed_files = Column(Integer, default=0)
    
    # Processing metadata
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    error_message = Column(Text)
    
    # Relationships
    user = relationship("User", back_populates="jobs")
    documents = relationship("Document", back_populates="job")


class Document(Base):
    """Document model - represents individual processed files"""
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("job_id", "original_filename", name="uq_job_document"),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, ForeignKey("processing_jobs.id"), nullable=False)
    
    # RBAC
    rbac_level = Column(SQLEnum(RBACLevel), nullable=False)
    station_id = Column(String, index=True)
    district_id = Column(String, index=True)
    state_id = Column(String, index=True)
    
    # File information
    original_filename = Column(String, nullable=False)
    file_type = Column(SQLEnum(FileType), nullable=False)
    gcs_path = Column(String, nullable=False)  # Original file path in GCS
    
    # Processing artifacts (GCS paths)
    extracted_text_path = Column(String)
    translated_text_path = Column(String)
    summary_path = Column(String)
    transcription_path = Column(String)  # For audio/video files
    
    # Summary text (cached for quick access)
    summary_text = Column(Text)
    
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
    
    # Metadata
    chunk_metadata = Column("metadata", JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    document = relationship("Document", back_populates="chunks")
    
    # Index for vector similarity search
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
    
    # Entity information
    entity_id = Column(String, unique=True, index=True, nullable=False)  # Neo4j node ID or unique identifier
    entity_name = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    properties = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    document = relationship("Document", back_populates="graph_entities")


class GraphRelationship(Base):
    """Graph relationships between entities"""
    __tablename__ = "graph_relationships"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Relationship information
    source_entity_id = Column(String, ForeignKey("graph_entities.entity_id"), nullable=False)
    target_entity_id = Column(String, ForeignKey("graph_entities.entity_id"), nullable=False)
    relationship_type = Column(String, nullable=False)
    properties = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class ActivityLog(Base):
    """User activity log for tracking and audit"""
    __tablename__ = "activity_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    activity_type = Column(String, nullable=False)  # upload, query, view_graph, etc.
    details = Column(JSON)
    
    # RBAC context
    rbac_level = Column(SQLEnum(RBACLevel))
    station_id = Column(String)
    district_id = Column(String)
    state_id = Column(String)
    
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
