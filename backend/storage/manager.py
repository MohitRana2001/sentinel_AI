"""
Storage Manager - Singleton for Global Storage Access

This module provides a singleton StorageManager that wraps the storage backend
and provides a convenient API for the entire application.
"""
from typing import BinaryIO, List, Optional

from storage.base import StorageBackend


class StorageManager:
    """
    Singleton storage manager that provides a unified interface to the storage backend.
    
    This class wraps the storage backend and provides convenient methods for
    file operations throughout the application.
    
    Usage:
        from storage import storage_manager
        
        # All operations use the configured backend
        storage_manager.upload_text("content", "path/to/file.txt")
        text = storage_manager.download_text("path/to/file.txt")
    """
    
    _instance = None
    _backend: Optional[StorageBackend] = None
    
    def __new__(cls):
        """Ensure only one instance exists (Singleton pattern)."""
        if cls._instance is None:
            cls._instance = super(StorageManager, cls).__new__(cls)
        return cls._instance
    
    def initialize(self, backend: StorageBackend):
        """
        Initialize the storage manager with a backend.
        
        Args:
            backend: StorageBackend instance to use
        """
        self._backend = backend
        print(f"✅ StorageManager initialized with {backend.get_backend_type()} backend")
    
    def _ensure_initialized(self):
        """Ensure storage backend is initialized."""
        if self._backend is None:
            raise RuntimeError(
                "StorageManager not initialized. Call storage_manager.initialize(backend) first."
            )
    
    @property
    def backend(self) -> StorageBackend:
        """Get the underlying storage backend."""
        self._ensure_initialized()
        return self._backend
    
    # Delegate all methods to the backend
    
    def upload_file(self, file_obj: BinaryIO, remote_path: str) -> str:
        """Upload file from file object."""
        self._ensure_initialized()
        return self._backend.upload_file(file_obj, remote_path)
    
    def upload_from_filename(self, local_path: str, remote_path: str) -> str:
        """Upload file from local filesystem."""
        self._ensure_initialized()
        return self._backend.upload_from_filename(local_path, remote_path)
    
    def download_file(self, remote_path: str, local_path: str) -> str:
        """Download file to local path."""
        self._ensure_initialized()
        return self._backend.download_file(remote_path, local_path)
    
    def download_to_temp(self, remote_path: str, suffix: Optional[str] = None) -> str:
        """Download file to temporary location."""
        self._ensure_initialized()
        return self._backend.download_to_temp(remote_path, suffix)
    
    def upload_text(self, text: str, remote_path: str) -> str:
        """Upload text content."""
        self._ensure_initialized()
        return self._backend.upload_text(text, remote_path)
    
    def download_text(self, remote_path: str) -> str:
        """Download text content."""
        self._ensure_initialized()
        return self._backend.download_text(remote_path)
    
    def list_files(self, prefix: str) -> List[str]:
        """List files with prefix."""
        self._ensure_initialized()
        return self._backend.list_files(prefix)
    
    def delete_file(self, remote_path: str) -> None:
        """Delete file."""
        self._ensure_initialized()
        self._backend.delete_file(remote_path)
    
    def file_exists(self, remote_path: str) -> bool:
        """Check if file exists."""
        self._ensure_initialized()
        return self._backend.file_exists(remote_path)
    
    def get_backend_type(self) -> str:
        """Get the type of storage backend being used."""
        self._ensure_initialized()
        return self._backend.get_backend_type()
    
    def health_check(self) -> bool:
        """Perform health check on storage backend."""
        self._ensure_initialized()
        return self._backend.health_check()
    
    def get_info(self) -> dict:
        """
        Get information about the storage backend.
        
        Returns:
            Dictionary with backend information
        """
        self._ensure_initialized()
        return {
            'backend_type': self._backend.get_backend_type(),
            'healthy': self._backend.health_check(),
            'initialized': self._backend is not None
        }


# Global singleton instance
storage_manager = StorageManager()

