#!/usr/bin/env python3
"""
Test script to verify citations have proper rects (not full page).
"""

import asyncio
import httpx
import json

async def test_citation_rects():
    """Test that citations have proper rects and not full page dimensions."""
    
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
            
        # Test all documents
        for doc in documents:
            doc_id = doc.get('id')
            print(f"\n📄 Document: {doc.get('filename', 'Unknown')}")
            
            # Get citations for this document
            citations_response = await client.get(f"http://localhost:8000/api/documents/{doc_id}/citations")
            
            if citations_response.status_code == 200:
                citations = citations_response.json()
                if citations:
                    print(f"  Found {len(citations)} citations")
                    
                    # Check all citations
                    full_page_count = 0
                    specific_rect_count = 0
                    no_rect_count = 0
                    
                    for citation in citations:
                        rects = citation.get('rects', [])
                        
                        if not rects:
                            no_rect_count += 1
                            print(f"    ❌ Citation {citation.get('id', 'N/A')[:8]}: NO RECTS - Will show full page!")
                            print(f"       Text: {citation.get('citedText', 'N/A')[:50]}...")
                        else:
                            # Check if this looks like a full page rect
                            rect = rects[0]
                            width = rect.get('width', 0)
                            height = rect.get('height', 0)
                            
                            # Full page is typically around 600x800 or larger
                            if width > 500 and height > 700:
                                full_page_count += 1
                                print(f"    ⚠️  Citation {citation.get('id', 'N/A')[:8]}: FULL PAGE rect ({width:.1f}x{height:.1f})")
                                print(f"       Text: {citation.get('citedText', 'N/A')[:50]}...")
                            else:
                                specific_rect_count += 1
                                if specific_rect_count <= 3:  # Show first 3 specific rects
                                    print(f"    ✅ Citation {citation.get('id', 'N/A')[:8]}: Specific rect ({width:.1f}x{height:.1f})")
                                    print(f"       Text: {citation.get('citedText', 'N/A')[:50]}...")
                    
                    # Summary
                    print(f"\n  Summary:")
                    print(f"    ✅ Specific rects: {specific_rect_count}")
                    print(f"    ⚠️  Full page rects: {full_page_count}")
                    print(f"    ❌ No rects: {no_rect_count}")
                    
                    if full_page_count > 0 or no_rect_count > 0:
                        print(f"\n  ⚠️  WARNING: {full_page_count + no_rect_count} citations will highlight full pages!")

if __name__ == "__main__":
    asyncio.run(test_citation_rects())