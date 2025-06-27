import asyncio
import websockets

async def test():
    uri = "ws://localhost:8001/ws/test"
    async with websockets.connect(uri) as websocket:
        msg = await websocket.recv()
        print(f"Received: {msg}")
        
        await websocket.send("Hello")
        response = await websocket.recv()
        print(f"Response: {response}")

asyncio.run(test())