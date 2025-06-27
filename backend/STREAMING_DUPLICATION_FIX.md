# Streaming Text Duplication Fix

## Issue
Claude's streaming API was causing duplicate text to appear in messages:
1. During streaming: Properly formatted text with line breaks, bullet points, etc.
2. After streaming: Unformatted duplicate of the same content

## Root Cause
Multiple issues were causing the duplication:

1. **In `api_service.py`**: The `_process_streaming_response` method was correctly accumulating text from streaming deltas, but `stream.get_final_message()` contains the complete response from Claude again (without formatting).

2. **In `api_service.py`**: The `analyze_with_visualization_tools_streaming` method was accumulating text across multiple turns, causing duplication when Claude repeats content after tool use.

3. **In `conversation_service.py`**: The `enhanced_emit_callback` was overwriting the entire message content on every `content_update` event, causing formatted text to be replaced with unformatted text.

## Solution
Three-part fix to address all sources of duplication:

### 1. Modified `_process_streaming_response` to:
- Track whether we received any streaming text with a `received_streaming_text` flag
- Only use `final_message` for extracting tool calls, not text content
- Return the accumulated streaming text (which has proper formatting)

### 2. Modified `analyze_with_visualization_tools_streaming` to:
- Better handle text accumulation across turns
- Detect when Claude includes previous content in new responses
- Only use the latest complete response when it contains all previous content

### 3. Modified `enhanced_emit_callback` in `conversation_service.py` to:
- Only update the database when receiving genuinely new content
- Preserve formatted initial text instead of overwriting with unformatted text
- Properly append post-tool text instead of replacing the entire message

## Code Changes

### In `/Users/alexcardell/AlexCoding_Local/cfin/backend/pdf_processing/api_service.py`:

1. **In `_process_streaming_response`**:
```python
received_streaming_text = False  # Track if we received any streaming text

# When receiving text:
accumulated_text += text_delta
received_streaming_text = True  # Mark that we received streaming text

# Only use final_message for tool calls:
if received_streaming_text:
    logger.info(f"Received {len(accumulated_text)} chars during streaming, will ignore text in final_message")
```

2. **In `analyze_with_visualization_tools_streaming`**:
```python
# Better duplicate detection for multi-turn responses
if accumulated_text.strip() in response_text:
    # The new response contains all previous content plus more
    accumulated_text = response_text
    logger.info(f"Turn {turn + 1}: Response contains previous content, using complete response")
elif self._is_substantially_new_content(response_text, accumulated_text):
    # This is genuinely new content, append it
    accumulated_text += "\n\n" + response_text
else:
    # This is duplicate content, skip it
    logger.info(f"Turn {turn + 1}: Skipping duplicate content")
```

### In `/Users/alexcardell/AlexCoding_Local/cfin/backend/services/conversation_service.py`:

**In `enhanced_emit_callback`**:
```python
# Smart content updating to preserve formatting
if not current_content or current_content == "Processing your request...":
    # First real content, always update
    should_update = True
elif event.get("is_post_tools") and event.get("post_tool_text"):
    # Append post-tool text to existing content
    new_content = current_content + "\n\n" + post_tool_text
    should_update = True
elif len(new_content) > len(current_content):
    # New content is longer, likely contains more information
    should_update = True
else:
    # Don't update if new content is shorter (likely missing formatting)
    should_update = False
```

## Testing
The backend server is running with --reload and will automatically pick up these changes. Test by:
1. Sending a query that generates formatted content with tools
2. Checking that the initial formatted response is preserved
3. Verifying that post-tool content is appended, not replaced
4. Ensuring no unformatted duplicates appear

## Impact
This comprehensive fix ensures:
- Initial formatted text is preserved throughout the streaming process
- Post-tool content is properly appended without losing formatting
- No duplicate content in the final message
- Better handling of Claude's multi-turn response patterns