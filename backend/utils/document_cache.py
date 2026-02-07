"""
Document Cache for Large PDF Handling
=====================================

This module provides caching functionality for large PDF documents to optimize
performance when handling multiple requests for the same documents.
"""

import hashlib
import asyncio
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class DocumentCache:
    """Cache for storing document file IDs and metadata to avoid re-uploading."""
    
    def __init__(self, ttl_hours: int = 168):  # 7 days default
        self._file_id_cache: Dict[str, Tuple[str, datetime]] = {}
        self._document_hash_cache: Dict[str, str] = {}
        self._ttl = timedelta(hours=ttl_hours)
        self._lock = asyncio.Lock()
        self._max_cache_size = 1000
        
    async def get_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(65536), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    async def get_or_upload_file(
        self, 
        file_path: str,
        upload_func,
        force_upload: bool = False
    ) -> str:
        """Get cached file ID or upload and cache new one."""
        async with self._lock:
            # Calculate file hash
            file_hash = await self.get_file_hash(file_path)
            
            # Check if we have a valid cached file ID
            if not force_upload and file_hash in self._file_id_cache:
                file_id, timestamp = self._file_id_cache[file_hash]
                if datetime.utcnow() - timestamp < self._ttl:
                    logger.info(f"Using cached file ID for {file_path}: {file_id}")
                    return file_id
                else:
                    # Expired, remove from cache
                    del self._file_id_cache[file_hash]
            
            # Upload file
            logger.info(f"Uploading file {file_path} to Files API")
            file_id = await upload_func(file_path)
            
            # Cache the file ID
            self._file_id_cache[file_hash] = (file_id, datetime.utcnow())
            
            # Evict oldest entries if cache is too large
            if len(self._file_id_cache) > self._max_cache_size:
                oldest_hash = min(
                    self._file_id_cache.keys(),
                    key=lambda k: self._file_id_cache[k][1]
                )
                del self._file_id_cache[oldest_hash]
            
            return file_id
    
    async def add_cache_control(self, document_block: Dict) -> Dict:
        """Add cache control headers for large documents."""
        # Check document size (if available in metadata)
        doc_size = document_block.get("metadata", {}).get("file_size", 0)
        
        if doc_size > 50_000_000:  # 50MB
            document_block["cache_control"] = {"type": "ephemeral"}
            logger.info(f"Added ephemeral cache control for large document")
        
        return document_block
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        valid_entries = 0
        expired_entries = 0
        now = datetime.utcnow()
        
        for file_hash, (file_id, timestamp) in self._file_id_cache.items():
            if now - timestamp < self._ttl:
                valid_entries += 1
            else:
                expired_entries += 1
        
        return {
            "total_entries": len(self._file_id_cache),
            "valid_entries": valid_entries,
            "expired_entries": expired_entries,
            "cache_size_limit": self._max_cache_size,
            "ttl_hours": self._ttl.total_seconds() / 3600
        }
    
    async def clear_expired(self):
        """Remove expired entries from cache."""
        async with self._lock:
            now = datetime.utcnow()
            expired_hashes = [
                file_hash
                for file_hash, (_, timestamp) in self._file_id_cache.items()
                if now - timestamp >= self._ttl
            ]
            
            for file_hash in expired_hashes:
                del self._file_id_cache[file_hash]
            
            logger.info(f"Cleared {len(expired_hashes)} expired cache entries")
            return len(expired_hashes)
    
    def clear(self):
        """Clear all cache entries."""
        self._file_id_cache.clear()
        self._document_hash_cache.clear()
        logger.info("Document cache cleared")


# Global cache instance
_document_cache = DocumentCache()


def get_document_cache() -> DocumentCache:
    """Get the global document cache instance."""
    return _document_cache