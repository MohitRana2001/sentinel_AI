"""
Abstract Storage Interface for Sentinel AI

This module defines the base interface for all storage backends.
All storage implementations must inherit from StorageBackend and implement
all abstract methods.

Design Pattern: Strategy Pattern + Abstract Factory
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO, List, Optional


class StorageBackend(ABC):
    """
    Abstract base class for storage backends.
    
    All storage implementations (GCS, S3, Azure, Local, etc.) must implement
    this interface to ensure consistent behavior across different storage systems.
    """
    
    @abstractmethod
    def upload_file(self, file_obj: BinaryIO, remote_path: str) -> str:
        """
        Upload file from a file object to storage.
        
        Args:
            file_obj: Binary file object to upload
            remote_path: Destination path in storage (without bucket/container prefix)
            
        Returns:
            Storage URI or path identifier (e.g., 'gs://bucket/path' or 'local/path')
            
        Raises:
            StorageError: If upload fails
        """
        pass
    
    @abstractmethod
    def upload_from_filename(self, local_path: str, remote_path: str) -> str:
        """
        Upload file from local filesystem to storage.
        
        Args:
            local_path: Path to local file
            remote_path: Destination path in storage
            
        Returns:
            Storage URI or path identifier
            
        Raises:
            StorageError: If upload fails
        """
        pass
    
    @abstractmethod
    def download_file(self, remote_path: str, local_path: str) -> str:
        """
        Download file from storage to local path.
        
        Args:
            remote_path: Source path in storage
            local_path: Destination path on local filesystem
            
        Returns:
            Local file path
            
        Raises:
            StorageError: If download fails
        """
        pass
    
    @abstractmethod
    def download_to_temp(self, remote_path: str, suffix: Optional[str] = None) -> str:
        """
        Download file from storage to a temporary file.
        
        Args:
            remote_path: Source path in storage
            suffix: Optional file suffix (e.g., '.pdf', '.txt')
            
        Returns:
            Path to temporary file (caller is responsible for cleanup)
            
        Raises:
            StorageError: If download fails
        """
        pass
    
    @abstractmethod
    def upload_text(self, text: str, remote_path: str) -> str:
        """
        Upload text content to storage.
        
        Args:
            text: Text content to upload
            remote_path: Destination path in storage
            
        Returns:
            Storage URI or path identifier
            
        Raises:
            StorageError: If upload fails
        """
        pass
    
    @abstractmethod
    def download_text(self, remote_path: str) -> str:
        """
        Download text content from storage.
        
        Args:
            remote_path: Source path in storage
            
        Returns:
            Text content as string
            
        Raises:
            StorageError: If download fails
        """
        pass
    
    @abstractmethod
    def list_files(self, prefix: str) -> List[str]:
        """
        List all files with given prefix.
        
        Args:
            prefix: Path prefix to filter files
            
        Returns:
            List of file paths (relative to storage root)
            
        Raises:
            StorageError: If listing fails
        """
        pass
    
    @abstractmethod
    def delete_file(self, remote_path: str) -> None:
        """
        Delete file from storage.
        
        Args:
            remote_path: Path to file in storage
            
        Raises:
            StorageError: If deletion fails
        """
        pass
    
    @abstractmethod
    def file_exists(self, remote_path: str) -> bool:
        """
        Check if file exists in storage.
        
        Args:
            remote_path: Path to file in storage
            
        Returns:
            True if file exists, False otherwise
        """
        pass
    
    @abstractmethod
    def get_backend_type(self) -> str:
        """
        Get the storage backend type identifier.
        
        Returns:
            Backend type string (e.g., 'gcs', 's3', 'local', 'azure')
        """
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """
        Perform a health check on the storage backend.
        
        Returns:
            True if storage is accessible and healthy, False otherwise
        """
        pass


class StorageError(Exception):
    """Base exception for all storage-related errors."""
    pass


class StorageConnectionError(StorageError):
    """Exception raised when connection to storage backend fails."""
    pass


class StorageNotFoundError(StorageError):
    """Exception raised when requested file/object is not found."""
    pass


class StoragePermissionError(StorageError):
    """Exception raised when operation is not permitted due to access control."""
    pass


class StorageQuotaExceededError(StorageError):
    """Exception raised when storage quota is exceeded."""
    pass

