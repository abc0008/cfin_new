#!/usr/bin/env python3
"""
Cross-tenant file cache for Claude Files API optimization.
Prevents duplicate uploads of identical PDFs by caching file IDs by content SHA256.
Production-grade implementation with atomic writes and TTL expiration.
"""

import logging
import asyncio
import time
from typing import Optional, Dict
from utils.hashlib_utils import sha256_str

logger = logging.getLogger(__name__)

# Anthropic Files API TTL (90 days as per documentation)
CLAUDE_FILE_TTL_SECONDS = 90 * 24 * 60 * 60  # 90 days

class FileCacheManager:
    """
    Thread-safe cache for Claude file IDs to avoid duplicate uploads.
    Key: PDF content SHA256, Value: Claude file ID with expiration
    Production implementation with atomic writes and TTL.
    """
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, any]] = {}
        self._lock = asyncio.Lock()
        
    async def get_file_id(self, pdf_content: bytes) -> Optional[str]:
        """
        Get cached file ID for PDF content if it exists and hasn't expired.
        
        Args:
            pdf_content: Raw PDF bytes
            
        Returns:
            Claude file ID if cached and valid, None otherwise
        """
        # Handle both bytes and string input
        if isinstance(pdf_content, bytes):
            content_hash = sha256_str(pdf_content.decode('utf-8', errors='ignore'))
        else:
            content_hash = sha256_str(str(pdf_content))
        
        async with self._lock:
            cached_entry = self._cache.get(content_hash)
            if not cached_entry:
                logger.debug("Cache MISS: No existing file_id for content hash=%s", 
                            content_hash[:16] + "...")
                return None
            
            # Check TTL expiration
            current_time = time.time()
            if current_time > cached_entry['expires_at']:
                # Remove expired entry
                del self._cache[content_hash]
                logger.info("Cache EXPIRED: Removed expired file_id=%s for hash=%s", 
                           cached_entry['file_id'], content_hash[:16] + "...")
                return None
            
            file_id = cached_entry['file_id']
            logger.info("Cache HIT: Found valid file_id=%s for content hash=%s (expires in %d seconds)", 
                       file_id, content_hash[:16] + "...", 
                       int(cached_entry['expires_at'] - current_time))
            return file_id
    
    async def cache_file_id(self, pdf_content: bytes, file_id: str) -> None:
        """
        Cache a file ID for future use with atomic write semantics.
        
        Args:
            pdf_content: Raw PDF bytes
            file_id: Claude file ID from upload
        """
        # Handle both bytes and string input
        if isinstance(pdf_content, bytes):
            content_hash = sha256_str(pdf_content.decode('utf-8', errors='ignore'))
        else:
            content_hash = sha256_str(str(pdf_content))
        
        expires_at = time.time() + CLAUDE_FILE_TTL_SECONDS
        
        async with self._lock:
            # Atomic write: only update if not already present (race condition protection)
            if content_hash not in self._cache:
                self._cache[content_hash] = {
                    'file_id': file_id,
                    'created_at': time.time(),
                    'expires_at': expires_at
                }
                logger.info("Cached file_id=%s for content hash=%s (expires: %s, cache size: %d)", 
                           file_id, content_hash[:16] + "...", 
                           time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(expires_at)),
                           len(self._cache))
            else:
                logger.debug("Cache entry already exists for hash=%s, skipping duplicate write", 
                            content_hash[:16] + "...")
    
    async def get_cache_stats(self) -> Dict[str, any]:
        """Get cache statistics including expiration info."""
        async with self._lock:
            current_time = time.time()
            valid_entries = 0
            expired_entries = 0
            
            for entry in self._cache.values():
                if current_time > entry['expires_at']:
                    expired_entries += 1
                else:
                    valid_entries += 1
            
            return {
                "cached_files": len(self._cache),
                "valid_entries": valid_entries,
                "expired_entries": expired_entries,
                "total_size_bytes": sum(len(k) + len(str(v)) for k, v in self._cache.items()),
                "ttl_seconds": CLAUDE_FILE_TTL_SECONDS
            }
    
    async def cleanup_expired(self) -> int:
        """Remove expired entries and return count cleaned."""
        async with self._lock:
            current_time = time.time()
            expired_keys = [
                content_hash for content_hash, entry in self._cache.items()
                if current_time > entry['expires_at']
            ]
            
            for key in expired_keys:
                del self._cache[key]
            
            if expired_keys:
                logger.info("Cleaned up %d expired cache entries", len(expired_keys))
            
            return len(expired_keys)
    
    async def clear_cache(self) -> int:
        """Clear all cached entries and return count cleared."""
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info("Cleared %d cached file IDs", count)
            return count

# Global cache instance
_file_cache = FileCacheManager()

async def get_cached_file_id(pdf_content: bytes) -> Optional[str]:
    """Get cached Claude file ID for PDF content."""
    return await _file_cache.get_file_id(pdf_content)

async def cache_file_id(pdf_content: bytes, file_id: str) -> None:
    """Cache Claude file ID for PDF content with atomic write."""
    await _file_cache.cache_file_id(pdf_content, file_id)

async def get_file_cache_stats() -> Dict[str, any]:
    """Get file cache statistics."""
    return await _file_cache.get_cache_stats()

async def cleanup_expired_cache() -> int:
    """Cleanup expired cache entries."""
    return await _file_cache.cleanup_expired() 