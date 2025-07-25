#!/usr/bin/env python3
"""
Test streaming conversation to trigger citation processor.
"""

import asyncio
import json
import logging
from httpx import AsyncClient
from uuid import uuid4

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_streaming_conversation():
    """Test streaming conversation that should trigger citation processor."""
    async with AsyncClient(base_url="http://localhost:8000", timeout=30.0) as client:
        # Create a conversation
        conversation_data = {
            "title": "Test Citation Processing",
            "documentIds": ["8ab86f50-1e25-42ac-b27f-a5e27496275d"]  # Bank_5Q_Trend_Report.pdf
        }
        
        conv_response = await client.post("/api/conversation", json=conversation_data)
        if conv_response.status_code not in [200, 201]:
            logger.error(f"Failed to create conversation: {conv_response.text}")
            return
            
        conversation = conv_response.json()
        logger.info(f"Full conversation response: {conversation}")
        
        # Try different field names
        conversation_id = (conversation.get("id") or 
                          conversation.get("conversationId") or 
                          conversation.get("sessionId"))
        
        if not conversation_id:
            logger.error(f"No conversation ID found in response: {conversation}")
            return
            
        logger.info(f"Created conversation: {conversation_id}")
        
        # Send a message that should trigger citations
        message_data = {
            "sessionId": conversation_id,  # The API expects sessionId, not conversationId
            "content": "What was the Interest Income in Q3 2024? Also tell me about Operating Expenses in Q4 2024.",
            "documentIds": ["8ab86f50-1e25-42ac-b27f-a5e27496275d"],
            "stream": True
        }
        
        logger.info("Sending message to trigger citations...")
        
        # Stream the response
        async with client.stream("POST", f"/api/conversation/{conversation_id}/message/stream", json=message_data) as response:
            async for line in response.aiter_lines():
                if line.strip():
                    try:
                        if line.startswith("data: "):
                            data = json.loads(line[6:])
                            
                            if data.get("type") == "citation":
                                citation = data.get("data", {})
                                logger.info(f"\n📍 New Citation:")
                                logger.info(f"  ID: {citation.get('id', 'N/A')[:8]}...")
                                logger.info(f"  CitedText: {citation.get('cited_text', '')[:50]}...")
                                logger.info(f"  DisplayText: {citation.get('display_text')}")
                                logger.info(f"  SearchableText: {citation.get('searchable_text')}")
                            elif data.get("type") == "content":
                                logger.info(f"Content: {data.get('data', '')[:100]}...")
                            elif data.get("type") == "complete":
                                logger.info("✅ Stream complete")
                                break
                    except json.JSONDecodeError:
                        pass
        
        # Wait a moment for processing
        await asyncio.sleep(2)
        
        # Fetch citations to see if they were processed
        citations_response = await client.get(f"/api/documents/8ab86f50-1e25-42ac-b27f-a5e27496275d/citations")
        if citations_response.status_code == 200:
            citations = citations_response.json()
            logger.info(f"\n📊 Total citations in document: {len(citations)}")
            
            # Look for citations with searchable_text
            citations_with_searchable = [c for c in citations if c.get("searchableText")]
            logger.info(f"Citations with searchableText: {len(citations_with_searchable)}")
            
            if citations_with_searchable:
                logger.info("\n✅ Citations with searchableText:")
                for c in citations_with_searchable[:5]:  # Show first 5
                    logger.info(f"  - {c['id'][:8]}... searchableText='{c['searchableText']}'")

async def main():
    """Run the test."""
    logger.info("Starting streaming citation test...")
    
    try:
        await test_streaming_conversation()
        logger.info("✅ Test completed successfully")
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())