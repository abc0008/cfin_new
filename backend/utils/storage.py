"""
Storage Service Module
=====================

This module provides an abstraction layer for file storage operations in the CFIN
financial analysis platform. It implements storage services that support both local
filesystem and AWS S3 cloud storage, allowing the application to work seamlessly
with different storage backends.

Primary responsibilities:
- Provide a consistent interface for file storage operations
- Support multiple storage backends (local filesystem and AWS S3)
- Handle file saving, retrieval, and deletion operations
- Manage file paths and identifiers consistently across backends

Key Components:
- StorageService: Abstract base class defining the storage interface
- LocalStorageService: Implementation for local filesystem storage
- S3StorageService: Implementation for AWS S3 cloud storage
- Factory method for obtaining the appropriate storage service based on configuration

Interactions with other files:
-----------------------------
1. cfin/backend/repositories/document_repository.py:
   - Uses StorageService for file storage operations
   - Methods used: save_file, get_file, delete_file, get_file_path
   - Handles document binary content persistence and retrieval

2. cfin/backend/pdf_processing/document_service.py:
   - Indirectly uses StorageService through DocumentRepository
   - Uploads and processes PDF files stored by this service

3. cfin/backend/pdf_processing/langgraph_service.py:
   - Indirectly uses StorageService to access document binary content
   - Retrieves PDF files for analysis and citation extraction

4. cfin/backend/pdf_processing/claude_service.py:
   - May directly access files stored by StorageService
   - Retrieves PDF binary content for Claude API processing

5. cfin/backend/api/routes/documents.py:
   - Upload endpoints use StorageService via DocumentRepository
   - Routes document uploads through the storage layer

This service is configurable through environment variables:
- STORAGE_TYPE: "local", "s3", or "supabase" to select the storage backend
- UPLOAD_DIR: Directory for local file storage
- S3_BUCKET_NAME: AWS S3 bucket for cloud storage
- AWS_ACCESS_KEY_ID: AWS credentials for S3 access
- AWS_SECRET_ACCESS_KEY: AWS credentials for S3 access
- S3_REGION: AWS region for S3 bucket
- SUPABASE_URL: Supabase project URL
- SUPABASE_STORAGE_BUCKET: Supabase Storage bucket for document PDFs
- SUPABASE_SECRET_KEY / SUPABASE_SERVICE_ROLE_KEY / SUPABASE_PUBLISHABLE_KEY:
  API key used by the backend to access Supabase Storage

The storage service layer ensures file operations are consistent regardless of
the underlying storage mechanism, making the application more flexible and
easier to deploy in different environments.
"""

import os
import io
import aiofiles
import httpx
from typing import Optional
import logging
from abc import ABC, abstractmethod
from urllib.parse import quote

logger = logging.getLogger(__name__)

class StorageService(ABC):
    """Abstract base class for storage services."""
    
    @abstractmethod
    async def save_file(self, file_data: bytes, file_id: str, content_type: str) -> str:
        """Save a file to storage and return the path or URL."""
        pass
    
    @abstractmethod
    async def get_file(self, file_id: str) -> Optional[bytes]:
        """Get a file's contents from storage."""
        pass
    
    @abstractmethod
    async def delete_file(self, file_id: str) -> bool:
        """Delete a file from storage."""
        pass
    
    @abstractmethod
    def get_file_path(self, file_id: str) -> str:
        """Get the physical path to a file in storage."""
        pass
    
    @staticmethod
    def get_storage_service() -> 'StorageService':
        """Factory method to get the appropriate storage service."""
        storage_type = os.getenv("STORAGE_TYPE", "local").lower()
        
        if storage_type == "s3":
            return S3StorageService()
        if storage_type == "supabase":
            return SupabaseStorageService()
        else:
            return LocalStorageService()


class LocalStorageService(StorageService):
    """Storage service for local filesystem."""
    
    def __init__(self):
        self.upload_dir = os.getenv("UPLOAD_DIR", "./uploads")
        # Create upload directory if it doesn't exist
        os.makedirs(self.upload_dir, exist_ok=True)
    
    async def save_file(self, file_data: bytes, file_id: str, content_type: str) -> str:
        """Save a file to local storage."""
        file_path = os.path.join(self.upload_dir, file_id)
        
        try:
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(file_data)
            logger.info(f"File {file_id} saved to {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Error saving file {file_id}: {str(e)}")
            raise
    
    async def get_file(self, file_id: str) -> Optional[bytes]:
        """Get a file's contents from local storage."""
        file_path = os.path.join(self.upload_dir, file_id)
        
        try:
            if not os.path.exists(file_path):
                logger.warning(f"File {file_id} not found at {file_path}")
                return None
            
            async with aiofiles.open(file_path, "rb") as f:
                data = await f.read()
            return data
        except Exception as e:
            logger.error(f"Error reading file {file_id}: {str(e)}")
            return None
    
    async def delete_file(self, file_id: str) -> bool:
        """Delete a file from local storage."""
        file_path = os.path.join(self.upload_dir, file_id)
        
        try:
            if not os.path.exists(file_path):
                logger.warning(f"File {file_id} not found at {file_path}")
                return False
            
            os.remove(file_path)
            logger.info(f"File {file_id} deleted from {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error deleting file {file_id}: {str(e)}")
            return False
    
    def get_file_path(self, file_id: str) -> str:
        """Get the physical path to a file in local storage."""
        return os.path.join(self.upload_dir, file_id)


class S3StorageService(StorageService):
    """Storage service for AWS S3."""
    
    def __init__(self):
        import boto3

        self.bucket_name = os.getenv("S3_BUCKET_NAME")
        if not self.bucket_name:
            raise ValueError("S3_BUCKET_NAME environment variable is not set")
        
        self.region = os.getenv("S3_REGION", "us-west-2")
        
        self.s3_client = boto3.client(
            's3',
            region_name=self.region,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
        )
    
    async def save_file(self, file_data: bytes, file_id: str, content_type: str) -> str:
        """Save a file to S3 storage."""
        try:
            file_obj = io.BytesIO(file_data)
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                file_id,
                ExtraArgs={
                    "ContentType": content_type,
                }
            )
            s3_url = f"s3://{self.bucket_name}/{file_id}"
            logger.info(f"File {file_id} uploaded to S3: {s3_url}")
            return s3_url
        except Exception as e:
            logger.error(f"Error uploading file {file_id} to S3: {str(e)}")
            raise
    
    async def get_file(self, file_id: str) -> Optional[bytes]:
        """Get a file's contents from S3 storage."""
        try:
            file_obj = io.BytesIO()
            self.s3_client.download_fileobj(
                self.bucket_name,
                file_id,
                file_obj
            )
            file_obj.seek(0)
            data = file_obj.read()
            return data
        except Exception as e:
            logger.error(f"Error downloading file {file_id} from S3: {str(e)}")
            return None
    
    async def delete_file(self, file_id: str) -> bool:
        """Delete a file from S3 storage."""
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=file_id
            )
            logger.info(f"File {file_id} deleted from S3 bucket {self.bucket_name}")
            return True
        except Exception as e:
            logger.error(f"Error deleting file {file_id} from S3: {str(e)}")
            return False
    
    def get_file_path(self, file_id: str) -> str:
        """
        Get the path to a file in S3 storage.
        
        Note: For S3, there's no direct file path. This returns a URL that can
        be used for accessing the file, but it's not a local path.
        """
        # For S3, we don't have a physical path, so return an S3 URL
        return f"s3://{self.bucket_name}/{file_id}"


class SupabaseStorageService(StorageService):
    """Storage service for Supabase Storage."""

    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
        if not self.supabase_url:
            raise ValueError("SUPABASE_URL environment variable is not set")

        self.bucket_name = os.getenv("SUPABASE_STORAGE_BUCKET", "cfin-documents")
        self.api_key = (
            os.getenv("SUPABASE_SECRET_KEY")
            or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            or os.getenv("SUPABASE_SERVICE_KEY")
            or os.getenv("SUPABASE_ANON_KEY")
            or os.getenv("SUPABASE_PUBLISHABLE_KEY")
        )
        if not self.api_key:
            raise ValueError(
                "SUPABASE_SECRET_KEY, SUPABASE_SERVICE_ROLE_KEY, or "
                "SUPABASE_PUBLISHABLE_KEY environment variable is not set"
            )

        self.timeout = httpx.Timeout(60.0, connect=10.0)

    def _headers(self, content_type: Optional[str] = None) -> dict:
        headers = {
            "apikey": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
        }
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def _object_url(self, file_id: str) -> str:
        bucket = quote(self.bucket_name, safe="")
        object_path = quote(file_id.lstrip("/"), safe="/")
        return f"{self.supabase_url}/storage/v1/object/{bucket}/{object_path}"

    async def save_file(self, file_data: bytes, file_id: str, content_type: str) -> str:
        """Save a file to Supabase Storage."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self._object_url(file_id),
                    content=file_data,
                    headers={
                        **self._headers(content_type),
                        "x-upsert": "true",
                    },
                )

            if response.status_code not in {200, 201}:
                raise RuntimeError(
                    f"Supabase upload failed for {file_id}: "
                    f"{response.status_code} {response.text[:300]}"
                )

            logger.info(f"File {file_id} uploaded to Supabase Storage")
            return f"supabase://{self.bucket_name}/{file_id}"
        except Exception as e:
            logger.error(f"Error uploading file {file_id} to Supabase Storage: {str(e)}")
            raise

    async def get_file(self, file_id: str) -> Optional[bytes]:
        """Get a file's contents from Supabase Storage."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    self._object_url(file_id),
                    headers=self._headers(),
                )

            if response.status_code == 404 or (
                response.status_code == 400 and '"statusCode":"404"' in response.text
            ):
                logger.warning(f"File {file_id} not found in Supabase Storage")
                return None

            if response.status_code >= 400:
                logger.error(
                    f"Supabase download failed for {file_id}: "
                    f"{response.status_code} {response.text[:300]}"
                )
                return None

            return response.content
        except Exception as e:
            logger.error(f"Error downloading file {file_id} from Supabase Storage: {str(e)}")
            return None

    async def delete_file(self, file_id: str) -> bool:
        """Delete a file from Supabase Storage."""
        try:
            delete_url = (
                f"{self.supabase_url}/storage/v1/object/"
                f"{quote(self.bucket_name, safe='')}"
            )
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    "DELETE",
                    delete_url,
                    json={"prefixes": [file_id]},
                    headers=self._headers("application/json"),
                )

            if response.status_code not in {200, 204}:
                logger.error(
                    f"Supabase delete failed for {file_id}: "
                    f"{response.status_code} {response.text[:300]}"
                )
                return False

            logger.info(f"File {file_id} deleted from Supabase Storage")
            return True
        except Exception as e:
            logger.error(f"Error deleting file {file_id} from Supabase Storage: {str(e)}")
            return False

    def get_file_path(self, file_id: str) -> str:
        """Get the logical path to a file in Supabase Storage."""
        return f"supabase://{self.bucket_name}/{file_id}"
