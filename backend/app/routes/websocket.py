from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from typing import Dict, Any, Optional
import json
import logging
import asyncio
from datetime import datetime

from services.conversation_service import ConversationService
from pdf_processing.document_service import DocumentService
from repositories.document_repository import DocumentRepository
from repositories.conversation_repository import ConversationRepository
from utils.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ws", tags=["websocket"])

# Connection manager for WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"WebSocket connected: {client_id}")
        
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"WebSocket disconnected: {client_id}")
    
    async def send_message(self, client_id: str, message: Dict[str, Any]):
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to {client_id}: {e}")
                self.disconnect(client_id)
    
    async def broadcast(self, message: Dict[str, Any]):
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting to {client_id}: {e}")
                self.disconnect(client_id)

manager = ConnectionManager()

# Dependencies
async def get_document_repository(db: AsyncSession = Depends(get_db)):
    return DocumentRepository(db)

async def get_conversation_repository(db: AsyncSession = Depends(get_db)):
    return ConversationRepository(db)

async def get_conversation_service(
    conversation_repository: ConversationRepository = Depends(get_conversation_repository),
    document_repository: DocumentRepository = Depends(get_document_repository)
):
    return ConversationService(
        conversation_repository=conversation_repository,
        document_repository=document_repository
    )

async def get_document_service(
    document_repository: DocumentRepository = Depends(get_document_repository)
):
    return DocumentService(document_repository)

@router.websocket("/conversation/{conversation_id}")
async def websocket_conversation(
    websocket: WebSocket,
    conversation_id: str,
    user_id: Optional[str] = "default-user"  # In production, extract from JWT token
):
    """
    WebSocket endpoint for real-time conversation streaming.
    
    Protocol:
    - Client sends: {"type": "message", "content": "user message", "options": {...}}
    - Server sends: {"type": "text_delta", "text": "partial text", "accumulated_text": "full text so far"}
    - Server sends: {"type": "tool_start", "tool_id": "...", "tool_name": "..."}
    - Server sends: {"type": "tool_complete", "tool_id": "...", "result": {...}}
    - Server sends: {"type": "message_complete", "message_id": "..."}
    """
    logger.info(f"WebSocket endpoint called for conversation: {conversation_id}, user: {user_id}")
    # Use timestamp to make client_id unique for each connection
    import time
    client_id = f"{user_id}_{conversation_id}_{int(time.time() * 1000)}"
    
    # Create services (we can't use Depends in WebSocket endpoints easily)
    from utils.database import SessionLocal as AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        document_repository = DocumentRepository(db)
        conversation_repository = ConversationRepository(db)
        conversation_service = ConversationService(
            conversation_repository=conversation_repository,
            document_repository=document_repository
        )
        
        try:
            await manager.connect(websocket, client_id)
            logger.info(f"WebSocket connection established for conversation: {conversation_id}")
        except Exception as e:
            logger.error(f"Failed to accept WebSocket connection: {e}", exc_info=True)
            # Try to send error message before closing
            try:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"Connection failed: {str(e)}"
                }))
            except:
                pass
            await websocket.close(code=1011, reason=str(e))
            return
        
        try:
            # Verify conversation exists and user has access
            try:
                conversation = await conversation_service.get_conversation(conversation_id)
                logger.info(f"Found conversation: {conversation_id}")
            except Exception as e:
                logger.error(f"Error fetching conversation {conversation_id}: {e}")
                # For now, continue without the conversation check to debug WebSocket issues
                logger.warning("Continuing without conversation validation for debugging")
                conversation = None
                
            if conversation:
                if conversation.user_id != user_id:
                    logger.warning(f"User {user_id} does not have access to conversation {conversation_id}")
                    await websocket.send_text(json.dumps({
                        "type": "error", 
                        "message": "Access denied"
                    }))
                    await websocket.close()
                    return
            else:
                logger.warning(f"Conversation not found: {conversation_id} - continuing for debugging")
            
            # Send initial connection confirmation
            await manager.send_message(client_id, {
                "type": "connected",
                "conversation_id": conversation_id,
                "timestamp": datetime.utcnow().isoformat() + 'Z'
            })
            
            while True:
                # Wait for message from client
                data = await websocket.receive_text()
                
                try:
                    message_data = json.loads(data)
                except json.JSONDecodeError:
                    await manager.send_message(client_id, {
                        "type": "error",
                        "message": "Invalid JSON format"
                    })
                    continue
                
                if message_data.get("type") == "message":
                    # Process streaming message
                    await handle_streaming_message(
                        conversation_service=conversation_service,
                        conversation_id=conversation_id,
                        user_message=message_data.get("content", ""),
                        options=message_data.get("options", {}),
                        client_id=client_id
                    )
                elif message_data.get("type") == "ping":
                    # Respond to ping with pong
                    await manager.send_message(client_id, {
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat() + 'Z'
                    })
                else:
                    await manager.send_message(client_id, {
                        "type": "error",
                        "message": f"Unknown message type: {message_data.get('type')}"
                    })
                    
        except WebSocketDisconnect:
            manager.disconnect(client_id)
        except Exception as e:
            logger.error(f"WebSocket error for {client_id}: {e}", exc_info=True)
            await manager.send_message(client_id, {
                "type": "error",
                "message": f"Server error: {str(e)}"
            })
            manager.disconnect(client_id)

async def handle_streaming_message(
    conversation_service: ConversationService,
    conversation_id: str,
    user_message: str,
    options: Dict[str, Any],
    client_id: str
):
    """
    Handle a streaming message request and emit real-time updates.
    """
    try:
        # Generate a unique message ID for this streaming session
        import uuid
        message_id = str(uuid.uuid4())
        
        # Emit message start event
        await manager.send_message(client_id, {
            "type": "message_start",
            "message_id": message_id,
            "timestamp": datetime.now().isoformat()
        })
        
        # Define callback for streaming events
        async def emit_callback(event: Dict[str, Any]):
            await manager.send_message(client_id, event)
        
        # Process the message with streaming enabled
        result = await conversation_service.process_user_message_streaming(
            conversation_id=conversation_id,
            content=user_message,
            citation_ids=options.get("citation_ids", []),
            referenced_documents=options.get("referenced_documents", []),
            referenced_analyses=options.get("referenced_analyses", []),
            emit_callback=emit_callback,
            message_id=message_id
        )
        
        # Note: message_complete event is now sent by conversation_service
        # to ensure proper timing after all visualizations are processed
        
    except Exception as e:
        logger.error(f"Error handling streaming message: {e}", exc_info=True)
        await manager.send_message(client_id, {
            "type": "error",
            "message": f"Error processing message: {str(e)}",
            "timestamp": datetime.now().isoformat()
        })

@router.websocket("/analysis/{analysis_type}")
async def websocket_analysis(
    websocket: WebSocket,
    analysis_type: str,
    user_id: Optional[str] = "default-user"
):
    """
    WebSocket endpoint for real-time analysis streaming.
    Handles long-running analysis tasks with progress updates.
    """
    client_id = f"{user_id}_analysis_{analysis_type}"
    
    await manager.connect(websocket, client_id)
    
    try:
        # Send initial connection confirmation
        await manager.send_message(client_id, {
            "type": "connected",
            "analysis_type": analysis_type,
            "timestamp": datetime.now().isoformat()
        })
        
        while True:
            data = await websocket.receive_text()
            
            try:
                message_data = json.loads(data)
            except json.JSONDecodeError:
                await manager.send_message(client_id, {
                    "type": "error",
                    "message": "Invalid JSON format"
                })
                continue
            
            if message_data.get("type") == "start_analysis":
                # Handle analysis request
                await handle_streaming_analysis(
                    analysis_type=analysis_type,
                    document_ids=message_data.get("document_ids", []),
                    options=message_data.get("options", {}),
                    client_id=client_id
                )
                
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"Analysis WebSocket error for {client_id}: {e}", exc_info=True)
        await manager.send_message(client_id, {
            "type": "error",
            "message": f"Server error: {str(e)}"
        })
        manager.disconnect(client_id)

async def handle_streaming_analysis(
    analysis_type: str,
    document_ids: list,
    options: Dict[str, Any],
    client_id: str
):
    """
    Handle streaming analysis requests with progress updates.
    """
    try:
        await manager.send_message(client_id, {
            "type": "analysis_start",
            "analysis_type": analysis_type,
            "document_count": len(document_ids),
            "timestamp": datetime.now().isoformat()
        })
        
        # Define progress callback
        async def progress_callback(event: Dict[str, Any]):
            await manager.send_message(client_id, event)
        
        # TODO: Implement actual analysis service call with streaming
        # This would integrate with the analysis service
        
        # For now, simulate progress
        for i in range(len(document_ids)):
            await asyncio.sleep(1)  # Simulate processing time
            await progress_callback({
                "type": "analysis_progress",
                "document_index": i,
                "document_id": document_ids[i],
                "progress": (i + 1) / len(document_ids),
                "message": f"Processing document {i + 1} of {len(document_ids)}"
            })
        
        await manager.send_message(client_id, {
            "type": "analysis_complete",
            "results": {"placeholder": "analysis results would go here"},
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in streaming analysis: {e}", exc_info=True)
        await manager.send_message(client_id, {
            "type": "error",
            "message": f"Analysis error: {str(e)}"
        })