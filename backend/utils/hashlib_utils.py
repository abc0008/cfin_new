"""
Utility functions for hashing operations.
"""
import hashlib

def sha256_str(txt: str) -> str:
    """
    Generate SHA256 hash of a string.
    
    Args:
        txt: The string to hash
        
    Returns:
        The SHA256 hash as a hexadecimal string
    """
    return hashlib.sha256(txt.encode("utf-8")).hexdigest() 