# backend/utils/token_utils.py

import json
from typing import List, Dict, Any

def count_tokens(messages: List[Dict[str, Any]]) -> int:
    """
    Estimate token count for a list of messages.
    This is a rough approximation: 4 characters ≈ 1 token for English text.
    
    Args:
        messages: List of message dictionaries
        
    Returns:
        Estimated token count
    """
    total_chars = 0
    
    for message in messages:
        content = message.get("content", "")
        
        # Handle string content
        if isinstance(content, str):
            total_chars += len(content)
        
        # Handle list content (multimodal messages)
        elif isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    # Count text content
                    if item.get("type") == "text":
                        total_chars += len(item.get("text", ""))
                    # For document/image content, add a base estimate
                    elif item.get("type") in ["document", "image"]:
                        total_chars += 100  # Base overhead for media
        
        # Handle dict content (legacy format)
        elif isinstance(content, dict):
            total_chars += len(json.dumps(content))
    
    # Rough approximation: 4 characters ≈ 1 token
    return total_chars // 4 