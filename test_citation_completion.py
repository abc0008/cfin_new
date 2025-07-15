#!/usr/bin/env python
"""
Test script to verify that citation completion logic works correctly
with the updated heuristic.
"""

# Simulate the citation completion logic
def test_citation_completion():
    test_cases = [
        {
            "name": "All 3 citations received",
            "received_citation_markers": {1, 2, 3},
            "highest_citation_marker": 3,
            "citations_in_current_batch": 1,
            "expected_result": True,
            "expected_reason": "All 3 citations received, completing message"
        },
        {
            "name": "Only first citation received",
            "received_citation_markers": {1},
            "highest_citation_marker": 3,
            "citations_in_current_batch": 1,
            "expected_result": False,
            "expected_reason": "Still waiting for citations 2 and 3"
        },
        {
            "name": "Two citations in batch",
            "received_citation_markers": {1, 2},
            "highest_citation_marker": 2,
            "citations_in_current_batch": 2,
            "expected_result": True,
            "expected_reason": "Received batch of 2 citations, completing message"
        },
        {
            "name": "Single citation only",
            "received_citation_markers": {1},
            "highest_citation_marker": 1,
            "citations_in_current_batch": 1,
            "expected_result": True,
            "expected_reason": "Single citation received, completing message"
        },
        {
            "name": "Both citations when expecting 2",
            "received_citation_markers": {1, 2},
            "highest_citation_marker": 2,
            "citations_in_current_batch": 1,
            "expected_result": True,
            "expected_reason": "Both citations received, completing message"
        },
        {
            "name": "Missing middle citation",
            "received_citation_markers": {1, 3},
            "highest_citation_marker": 3,
            "citations_in_current_batch": 1,
            "expected_result": False,
            "expected_reason": "Missing citation 2"
        }
    ]
    
    for test in test_cases:
        print(f"\n--- Test: {test['name']} ---")
        print(f"Received: {sorted(test['received_citation_markers'])}")
        print(f"Highest: {test['highest_citation_marker']}")
        print(f"Batch size: {test['citations_in_current_batch']}")
        
        # Apply the logic from the code
        received_citation_markers = test['received_citation_markers']
        highest_citation_marker = test['highest_citation_marker']
        citations_in_current_batch = test['citations_in_current_batch']
        
        # Check if we have all expected citations (1 through highest_citation_marker)
        expected_citations = set(range(1, highest_citation_marker + 1))
        all_citations_received = expected_citations == received_citation_markers
        
        # Complete when we have all expected citations
        should_complete = False
        reason = ""
        
        if all_citations_received:
            if highest_citation_marker >= 3:
                # For 3+ citations, complete as soon as we have them all
                should_complete = True
                reason = f"All {highest_citation_marker} citations received, completing message"
            elif highest_citation_marker == 2 and len(received_citation_markers) == 2:
                # For exactly 2 citations, complete when we have both
                should_complete = True
                reason = "Both citations received, completing message"
            elif highest_citation_marker == 1 and citations_in_current_batch >= 1:
                # For single citation, complete when we receive it
                should_complete = True
                reason = "Single citation received, completing message"
        elif citations_in_current_batch >= 2:
            # If we get multiple citations in a batch, that's often a sign we have them all
            should_complete = True
            reason = f"Received batch of {citations_in_current_batch} citations, completing message"
        else:
            reason = f"Still waiting for citations. Have {sorted(received_citation_markers)}, expecting {sorted(expected_citations)}"
        
        print(f"Should complete: {should_complete}")
        print(f"Reason: {reason}")
        print(f"Expected: {test['expected_result']} - {test['expected_reason']}")
        print(f"PASS" if should_complete == test['expected_result'] else "FAIL")

if __name__ == "__main__":
    test_citation_completion()