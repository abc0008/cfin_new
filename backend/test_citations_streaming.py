#!/usr/bin/env python3
"""
Test script to verify citation streaming functionality
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
import json

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import services
from pdf_processing.api_service import ClaudeService
from pdf_processing.claude_file_client import upload_pdf
from services.conversation_service import ConversationService
from repositories.conversation_repository import ConversationRepository
from repositories.document_repository import DocumentRepository
from repositories.analysis_repository import AnalysisRepository
from database import SessionLocal

async def test_citation_streaming():
    """Test citation streaming with a sample PDF"""
    
    # Initialize services
    db = SessionLocal()
    claude_service = ClaudeService()
    doc_repo = DocumentRepository(db)
    conv_repo = ConversationRepository(db)
    analysis_repo = AnalysisRepository(db)
    conv_service = ConversationService(conv_repo, doc_repo, analysis_repo, claude_service)
    
    # Track events
    events_received = []
    citations_received = []
    
    async def event_callback(event):
        """Callback to track streaming events"""
        event_type = event.get('type')
        events_received.append(event_type)
        
        logger.info(f"Event: {event_type}")
        
        if event_type == 'citations_delta':
            citation = event.get('citation', {})
            citations_received.append(citation)
            logger.info(f"Citation received: {citation.get('type')} - '{citation.get('cited_text', '')[:50]}...'")
        elif event_type == 'message_start':
            logger.info(f"Message started: {event.get('message_id')}")
        elif event_type == 'text_delta':
            logger.info(f"Text delta: {len(event.get('text', ''))} chars")
        elif event_type == 'content_update':
            logger.info(f"Content update: {len(event.get('accumulated_text', ''))} total chars")
    
    try:
        # Create a test conversation
        conversation = await conv_service.create_conversation("Citation Test")
        conversation_id = conversation.id
        logger.info(f"Created conversation: {conversation_id}")
        
        # Prepare test document data (you would need an actual PDF for real testing)
        test_document = {
            "id": "test-doc-123",
            "filename": "test_financial_report.pdf",
            "claude_file_id": "file_test_123",  # In real test, upload actual PDF
            "content": "Sample financial report content..."
        }
        
        # Test with a query that should trigger citations
        test_query = "What are the key financial metrics mentioned in this document? Please cite specific numbers and their sources."
        
        logger.info(f"Sending query: {test_query}")
        
        # Call the streaming API with citation-enabled document
        result = await claude_service.analyze_with_visualization_tools_streaming(
            document_text=test_document["content"],
            user_query=test_query,
            file_id=test_document.get("claude_file_id"),
            emit_callback=event_callback
        )
        
        # Log results
        logger.info(f"\nStreaming completed!")
        logger.info(f"Events received: {set(events_received)}")
        logger.info(f"Total citations: {len(citations_received)}")
        
        if citations_received:
            logger.info("\nCitations details:")
            for i, citation in enumerate(citations_received):
                logger.info(f"  Citation {i+1}:")
                logger.info(f"    Type: {citation.get('type')}")
                logger.info(f"    Text: {citation.get('cited_text', '')[:100]}...")
                logger.info(f"    Page: {citation.get('start_page_number')}-{citation.get('end_page_number')}")
        else:
            logger.warning("No citations received during streaming!")
        
        # Check if citations were saved in the result
        if 'citations' in result:
            logger.info(f"\nCitations in final result: {len(result['citations'])}")
        
        return {
            "success": True,
            "events": events_received,
            "citations": citations_received,
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        db.close()

if __name__ == "__main__":
    # Run the test
    result = asyncio.run(test_citation_streaming())
    
    # Print summary
    print("\n=== Test Summary ===")
    print(f"Success: {result['success']}")
    if result['success']:
        print(f"Total events: {len(result['events'])}")
        print(f"Citations found: {len(result['citations'])}")
        print(f"Event types: {set(result['events'])}")
    else:
        print(f"Error: {result.get('error')}")