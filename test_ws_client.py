import asyncio
import websockets
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_websocket():
    uri = "ws://localhost:8000/ws/conversation/test-conversation-123"
    
    try:
        logger.info(f"Connecting to {uri}")
        
        async with websockets.connect(uri) as websocket:
            logger.info("Connected successfully!")
            
            # Wait for initial message
            message = await websocket.recv()
            logger.info(f"Received: {message}")
            
            # Send a test message
            test_message = {
                "type": "message",
                "content": "Hello from Python client",
                "options": {}
            }
            await websocket.send(json.dumps(test_message))
            logger.info("Sent test message")
            
            # Wait for response
            response = await websocket.recv()
            logger.info(f"Received response: {response}")
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(test_websocket())