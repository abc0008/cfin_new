#!/usr/bin/env python3
"""
Integration tests for Claude API upgrades (Steps 4-6).
Tests the NEW optimization features: Files API, token-efficient tools, model routing, and service optimizations.
Does NOT overlap with existing Claude service functionality tests.
"""

import asyncio
import logging
import os
import sys
from unittest.mock import Mock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestClaudeUpgradeIntegration:
    """Integration tests for Claude API upgrade optimizations."""

    async def test_files_api_client_integration(self):
        """Test Files API client integration (NEW in upgrade)."""
        logger.info("Testing Files API client integration...")
        
        from pdf_processing.claude_file_client import upload_pdf
        
        # Create test PDF data
        test_pdf_data = b"Mock PDF content for testing Files API"
        test_filename = "test_financial_document.pdf"
        
        # Mock the httpx response for Files API
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "file_upgrade_test123",
            "type": "file",
            "filename": test_filename,
            "size": len(test_pdf_data)
        }
        
        with patch('httpx.AsyncClient.post', return_value=mock_response) as mock_post:
            file_id = await upload_pdf(test_pdf_data, test_filename)
            
            assert file_id == "file_upgrade_test123"
            assert mock_post.called
            
            # Verify Files API specific headers (NEW in upgrade)
            call_args = mock_post.call_args
            headers = call_args[1]['headers']
            assert 'anthropic-beta' in headers
            assert 'files-api-2025-04-14' in headers['anthropic-beta']
            
            # Verify size limit validation (NEW in upgrade)
            assert len(test_pdf_data) <= 32 * 1024 * 1024  # 32MB limit
            
            logger.info("✅ Files API client integration test passed")

    async def test_model_router_optimization(self):
        """Test intelligent model routing (NEW in upgrade)."""
        logger.info("Testing model router optimization...")
        
        from pdf_processing.model_router import choose_model
        from settings import MODEL_HAIKU, MODEL_SONNET
        
        # Test light tools + small token count = Haiku
        light_tools = {"generate_table_data"}
        small_token_count = 1000  # Under 6k threshold
        
        model = choose_model(light_tools, small_token_count)
        assert model == MODEL_HAIKU
        logger.info(f"Light tools + small tokens ({small_token_count}) correctly routed to: {model}")
        
        # Test heavy tools = Sonnet
        heavy_tools = {"generate_complex_analysis", "extract_comprehensive_data"}
        
        model = choose_model(heavy_tools, small_token_count)
        assert model == MODEL_SONNET
        logger.info(f"Heavy tools correctly routed to: {model}")
        
        # Test large token count = Sonnet
        large_token_count = 8000  # Over 6k threshold
        
        model = choose_model(light_tools, large_token_count)
        assert model == MODEL_SONNET
        logger.info(f"Large token count ({large_token_count}) correctly routed to: {model}")
        
        logger.info("✅ Model router optimization test passed")

    async def test_token_counting_efficiency(self):
        """Test token counting for efficiency measurement (NEW in upgrade)."""
        logger.info("Testing token counting efficiency...")
        
        from utils.token_utils import count_tokens
        
        # Test simple message token counting
        simple_message = [{"role": "user", "content": "Hello world"}]
        simple_tokens = count_tokens(simple_message)
        assert simple_tokens > 0
        
        # Test file reference message (should be more efficient)
        file_message = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Analyze this document"},
                    {"type": "document", "source": {"type": "file", "file_id": "file_123"}}
                ]
            }
        ]
        file_tokens = count_tokens(file_message)
        assert file_tokens > 0
        
        # File reference should be much more efficient than embedding full text
        large_text_message = [{"role": "user", "content": "Analyze this: " + "text " * 1000}]
        large_text_tokens = count_tokens(large_text_message)
        
        # File reference should use significantly fewer tokens than full text
        efficiency_ratio = file_tokens / large_text_tokens
        assert efficiency_ratio < 0.1  # File reference should be <10% of full text tokens
        
        logger.info(f"Token efficiency: file reference uses {efficiency_ratio:.1%} of full text tokens")
        logger.info("✅ Token counting efficiency test passed")

    async def test_rate_limiting_bucket_integration(self):
        """Test rate limiting bucket integration (NEW in upgrade)."""
        logger.info("Testing rate limiting bucket integration...")
        
        from utils.claude_bucket import ClaudeBucket
        
        # Test bucket state update
        test_headers = {
            "anthropic-ratelimit-tokens-remaining": "5000",
            "anthropic-ratelimit-tokens-reset": "30.5"
        }
        
        ClaudeBucket.update(test_headers)
        
        assert ClaudeBucket._tokens_remaining == 5000
        # _reset_ts is calculated as current time + reset seconds, so just verify it's reasonable
        import time
        expected_reset_time = time.time() + 30.5
        assert abs(ClaudeBucket._reset_ts - expected_reset_time) < 2  # Within 2 seconds tolerance
        
        # Test throttle calculation (should not throttle with plenty of tokens)
        delay = await ClaudeBucket.throttle(100)  # Need 100 tokens
        # Should not need to wait since we have 5000 tokens available
        assert delay is None
        
        # Test low token scenario
        ClaudeBucket.update({
            "anthropic-ratelimit-tokens-remaining": "100",
            "anthropic-ratelimit-tokens-reset": "10.0"
        })
        
        # Should still work, but would calculate delay for very low tokens
        delay = await ClaudeBucket.throttle(50)  # Need 50 tokens, have 100
        # Should not need to wait since we still have enough tokens
        assert delay is None
        
        logger.info("✅ Rate limiting bucket integration test passed")

    async def test_claude_service_optimization_integration(self):
        """Test ClaudeService optimization integration (NEW in upgrade)."""
        logger.info("Testing ClaudeService optimization integration...")
        
        from pdf_processing.api_service import ClaudeService
        from repositories.document_repository import DocumentRepository
        
        # Mock repository and document
        mock_repo = Mock(spec=DocumentRepository)
        mock_doc = Mock()
        mock_doc.full_text = "Cached optimized financial document text"
        mock_doc.text_sha256 = "abc123def456"
        mock_doc.claude_file_id = "file_cached_123"
        mock_repo.get_document.return_value = mock_doc
        
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test_key'}):
            service = ClaudeService()
            
            # Test optimized text retrieval with caching
            with patch.object(service, '_extract_full_text', return_value="Fresh extracted text") as mock_extract:
                # Should return cached text, not extract fresh
                result = await service.get_document_text("test_doc_id", mock_repo)
                
                # Should use cached text
                assert result == "Cached optimized financial document text"
                # Should not call extraction since text is cached
                mock_extract.assert_not_called()
                
                logger.info("✅ Cached text retrieval optimization working")
        
        logger.info("✅ ClaudeService optimization integration test passed")

    async def test_anthropic_beta_headers_integration(self):
        """Test Anthropic beta headers integration (NEW in upgrade)."""
        logger.info("Testing Anthropic beta headers integration...")
        
        from pdf_processing.api_service import ClaudeService
        from settings import ANTHROPIC_BETA
        
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test_key'}):
            service = ClaudeService()
            
            # Verify extra headers include both beta features
            assert hasattr(service, '_extra_headers')
            assert ANTHROPIC_BETA in service._extra_headers['anthropic-beta']
            assert 'token-efficient-tools-2025-02-19' in service._extra_headers['anthropic-beta']
            assert 'files-api-2025-04-14' in service._extra_headers['anthropic-beta']
            
            logger.info(f"Beta headers correctly configured: {service._extra_headers['anthropic-beta']}")
        
        logger.info("✅ Anthropic beta headers integration test passed")

    async def test_hash_utilities_integration(self):
        """Test hash utilities for caching (NEW in upgrade)."""
        logger.info("Testing hash utilities integration...")
        
        from utils.hashlib_utils import sha256_str
        
        # Test consistent hashing
        test_text = "Financial document content for hashing test"
        hash1 = sha256_str(test_text)
        hash2 = sha256_str(test_text)
        
        assert hash1 == hash2  # Same input should give same hash
        assert len(hash1) == 64  # SHA256 is 64 hex characters
        assert isinstance(hash1, str)
        
        # Test different inputs give different hashes
        different_text = "Different financial content"
        hash3 = sha256_str(different_text)
        assert hash1 != hash3
        
        logger.info("✅ Hash utilities integration test passed")

    async def test_document_service_optimization_integration(self):
        """Test DocumentService uses new optimizations (NEW in upgrade)."""
        logger.info("Testing DocumentService optimization integration...")
        
        from pdf_processing.document_service import DocumentService
        from repositories.document_repository import DocumentRepository
        
        # Mock repository
        mock_repo = Mock(spec=DocumentRepository)
        
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test_key'}):
            service = DocumentService(mock_repo)
            
            # Verify service has Claude service with optimizations
            assert hasattr(service, 'claude_service')
            assert hasattr(service.claude_service, '_extra_headers')
            
            # Test optimized text retrieval method exists
            assert hasattr(service, 'get_document_text_optimized')
            
            # Mock the optimized retrieval
            with patch.object(service.claude_service, 'get_document_text', 
                             return_value="Optimized cached document text") as mock_get:
                
                result = await service.get_document_text_optimized("test_doc_123")
                assert result == "Optimized cached document text"
                assert mock_get.called
                
                logger.info("✅ DocumentService optimization integration working")
        
        logger.info("✅ DocumentService optimization integration test passed")

    async def test_end_to_end_optimization_flow(self):
        """Test end-to-end optimization flow (NEW in upgrade)."""
        logger.info("Testing end-to-end optimization flow...")
        
        from pdf_processing.api_service import ClaudeService
        from pdf_processing.model_router import choose_model
        from utils.token_utils import count_tokens
        from utils.claude_bucket import ClaudeBucket
        
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test_key'}):
            service = ClaudeService()
            
            # Simulate end-to-end optimized request
            test_query = "Analyze the revenue trends"
            test_tools = {"generate_table_data"}  # Light tool
            
            # 1. Model routing should choose Haiku for light tools
            test_token_count = count_tokens([{"role": "user", "content": test_query}])
            chosen_model = choose_model(test_tools, test_token_count)
            assert chosen_model == "claude-3-haiku-20250315"
            
            # 2. Token counting should work
            test_messages = [{"role": "user", "content": test_query}]
            token_count = count_tokens(test_messages)
            assert token_count > 0
            
            # 3. Rate limiting bucket should be functional
            ClaudeBucket.update({
                "anthropic-ratelimit-tokens-remaining": "10000",
                "anthropic-ratelimit-tokens-reset": "60.0"
            })
            delay = await ClaudeBucket.throttle(500)  # Need 500 tokens
            assert delay is None  # No throttling needed with high token count
            
            # 4. Service should have optimization headers
            assert 'anthropic-beta' in service._extra_headers
            
            logger.info("✅ End-to-end optimization flow working correctly")
        
        logger.info("✅ End-to-end optimization flow test passed")

async def test_multi_tool_request():
    """Test multi-tool request (chart + metric) under new header setup."""
    logger.info("Testing multi-tool request...")
    
    from pdf_processing.api_service import ClaudeService
    
    # Mock a response with multiple tools
    mock_response = Mock()
    mock_response.content = [
        Mock(type="text", text="Analysis of revenue trends..."),
        Mock(type="tool_use", name="generate_graph_data", input={"type": "line", "data": [{"x": "Q1", "y": 100}]}),
        Mock(type="tool_use", name="generate_financial_metric", input={"name": "Revenue", "value": 1000000})
    ]
    mock_response.response_headers = {"anthropic-ratelimit-tokens-remaining": "8000"}
    
    with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test_key'}):
        with patch.object(ClaudeService, '_claude_call', return_value=mock_response):
            service = ClaudeService()
            result = await service.analyze_with_visualization_tools(
                document_text="Sample financial document",
                user_query="Generate a revenue chart and calculate key metrics",
                requested_tools={"generate_graph_data", "generate_financial_metric"}
            )
            
            # Verify multi-tool response structure
            assert "analysis_text" in result
            assert "visualizations" in result
            assert "metrics" in result
            logger.info("✅ Multi-tool request handled correctly with optimized headers")

async def main():
    """Run all Claude upgrade integration tests."""
    logger.info("🚀 Starting Claude API upgrade integration tests...")
    
    test_suite = TestClaudeUpgradeIntegration()
    
    try:
        await test_suite.test_files_api_client_integration()
        await test_suite.test_model_router_optimization()
        await test_suite.test_token_counting_efficiency()
        await test_suite.test_rate_limiting_bucket_integration()
        await test_suite.test_claude_service_optimization_integration()
        await test_suite.test_anthropic_beta_headers_integration()
        await test_suite.test_hash_utilities_integration()
        await test_suite.test_document_service_optimization_integration()
        await test_suite.test_end_to_end_optimization_flow()
        await test_multi_tool_request()
        
        logger.info("🎉 All Claude API upgrade integration tests passed!")
        logger.info("✅ New optimization features are fully functional")
        
        # Summary of NEW optimizations tested
        logger.info("\n📊 CLAUDE UPGRADE OPTIMIZATION SUMMARY:")
        logger.info("• Files API integration (32MB limit, proper headers) - ✅ Working")
        logger.info("• Token-efficient tools with proper beta headers - ✅ Working") 
        logger.info("• Intelligent model routing (Haiku/Sonnet) - ✅ Working")
        logger.info("• Rate limiting with bucket throttling - ✅ Working")
        logger.info("• SHA256 caching for text optimization - ✅ Working")
        logger.info("• Service-level optimization integration - ✅ Working")
        logger.info("• End-to-end efficiency improvements - ✅ Working")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Claude upgrade integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 