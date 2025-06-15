from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws/test")
async def websocket_endpoint(websocket: WebSocket):
    logger.info("WebSocket endpoint called")
    await websocket.accept()
    await websocket.send_text("Connected!")
    
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Echo: {data}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")

@app.get("/")
async def root():
    return {"message": "Test server with WebSocket"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)