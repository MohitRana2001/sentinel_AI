"""
Storage Configuration and Initialization

This module initializes the global storage manager based on application configuration.
Import this module to get access to the configured storage manager.

Usage:
    from storage_config import storage_manager
    
    # Use storage_manager for all storage operations
    storage_manager.upload_text("content", "path/to/file.txt")
"""
from config import settings
from storage import storage_manager, StorageFactory

# Initialize storage manager on module import
try:
    print("🏗️  Initializing configurable storage system...")
    print(f"📦 Storage backend: {settings.STORAGE_BACKEND}")
    
    # Create backend using factory
    backend = StorageFactory.create_from_env(settings, auto_fallback=True)
    
    # Initialize the global storage manager
    storage_manager.initialize(backend)
    
    # Display storage info
    info = storage_manager.get_info()
    print(f"✅ Storage system ready: {info}")
    
except Exception as e:
    print(f"❌ Failed to initialize storage system: {e}")
    print("⚠️  Application may not function correctly without storage!")
    raise

# Export for convenience
__all__ = ['storage_manager']

