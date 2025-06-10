#!/usr/bin/env python3
"""
Test script to verify API alignment between frontend and backend
Run this after starting the backend server
"""

import requests
import json
from typing import Dict, Any, List

# API base URL
BASE_URL = "http://localhost:8000"

def pretty_print_response(response_data: Any, title: str):
    """Pretty print API response"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    print(json.dumps(response_data, indent=2))

def check_field_format(data: Dict[str, Any], path: str = "") -> List[str]:
    """Check if response fields match expected format (camelCase for frontend)"""
    issues = []
    
    for key, value in data.items():
        current_path = f"{path}.{key}" if path else key
        
        # Check for snake_case in response (frontend expects camelCase)
        if "_" in key:
            camel_case = key.split('_')
            camel_case = camel_case[0] + ''.join(word.capitalize() for word in camel_case[1:])
            issues.append(f"Snake case field '{current_path}' should be '{camel_case}'")
        
        # Recursively check nested objects
        if isinstance(value, dict):
            issues.extend(check_field_format(value, current_path))
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    issues.extend(check_field_format(item, f"{current_path}[{i}]"))
    
    return issues

def test_document_endpoints():
    """Test document-related endpoints"""
    print("\n🔍 Testing Document Endpoints")
    
    # 1. List documents
    try:
        response = requests.get(f"{BASE_URL}/api/documents")
        if response.status_code == 200:
            data = response.json()
            pretty_print_response(data[:1] if data else [], "GET /api/documents (first item)")
            
            # Check field format
            if data:
                issues = check_field_format(data[0])
                if issues:
                    print("\n⚠️  Field format issues:")
                    for issue in issues:
                        print(f"   - {issue}")
        else:
            print(f"❌ Failed to list documents: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing document list: {e}")
    
    # 2. Get document count
    try:
        response = requests.get(f"{BASE_URL}/api/documents/count")
        if response.status_code == 200:
            data = response.json()
            pretty_print_response(data, "GET /api/documents/count")
    except Exception as e:
        print(f"❌ Error testing document count: {e}")

def test_conversation_endpoints():
    """Test conversation-related endpoints"""
    print("\n🔍 Testing Conversation Endpoints")
    
    # 1. Create conversation
    try:
        payload = {
            "title": "Test Conversation",
            "documentIds": []  # Frontend sends camelCase
        }
        response = requests.post(f"{BASE_URL}/api/conversation", json=payload)
        if response.status_code == 201:
            data = response.json()
            pretty_print_response(data, "POST /api/conversation")
            
            session_id = data.get("session_id") or data.get("sessionId")
            
            # Check field format
            issues = check_field_format(data)
            if issues:
                print("\n⚠️  Field format issues:")
                for issue in issues:
                    print(f"   - {issue}")
            
            # 2. Send message
            if session_id:
                message_payload = {
                    "session_id": session_id,  # Backend expects snake_case
                    "content": "Test message",
                    "user_id": "default-user"
                }
                msg_response = requests.post(
                    f"{BASE_URL}/api/conversation/{session_id}/message", 
                    json=message_payload
                )
                if msg_response.status_code == 200:
                    msg_data = msg_response.json()
                    pretty_print_response(msg_data, "POST /api/conversation/{id}/message")
                    
                    # Check message field format
                    msg_issues = check_field_format(msg_data)
                    if msg_issues:
                        print("\n⚠️  Message field format issues:")
                        for issue in msg_issues:
                            print(f"   - {issue}")
        else:
            print(f"❌ Failed to create conversation: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Error testing conversation: {e}")

def test_analysis_endpoints():
    """Test analysis-related endpoints"""
    print("\n🔍 Testing Analysis Endpoints")
    
    # 1. Get analysis types
    try:
        response = requests.get(f"{BASE_URL}/api/analysis/types")
        if response.status_code == 200:
            data = response.json()
            pretty_print_response(data[:1] if data else [], "GET /api/analysis/types (first item)")
    except Exception as e:
        print(f"❌ Error testing analysis types: {e}")

def main():
    """Run all API alignment tests"""
    print("🚀 API Alignment Test Suite")
    print(f"Testing against: {BASE_URL}")
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code != 200:
            print("❌ Backend server is not responding. Please start the server first.")
            return
    except:
        print("❌ Cannot connect to backend server. Please start the server first.")
        return
    
    # Run tests
    test_document_endpoints()
    test_conversation_endpoints()
    test_analysis_endpoints()
    
    print("\n✅ API alignment tests completed")
    print("\n📋 Summary:")
    print("- Check for snake_case fields that should be camelCase")
    print("- Verify all required fields are present")
    print("- Ensure nested objects follow the same conventions")

if __name__ == "__main__":
    main()