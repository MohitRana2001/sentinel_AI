"""
Configuration for Sentinel AI - Edge Inference System
"""
import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict


# Resolve project root (two levels up: backend/config.py -> backend -> repo root)
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from local files before Pydantic reads them.
# .env.local overrides .env to mirror frontend conventions.
load_dotenv(BASE_DIR / ".env", override=False)
load_dotenv(BASE_DIR / ".env.local", override=True)


class Settings(BaseSettings):
    """Application settings"""
    
    # App Configuration
    ENV: str = os.getenv("ENV", "development")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_PREFIX: str = "/api/v1"
    ADMIN_SIGNUP_SECRET: str = "D9ig7olbsvvDcYdubTl90ZcxdbLyQfVDTDXKldmyYGo"

    NEO4J_URI: str = os.getenv("NEO4j_URI", "url")
    NEO4J_USERNAME: str = os.getenv("NEO4J_USERNAME", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4j_PASSWORD", "pass")
    NEO4J_DATABASE: str = os.getenv("NEO4J_DATABASE", "neo4j")

    
    USE_GEMINI_FOR_DEV: bool = os.getenv("USE_GEMINI_FOR_DEV", "false").lower() == "true"
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    USE_SQLITE_FOR_DEV: bool = os.getenv("USE_SQLITE_FOR_DEV", "false").lower() == "true"
    SQLITE_DB_PATH: str = os.getenv("SQLITE_DB_PATH", "./sentinel_dev.db")
    
    MAX_UPLOAD_FILES: int = int(os.getenv("MAX_UPLOAD_FILES", "10"))
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "4"))
    ALLOWED_EXTENSIONS: str = os.getenv("ALLOWED_EXTENSIONS", ".pdf,.docx,.txt,.mp3,.wav,.mp4,.avi,.mov")
    
    # Supported backends: 'gcs', 's3', 'local', 'azure' (future)
    STORAGE_BACKEND: str = os.getenv("STORAGE_BACKEND", "gcs")
    
    # GCS Configuration
    GCS_BUCKET_NAME: str = os.getenv("GCS_BUCKET_NAME", "")
    GCS_PROJECT_ID: str = os.getenv("GCS_PROJECT_ID", "")
    GCS_CREDENTIALS_PATH: str = os.getenv("GCS_CREDENTIALS_PATH", "/app/credentials/gcs-key.json")

    # Local Storage Configuration
    LOCAL_STORAGE_PATH: str = os.getenv("LOCAL_STORAGE_PATH", "./.local_storage")

    LOCAL_GCS_STORAGE_PATH: str = os.getenv("LOCAL_GCS_STORAGE_PATH", "./.local_gcs")
    
    # Redis Configuration
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    
    # Redis Pub/Sub Channels (legacy - for backward compatibility)
    REDIS_CHANNEL_DOCUMENT: str = "document_processor"
    REDIS_CHANNEL_AUDIO: str = "audio_processor"
    REDIS_CHANNEL_VIDEO: str = "video_processor"
    REDIS_CHANNEL_GRAPH: str = "graph_processor"
    
    # Redis Queues (for parallel processing with work distribution)
    REDIS_QUEUE_DOCUMENT: str = "document_queue"
    REDIS_QUEUE_AUDIO: str = "audio_queue"
    REDIS_QUEUE_VIDEO: str = "video_queue"
    REDIS_QUEUE_GRAPH: str = "graph_queue"
    
    # AlloyDB Configuration
    ALLOYDB_HOST: str = os.getenv("ALLOYDB_HOST", "localhost")
    ALLOYDB_PORT: int = int(os.getenv("ALLOYDB_PORT", "5432"))
    ALLOYDB_USER: str = os.getenv("ALLOYDB_USER", "postgres")
    ALLOYDB_PASSWORD: str = os.getenv("ALLOYDB_PASSWORD", "password")
    ALLOYDB_DATABASE: str = os.getenv("ALLOYDB_DATABASE", "sentinel_db")
    
    @property
    def DATABASE_URL(self) -> str:
        if self.USE_SQLITE_FOR_DEV:
            return f"sqlite:///{self.SQLITE_DB_PATH}"
        return f"postgresql://{self.ALLOYDB_USER}:{self.ALLOYDB_PASSWORD}@{self.ALLOYDB_HOST}:{self.ALLOYDB_PORT}/{self.ALLOYDB_DATABASE}"
    
    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    SUMMARY_LLM_HOST: str = os.getenv("SUMMARY_LLM_HOST", "localhost")
    SUMMARY_LLM_PORT: int = int(os.getenv("SUMMARY_LLM_PORT", "11434"))
    SUMMARY_LLM_MODEL: str = os.getenv("SUMMARY_LLM_MODEL", "gemma3:1b")
    
    GRAPH_LLM_HOST: str = os.getenv("GRAPH_LLM_HOST", "10.0.2.4")
    GRAPH_LLM_PORT: int = int(os.getenv("GRAPH_LLM_PORT", "11434"))
    GRAPH_LLM_MODEL: str = os.getenv("GRAPH_LLM_MODEL", "gemma3:4b")
    
    CHAT_LLM_HOST: str = os.getenv("CHAT_LLM_HOST", "localhost")
    CHAT_LLM_PORT: int = int(os.getenv("CHAT_LLM_PORT", "11436"))
    CHAT_LLM_MODEL: str = os.getenv("CHAT_LLM_MODEL", "gemma3:1b")
    
    MULTIMODAL_LLM_HOST: str = os.getenv("MULTIMODAL_LLM_HOST", "localhost")
    MULTIMODAL_LLM_PORT: int = int(os.getenv("MULTIMODAL_LLM_PORT", "11437"))
    MULTIMODAL_LLM_MODEL: str = os.getenv("MULTIMODAL_LLM_MODEL", "gemma3:12b")
    
    TRANSLATION_THRESHOLD_MB: int = int(os.getenv("TRANSLATION_THRESHOLD_MB", "10"))
    TRANSLATION_LOCAL: bool = os.getenv("TRANSLATION_LOCAL", "True").lower() == "true"
    
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    RBAC_LEVELS: List[str] = ["admin", "manager", "analyst"]
    
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    # CORS_ORIGINS: List[str] = ["http://nodejsapp.enter-mnemon.com/", "http://localhost:3000"]
    
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "2000"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "100"))
    
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "embeddinggemma:latest")
    EMBEDDING_LLM_HOST: str = os.getenv("EMBEDDING_LLM_HOST", "localhost")
    EMBEDDING_LLM_PORT: int = int(os.getenv("EMBEDDING_LLM_PORT", "11434"))
    
    GOOGLE_CHAT_MODEL: str = os.getenv("GOOGLE_CHAT_MODEL", "gemini-2.0-flash-exp")
    GOOGLE_AGENT_REFERENCE_PATHS_RAW: str = os.getenv("GOOGLE_AGENT_REFERENCE_PATHS", "")
    
    @property
    def SUMMARY_LLM_URL(self) -> str:
        return f"http://{self.SUMMARY_LLM_HOST}:{self.SUMMARY_LLM_PORT}"
    
    @property
    def GRAPH_LLM_URL(self) -> str:
        return f"http://{self.GRAPH_LLM_HOST}:{self.GRAPH_LLM_PORT}"
    
    @property
    def CHAT_LLM_URL(self) -> str:
        return f"http://{self.CHAT_LLM_HOST}:{self.CHAT_LLM_PORT}"
    
    @property
    def MULTIMODAL_LLM_URL(self) -> str:
        return f"http://{self.MULTIMODAL_LLM_HOST}:{self.MULTIMODAL_LLM_PORT}"
    
    @property
    def EMBEDDING_LLM_URL(self) -> str:
        return f"http://{self.EMBEDDING_LLM_HOST}:{self.EMBEDDING_LLM_PORT}"
    
    @property
    def allowed_extensions_list(self) -> List[str]:
        return [ext.strip() for ext in self.ALLOWED_EXTENSIONS.split(",")]
    
    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024
    
    @property
    def google_agent_reference_paths(self) -> list[str]:
        if not self.GOOGLE_AGENT_REFERENCE_PATHS_RAW:
            return []
        return [path.strip() for path in self.GOOGLE_AGENT_REFERENCE_PATHS_RAW.split(",") if path.strip()]
    
    class Settings(BaseSettings):
        model_config = SettingsConfigDict(
            env_file=('.env'),
            case_sensitive=True,
            extra='ignore'
        )


settings = Settings()
