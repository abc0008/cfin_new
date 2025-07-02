#!/usr/bin/env python3
"""
Test script to verify citation handling in ClaudeService
"""
import asyncio
import json
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from pdf_processing.api_service import ClaudeService

async def test_citations():
    """Test citation extraction from PDF with streaming"""
    print("Testing Citation Handling in ClaudeService\n")
    
    # Initialize service
    service = ClaudeService()
    
    # Use the sample PDF
    pdf_path = Path(__file__).parent.parent.parent / "ExampleDocs" / "Bank_5Q_Trend_Report.pdf"
    if not pdf_path.exists():
        print(f"❌ PDF not found at {pdf_path}")
        return
    
    print(f"✅ Using PDF: {pdf_path.name}")
    
    # Read PDF content
    with open(pdf_path, 'rb') as f:
        pdf_content = f.read()
    
    # Create document
    documents = [{
        "content": pdf_content,
        "title": "Bank 5Q Trend Report",
        "type": "pdf"
    }]
    
    # Test query that should trigger citations
    query = "What are the specific revenue figures mentioned in the document? Please cite the exact figures."
    
    print(f"\n📝 Query: {query}")
    print("\n" + "="*50 + "\n")
    
    # Track events
    events = []
    citations_found = []
    citation_markers_found = []
    text_chunks = []
    
    async def event_handler(event):
        """Handle streaming events"""
        events.append(event)
        
        if event['type'] == 'text_delta':
            text_chunks.append(event['text'])
            # Check if citation markers are in the text
            import re
            markers = re.findall(r'\[\d+\]', event['text'])
            if markers:
                citation_markers_found.extend(markers)
                print(f"🎯 Found citation markers in text: {markers}")
        
        elif event['type'] == 'citation_marker':
            print(f"📌 Citation marker event: {event['marker']}")
        
        elif event['type'] == 'citations_delta':
            citation = event['citation']
            citations_found.append(citation)
            print(f"📚 Citation {citation.get('citation_index', '?')}: {citation['type']} - '{citation['cited_text'][:50]}...'")
        
        elif event['type'] == 'content_update':
            # Check final text for citation markers
            if 'accumulated_text' in event:
                import re
                all_markers = re.findall(r'\[\d+\]', event['accumulated_text'])
                if all_markers:
                    print(f"📊 Total citation markers in accumulated text: {all_markers}")
    
    # Process with streaming
    print("🔄 Processing with streaming...\n")
    
    try:
        response = await service.process_query_with_documents(
            query=query,
            documents=documents,
            stream=True,
            emit_callback=event_handler
        )
        
        print("\n" + "="*50 + "\n")
        print("📊 Results:\n")
        
        # Full text
        print(f"📝 Response Text ({len(response['text'])} chars):")
        print("-" * 40)
        print(response['text'][:500] + "..." if len(response['text']) > 500 else response['text'])
        print("-" * 40)
        
        # Check for citation markers in final text
        import re
        final_markers = re.findall(r'\[\d+\]', response['text'])
        print(f"\n🎯 Citation markers in final text: {final_markers}")
        
        # Citations
        print(f"\n📚 Citations found: {len(response['citations'])}")
        for i, citation in enumerate(response['citations'], 1):
            print(f"\n  Citation {i}:")
            print(f"    - Type: {citation['type']}")
            print(f"    - Text: '{citation['cited_text'][:100]}...'")
            print(f"    - Page: {citation.get('start_page_number', 'N/A')}")
            print(f"    - Index: {citation.get('citation_index', 'N/A')}")
        
        # Event summary
        print(f"\n📊 Event Summary:")
        print(f"  - Total events: {len(events)}")
        print(f"  - Citation events: {len(citations_found)}")
        print(f"  - Citation markers in text: {len(citation_markers_found)} {citation_markers_found}")
        print(f"  - Text chunks: {len(text_chunks)}")
        
        # Verify citation markers match citations
        if len(final_markers) == len(response['citations']):
            print(f"\n✅ SUCCESS: Citation markers ({len(final_markers)}) match citations ({len(response['citations'])})")
        else:
            print(f"\n❌ MISMATCH: {len(final_markers)} markers but {len(response['citations'])} citations")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_citations())