#!/usr/bin/env python3
"""
Simple test to verify Claude API upgrades are working.
Tests token headers, model routing, and Files API integration.
"""

import asyncio
import logging
import os
import pytest
from unittest.mock import Mock, patch, AsyncMock

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_claude_service_headers():
    """Test that ClaudeService includes the correct headers."""
    from pdf_processing.api_service import ClaudeService
    from settings import ANTHROPIC_BETA
    
    # Mock the API key
    with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test_key'}):
        service = ClaudeService()
        
        # Check that the extra headers are set correctly
        assert service._extra_headers["anthropic-beta"] == ANTHROPIC_BETA
        logger.info("✅ Headers test passed - anthropic-beta header is correctly set")
        
        # Check that the header includes both beta flags
        assert "token-efficient-tools-2025-02-19" in ANTHROPIC_BETA
        assert "files-api-2025-04-14" in ANTHROPIC_BETA
        logger.info("✅ Beta flags test passed - both token-efficient and files-api flags present")

@pytest.mark.asyncio
async def test_model_router():
    """Test the model router chooses the right model."""
    from pdf_processing.model_router import choose_model
    from settings import MODEL_HAIKU, MODEL_SONNET
    
    # Test light tools with small token count -> Haiku
    light_tools = {"generate_table_data", "generate_financial_metric"}
    small_tokens = 3000
    model = choose_model(light_tools, small_tokens)
    assert model == MODEL_HAIKU
    logger.info("✅ Model router test 1 passed - light tools + small tokens = Haiku")
    
    # Test heavy tools or large token count -> Sonnet  
    heavy_tools = {"generate_graph_data", "complex_analysis"}
    large_tokens = 8000
    model = choose_model(heavy_tools, large_tokens)
    assert model == MODEL_SONNET
    logger.info("✅ Model router test 2 passed - heavy tools + large tokens = Sonnet")
    
    # Test light tools but large token count -> Sonnet
    model = choose_model(light_tools, large_tokens)
    assert model == MODEL_SONNET
    logger.info("✅ Model router test 3 passed - light tools + large tokens = Sonnet")

async def test_token_counting():
    """Test the token counting utility."""
    from utils.token_utils import count_tokens
    
    # Test simple text message
    messages = [{"role": "user", "content": "Hello world"}]
    tokens = count_tokens(messages)
    assert tokens > 0
    logger.info(f"✅ Token counting test 1 passed - simple message: {tokens} tokens")
    
    # Test multimodal message
    messages = [
        {
            "role": "user", 
            "content": [
                {"type": "text", "text": "Analyze this document"},
                {"type": "document", "source": {"type": "file", "file_id": "test_id"}}
            ]
        }
    ]
    tokens = count_tokens(messages)
    assert tokens > 0
    logger.info(f"✅ Token counting test 2 passed - multimodal message: {tokens} tokens")

async def test_claude_bucket():
    """Test the rate limiting bucket."""
    from utils.claude_bucket import ClaudeBucket
    
    # Test updating bucket state
    ClaudeBucket.update({
        "anthropic-ratelimit-tokens-remaining": "1000",
        "anthropic-ratelimit-tokens-reset": "10.5"
    })
    
    assert ClaudeBucket._tokens_remaining == 1000
    logger.info("✅ Claude bucket test passed - rate limit state updated correctly")

async def test_hash_utils():
    """Test the SHA256 utility."""
    from utils.hashlib_utils import sha256_str
    
    text = "Hello, world!"
    hash1 = sha256_str(text)
    hash2 = sha256_str(text)
    
    assert hash1 == hash2  # Same input should give same hash
    assert len(hash1) == 64  # SHA256 is 64 hex characters
    logger.info("✅ Hash utils test passed - consistent SHA256 hashing")

async def main():
    """Run all tests."""
    logger.info("🚀 Starting Claude API upgrade tests...")
    
    try:
        await test_claude_service_headers()
        await test_model_router()
        await test_token_counting()
        await test_claude_bucket()
        await test_hash_utils()
        
        logger.info("🎉 All tests passed! Claude API upgrades are working correctly.")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 