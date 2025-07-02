#!/usr/bin/env python3
import asyncio
import websockets
import json
import sys

async def test_citation_flow():
    uri = "ws://localhost:8000/ws/conversation/42b80643-c57f-436a-9e7c-ff31b1ca621f"
    
    print("Connecting to WebSocket...")
    async with websockets.connect(uri) as websocket:
        print("Connected! Sending message...")
        
        # Send a message that should trigger citations
        message = {
            "type": "message",
            "content": "Based on the bank report, what was the net interest income in Q1 2025? Please reference the specific section where this information is found.",
            "options": {
                "citation_ids": [],
                "referenced_documents": ["2abd6fc9-aa29-4d79-a24c-f8b50e8ace5c"],
                "referenced_analyses": []
            }
        }
        
        await websocket.send(json.dumps(message))
        print("Message sent! Listening for events...")
        print("-" * 80)
        
        # Track citations
        citations_received = []
        
        # Listen for events
        while True:
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=60.0)
                event = json.loads(response)
                event_type = event.get("type", "unknown")
                
                # Log different event types with relevant info
                if event_type == "connected":
                    print(f"✅ CONNECTED")
                elif event_type == "message_start":
                    print(f"✅ MESSAGE_START: message_id={event.get('message_id')}")
                elif event_type == "text_delta":
                    text = event.get("text", "")
                    if "[" in text and "]" in text:
                        print(f"📝 CITATION MARKER IN TEXT: {text}")
                elif event_type == "citation_marker":
                    print(f"📍 CITATION_MARKER: {event.get('marker')} - citation index: {event.get('citation_index')}")
                    citations_received.append(event.get('citation'))
                elif event_type == "citations_delta":
                    print(f"📚 CITATIONS_DELTA: citation at block {event.get('block_index')}")
                    if event.get('citation') not in citations_received:
                        citations_received.append(event.get('citation'))
                elif event_type == "tool_start":
                    print(f"🔧 TOOL_START: {event.get('tool_name')}")
                elif event_type == "message_complete":
                    print(f"\n✅ MESSAGE_COMPLETE: message_id={event.get('message_id')}")
                    print(f"   Citations in event: {len(event.get('citations', []))}")
                    print(f"   Citations received during stream: {len(citations_received)}")
                    print(f"   Analysis blocks: {len(event.get('analysis_blocks', []))}")
                    
                    # Print citation details
                    if citations_received:
                        print("\n📚 Citation details:")
                        for i, cit in enumerate(citations_received):
                            if cit:
                                print(f"   [{i+1}] Pages {cit.get('start_page_number')}-{cit.get('end_page_number')}")
                    break
                elif event_type == "error":
                    print(f"❌ ERROR: {event.get('message')}")
                    break
                    
            except asyncio.TimeoutError:
                print("\nTimeout waiting for response")
                break
            except Exception as e:
                print(f"\nError: {e}")
                break

if __name__ == "__main__":
    asyncio.run(test_citation_flow())