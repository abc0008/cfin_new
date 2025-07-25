#!/usr/bin/env python3
"""
Test the complete citation flow from creation to highlighting.
"""

import asyncio
import httpx
import json

async def test_citation_flow():
    """Test the complete citation flow."""
    
    print("🔍 Testing Citation Flow\n")
    
    async with httpx.AsyncClient(follow_redirects=True) as client:
        # 1. Get a document with citations
        response = await client.get("http://localhost:8000/api/documents/")
        documents = response.json()
        
        test_doc = None
        for doc in documents:
            if "Bank_5Q" in doc.get('filename', ''):
                test_doc = doc
                break
        
        if not test_doc:
            print("❌ No Bank_5Q document found for testing")
            return
            
        doc_id = test_doc['id']
        print(f"1️⃣ Testing with document: {test_doc['filename']}")
        
        # 2. Get citations
        citations_response = await client.get(f"http://localhost:8000/api/documents/{doc_id}/citations")
        citations = citations_response.json()
        
        print(f"\n2️⃣ Found {len(citations)} citations")
        
        # 3. Analyze citation data
        print("\n3️⃣ Citation Analysis:")
        
        # Check first citation in detail
        if citations:
            citation = citations[0]
            print(f"\n  First Citation Details:")
            print(f"  - ID: {citation.get('id', 'N/A')[:8]}...")
            print(f"  - Text: {citation.get('text', 'N/A')}")
            print(f"  - CitedText: {citation.get('citedText', 'N/A')}")
            print(f"  - DisplayText: {citation.get('displayText', 'N/A')}")
            
            rects = citation.get('rects', [])
            if rects:
                rect = rects[0]
                print(f"\n  Rectangle Details:")
                print(f"  - Position: ({rect.get('x1', 0):.1f}, {rect.get('y1', 0):.1f})")
                print(f"  - Size: {rect.get('width', 0):.1f} x {rect.get('height', 0):.1f}")
                print(f"  - Page: {rect.get('pageNumber', 'N/A')}")
                
                # Check if this is a full page rect
                if rect.get('width', 0) > 500 and rect.get('height', 0) > 700:
                    print(f"  ⚠️  WARNING: This looks like a FULL PAGE rect!")
                else:
                    print(f"  ✅ This is a SPECIFIC rect (not full page)")
            
        # 4. Check citation processing
        print("\n4️⃣ Citation Processing Check:")
        
        # Look for citations with extracted values
        extracted_count = 0
        for citation in citations:
            text = citation.get('citedText', '')
            # Check if this looks like an extracted value
            if ':' in text and '$' in text and len(text) < 50:
                extracted_count += 1
                if extracted_count <= 3:
                    print(f"  ✅ Extracted value: {text}")
        
        print(f"\n  Total citations with extracted values: {extracted_count}/{len(citations)}")
        
        # 5. Summary
        print("\n5️⃣ Summary:")
        specific_rect_count = sum(1 for c in citations if c.get('rects') and 
                                  c['rects'][0].get('width', 0) < 500)
        print(f"  ✅ Citations with specific rects: {specific_rect_count}/{len(citations)}")
        
        if specific_rect_count == len(citations):
            print("\n✅ SUCCESS: All citations have specific highlighting (not full page)!")
        else:
            print(f"\n⚠️  WARNING: {len(citations) - specific_rect_count} citations may show full page!")

if __name__ == "__main__":
    asyncio.run(test_citation_flow())