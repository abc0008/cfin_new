#!/usr/bin/env python3
"""
Secure logging utilities for data privacy and compliance.
Sanitizes sensitive content from logs while maintaining debugging capability.
"""

import logging
import re
import hashlib
from typing import Any, Dict, Optional
from functools import wraps

logger = logging.getLogger(__name__)

# Patterns that indicate sensitive content
SENSITIVE_PATTERNS = [
    r'data:application/pdf;base64,',  # Base64 PDF data
    r'"data":\s*"[A-Za-z0-9+/=]{100,}',  # Large base64 strings in JSON
    r'%PDF-\d\.\d',  # PDF file headers
    r'[A-Za-z0-9+/=]{500,}',  # Long base64-like strings
    r'SSN:\s*\d{3}-\d{2}-\d{4}',  # Social Security Numbers
    r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',  # Credit card patterns
    r'Bearer\s+[A-Za-z0-9\-_.~+/]+=*',  # API tokens
]

def _mask_sensitive_content(content: str, max_visible_chars: int = 50) -> str:
    """
    Mask sensitive content while preserving structure for debugging.
    
    Args:
        content: Original content that may contain sensitive data
        max_visible_chars: Maximum characters to show before masking
        
    Returns:
        Sanitized content safe for logging
    """
    if not content or len(content) <= max_visible_chars:
        return content
    
    # Check for sensitive patterns
    for pattern in SENSITIVE_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            # Create a content hash for tracking
            content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
            
            # Show beginning, mask middle, show hash
            visible_start = content[:max_visible_chars]
            return f"{visible_start}...[MASKED:{len(content)-max_visible_chars} chars, hash:{content_hash}]"
    
    # If no sensitive patterns detected, truncate normally
    if len(content) > max_visible_chars * 2:
        return f"{content[:max_visible_chars]}...[TRUNCATED:{len(content)} total chars]"
    
    return content

def _sanitize_dict(data: Dict[str, Any], max_depth: int = 3) -> Dict[str, Any]:
    """Recursively sanitize dictionary values."""
    if max_depth <= 0:
        return {"...": "max_depth_reached"}
    
    sanitized = {}
    for key, value in data.items():
        if isinstance(value, str):
            sanitized[key] = _mask_sensitive_content(value)
        elif isinstance(value, dict):
            sanitized[key] = _sanitize_dict(value, max_depth - 1)
        elif isinstance(value, list):
            sanitized[key] = [
                _sanitize_dict(item, max_depth - 1) if isinstance(item, dict)
                else _mask_sensitive_content(str(item)) if isinstance(item, str)
                else item
                for item in (value[:5] if len(value) > 5 else value)  # Limit list size
            ]
            if len(value) > 5:
                sanitized[key].append(f"...[{len(value)-5} more items]")
        else:
            sanitized[key] = value
    
    return sanitized

def safe_log_dict(data: Dict[str, Any], message: str = "", level: int = logging.DEBUG) -> None:
    """
    Safely log a dictionary with sensitive content masking.
    
    Args:
        data: Dictionary to log
        message: Optional message prefix
        level: Logging level to use
    """
    try:
        sanitized = _sanitize_dict(data)
        if message:
            logger.log(level, "%s: %s", message, sanitized)
        else:
            logger.log(level, "%s", sanitized)
    except Exception as e:
        logger.error("Error in safe_log_dict: %s", str(e))

def safe_log_api_call(function_name: str, **kwargs) -> None:
    """
    Safely log API call parameters with sensitive data masking.
    
    Args:
        function_name: Name of the function being called
        **kwargs: Parameters being passed to the function
    """
    sanitized_kwargs = _sanitize_dict(kwargs)
    logger.info("API Call: %s with parameters: %s", function_name, sanitized_kwargs)

def audit_pdf_access(operation: str, file_id: str, user_context: str = "", 
                     file_size: Optional[int] = None) -> None:
    """
    Create audit trail for PDF file access with privacy compliance.
    
    Args:
        operation: Type of operation (upload, download, process, cache_hit)
        file_id: Claude file ID or document ID
        user_context: User or system context
        file_size: Size of file in bytes
    """
    audit_entry = {
        "timestamp": "AUTO",  # Logger will add timestamp
        "operation": operation,
        "file_id": file_id,
        "user_context": user_context,
        "file_size_bytes": file_size,
        "privacy_note": "PDF content not logged for compliance"
    }
    
    # Use a dedicated audit logger if configured
    audit_logger = logging.getLogger("audit.pdf_access")
    audit_logger.info("PDF_ACCESS: %s", audit_entry)

def secure_function_logging(exclude_params: set = None):
    """
    Decorator to add secure logging to functions that handle sensitive data.
    
    Args:
        exclude_params: Set of parameter names to completely exclude from logs
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            exclude_params_safe = exclude_params or set()
            
            # Log function entry with sanitized parameters
            safe_params = {
                k: v for k, v in kwargs.items() 
                if k not in exclude_params_safe
            }
            safe_log_dict(safe_params, f"ENTER {func.__name__}", logging.DEBUG)
            
            try:
                result = await func(*args, **kwargs)
                logger.debug("EXIT %s: SUCCESS", func.__name__)
                return result
            except Exception as e:
                logger.error("EXIT %s: ERROR - %s", func.__name__, str(e))
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            exclude_params_safe = exclude_params or set()
            
            # Log function entry with sanitized parameters
            safe_params = {
                k: v for k, v in kwargs.items() 
                if k not in exclude_params_safe
            }
            safe_log_dict(safe_params, f"ENTER {func.__name__}", logging.DEBUG)
            
            try:
                result = func(*args, **kwargs)
                logger.debug("EXIT %s: SUCCESS", func.__name__)
                return result
            except Exception as e:
                logger.error("EXIT %s: ERROR - %s", func.__name__, str(e))
                raise
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

class PrivacyAwareLogger:
    """
    Logger wrapper that automatically sanitizes sensitive content.
    """
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def info(self, message: str, *args, **kwargs):
        """Log info message with automatic sanitization."""
        sanitized_message = _mask_sensitive_content(str(message))
        # Only mask string arguments, preserve numeric types for formatting
        sanitized_args = [
            _mask_sensitive_content(str(arg)) if isinstance(arg, str) 
            else arg 
            for arg in args
        ]
        self.logger.info(sanitized_message, *sanitized_args, **kwargs)
    
    def debug(self, message: str, *args, **kwargs):
        """Log debug message with automatic sanitization."""
        sanitized_message = _mask_sensitive_content(str(message))
        # Only mask string arguments, preserve numeric types for formatting
        sanitized_args = [
            _mask_sensitive_content(str(arg)) if isinstance(arg, str) 
            else arg 
            for arg in args
        ]
        self.logger.debug(sanitized_message, *sanitized_args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        """Log warning message with automatic sanitization."""
        sanitized_message = _mask_sensitive_content(str(message))
        # Only mask string arguments, preserve numeric types for formatting
        sanitized_args = [
            _mask_sensitive_content(str(arg)) if isinstance(arg, str) 
            else arg 
            for arg in args
        ]
        self.logger.warning(sanitized_message, *sanitized_args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        """Log error message with automatic sanitization."""
        sanitized_message = _mask_sensitive_content(str(message))
        # Only mask string arguments, preserve numeric types for formatting
        sanitized_args = [
            _mask_sensitive_content(str(arg)) if isinstance(arg, str) 
            else arg 
            for arg in args
        ]
        self.logger.error(sanitized_message, *sanitized_args, **kwargs)

# Privacy compliance check
def audit_log_compliance() -> Dict[str, Any]:
    """
    Audit current logging configuration for privacy compliance.
    
    Returns:
        Compliance report
    """
    compliance_report = {
        "timestamp": "AUTO",
        "secure_logging_active": True,
        "sensitive_patterns_monitored": len(SENSITIVE_PATTERNS),
        "audit_trails_enabled": True,
        "recommendations": []
    }
    
    # Check if audit logger is properly configured
    audit_logger = logging.getLogger("audit.pdf_access")
    if not audit_logger.handlers:
        compliance_report["recommendations"].append(
            "Configure dedicated audit.pdf_access logger for compliance"
        )
    
    # Check logging level
    root_logger = logging.getLogger()
    if root_logger.level <= logging.DEBUG:
        compliance_report["recommendations"].append(
            "Consider raising log level in production to reduce sensitive data exposure"
        )
    
    return compliance_report 