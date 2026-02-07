#!/usr/bin/env python3
"""
Test that citation markers appear correctly in streamed messages.
"""

import asyncio
import json
import websockets
import httpx
from datetime import datetime

async def test_citation_markers():
    """Test that citation markers appear in messages."""
    
    # Create a conversation first
    async with httpx.AsyncClient() as client:
        # Create conversation
        conv_response = await client.post(
            "http://localhost:8000/api/conversation/create",
            json={"title": "Citation Marker Test"}
        )
        conversation = conv_response.json()
        conversation_id = conversation["id"]
        print(f"Created conversation: {conversation_id}")
        
        # Upload a test document
        with open("test_docs/Wells_Fargo_Q3_2024.pdf", "rb") as f:
            files = {"file": ("Wells_Fargo_Q3_2024.pdf", f, "application/pdf")}
            upload_response = await client.post(
                "http://localhost:8000/api/documents/upload",
                files=files
            )
            document = upload_response.json()
            document_id = document["documentId"]
            print(f"Uploaded document: {document_id}")
    
    # Connect to WebSocket for streaming
    ws_url = f"ws://localhost:8000/ws/conversation/{conversation_id}"
    
    async with websockets.connect(ws_url) as websocket:
        print(f"Connected to WebSocket")
        
        # Send a message that should trigger citations
        message = {
            "type": "message",
            "content": "What was Wells Fargo's net interest income in Q3 2024? Please cite specific numbers.",
            "options": {
                "citation_ids": [],
                "referenced_documents": [document_id],
                "referenced_analyses": []
            }
        }
        
        await websocket.send(json.dumps(message))
        print("Sent message requesting citations")
        
        # Collect all events
        message_content = ""
        citation_markers_found = []
        citations_found = []
        message_complete = False
        
        while not message_complete:
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                event = json.loads(response)
                
                print(f"\nEvent type: {event.get('type')}")
                
                if event.get('type') == 'text_delta':
                    text = event.get('text', '')
                    message_content += text
                    
                    # Check for citation markers
                    import re
                    markers = re.findall(r'\[\d+\]', text)
                    if markers:
                        citation_markers_found.extend(markers)
                        print(f"  Citation markers found in text_delta: {markers}")
                    
                    print(f"  Text: {text[:100]}...")
                
                elif event.get('type') == 'citations_delta':
                    citation = event.get('citation', {})
                    cited_text = citation.get('cited_text', '')
                    citations_found.append(cited_text)
                    print(f"  Citation: {cited_text[:100]}...")
                
                elif event.get('type') == 'message_complete':
                    message_complete = True
                    print(f"  Message complete!")
                
            except asyncio.TimeoutError:
                print("Timeout waiting for response")
                break
        
        print("\n" + "="*50)
        print("SUMMARY:")
        print(f"Message content length: {len(message_content)}")
        print(f"Citation markers found: {citation_markers_found}")
        print(f"Number of citations: {len(citations_found)}")
        
        # Check if citation markers are in the final message
        import re
        final_markers = re.findall(r'\[\d+\]', message_content)
        print(f"Citation markers in final message: {final_markers}")
        
        if final_markers:
            print("\n✅ SUCCESS: Citation markers are present in the message!")
        else:
            print("\n❌ FAILURE: No citation markers found in the message!")
            print(f"\nFinal message content:\n{message_content}")

if __name__ == "__main__":
    asyncio.run(test_citation_markers())