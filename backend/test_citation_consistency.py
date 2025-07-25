#!/usr/bin/env python3
"""
Test citation field consistency between backend and frontend expectations.
"""

import asyncio
import httpx
import json

async def test_citation_fields():
    """Verify citation API returns the expected fields."""
    # Use a known document ID for testing
    doc_id = "46280943-065e-4ddd-a391-ebb19faa330f"
    print(f"Testing document: {doc_id}")
    
    async with httpx.AsyncClient() as client:
        
        # Get citations for this document
        citations_response = await client.get(f"http://localhost:8000/api/documents/{doc_id}/citations")
        if citations_response.status_code != 200:
            print(f"Error fetching citations: {citations_response.status_code}")
            return
            
        citations = citations_response.json()
        print(f"\nFound {len(citations)} citations")
        
        if citations:
            citation = citations[0]
            print("\nFirst citation structure:")
            print(json.dumps(citation, indent=2))
            
            # Verify expected fields
            print("\nField validation:")
            expected_fields = ['id', 'documentId', 'citedText', 'displayText', 'searchableText', 'rects']
            for field in expected_fields:
                if field in citation:
                    print(f"✓ {field}: present")
                else:
                    print(f"✗ {field}: MISSING")
                    
            # Check for deprecated fields
            deprecated_fields = ['text']
            for field in deprecated_fields:
                if field in citation:
                    print(f"⚠ {field}: DEPRECATED FIELD STILL PRESENT")
                else:
                    print(f"✓ {field}: correctly removed")
                    
            # Verify citedText is the primary display field
            if citation.get('citedText'):
                print(f"\n✓ citedText value: '{citation['citedText'][:50]}...'")
                
                # Check if displayText matches or provides enhanced value
                if citation.get('displayText'):
                    if citation['displayText'] == citation['citedText']:
                        print("  displayText: same as citedText (OK)")
                    else:
                        print(f"  displayText: '{citation['displayText'][:50]}...' (enhanced)")
                        
                # Check searchableText for PDF search
                if citation.get('searchableText'):
                    print(f"  searchableText: '{citation['searchableText']}' (for PDF search)")

if __name__ == "__main__":
    asyncio.run(test_citation_fields())