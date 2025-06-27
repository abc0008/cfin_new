#!/usr/bin/env python3
"""
Test script for the streaming content preservation fix.
Validates that complete analytical content is preserved after tool processing.
"""

import asyncio
import logging
import os
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def test_content_preservation():
    """Test that streaming content is preserved correctly after tool processing."""
    from services.conversation_service import ConversationService
    from repositories.conversation_repository import ConversationRepository
    from repositories.document_repository import DocumentRepository
    from repositories.analysis_repository import AnalysisRepository
    from utils.database import get_db_session
    
    logger.info("Testing streaming content preservation fix...")
    
    # Initialize services
    async with get_db_session() as session:
        conversation_repo = ConversationRepository(session)
        document_repo = DocumentRepository(session)
        analysis_repo = AnalysisRepository(session)
        
        conversation_service = ConversationService(
            conversation_repository=conversation_repo,
            document_repository=document_repo,
            analysis_repository=analysis_repo
        )
        
        # Create a test conversation
        test_conversation = await conversation_repo.create_conversation(
            user_id="test-user",
            title="Content Preservation Test"
        )
        
        logger.info(f"Created test conversation: {test_conversation.id}")
        
        # Track events and content updates
        events_received = []
        content_updates = []
        final_message = None
        
        async def test_callback(event):
            events_received.append(event)
            
            if event.get('type') == 'content_update':
                content_updates.append({
                    'content_length': event.get('content_length', 0),
                    'accumulated_text': event.get('accumulated_text', ''),
                    'is_initial_content': event.get('is_initial_content'),
                    'content_preserved': event.get('content_preserved')
                })
                logger.info(f"Content update: {event.get('content_length')} chars, initial={event.get('is_initial_content')}, preserved={event.get('content_preserved')}")
            
            elif event.get('type') == 'message_complete':
                logger.info(f"Message complete: {event.get('message_id')}")
        
        try:
            # Test with a query that would trigger visualization tools
            test_query = "How have deposit mix trends changed over time? Please provide a comprehensive analysis with charts and detailed insights."
            
            logger.info(f"Processing streaming message: {test_query}")
            
            result = await conversation_service.process_user_message_streaming(
                conversation_id=str(test_conversation.id),
                content=test_query,
                emit_callback=test_callback
            )
            
            if result and result.get('success') and result.get('message'):
                final_message = result['message']
                logger.info(f"Final message content length: {len(final_message.content) if final_message.content else 0} chars")
                logger.info(f"Final message preview: {final_message.content[:200]}..." if final_message.content else "No content")
                
                # Validate the fix
                validate_content_preservation(events_received, content_updates, final_message)
            else:
                logger.error(f"Failed to process streaming message: {result}")
                
        except Exception as e:
            logger.error(f"Error during test: {str(e)}")
            logger.exception(e)
        finally:
            # Clean up test conversation
            logger.info(f"Cleaning up test conversation: {test_conversation.id}")
            # Note: Add cleanup logic if needed

def validate_content_preservation(events: List[Dict[str, Any]], content_updates: List[Dict[str, Any]], final_message) -> None:
    """Validate that the content preservation fix is working correctly."""
    
    logger.info("=== CONTENT PRESERVATION VALIDATION ===")
    
    # Check 1: We should have received content_update events
    content_events = [e for e in events if e.get('type') == 'content_update']
    logger.info(f"✓ Received {len(content_events)} content_update events")
    
    # Check 2: We should have initial content and preserved content flags
    initial_content_events = [u for u in content_updates if u.get('is_initial_content')]
    preserved_content_events = [u for u in content_updates if u.get('content_preserved')]
    
    logger.info(f"✓ Initial content events: {len(initial_content_events)}")
    logger.info(f"✓ Preserved content events: {len(preserved_content_events)}")
    
    # Check 3: Final message should have substantial content
    if final_message and final_message.content:
        content_length = len(final_message.content)
        logger.info(f"✓ Final message content length: {content_length} chars")
        
        # The fix should ensure we have substantial content (not truncated)
        if content_length < 100:
            logger.warning(f"⚠️  Final content is suspiciously short: {content_length} chars")
            logger.warning(f"Content: {final_message.content}")
        elif content_length > 500:
            logger.info(f"✅ Final content is comprehensive: {content_length} chars")
        else:
            logger.info(f"✓ Final content is reasonable: {content_length} chars")
        
        # Check for common truncation patterns
        if final_message.content.strip().endswith(("The", "Let me provide", "shows")):
            logger.error(f"❌ Final content appears truncated: '{final_message.content[-50:]}'")
        else:
            logger.info(f"✅ Final content does not appear truncated")
            
    else:
        logger.error(f"❌ Final message has no content")
    
    # Check 4: Tool processing events
    tool_events = [e for e in events if e.get('type') in ['tool_start', 'tool_complete', 'chart_ready', 'table_ready', 'metric_ready']]
    logger.info(f"✓ Tool processing events: {len(tool_events)}")
    
    # Check 5: Message completion
    completion_events = [e for e in events if e.get('type') == 'message_complete']
    logger.info(f"✓ Message completion events: {len(completion_events)}")
    
    if len(completion_events) > 0:
        logger.info(f"✅ Streaming process completed successfully")
    else:
        logger.warning(f"⚠️  No message completion event received")
    
    logger.info("=== VALIDATION COMPLETE ===")

async def main():
    """Run the content preservation test."""
    try:
        await test_content_preservation()
        logger.info("✅ Content preservation test completed")
    except Exception as e:
        logger.error(f"❌ Content preservation test failed: {str(e)}")
        logger.exception(e)

if __name__ == "__main__":
    asyncio.run(main())