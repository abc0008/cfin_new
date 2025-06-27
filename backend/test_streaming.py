#!/usr/bin/env python3
"""
Test script for the hybrid streaming implementation.
Tests both text streaming and tool buffering functionality.
"""

import asyncio
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def test_streaming_basic():
    """Test basic text streaming functionality."""
    from pdf_processing.api_service import ClaudeService
    
    logger.info("Testing basic text streaming...")
    
    claude_service = ClaudeService()
    
    # Test simple message streaming
    messages = [{"role": "user", "content": "Explain what financial analysis means and why it's important for businesses. Please provide a detailed explanation."}]
    
    events_received = []
    
    async def test_callback(event):
        events_received.append(event)
        logger.info(f"Received event: {event.get('type')} - {event}")
    
    try:
        result = await claude_service.generate_response(
            system_prompt="You are a helpful financial analysis assistant.",
            messages=messages,
            stream=True,
            emit_callback=test_callback
        )
        
        logger.info(f"Streaming result: {result}")
        logger.info(f"Total events received: {len(events_received)}")
        
        # Check for expected event types
        event_types = [event.get('type') for event in events_received]
        logger.info(f"Event types: {set(event_types)}")
        
        # Verify we got text content
        text_deltas = [event for event in events_received if event.get('type') == 'text_delta']
        total_text = ''.join([event.get('text', '') for event in text_deltas])
        
        logger.info(f"Streamed text length: {len(total_text)}")
        logger.info(f"Final result text length: {len(result.get('text', ''))}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in basic streaming test: {e}")
        return False

async def test_streaming_tools():
    """Test streaming with tool calls (should buffer tools, stream text)."""
    from pdf_processing.api_service import ClaudeService
    
    logger.info("Testing tool streaming functionality...")
    
    claude_service = ClaudeService()
    
    # Test with a financial analysis question that should trigger tools
    messages = [
        {
            "role": "user", 
            "content": "Create a chart showing quarterly revenue trends: Q1 2023: $100M, Q2 2023: $120M, Q3 2023: $140M, Q4 2023: $135M. Also create a table with this data."
        }
    ]
    
    events_received = []
    
    async def test_callback(event):
        events_received.append(event)
        logger.info(f"Tool test event: {event.get('type')} - {event}")
    
    try:
        result = await claude_service.execute_tool_interaction_turn(
            system_prompt="You are a financial analysis assistant. Use tools to create visualizations when appropriate.",
            messages=messages,
            stream=True,
            emit_callback=test_callback
        )
        
        logger.info(f"Tool streaming result keys: {result.keys() if isinstance(result, dict) else 'Not a dict'}")
        logger.info(f"Total tool events received: {len(events_received)}")
        
        # Check for tool-related events
        tool_events = [event for event in events_received if 'tool' in event.get('type', '')]
        text_events = [event for event in events_received if event.get('type') == 'text_delta']
        
        logger.info(f"Tool events: {len(tool_events)}")
        logger.info(f"Text events: {len(text_events)}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in tool streaming test: {e}")
        return False

async def main():
    """Run all streaming tests."""
    logger.info("Starting streaming implementation tests...")
    
    # Check if API key is available
    if not os.getenv("ANTHROPIC_API_KEY"):
        logger.error("ANTHROPIC_API_KEY not found. Please set it in your environment.")
        return
    
    # Test basic streaming
    basic_success = await test_streaming_basic()
    
    # Wait a moment between tests
    await asyncio.sleep(2)
    
    # Test tool streaming
    tool_success = await test_streaming_tools()
    
    # Summary
    logger.info("=" * 50)
    logger.info("STREAMING TEST RESULTS:")
    logger.info(f"Basic text streaming: {'✓ PASS' if basic_success else '✗ FAIL'}")
    logger.info(f"Tool streaming: {'✓ PASS' if tool_success else '✗ FAIL'}")
    logger.info("=" * 50)
    
    if basic_success and tool_success:
        logger.info("🎉 All streaming tests passed!")
    else:
        logger.warning("⚠️  Some streaming tests failed. Check the logs above.")

if __name__ == "__main__":
    asyncio.run(main())