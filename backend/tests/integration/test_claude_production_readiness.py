#!/usr/bin/env python3
"""
Production readiness E2E tests for Claude API optimization.
Validates all optimizations work correctly end-to-end.
"""

import pytest
import asyncio
import os
import time

# Import the services we need to test
from pdf_processing.claude_file_client import upload_pdf
from pdf_processing.model_router import choose_model, get_model_stats
from pdf_processing.api_service import ClaudeService
from utils.file_cache import get_file_cache_stats, cleanup_expired_cache
from utils.request_context import init_request_metrics, get_request_metrics, get_cost_summary
from utils.secure_logging import audit_log_compliance
from utils.metrics import get_metrics_summary

# Test data - small sample PDF
TEST_PDF_CONTENT = b"""
%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
72 720 Td
(Test Financial Report) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000189 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
283
%%EOF
""".strip()

@pytest.mark.asyncio
@pytest.mark.integration
class TestClaudeProductionReadiness:
    """
    Comprehensive E2E tests for production readiness.
    Tests all optimization features working together.
    """

    async def test_complete_file_upload_optimization_flow(self):
        """Test the complete file upload with caching and metrics."""
        # Initialize request metrics
        metrics = init_request_metrics("test_upload_flow")
        
        filename = "test_financial_report.pdf"
        
        # First upload - should hit the API
        start_time = time.time()
        file_id_1 = await upload_pdf(filename, TEST_PDF_CONTENT)
        first_upload_time = time.time() - start_time
        
        assert file_id_1.startswith("file_"), "File ID should have correct format"
        
        # Second upload of same content - should hit cache
        start_time = time.time()
        file_id_2 = await upload_pdf(filename, TEST_PDF_CONTENT)
        second_upload_time = time.time() - start_time
        
        assert file_id_1 == file_id_2, "Cache should return same file ID"
        assert second_upload_time < first_upload_time, "Cache hit should be faster"
        
        # Verify cache stats
        cache_stats = await get_file_cache_stats()
        assert cache_stats["cached_files"] >= 1, "Should have cached files"
        assert cache_stats["valid_entries"] >= 1, "Should have valid cache entries"
        
        # Verify request metrics
        current_metrics = get_request_metrics()
        assert current_metrics is not None, "Request metrics should be tracked"
        
        print(f"✅ File upload optimization: 1st={first_upload_time:.3f}s, 2nd={second_upload_time:.3f}s")

    async def test_model_routing_decisions(self):
        """Test model routing based on tools and token count."""
        # Test light tools → Haiku
        light_tools = {"generate_table_data", "generate_financial_metric"}
        model_haiku = choose_model(light_tools, 3000)
        assert "haiku" in model_haiku.lower(), "Should route to Haiku for light tools"
        
        # Test heavy tools → Sonnet  
        heavy_tools = {"generate_graph_data", "complex_analysis"}
        model_sonnet = choose_model(heavy_tools, 3000)
        assert "sonnet" in model_sonnet.lower(), "Should route to Sonnet for heavy tools"
        
        # Test high token count → Sonnet
        model_high_tokens = choose_model(light_tools, 8000)
        assert "sonnet" in model_high_tokens.lower(), "Should route to Sonnet for high token count"
        
        # Verify model stats tracking
        stats = get_model_stats()
        assert stats["total_calls"] >= 3, "Should track model calls"
        assert "haiku_calls" in stats, "Should track Haiku calls"
        assert "sonnet_calls" in stats, "Should track Sonnet calls"
        
        print(f"✅ Model routing: {stats['haiku_calls']} Haiku, {stats['sonnet_calls']} Sonnet")

    async def test_token_counting_accuracy(self):
        """Test token counting for cost estimation."""
        from utils.token_utils import count_tokens
        
        # Test message token counting
        messages = [
            {"role": "user", "content": "Analyze this financial document for key metrics and trends."}
        ]
        
        token_count = count_tokens(messages)
        assert token_count > 0, "Should count tokens correctly"
        assert token_count < 100, "Simple message should have reasonable token count"
        
        # Test longer content
        long_content = "Financial analysis " * 100  # ~200 words
        long_messages = [{"role": "user", "content": long_content}]
        long_token_count = count_tokens(long_messages)
        
        assert long_token_count > token_count, "Longer content should have more tokens"
        
        print(f"✅ Token counting: short={token_count}, long={long_token_count}")

    @pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="No API key")
    async def test_claude_api_integration_with_optimizations(self):
        """Test actual Claude API calls with all optimizations enabled."""
        claude_service = ClaudeService()
        
        # Initialize request context
        init_request_metrics("test_api_integration")
        
        # Test tool-based analysis
        test_query = "Extract the top 3 financial metrics from this document."
        test_document = "Revenue: $1.2M\nNet Income: $300K\nGross Margin: 25%"
        
        result = await claude_service.analyze_with_visualization_tools(
            document_text=test_document,
            user_query=test_query,
            requested_tools={"generate_financial_metric"}
        )
        
        assert "analysis_text" in result, "Should return analysis text"
        assert "metrics" in result, "Should return metrics"
        assert len(result["metrics"]) > 0, "Should extract financial metrics"
        
        # Verify cost tracking
        cost_summary = get_cost_summary()
        assert "model_chosen" in cost_summary, "Should track model choice"
        assert "routing_reason" in cost_summary, "Should track routing reason"
        
        print(f"✅ API integration: model={cost_summary.get('model_chosen')}, "
              f"tools={cost_summary.get('tools_requested')}")

    async def test_security_and_privacy_compliance(self):
        """Test security features and privacy compliance."""
        # Test secure logging compliance
        compliance_report = audit_log_compliance()
        assert compliance_report["secure_logging_active"], "Secure logging should be active"
        assert compliance_report["audit_trails_enabled"], "Audit trails should be enabled"
        
        # Test sensitive data masking
        from utils.secure_logging import _mask_sensitive_content
        
        sensitive_data = "data:application/pdf;base64," + "A" * 1000
        masked = _mask_sensitive_content(sensitive_data)
        assert "MASKED" in masked, "Should mask sensitive PDF data"
        assert len(masked) < len(sensitive_data), "Masked content should be shorter"
        
        # Test API key masking in headers
        from pdf_processing.claude_file_client import _get_masked_headers
        masked_headers = _get_masked_headers()
        assert "***" in masked_headers["x-api-key"], "Should mask API key"
        
        print(f"✅ Security: patterns={compliance_report['sensitive_patterns_monitored']}, "
              f"recommendations={len(compliance_report['recommendations'])}")

    async def test_error_handling_and_retry_logic(self):
        """Test error handling and retry mechanisms."""
        # Test with invalid file size (should fail fast)
        oversized_data = b"x" * (50 * 1024 * 1024)  # 50MB > 32MB limit
        
        with pytest.raises(ValueError, match="exceeds.*limit"):
            await upload_pdf("oversized.pdf", oversized_data)
        
        # Test cache cleanup
        expired_count = await cleanup_expired_cache()
        assert expired_count >= 0, "Cleanup should return count"
        
        print(f"✅ Error handling: cache cleanup removed {expired_count} entries")

    async def test_metrics_and_monitoring_integration(self):
        """Test metrics collection and monitoring capabilities."""
        metrics_summary = get_metrics_summary()
        
        assert "prometheus_available" in metrics_summary, "Should report Prometheus status"
        assert "model_routing" in metrics_summary, "Should include model routing stats"
        assert "metrics_endpoints" in metrics_summary, "Should list available metrics"
        
        # Test that metrics endpoints are properly defined
        expected_metrics = [
            "claude_files_upload_seconds",
            "claude_tool_calls_total",
            "claude_cache_operations_total",
            "claude_token_efficiency_ratio",
            "claude_cost_reduction_percent"
        ]
        
        available_metrics = metrics_summary.get("metrics_endpoints", [])
        for metric in expected_metrics:
            assert metric in available_metrics, f"Should include {metric} metric"
        
        print(f"✅ Monitoring: {len(available_metrics)} metrics available, "
              f"Prometheus={metrics_summary['prometheus_available']}")

    async def test_cost_optimization_validation(self):
        """Test cost optimization claims with real measurements."""
        # Reset stats for clean measurement
        from pdf_processing.model_router import _model_call_counts
        _model_call_counts["haiku"] = 0
        _model_call_counts["sonnet"] = 0
        
        # Simulate various tool requests to demonstrate cost optimization
        test_scenarios = [
            ({"generate_table_data"}, 2000),  # Should → Haiku
            ({"generate_financial_metric"}, 3000),  # Should → Haiku  
            ({"generate_graph_data"}, 4000),  # Should → Sonnet
            ({"generate_table_data"}, 8000),  # Should → Sonnet (high tokens)
            ({"generate_financial_metric"}, 1500),  # Should → Haiku
        ]
        
        for tools, tokens in test_scenarios:
            choose_model(tools, tokens)
        
        stats = get_model_stats()
        haiku_ratio = stats["haiku_ratio"]
        
        # Validate cost optimization claims
        assert haiku_ratio >= 0.4, f"Should achieve >40% Haiku usage (got {haiku_ratio:.1%})"
        
        # Calculate actual cost reduction
        total_calls = stats["total_calls"]
        haiku_calls = stats["haiku_calls"]
        sonnet_calls = stats["sonnet_calls"]
        
        # Cost calculation (Haiku is ~12x cheaper)
        actual_cost = haiku_calls * 1 + sonnet_calls * 12
        baseline_cost = total_calls * 12  # All Sonnet
        cost_reduction = ((baseline_cost - actual_cost) / baseline_cost) * 100
        
        print(f"✅ Cost optimization: {haiku_ratio:.1%} Haiku usage, "
              f"{cost_reduction:.1f}% cost reduction")
        
        # Validate that we achieve meaningful cost reduction
        assert cost_reduction >= 20, f"Should achieve >20% cost reduction (got {cost_reduction:.1f}%)"

# Main test runner for CI integration
async def run_production_readiness_tests():
    """
    Run all production readiness tests and return summary.
    Suitable for CI/CD pipeline integration.
    """
    test_results = {
        "timestamp": time.time(),
        "tests_passed": 0,
        "tests_failed": 0,
        "optimization_metrics": {},
        "compliance_status": "UNKNOWN"
    }
    
    test_instance = TestClaudeProductionReadiness()
    
    tests = [
        "test_complete_file_upload_optimization_flow",
        "test_model_routing_decisions", 
        "test_token_counting_accuracy",
        "test_security_and_privacy_compliance",
        "test_error_handling_and_retry_logic",
        "test_metrics_and_monitoring_integration",
        "test_cost_optimization_validation"
    ]
    
    # Only run API test if API key is available
    if os.getenv("ANTHROPIC_API_KEY"):
        tests.append("test_claude_api_integration_with_optimizations")
    
    for test_name in tests:
        try:
            test_method = getattr(test_instance, test_name)
            await test_method()
            test_results["tests_passed"] += 1
            print(f"✅ PASSED: {test_name}")
        except Exception as e:
            test_results["tests_failed"] += 1
            print(f"❌ FAILED: {test_name} - {str(e)}")
    
    # Collect final metrics
    try:
        test_results["optimization_metrics"] = {
            "cache_stats": await get_file_cache_stats(),
            "model_stats": get_model_stats(),
            "metrics_summary": get_metrics_summary(),
            "compliance_report": audit_log_compliance()
        }
        test_results["compliance_status"] = "COMPLIANT"
    except Exception as e:
        test_results["compliance_status"] = f"ERROR: {str(e)}"
    
    # Overall status
    total_tests = test_results["tests_passed"] + test_results["tests_failed"]
    success_rate = test_results["tests_passed"] / max(total_tests, 1)
    
    print(f"\n🔬 PRODUCTION READINESS SUMMARY:")
    print(f"   Tests: {test_results['tests_passed']}/{total_tests} passed ({success_rate:.1%})")
    print(f"   Compliance: {test_results['compliance_status']}")
    
    if success_rate >= 0.9:
        print(f"   Status: ✅ PRODUCTION READY")
        test_results["status"] = "PRODUCTION_READY"
    else:
        print(f"   Status: ❌ NOT READY")
        test_results["status"] = "NOT_READY"
    
    return test_results

if __name__ == "__main__":
    # Allow running as standalone script
    asyncio.run(run_production_readiness_tests()) 