#!/usr/bin/env python3
"""
Test the citation API endpoint to see what's being returned.
"""

import asyncio
import httpx
import json

async def test_citations():
    """Test fetching citations from the API."""
    # The document ID from the console logs
    document_id = "46280943-065e-4ddd-a391-ebb19faa330f"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://localhost:8000/api/documents/{document_id}/citations")
        
        if response.status_code == 200:
            citations = response.json()
            print(f"Found {len(citations)} citations\n")
            
            for i, citation in enumerate(citations[:2]):  # Show first 2
                print(f"Citation {i+1}:")
                print(f"  ID: {citation.get('id', 'N/A')}")
                print(f"  DocumentId: {citation.get('documentId', 'N/A')}")
                print(f"  CitedText: {citation.get('citedText', 'N/A')[:100] if citation.get('citedText') else 'N/A'}")
                print(f"  DisplayText: {citation.get('displayText', 'N/A')}")
                print(f"  SearchableText: {citation.get('searchableText', 'N/A')}")
                # Check if old 'text' field still exists
                if 'text' in citation:
                    print(f"  WARNING: Old 'text' field still present: {citation['text'][:50]}...")
                print(f"  Page: {citation.get('page', 'N/A')}")
                print(f"  Rects: {len(citation.get('rects', []))} rects")
                if citation.get('rects'):
                    print(f"    First rect: {citation['rects'][0]}")
                print()
        else:
            print(f"Error {response.status_code}: {response.text}")

asyncio.run(test_citations())