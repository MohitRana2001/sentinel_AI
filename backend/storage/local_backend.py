"""
Local Filesystem Storage Backend Implementation

This module implements the StorageBackend interface for local filesystem storage.
Perfect for development, testing, and edge deployments without cloud dependencies.
"""
import os
import shutil
import tempfile
from pathlib import Path
from typing import BinaryIO, List, Optional

from storage.base import (
    StorageBackend,
    StorageError,
    StorageNotFoundError
)


class LocalStorageBackend(StorageBackend):
    """
    Local filesystem storage backend implementation.
    
    Features:
    - No external dependencies
    - Fast local access
    - Perfect for development and testing
    - Mirrors cloud storage interface
    """
    
    def __init__(self, base_path: str):
        """
        Initialize local storage backend.
        
        Args:
            base_path: Base directory for storage (e.g., './.local_storage')
            
        Raises:
            StorageError: If base path cannot be created
        """
        self.base_path = Path(base_path).resolve()
        
        # Create base directory if it doesn't exist
        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
            print(f"✅ Local storage initialized at: {self.base_path}")
        except Exception as e:
            raise StorageError(f"Failed to create local storage directory: {e}")
    
    def _get_full_path(self, remote_path: str) -> Path:
        """
        Convert remote path to full local path.
        
        Args:
            remote_path: Relative path in storage
            
        Returns:
            Full local filesystem path
        """
        # Normalize path (remove leading slashes, etc.)
        normalized = remote_path.lstrip('/')
        full_path = self.base_path / normalized
        
        # Ensure the path is within base_path (security check)
        try:
            full_path.resolve().relative_to(self.base_path.resolve())
        except ValueError:
            raise StorageError(
                f"Invalid path: {remote_path} resolves outside base directory"
            )
        
        return full_path
    
    def upload_file(self, file_obj: BinaryIO, remote_path: str) -> str:
        """Upload file from file object to local storage."""
        try:
            target = self._get_full_path(remote_path)
            
            # Create parent directories
            target.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            file_obj.seek(0)
            with open(target, "wb") as dest:
                shutil.copyfileobj(file_obj, dest)
            file_obj.seek(0)  # Reset for potential reuse
            
            return remote_path
        except Exception as e:
            raise StorageError(f"Failed to upload file to local storage: {e}")
    
    def upload_from_filename(self, local_path: str, remote_path: str) -> str:
        """Upload file from local filesystem to storage."""
        try:
            if not os.path.exists(local_path):
                raise StorageNotFoundError(f"Source file not found: {local_path}")
            
            target = self._get_full_path(remote_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.copy2(local_path, target)  # copy2 preserves metadata
            return remote_path
        except StorageNotFoundError:
            raise
        except Exception as e:
            raise StorageError(f"Failed to upload file from {local_path}: {e}")
    
    def download_file(self, remote_path: str, local_path: str) -> str:
        """Download file from storage to local path."""
        try:
            source = self._get_full_path(remote_path)
            
            if not source.exists():
                raise StorageNotFoundError(f"File not found: {remote_path}")
            
            # Create parent directory for destination
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            shutil.copy2(source, local_path)
            return local_path
        except StorageNotFoundError:
            raise
        except Exception as e:
            raise StorageError(f"Failed to download file: {e}")
    
    def download_to_temp(self, remote_path: str, suffix: Optional[str] = None) -> str:
        """Download file to temporary file."""
        try:
            source = self._get_full_path(remote_path)
            
            if not source.exists():
                raise StorageNotFoundError(f"File not found: {remote_path}")
            
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            shutil.copy2(source, temp_file.name)
            return temp_file.name
        except StorageNotFoundError:
            raise
        except Exception as e:
            raise StorageError(f"Failed to download file to temp: {e}")
    
    def upload_text(self, text: str, remote_path: str) -> str:
        """Upload text content to storage."""
        try:
            target = self._get_full_path(remote_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            
            target.write_text(text, encoding='utf-8')
            return remote_path
        except Exception as e:
            raise StorageError(f"Failed to upload text: {e}")
    
    def download_text(self, remote_path: str) -> str:
        """Download text content from storage."""
        try:
            source = self._get_full_path(remote_path)
            
            if not source.exists():
                raise StorageNotFoundError(f"File not found: {remote_path}")
            
            return source.read_text(encoding='utf-8')
        except StorageNotFoundError:
            raise
        except Exception as e:
            raise StorageError(f"Failed to download text: {e}")
    
    def list_files(self, prefix: str) -> List[str]:
        """List all files with given prefix."""
        try:
            results = []
            
            # Handle empty prefix (list all files)
            if not prefix:
                search_path = self.base_path
            else:
                search_path = self._get_full_path(prefix)
                # If prefix is a file, return it if it exists
                if search_path.is_file():
                    return [prefix]
            
            # Recursively find all files under search path
            if search_path.exists() and search_path.is_dir():
                for path in search_path.rglob("*"):
                    if path.is_file():
                        # Get relative path from base_path
                        try:
                            rel_path = path.relative_to(self.base_path).as_posix()
                            results.append(rel_path)
                        except ValueError:
                            # Skip files outside base_path
                            continue
            
            # Filter by prefix
            if prefix:
                results = [r for r in results if r.startswith(prefix.lstrip('/'))]
            
            return sorted(results)
        except Exception as e:
            raise StorageError(f"Failed to list files: {e}")
    
    def delete_file(self, remote_path: str) -> None:
        """Delete file from storage."""
        try:
            target = self._get_full_path(remote_path)
            
            if not target.exists():
                raise StorageNotFoundError(f"File not found: {remote_path}")
            
            if target.is_file():
                target.unlink()
            elif target.is_dir():
                shutil.rmtree(target)
            else:
                raise StorageError(f"Invalid file type: {remote_path}")
        except StorageNotFoundError:
            raise
        except Exception as e:
            raise StorageError(f"Failed to delete file: {e}")
    
    def file_exists(self, remote_path: str) -> bool:
        """Check if file exists."""
        try:
            return self._get_full_path(remote_path).exists()
        except Exception as e:
            print(f"⚠️ Error checking file existence: {e}")
            return False
    
    def get_backend_type(self) -> str:
        """Get backend type identifier."""
        return "local"
    
    def health_check(self) -> bool:
        """Perform health check on local storage."""
        try:
            # Check if base path is accessible
            if not self.base_path.exists():
                return False
            
            # Try to create a test file
            test_file = self.base_path / ".health_check"
            test_file.touch()
            test_file.unlink()
            
            return True
        except Exception as e:
            print(f"❌ Local storage health check failed: {e}")
            return False

