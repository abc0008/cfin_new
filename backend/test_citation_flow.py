#!/usr/bin/env python3
"""
Test the complete citation flow from backend to frontend.
"""

import asyncio
import json
import httpx
from datetime import datetime

async def test_citation_flow():
    """Test the complete flow of citations."""
    
    # First, let's check if we have a conversation with citations
    async with httpx.AsyncClient() as client:
        # Get recent conversations
        conv_response = await client.get("http://localhost:8000/api/conversation/history?limit=5")
        conv_data = conv_response.json()
        
        # Handle both array and object responses
        if isinstance(conv_data, dict):
            conversations = conv_data.get("conversations", [])
        else:
            conversations = conv_data
            
        print(f"Found {len(conversations)} recent conversations")
        
        # Find a conversation with citations
        for conv in conversations:
            conv_id = conv["id"]
            print(f"\nChecking conversation: {conv_id}")
            
            # Get messages for this conversation
            msg_response = await client.get(f"http://localhost:8000/api/conversation/{conv_id}")
            if msg_response.status_code != 200:
                print(f"  Error getting messages: {msg_response.status_code}")
                continue
                
            conversation_data = msg_response.json()
            messages = conversation_data.get("messages", [])
            
            print(f"  Found {len(messages)} messages")
            
            # Check each message for citations
            for msg in messages:
                if msg.get("role") == "assistant" and msg.get("citations"):
                    citations = msg["citations"]
                    content = msg.get("content", "")
                    
                    print(f"\n  Message ID: {msg['id']}")
                    print(f"  Citations found: {len(citations)}")
                    print(f"  Content has markers: {bool('[1]' in content or '[2]' in content or '[3]' in content)}")
                    print(f"  Content preview: {content[:200]}...")
                    
                    # Check citation details
                    for i, citation in enumerate(citations[:3]):  # First 3 citations
                        print(f"\n  Citation {i+1}:")
                        print(f"    ID: {citation.get('id')}")
                        print(f"    Text: {citation.get('citedText', '')[:50]}...")
                        print(f"    Has rects: {bool(citation.get('rects'))}")
                        if citation.get('rects'):
                            print(f"    Rect count: {len(citation['rects'])}")
                    
                    # Found a message with citations, now check if they're accessible via API
                    if citations and len(citations) > 0:
                        doc_id = citations[0].get("documentId")
                        if doc_id:
                            print(f"\n  Checking document citations API for doc: {doc_id}")
                            doc_cit_response = await client.get(f"http://localhost:8000/api/documents/{doc_id}/citations")
                            if doc_cit_response.status_code == 200:
                                doc_citations = doc_cit_response.json()
                                print(f"  Document has {len(doc_citations)} citations in total")
                            else:
                                print(f"  Error getting document citations: {doc_cit_response.status_code}")

if __name__ == "__main__":
    asyncio.run(test_citation_flow())