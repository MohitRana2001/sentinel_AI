"""
Configurable Storage System for Sentinel AI

This package provides a flexible, production-ready storage abstraction layer that supports
multiple storage backends (GCS, S3, Local, Azure, etc.) with seamless switching via configuration.

Design Patterns Used:
- Strategy Pattern: Different storage backends implement the same interface
- Factory Pattern: StorageFactory creates appropriate backend based on configuration
- Singleton Pattern: StorageManager provides a single global storage instance

Quick Start:
    from storage import storage_manager
    
    # Upload file
    uri = storage_manager.upload_text("Hello World", "test.txt")
    
    # Download file
    content = storage_manager.download_text("test.txt")
    
    # Check backend type
    backend_type = storage_manager.get_backend_type()  # 'gcs', 's3', 'local', etc.

Architecture:
    - storage.base: Abstract StorageBackend interface
    - storage.gcs_backend: Google Cloud Storage implementation
    - storage.local_backend: Local filesystem implementation
    - storage.s3_backend: AWS S3 implementation
    - storage.factory: Factory for creating storage backends
    - storage.manager: Singleton manager for global storage access
"""

from storage.base import (
    StorageBackend,
    StorageError,
    StorageConnectionError,
    StorageNotFoundError,
    StoragePermissionError,
    StorageQuotaExceededError
)
from storage.factory import StorageFactory
from storage.manager import StorageManager, storage_manager

__all__ = [
    # Base classes and exceptions
    'StorageBackend',
    'StorageError',
    'StorageConnectionError',
    'StorageNotFoundError',
    'StoragePermissionError',
    'StorageQuotaExceededError',
    
    # Factory and Manager
    'StorageFactory',
    'StorageManager',
    'storage_manager',  # Global singleton instance
]

__version__ = '1.0.0'

