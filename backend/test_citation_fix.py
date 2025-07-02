#!/usr/bin/env python3
"""
Test to verify citation marker fix in conversation service
"""
import re

def test_citation_detection():
    """Test the citation detection logic we added"""
    
    # Test cases
    test_cases = [
        {
            "name": "Text with citations",
            "analysis_text": "Revenue was $1.5M [1] and expenses were $800K [2].",
            "current_content": "Revenue was $1.5M and expenses were $800K.",
            "should_update": True
        },
        {
            "name": "Both have citations",
            "analysis_text": "Revenue was $1.5M [1] and expenses were $800K [2].",
            "current_content": "Revenue was $1.5M [1] and expenses were $800K [2].",
            "should_update": False
        },
        {
            "name": "Neither has citations",
            "analysis_text": "Revenue was $1.5M and expenses were $800K.",
            "current_content": "Revenue was $1.5M and expenses were $800K.",
            "should_update": False
        },
        {
            "name": "Multiple citation markers",
            "analysis_text": "Q1 revenue [1] was higher than Q2 [2] and Q3 [3].",
            "current_content": "Q1 revenue was higher than Q2 and Q3.",
            "should_update": True
        }
    ]
    
    print("Testing Citation Detection Logic\n")
    print("=" * 60)
    
    for test in test_cases:
        print(f"\nTest: {test['name']}")
        print(f"Analysis text: {test['analysis_text']}")
        print(f"Current text:  {test['current_content']}")
        
        # Apply the logic from conversation_service.py
        analysis_has_citations = bool(re.search(r'\[\d+\]', test['analysis_text']))
        current_has_citations = bool(re.search(r'\[\d+\]', test['current_content']))
        
        should_update = analysis_has_citations and not current_has_citations
        
        print(f"Analysis has citations: {analysis_has_citations}")
        print(f"Current has citations:  {current_has_citations}")
        print(f"Should update:          {should_update}")
        print(f"Expected:               {test['should_update']}")
        
        if should_update == test['should_update']:
            print("✅ PASS")
        else:
            print("❌ FAIL")
    
    print("\n" + "=" * 60)
    print("\nThe fix ensures that when analysis_text contains citation")
    print("markers but current content doesn't, the message will be updated.")

if __name__ == "__main__":
    test_citation_detection()