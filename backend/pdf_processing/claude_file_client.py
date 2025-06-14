import httpx
import settings
import asyncio
import os
from utils.file_cache import get_cached_file_id, cache_file_id
from utils.secure_logging import audit_pdf_access, PrivacyAwareLogger

log = PrivacyAwareLogger(__name__)

def _get_safe_headers() -> dict:
    """Get headers with actual API key for requests."""
    return {
        "x-api-key":         os.getenv("ANTHROPIC_API_KEY"),
        "anthropic-version": "2023-06-01",
        "anthropic-beta":    settings.ANTHROPIC_BETA,
    }

def _get_masked_headers() -> dict:
    """Get headers with masked API key for safe logging."""
    headers = _get_safe_headers()
    if headers["x-api-key"]:
        headers["x-api-key"] = headers["x-api-key"][:8] + "***"
    return headers

_BASE_URL = "https://api.anthropic.com/v1/files"

async def upload_pdf(filename: str, data: bytes, max_retries: int = 3) -> str:
    """
    Upload a PDF to Claude's Files API with retry logic and cross-tenant caching.
    
    Args:
        filename: Name of the PDF file
        data: Raw PDF bytes
        max_retries: Maximum retry attempts for 5xx errors
        
    Returns:
        File ID string (e.g. "file_01AB...")
        
    Raises:
        ValueError: If PDF exceeds 32MB limit
        httpx.HTTPStatusError: If API request fails after retries
    """
    if len(data) > settings.FILES_MAX_SIZE_MB * 1024 ** 2:
        raise ValueError(f"PDF exceeds Files-API {settings.FILES_MAX_SIZE_MB} MB limit")

    # Check cache first to avoid duplicate uploads
    cached_file_id = await get_cached_file_id(data)
    if cached_file_id:
        log.info("Using cached file_id=%s for %s (%.1f MB)", 
                cached_file_id, filename, len(data)/(1024**2))
        # Audit cache hit for compliance
        audit_pdf_access("cache_hit", cached_file_id, "system", len(data))
        return cached_file_id

    headers = _get_safe_headers()
    
    for attempt in range(max_retries + 1):
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.post(
                    _BASE_URL,
                    headers=headers,
                    files={"file": (filename, data, "application/pdf")},
                )
            r.raise_for_status()
            file_id = r.json()["id"]
            
            # Cache the file ID for future use
            await cache_file_id(data, file_id)
            
            # Audit successful upload for compliance
            audit_pdf_access("upload", file_id, "system", len(data))
            
            log.info("Uploaded %s (%.1f MB) → %s", filename, len(data)/(1024**2), file_id)
            return file_id
            
        except httpx.HTTPStatusError as e:
            # Retry only on 5xx server errors, not 4xx client errors
            if e.response.status_code >= 500 and attempt < max_retries:
                backoff_time = 2 ** attempt  # 1s, 2s, 4s exponential backoff
                log.warning("Upload failed with %d on attempt %d/%d, retrying in %ds (headers: %s)", 
                           e.response.status_code, attempt + 1, max_retries + 1, 
                           backoff_time, _get_masked_headers())
                await asyncio.sleep(backoff_time)
                continue
            elif e.response.status_code >= 400 and e.response.status_code < 500:
                # 4xx errors (bad request, auth, etc.) - don't retry, fail fast
                log.error("Upload failed with client error %d (no retry): %s (headers: %s)", 
                         e.response.status_code, str(e), _get_masked_headers())
                raise
            else:
                log.error("Upload failed permanently after %d attempts: %s (headers: %s)", 
                         max_retries + 1, str(e), _get_masked_headers())
                raise 