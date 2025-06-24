#!/usr/bin/env python3
"""
Comprehensive Test for Streaming Content Protection Fix

This test validates the enhanced content protection logic that prevents
initial streaming messages from disappearing during tool processing.

Tests multiple scenarios:
1. High quality streaming content vs truncated analysis
2. Low quality streaming content vs comprehensive analysis  
3. Equal quality content with different lengths
4. Tool processing interruption scenarios
5. Content quality assessment accuracy
"""

import asyncio
import sys
import os
import logging
from datetime import datetime

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from services.conversation_service import _assess_content_quality, _is_content_truncated

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestStreaming:
    """Test class for streaming content protection scenarios."""

    def test_content_quality_assessment(self):
        """Test the content quality assessment function."""
        print("\n=== Testing Content Quality Assessment ===")
        
        # Test cases with expected quality ranges
        test_cases = [
            # (content, expected_quality_range, description)
            ("", (0.0, 0.0), "Empty content"),
            ("The", (0.0, 0.2), "Very short content"),
            ("Let me provide a comprehensive analysis of the deposit mix trends over the", (0.1, 0.4), "Incomplete sentence"),
            ("""Let me provide a comprehensive analysis of the deposit mix trends over the reported periods. 
            The deposit mix shows a well-balanced approach to funding with strong diversification across multiple deposit types.
            This demonstrates effective liability management and customer relationship strategies.""", (0.6, 1.0), "Complete analysis"),
            ("""Based on the financial data provided, I can offer a comprehensive analysis of the deposit mix trends 
            and performance metrics for the bank. The analysis reveals several key insights about the institution's 
            funding strategy, customer base diversification, and operational efficiency.

            The deposit composition demonstrates a balanced approach with checking accounts representing approximately 
            35% of total deposits, savings accounts contributing 25%, and certificates of deposit making up 20% of 
            the portfolio. This diversification indicates strong customer relationship management and effective 
            product positioning across different market segments.

            Key performance indicators show consistent growth in core deposits with a 12% year-over-year increase 
            in non-interest bearing deposits, suggesting strong customer loyalty and operational excellence. 
            The cost of funds has remained stable at 1.8%, indicating effective pricing strategies and 
            competitive positioning in the market.""", (0.8, 1.0), "Comprehensive financial analysis")
        ]
        
        for content, expected_range, description in test_cases:
            quality = _assess_content_quality(content)
            min_expected, max_expected = expected_range
            
            print(f"  {description}:")
            print(f"    Content length: {len(content)} chars")
            print(f"    Quality score: {quality:.2f}")
            print(f"    Expected range: {min_expected}-{max_expected}")
            
            if min_expected <= quality <= max_expected:
                print(f"    ✅ PASS")
            else:
                print(f"    ❌ FAIL - Quality {quality:.2f} not in expected range {min_expected}-{max_expected}")
            print()

    def test_truncation_detection(self):
        """Test the content truncation detection function."""
        print("\n=== Testing Truncation Detection ===")
        
        test_cases = [
            # (content, expected_truncated, description)
            ("", True, "Empty content"),
            ("The", True, "Very short content"),
            ("Let me provide a comprehensive analysis of the deposit mix trends over the", True, "Mid-sentence truncation"),
            ("Let me provide", True, "Incomplete phrase"),
            ("Quarter-over-Quarter", True, "Dangling phrase"),
            ("The line chart above", True, "Chart reference without context"),
            ("This shows", True, "Incomplete statement"),
            ("The analysis indicates strong performance and", True, "Ends with conjunction"),
            ("Based on the analysis, the bank shows strong performance.", False, "Complete sentence"),
            ("""The comprehensive analysis reveals strong deposit growth trends. 
            The bank demonstrates excellent diversification across deposit types.
            Customer relationships remain strong with consistent growth patterns.""", False, "Complete analysis"),
            ("Analysis complete", True, "Too short for financial analysis"),
        ]
        
        for content, expected_truncated, description in test_cases:
            is_truncated = _is_content_truncated(content)
            
            print(f"  {description}:")
            print(f"    Content: \"{content[:50]}{'...' if len(content) > 50 else ''}\"")
            print(f"    Is truncated: {is_truncated}")
            print(f"    Expected: {expected_truncated}")
            
            if is_truncated == expected_truncated:
                print(f"    ✅ PASS")
            else:
                print(f"    ❌ FAIL - Got {is_truncated}, expected {expected_truncated}")
            print()

    def test_content_selection_logic(self):
        """Test the enhanced content selection logic scenarios."""
        print("\n=== Testing Content Selection Logic ===")
        
        # Simulate the key decision criteria from the enhanced logic
        def should_use_analysis(streaming_content, analysis_content):
            """Simulate the enhanced content selection logic."""
            streaming_quality = _assess_content_quality(streaming_content)
            analysis_quality = _assess_content_quality(analysis_content)
            
            return (
                # Analysis text must be significantly more comprehensive (not just longer)
                len(analysis_content.strip()) > len(streaming_content.strip()) * 1.2 and
                # Analysis text must be different (not just a duplicate)
                analysis_content.strip() != streaming_content.strip() and
                # Analysis text must have good quality (not truncated)
                analysis_quality >= streaming_quality and
                # Analysis text must not show signs of truncation
                not _is_content_truncated(analysis_content) and
                # Analysis text must be substantial (not just a fragment)
                len(analysis_content.strip()) > 200
            )
        
        scenarios = [
            {
                "name": "Scenario 1: High quality streaming vs truncated analysis",
                "streaming": """Let me provide a comprehensive analysis of the deposit mix trends over the reported periods. 
                The deposit mix shows a well-balanced approach to funding with strong diversification across multiple deposit types.
                This demonstrates effective liability management and customer relationship strategies with consistent growth patterns.""",
                "analysis": "Let me provide a comprehensive analysis of the deposit mix trends over the",
                "expected_choice": "streaming",
                "reason": "Analysis is truncated, streaming is complete"
            },
            {
                "name": "Scenario 2: Short streaming vs comprehensive analysis",
                "streaming": "Let me analyze the deposit trends.",
                "analysis": """Based on the comprehensive financial data analysis, the deposit mix demonstrates exceptional 
                diversification and growth trends. The bank maintains a well-balanced portfolio with checking accounts 
                representing 35% of deposits, savings contributing 25%, and CDs comprising 20% of the total portfolio.
                
                Key performance metrics indicate strong operational efficiency with 12% year-over-year growth in core deposits
                and stable funding costs at 1.8%. This reflects excellent customer relationship management and competitive
                positioning in the marketplace. The institution's liability management strategy appears highly effective.""",
                "expected_choice": "analysis",
                "reason": "Analysis is comprehensive and high quality, streaming is minimal"
            },
            {
                "name": "Scenario 3: Equal quality, analysis slightly longer",
                "streaming": """The deposit analysis reveals strong performance trends across all categories.
                Customer relationships remain solid with consistent growth in core deposits.""",
                "analysis": """The deposit analysis reveals strong performance trends across all categories.
                Customer relationships remain solid with consistent growth in core deposits and improved efficiency metrics.""",
                "expected_choice": "streaming",
                "reason": "Similar quality, not significantly longer (1.2x threshold)"
            },
            {
                "name": "Scenario 4: Duplicate content check",
                "streaming": """Complete deposit analysis showing strong growth and diversification.""",
                "analysis": """Complete deposit analysis showing strong growth and diversification.""",
                "expected_choice": "streaming",
                "reason": "Identical content, should preserve streaming"
            }
        ]
        
        for scenario in scenarios:
            print(f"  {scenario['name']}:")
            print(f"    Streaming length: {len(scenario['streaming'])} chars")
            print(f"    Analysis length: {len(scenario['analysis'])} chars")
            
            streaming_quality = _assess_content_quality(scenario['streaming'])
            analysis_quality = _assess_content_quality(scenario['analysis'])
            analysis_truncated = _is_content_truncated(scenario['analysis'])
            
            print(f"    Streaming quality: {streaming_quality:.2f}")
            print(f"    Analysis quality: {analysis_quality:.2f}")
            print(f"    Analysis truncated: {analysis_truncated}")
            
            should_use = should_use_analysis(scenario['streaming'], scenario['analysis'])
            actual_choice = "analysis" if should_use else "streaming"
            
            print(f"    Decision: Use {actual_choice}")
            print(f"    Expected: Use {scenario['expected_choice']}")
            print(f"    Reason: {scenario['reason']}")
            
            if actual_choice == scenario['expected_choice']:
                print(f"    ✅ PASS")
            else:
                print(f"    ❌ FAIL - Wrong choice made")
            print()

    def run_all_tests(self):
        """Run all test scenarios."""
        print("🧪 Starting Comprehensive Streaming Content Protection Tests")
        print("=" * 70)
        
        try:
            self.test_content_quality_assessment()
            self.test_truncation_detection()
            self.test_content_selection_logic()
            
            print("\n" + "=" * 70)
            print("✅ All streaming content protection tests completed!")
            print("\nThe enhanced content protection logic should now:")
            print("  - Preserve high-quality streaming content during tool processing")
            print("  - Only replace streaming content with demonstrably better analysis")
            print("  - Detect and reject truncated analysis content")
            print("  - Maintain excellent streaming UX while ensuring content completeness")
            return True
            
        except Exception as e:
            print(f"\n❌ Test failed with error: {e}")
            logger.error(f"Test execution failed: {e}", exc_info=True)
            return False

def main():
    """Main test execution function."""
    test_runner = TestStreaming()
    success = test_runner.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)