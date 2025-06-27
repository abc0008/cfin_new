import asyncio
import websockets
import json
import logging

logging.basicConfig(level=logging.DEBUG)
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
            
            # Send a ping message first
            ping_message = {
                "type": "ping"
            }
            await websocket.send(json.dumps(ping_message))
            logger.info("Sent ping message")
            
            # Wait for pong
            response = await websocket.recv()
            logger.info(f"Received response: {response}")
            
    except websockets.exceptions.InvalidStatus as e:
        logger.error(f"Invalid status: {e}")
    except Exception as e:
        logger.error(f"WebSocket error: {type(e).__name__}: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(test_websocket())