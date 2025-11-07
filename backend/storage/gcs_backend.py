"""
Google Cloud Storage (GCS) Backend Implementation

This module implements the StorageBackend interface for Google Cloud Storage.
Supports both service account credentials and default application credentials.
"""
import os
import shutil
import tempfile
from pathlib import Path
from typing import BinaryIO, List, Optional

from google.auth.exceptions import DefaultCredentialsError
from google.cloud import storage
from google.oauth2 import service_account

from storage.base import (
    StorageBackend,
    StorageError,
    StorageConnectionError,
    StorageNotFoundError,
    StoragePermissionError
)


class GCSStorageBackend(StorageBackend):
    """
    Google Cloud Storage backend implementation.
    
    Features:
    - Automatic credential detection (default, service account, env var)
    - Graceful error handling
    - Connection validation
    """
    
    def __init__(
        self,
        bucket_name: str,
        credentials_path: Optional[str] = None,
        project_id: Optional[str] = None
    ):
        """
        Initialize GCS storage backend.
        
        Args:
            bucket_name: Name of the GCS bucket
            credentials_path: Optional path to service account JSON file
            project_id: Optional GCP project ID
            
        Raises:
            StorageConnectionError: If connection to GCS fails
        """
        self.bucket_name = bucket_name
        self.client = None
        self.bucket = None
        
        if not bucket_name:
            raise StorageConnectionError("GCS bucket name is required")
        
        # Try multiple authentication methods
        self._initialize_client(credentials_path, project_id)
    
    def _initialize_client(self, credentials_path: Optional[str], project_id: Optional[str]):
        """Initialize GCS client with appropriate credentials."""
        credentials_env = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        
        try:
            # Method 1: Try default application credentials
            print("🔷 Attempting to use default application credentials for GCS...")
            self.client = storage.Client()
            self.bucket = self.client.bucket(self.bucket_name)
            
            # Validate connection
            if not self.bucket.exists():
                raise StorageConnectionError(
                    f"GCS bucket '{self.bucket_name}' does not exist or is not accessible"
                )
            
            print(f"✅ Connected to GCS bucket: {self.bucket_name} (using default credentials)")
            
        except Exception as default_error:
            # Method 2: Try credentials file if provided
            if credentials_path and os.path.exists(credentials_path):
                try:
                    print(f"⚠️  Default credentials failed, trying credentials file: {credentials_path}")
                    credentials = service_account.Credentials.from_service_account_file(
                        credentials_path
                    )
                    project = project_id or credentials.project_id
                    self.client = storage.Client(credentials=credentials, project=project)
                    self.bucket = self.client.bucket(self.bucket_name)
                    
                    if not self.bucket.exists():
                        raise StorageConnectionError(
                            f"GCS bucket '{self.bucket_name}' does not exist"
                        )
                    
                    print(f"✅ Connected to GCS bucket: {self.bucket_name} (using credentials file)")
                    return
                    
                except Exception as file_error:
                    print(f"❌ Credentials file failed: {file_error}")
            
            # Method 3: Try environment variable
            if credentials_env and os.path.exists(credentials_env):
                try:
                    print(f"⚠️  Trying GOOGLE_APPLICATION_CREDENTIALS: {credentials_env}")
                    credentials = service_account.Credentials.from_service_account_file(
                        credentials_env
                    )
                    project = project_id or credentials.project_id
                    self.client = storage.Client(credentials=credentials, project=project)
                    self.bucket = self.client.bucket(self.bucket_name)
                    
                    if not self.bucket.exists():
                        raise StorageConnectionError(
                            f"GCS bucket '{self.bucket_name}' does not exist"
                        )
                    
                    print(f"✅ Connected to GCS bucket: {self.bucket_name} (using env credentials)")
                    return
                    
                except Exception as env_error:
                    print(f"❌ Environment credentials failed: {env_error}")
            
            # All methods failed
            raise StorageConnectionError(
                f"Could not authenticate to GCS. Tried default credentials, "
                f"credentials file, and environment variable. Error: {default_error}"
            )
    
    def upload_file(self, file_obj: BinaryIO, remote_path: str) -> str:
        """Upload file from file object to GCS."""
        try:
            blob = self.bucket.blob(remote_path)
            blob.upload_from_file(file_obj, rewind=True)
            return f"gs://{self.bucket_name}/{remote_path}"
        except Exception as e:
            raise StorageError(f"Failed to upload file to GCS: {e}")
    
    def upload_from_filename(self, local_path: str, remote_path: str) -> str:
        """Upload file from local filesystem to GCS."""
        try:
            if not os.path.exists(local_path):
                raise StorageNotFoundError(f"Local file not found: {local_path}")
            
            blob = self.bucket.blob(remote_path)
            blob.upload_from_filename(local_path)
            return f"gs://{self.bucket_name}/{remote_path}"
        except StorageNotFoundError:
            raise
        except Exception as e:
            raise StorageError(f"Failed to upload file from {local_path}: {e}")
    
    def download_file(self, remote_path: str, local_path: str) -> str:
        """Download file from GCS to local path."""
        try:
            blob = self.bucket.blob(remote_path)
            
            if not blob.exists():
                raise StorageNotFoundError(f"File not found in GCS: {remote_path}")
            
            # Ensure parent directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            blob.download_to_filename(local_path)
            return local_path
        except StorageNotFoundError:
            raise
        except Exception as e:
            raise StorageError(f"Failed to download file from GCS: {e}")
    
    def download_to_temp(self, remote_path: str, suffix: Optional[str] = None) -> str:
        """Download file from GCS to temporary file."""
        try:
            blob = self.bucket.blob(remote_path)
            
            if not blob.exists():
                raise StorageNotFoundError(f"File not found in GCS: {remote_path}")
            
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            blob.download_to_filename(temp_file.name)
            return temp_file.name
        except StorageNotFoundError:
            raise
        except Exception as e:
            raise StorageError(f"Failed to download file to temp: {e}")
    
    def upload_text(self, text: str, remote_path: str) -> str:
        """Upload text content to GCS."""
        try:
            blob = self.bucket.blob(remote_path)
            blob.upload_from_string(text)
            return f"gs://{self.bucket_name}/{remote_path}"
        except Exception as e:
            raise StorageError(f"Failed to upload text to GCS: {e}")
    
    def download_text(self, remote_path: str) -> str:
        """Download text content from GCS."""
        try:
            blob = self.bucket.blob(remote_path)
            
            if not blob.exists():
                raise StorageNotFoundError(f"File not found in GCS: {remote_path}")
            
            return blob.download_as_text()
        except StorageNotFoundError:
            raise
        except Exception as e:
            raise StorageError(f"Failed to download text from GCS: {e}")
    
    def list_files(self, prefix: str) -> List[str]:
        """List all files with given prefix in GCS."""
        try:
            blobs = self.client.list_blobs(self.bucket_name, prefix=prefix)
            return [blob.name for blob in blobs]
        except Exception as e:
            raise StorageError(f"Failed to list files in GCS: {e}")
    
    def delete_file(self, remote_path: str) -> None:
        """Delete file from GCS."""
        try:
            blob = self.bucket.blob(remote_path)
            
            if blob.exists():
                blob.delete()
            else:
                raise StorageNotFoundError(f"File not found in GCS: {remote_path}")
        except StorageNotFoundError:
            raise
        except Exception as e:
            raise StorageError(f"Failed to delete file from GCS: {e}")
    
    def file_exists(self, remote_path: str) -> bool:
        """Check if file exists in GCS."""
        try:
            blob = self.bucket.blob(remote_path)
            return blob.exists()
        except Exception as e:
            print(f"⚠️ Error checking file existence in GCS: {e}")
            return False
    
    def get_backend_type(self) -> str:
        """Get backend type identifier."""
        return "gcs"
    
    def health_check(self) -> bool:
        """Perform health check on GCS connection."""
        try:
            # Try to list one file as a lightweight check
            blobs = list(self.client.list_blobs(self.bucket_name, max_results=1))
            return True
        except Exception as e:
            print(f"❌ GCS health check failed: {e}")
            return False

