#!/usr/bin/env python3
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8000/ws/conversation/test-conversation-123"
    
    try:
        print(f"Connecting to {uri}...")
        async with websockets.connect(uri) as websocket:
            print("Connected successfully!")
            
            # Wait for connected message
            message = await websocket.recv()
            print(f"Received: {message}")
            data = json.loads(message)
            print(f"Parsed: {data}")
            
            # Send ping
            ping_msg = json.dumps({"type": "ping"})
            print(f"Sending: {ping_msg}")
            await websocket.send(ping_msg)
            
            # Wait for pong
            pong = await websocket.recv()
            print(f"Received: {pong}")
            
            # Test sending a message
            test_msg = json.dumps({
                "type": "message",
                "content": "Hello from test client",
                "options": {}
            })
            print(f"Sending test message: {test_msg}")
            await websocket.send(test_msg)
            
            # Listen for responses
            for i in range(5):
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    print(f"Response {i+1}: {response}")
                except asyncio.TimeoutError:
                    print(f"No response after 2 seconds (iteration {i+1})")
                    break
                    
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())