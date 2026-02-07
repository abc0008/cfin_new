#!/usr/bin/env python3
"""
Test that searchable_text is being used for rect finding.
"""

import asyncio
import httpx
import json

async def test_searchable_text():
    """Test that citations use searchable_text for rect finding."""
    
    async with httpx.AsyncClient(follow_redirects=True) as client:
        # Get documents
        response = await client.get("http://localhost:8000/api/documents/")
        documents = response.json()
        
        # Find a document with citations
        for doc in documents:
            if "Bank_5Q" in doc.get('filename', ''):
                doc_id = doc['id']
                print(f"📄 Testing document: {doc['filename']}")
                
                # Get citations
                citations_response = await client.get(f"http://localhost:8000/api/documents/{doc_id}/citations")
                citations = citations_response.json()
                
                if citations:
                    print(f"\nFound {len(citations)} citations")
                    
                    # Check citations for searchable_text
                    for i, citation in enumerate(citations[:3]):
                        print(f"\nCitation {i+1}:")
                        print(f"  ID: {citation.get('id', 'N/A')[:8]}...")
                        print(f"  CitedText: {citation.get('citedText', 'N/A')[:50]}...")
                        print(f"  DisplayText: {citation.get('displayText', 'N/A')}")
                        print(f"  SearchableText: {citation.get('searchableText', 'N/A')}")
                        
                        # Check rects
                        rects = citation.get('rects', [])
                        if rects:
                            rect = rects[0]
                            width = rect.get('width', 0)
                            height = rect.get('height', 0)
                            print(f"  Rect size: {width:.1f} x {height:.1f}")
                            
                            # Check if this looks like it's highlighting the header or the value
                            if width > 200:  # Header row is typically wide
                                print(f"  ⚠️  WARNING: Wide rect - might be highlighting header row!")
                            else:
                                print(f"  ✅ Narrow rect - likely highlighting specific value")
                    
                    break

if __name__ == "__main__":
    asyncio.run(test_searchable_text())