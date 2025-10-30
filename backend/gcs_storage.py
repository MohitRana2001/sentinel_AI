"""
Google Cloud Storage utilities for file management
"""
import os
import shutil
import tempfile
from pathlib import Path
from typing import BinaryIO, List

from google.auth.exceptions import DefaultCredentialsError
from google.cloud import storage
from google.oauth2 import service_account

from config import settings


class GCSStorage:
    """Google Cloud Storage handler"""
    
    def __init__(self):
        self.local_mode = False
        self.local_path = Path(settings.LOCAL_GCS_STORAGE_PATH)
        bucket_name = settings.GCS_BUCKET_NAME
        project_id = settings.GCS_PROJECT_ID
        credentials_path = settings.GCS_CREDENTIALS_PATH
        credentials_env = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        
        try:
            if bucket_name and os.path.exists(credentials_path):
                credentials = service_account.Credentials.from_service_account_file(credentials_path)
                self.client = storage.Client(credentials=credentials, project=project_id or credentials.project_id)
            elif bucket_name and credentials_env and os.path.exists(credentials_env):
                credentials = service_account.Credentials.from_service_account_file(credentials_env)
                self.client = storage.Client(credentials=credentials, project=project_id or credentials.project_id)
            elif bucket_name and project_id:
                # Use default credentials for GCP environments
                self.client = storage.Client(project=project_id or None)
            else:
                raise DefaultCredentialsError("Missing bucket configuration for local fallback.")
            
            self.bucket = self.client.bucket(bucket_name)
        except DefaultCredentialsError:
            # Local development fallback that mirrors the GCS interface using the filesystem
            self.local_mode = True
            self.client = None
            self.bucket = None
            self.local_path.mkdir(parents=True, exist_ok=True)
            print(f"Warning: GCS credentials not found. Using local storage at {self.local_path}")

    def _local_target(self, gcs_path: str) -> Path:
        """Map GCS path to local filesystem path."""
        target = self.local_path / gcs_path
        target.parent.mkdir(parents=True, exist_ok=True)
        return target
    
    def upload_file(self, file_obj: BinaryIO, gcs_path: str) -> str:
        """
        Upload file to GCS
        
        Args:
            file_obj: File object to upload
            gcs_path: Destination path in GCS
            
        Returns:
            GCS URI (gs://bucket/path)
        """
        if self.local_mode:
            target = self._local_target(gcs_path)
            file_obj.seek(0)
            with open(target, "wb") as dest:
                shutil.copyfileobj(file_obj, dest)
            file_obj.seek(0)
            return gcs_path
        blob = self.bucket.blob(gcs_path)
        blob.upload_from_file(file_obj, rewind=True)
        return f"gs://{settings.GCS_BUCKET_NAME}/{gcs_path}"
    
    def upload_from_filename(self, local_path: str, gcs_path: str) -> str:
        """
        Upload file from local path to GCS
        
        Args:
            local_path: Local file path
            gcs_path: Destination path in GCS
            
        Returns:
            GCS URI
        """
        if self.local_mode:
            target = self._local_target(gcs_path)
            shutil.copy(local_path, target)
            return gcs_path
        blob = self.bucket.blob(gcs_path)
        blob.upload_from_filename(local_path)
        return f"gs://{settings.GCS_BUCKET_NAME}/{gcs_path}"
    
    def download_file(self, gcs_path: str, local_path: str) -> str:
        """
        Download file from GCS to local path
        
        Args:
            gcs_path: Source path in GCS
            local_path: Destination local path
            
        Returns:
            Local file path
        """
        if self.local_mode:
            source = self._local_target(gcs_path)
            shutil.copy(source, local_path)
            return local_path
        blob = self.bucket.blob(gcs_path)
        blob.download_to_filename(local_path)
        return local_path
    
    def download_to_temp(self, gcs_path: str, suffix: str = None) -> str:
        """
        Download file from GCS to temporary file
        
        Args:
            gcs_path: Source path in GCS
            suffix: File suffix (e.g., '.pdf')
            
        Returns:
            Temporary file path
        """
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        if self.local_mode:
            source = self._local_target(gcs_path)
            shutil.copy(source, temp_file.name)
            return temp_file.name
        blob = self.bucket.blob(gcs_path)
        blob.download_to_filename(temp_file.name)
        return temp_file.name
    
    def upload_text(self, text: str, gcs_path: str) -> str:
        """
        Upload text content to GCS
        
        Args:
            text: Text content
            gcs_path: Destination path in GCS
            
        Returns:
            GCS URI
        """
        if self.local_mode:
            target = self._local_target(gcs_path)
            target.write_text(text, encoding="utf-8")
            return gcs_path
        blob = self.bucket.blob(gcs_path)
        blob.upload_from_string(text)
        return f"gs://{settings.GCS_BUCKET_NAME}/{gcs_path}"
    
    def download_text(self, gcs_path: str) -> str:
        """
        Download text content from GCS
        
        Args:
            gcs_path: Source path in GCS
            
        Returns:
            Text content
        """
        if self.local_mode:
            source = self._local_target(gcs_path)
            return source.read_text(encoding="utf-8")
        blob = self.bucket.blob(gcs_path)
        return blob.download_as_text()
    
    def list_files(self, prefix: str) -> List[str]:
        """
        List all files with given prefix
        
        Args:
            prefix: GCS prefix
            
        Returns:
            List of file paths
        """
        if self.local_mode:
            base = self.local_path
            results = []
            for path in base.rglob("*"):
                if path.is_file():
                    rel_path = path.relative_to(base).as_posix()
                    if rel_path.startswith(prefix):
                        results.append(rel_path)
            return results
        blobs = self.client.list_blobs(settings.GCS_BUCKET_NAME, prefix=prefix)
        return [blob.name for blob in blobs]
    
    def delete_file(self, gcs_path: str):
        """Delete file from GCS"""
        if self.local_mode:
            target = self._local_target(gcs_path)
            if target.exists():
                target.unlink()
            return
        blob = self.bucket.blob(gcs_path)
        blob.delete()
    
    def file_exists(self, gcs_path: str) -> bool:
        """Check if file exists in GCS"""
        if self.local_mode:
            return self._local_target(gcs_path).exists()
        blob = self.bucket.blob(gcs_path)
        return blob.exists()


# Singleton instance
gcs_storage = GCSStorage()
