#!/usr/bin/env python3
"""
Test script to verify display_text is being returned by the API.
"""

import asyncio
import httpx
import json

async def test_display_text():
    """Test that the /api/documents/{id}/citations endpoint returns display_text."""
    
    # First, get all documents
    async with httpx.AsyncClient(follow_redirects=True) as client:
        # Get documents
        response = await client.get("http://localhost:8000/api/documents/")
        if response.status_code != 200:
            print(f"Failed to get documents: {response.status_code}")
            return
            
        documents = response.json()
        if not documents:
            print("No documents found in the system")
            return
            
        # Test the first document that has citations
        for doc in documents:
            doc_id = doc.get('id')
            print(f"\n📄 Testing document: {doc_id} - {doc.get('filename', 'Unknown')}")
            
            # Get citations for this document
            citations_response = await client.get(f"http://localhost:8000/api/documents/{doc_id}/citations")
            
            if citations_response.status_code == 200:
                citations = citations_response.json()
                if citations:
                    print(f"Found {len(citations)} citations")
                    
                    # Check first few citations
                    for i, citation in enumerate(citations[:3]):
                        print(f"\n  Citation {i+1}:")
                        print(f"    ID: {citation.get('id', 'N/A')}")
                        print(f"    Text: {citation.get('text', 'N/A')[:50]}...")
                        print(f"    CitedText: {citation.get('citedText', 'N/A')[:50]}...")
                        print(f"    DisplayText: {citation.get('displayText', 'N/A')}")
                        print(f"    Has Rects: {len(citation.get('rects', [])) > 0}")
                        
                    # Found citations, we can stop
                    break
            else:
                print(f"  Failed to get citations: {citations_response.status_code}")

if __name__ == "__main__":
    asyncio.run(test_display_text())