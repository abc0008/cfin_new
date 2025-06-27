#!/usr/bin/env python3
"""Test script to verify timestamp serialization fix"""

import sys
import os
sys.path.append('/Users/alexcardell/AlexCoding_Local/cfin/backend')

from datetime import datetime
from models.message import Message, MessageRole

# Test creating a message and serializing it
print("=== Testing Message Timestamp Serialization ===")

# Create a message with the default UTC timestamp
message = Message(
    session_id="test-session",
    role=MessageRole.USER,
    content="Test message"
)

print(f"Message created at: {message.timestamp}")
print(f"Message timestamp type: {type(message.timestamp)}")

# Serialize the message to JSON
json_data = message.model_dump(by_alias=True)
print(f"Serialized timestamp: {json_data['timestamp']}")
print(f"Timestamp ends with Z: {json_data['timestamp'].endswith('Z')}")

# Test with an assistant message
assistant_message = Message(
    session_id="test-session", 
    role=MessageRole.ASSISTANT,
    content="Assistant response"
)

assistant_json = assistant_message.model_dump(by_alias=True)
print(f"\nAssistant timestamp: {assistant_json['timestamp']}")
print(f"Assistant timestamp ends with Z: {assistant_json['timestamp'].endswith('Z')}")

# Test parsing a timestamp from frontend
from utils.message_converters import frontend_message_to_internal

frontend_msg = {
    "sessionId": "test-session",
    "role": "user", 
    "content": "Frontend message",
    "timestamp": "2025-06-19T06:10:19.280Z"
}

parsed_message = frontend_message_to_internal(frontend_msg)
parsed_json = parsed_message.model_dump(by_alias=True)
print(f"\nParsed frontend timestamp: {parsed_json['timestamp']}")
print(f"Parsed timestamp ends with Z: {parsed_json['timestamp'].endswith('Z')}")

print("\n=== Test Complete ===")