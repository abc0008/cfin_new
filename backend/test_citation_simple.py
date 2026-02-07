#!/usr/bin/env python3
"""
Simple test to verify citation markers are included in streamed text
"""
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv('../.env')

# Add backend to path
sys.path.append(str(Path(__file__).parent))

from pdf_processing.api_service import ClaudeService

async def test_citations():
    """Test citation functionality with a simple text"""
    print("Testing Citation Markers in Streaming\n")
    
    # Initialize service
    service = ClaudeService()
    
    # Simple test content that should trigger citations
    test_content = """
    Financial Report Summary:
    
    Revenue: $1.5 million in Q1 2024
    Expenses: $800,000 in Q1 2024
    Net Income: $700,000 in Q1 2024
    
    Key Metrics:
    - Gross Margin: 45%
    - Operating Margin: 30%
    - Net Margin: 20%
    """
    
    # Create a fake document for testing
    documents = [{
        "content": test_content.encode('utf-8'),
        "title": "Test Financial Report",
        "type": "text",
        "id": "test-doc-1"
    }]
    
    # Test query
    query = "What are the revenue and net income figures? Please cite specific numbers."
    
    print(f"📝 Query: {query}")
    print("=" * 50 + "\n")
    
    # Track streaming events
    events = []
    final_text = ""
    has_citation_markers = False
    
    async def event_handler(event):
        """Handle streaming events"""
        nonlocal final_text, has_citation_markers
        events.append(event)
        
        if event['type'] == 'text_delta':
            text = event.get('text', '')
            print(f"📄 Text delta: '{text}'")
            
            # Check for citation markers
            import re
            if re.search(r'\[\d+\]', text):
                has_citation_markers = True
                print(f"✅ Found citation markers in text!")
        
        elif event['type'] == 'content_update':
            final_text = event.get('accumulated_text', '')
            print(f"📊 Content update - length: {len(final_text)}")
        
        elif event['type'] == 'citations_delta':
            citation = event.get('citation', {})
            print(f"📚 Citation: {citation.get('cited_text', '')[:50]}...")
    
    # Process with streaming
    try:
        print("🔄 Processing with streaming...\n")
        
        response = await service.process_query_with_documents(
            query=query,
            documents=documents,
            stream=True,
            emit_callback=event_handler
        )
        
        print("\n" + "=" * 50 + "\n")
        print("📊 Results:\n")
        
        # Check final text
        print(f"📝 Final Response ({len(response['text'])} chars):")
        print("-" * 40)
        print(response['text'])
        print("-" * 40)
        
        # Check for citation markers
        import re
        markers_in_response = re.findall(r'\[\d+\]', response['text'])
        print(f"\n🎯 Citation markers found: {markers_in_response}")
        
        # Summary
        print(f"\n📊 Summary:")
        print(f"  - Total events: {len(events)}")
        print(f"  - Citations: {len(response.get('citations', []))}")
        print(f"  - Citation markers in stream: {has_citation_markers}")
        print(f"  - Citation markers in final text: {len(markers_in_response)}")
        
        if len(markers_in_response) > 0:
            print("\n✅ SUCCESS: Citation markers are properly included in the response!")
        else:
            print("\n❌ FAIL: No citation markers found in the response")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_citations())