# Streaming Deduplication Fix

## Problem
Multiple `content_update` events were being sent for nearly identical content, causing:
1. Database updates for every single character addition (e.g., 1298 chars → 1299 chars)
2. Unnecessary processing overhead
3. Potential race conditions with rapid updates

## Root Cause
The backend was sending a `content_update` event for EVERY `text_delta` event from Claude's streaming API. If Claude sent 100 small text chunks, we'd send 100 database updates.

## Solution
Implemented intelligent batching of content updates:

### In `_process_streaming_response` (api_service.py):

1. **Added tracking of last content update**:
```python
last_content_update_length = 0  # Track last content update to avoid duplicates
```

2. **Intelligent content update batching**:
```python
# Only send content_update if we have significant new content
# This prevents duplicate updates for single character additions
content_length_diff = len(accumulated_text) - last_content_update_length
if content_length_diff >= 50 or (content_length_diff > 0 and text_delta.endswith('\n')):
    await emit_callback({
        "type": "content_update",
        "accumulated_text": accumulated_text,
        "message_id": message_id,
        "is_post_tools": False,
        "post_tool_text": None
    })
    last_content_update_length = len(accumulated_text)
```

3. **Final content update on block completion**:
```python
# Content block completed - send final content_update if needed
if not tools_started and last_content_update_length < len(accumulated_text):
    # Send final content update for any remaining text
    await emit_callback({
        "type": "content_update",
        "accumulated_text": accumulated_text,
        "message_id": message_id,
        "is_post_tools": False,
        "post_tool_text": None
    })
```

## Benefits
1. **Reduced database writes**: Only updates when there's meaningful new content (50+ chars or at line breaks)
2. **Preserved formatting**: Still only sends pre-tool formatted text
3. **Better performance**: Fewer round trips between backend and frontend
4. **No duplicate messages**: Eliminates the 1298→1299 char duplicate update issue

## Result
- Text streams smoothly with `text_delta` events (real-time feel)
- Database updates happen intelligently in batches
- Final content is complete and properly formatted
- No more duplicate content or lost formatting