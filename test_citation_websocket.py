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
        
        # Listen for events
        while True:
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=60.0)
                event = json.loads(response)
                event_type = event.get("type", "unknown")
                
                # Log different event types with relevant info
                if event_type == "message_start":
                    print(f"✅ MESSAGE_START: message_id={event.get('message_id')}")
                elif event_type == "text_delta":
                    text = event.get("text", "")
                    if "[" in text and "]" in text:
                        print(f"📝 CITATION MARKER: {text}")
                    else:
                        sys.stdout.write(text)
                        sys.stdout.flush()
                elif event_type == "tool_start":
                    print(f"\n🔧 TOOL_START: {event.get('tool_name')} (id: {event.get('tool_id')})")
                elif event_type == "tool_complete":
                    print(f"✅ TOOL_COMPLETE: {event.get('tool_id')}")
                elif event_type == "message_complete":
                    print(f"\n✅ MESSAGE_COMPLETE: message_id={event.get('message_id')}")
                    print(f"   Citations: {len(event.get('citations', []))}")
                    print(f"   Analysis blocks: {len(event.get('analysis_blocks', []))}")
                    break
                elif event_type == "new_message_start":
                    print(f"\n📄 NEW_MESSAGE_START: message_id={event.get('message_id')} (post_viz: {event.get('is_post_visualization')})")
                elif event_type == "error":
                    print(f"❌ ERROR: {event.get('message')}")
                    break
                else:
                    print(f"\n[{event_type}] {json.dumps(event, indent=2)}")
                    
            except asyncio.TimeoutError:
                print("\nTimeout waiting for response")
                break
            except Exception as e:
                print(f"\nError: {e}")
                break

if __name__ == "__main__":
    asyncio.run(test_citation_flow())