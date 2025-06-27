from fastapi import FastAPI, WebSocket
import uvicorn
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.websocket("/ws/test")
async def websocket_endpoint(websocket: WebSocket):
    logger.info("WebSocket endpoint called")
    try:
        await websocket.accept()
        logger.info("WebSocket accepted")
        await websocket.send_text("Connected!")
        
        while True:
            data = await websocket.receive_text()
            logger.info(f"Received: {data}")
            await websocket.send_text(f"Echo: {data}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    finally:
        logger.info("WebSocket connection closed")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)