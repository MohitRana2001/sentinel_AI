"""
Storage Factory for Creating Storage Backends

This module implements the Factory pattern for creating storage backend instances
based on configuration. Supports automatic fallback to local storage if cloud
storage is unavailable.
"""
from typing import Optional

from storage.base import StorageBackend, StorageConnectionError


class StorageFactory:
    """
    Factory for creating storage backend instances.
    
    Supports:
    - GCS (Google Cloud Storage)
    - S3 (Amazon S3)
    - Local (Local filesystem)
    - Azure (Azure Blob Storage) - future
    """
    
    # Registry of available backends
    _backends = {}
    
    @classmethod
    def register_backend(cls, backend_type: str, backend_class):
        """
        Register a storage backend implementation.
        
        Args:
            backend_type: Backend identifier (e.g., 'gcs', 's3', 'local')
            backend_class: Backend class implementing StorageBackend
        """
        cls._backends[backend_type.lower()] = backend_class
        print(f"📦 Registered storage backend: {backend_type}")
    
    @classmethod
    def create_backend(
        cls,
        backend_type: str,
        config: dict,
        auto_fallback: bool = True
    ) -> StorageBackend:
        """
        Create a storage backend instance.
        
        Args:
            backend_type: Type of backend ('gcs', 's3', 'local', 'azure')
            config: Configuration dictionary for the backend
            auto_fallback: If True, fallback to local storage on failure
            
        Returns:
            StorageBackend instance
            
        Raises:
            StorageConnectionError: If backend creation fails and auto_fallback is False
        """
        backend_type = backend_type.lower()
        
        # Try to create the requested backend
        try:
            if backend_type not in cls._backends:
                # Try to load backend dynamically
                cls._load_backend(backend_type)
            
            if backend_type not in cls._backends:
                raise StorageConnectionError(
                    f"Unknown storage backend: {backend_type}. "
                    f"Available: {', '.join(cls._backends.keys())}"
                )
            
            backend_class = cls._backends[backend_type]
            backend = backend_class(**config)
            
            # Validate connection
            if backend.health_check():
                print(f"✅ Storage backend '{backend_type}' initialized successfully")
                return backend
            else:
                raise StorageConnectionError(
                    f"Storage backend '{backend_type}' failed health check"
                )
        
        except Exception as e:
            print(f"⚠️  Failed to initialize {backend_type} storage: {e}")
            
            if auto_fallback and backend_type != 'local':
                print("🔄 Falling back to local storage...")
                # Use default local config for fallback
                fallback_config = {
                    'base_path': './.local_storage'
                }
                return cls.create_backend('local', fallback_config, auto_fallback=False)
            
            raise StorageConnectionError(
                f"Failed to create {backend_type} storage backend: {e}"
            )
    
    @classmethod
    def _load_backend(cls, backend_type: str):
        """Dynamically load a storage backend."""
        try:
            if backend_type == 'gcs':
                from storage.gcs_backend import GCSStorageBackend
                cls.register_backend('gcs', GCSStorageBackend)
            
            elif backend_type == 's3':
                from storage.s3_backend import S3StorageBackend
                cls.register_backend('s3', S3StorageBackend)
            
            elif backend_type == 'local':
                from storage.local_backend import LocalStorageBackend
                cls.register_backend('local', LocalStorageBackend)
            
            elif backend_type == 'azure':
                # Future implementation
                raise ImportError("Azure Blob Storage backend not yet implemented")
            
            else:
                raise ValueError(f"Unknown backend type: {backend_type}")
        
        except ImportError as e:
            print(f"⚠️  Could not load {backend_type} backend: {e}")
            raise StorageConnectionError(
                f"Backend '{backend_type}' is not available. "
                f"Check dependencies or configuration."
            )
    
    @classmethod
    def create_from_env(cls, settings, auto_fallback: bool = True) -> StorageBackend:
        """
        Create storage backend from application settings/environment.
        
        This is the recommended way to initialize storage in your application.
        
        Args:
            settings: Application settings object with storage configuration
            auto_fallback: If True, fallback to local storage on failure
            
        Returns:
            StorageBackend instance
        """
        backend_type = getattr(settings, 'STORAGE_BACKEND', 'gcs').lower()
        
        # Build configuration based on backend type
        config = {}
        
        if backend_type == 'gcs':
            config = {
                'bucket_name': getattr(settings, 'GCS_BUCKET_NAME', ''),
                'credentials_path': getattr(settings, 'GCS_CREDENTIALS_PATH', None),
                'project_id': getattr(settings, 'GCS_PROJECT_ID', None)
            }
        
        elif backend_type == 's3':
            config = {
                'bucket_name': getattr(settings, 'S3_BUCKET_NAME', ''),
                'region_name': getattr(settings, 'S3_REGION_NAME', None),
                'aws_access_key_id': getattr(settings, 'AWS_ACCESS_KEY_ID', None),
                'aws_secret_access_key': getattr(settings, 'AWS_SECRET_ACCESS_KEY', None),
                'endpoint_url': getattr(settings, 'S3_ENDPOINT_URL', None)
            }
        
        elif backend_type == 'local':
            config = {
                'base_path': getattr(settings, 'LOCAL_STORAGE_PATH', './.local_storage')
            }
        
        elif backend_type == 'azure':
            config = {
                'account_name': getattr(settings, 'AZURE_STORAGE_ACCOUNT', ''),
                'account_key': getattr(settings, 'AZURE_STORAGE_KEY', None),
                'container_name': getattr(settings, 'AZURE_CONTAINER_NAME', '')
            }
        
        # Store local config separately for fallback
        local_config = {
            'base_path': getattr(settings, 'LOCAL_STORAGE_PATH', './.local_storage')
        }
        
        print(f"🏗️  Initializing storage backend: {backend_type}")
        
        try:
            return cls.create_backend(backend_type, config, auto_fallback=auto_fallback)
        except Exception as e:
            if auto_fallback and backend_type != 'local':
                print(f"⚠️  Failed to initialize {backend_type}: {e}")
                print("🔄 Falling back to local storage...")
                return cls.create_backend('local', local_config, auto_fallback=False)
            raise

