# Streaming Fix: No Unformatted Text

## Goal
Never show unformatted text to the user. Only show the properly formatted text that comes through during initial streaming.

## Problem
Claude's streaming API sends text in two phases:
1. **Initial streaming**: Properly formatted text with line breaks, bullet points, numbered lists
2. **Post-tool streaming**: Often the same content but without formatting

The unformatted version was overwriting the formatted version.

## Solution
Two simple changes to completely prevent unformatted text from being used:

### 1. In `api_service.py` - `_process_streaming_response`
Only send `content_update` events for pre-tool text:
```python
# Only send content_update for initial text (before tools)
# Post-tool text is often unformatted duplicate, so we skip it
if not tools_started:
    await emit_callback({
        "type": "content_update",
        "accumulated_text": accumulated_text,
        "message_id": message_id,
        "is_post_tools": False,
        "post_tool_text": None
    })
```

### 2. In `conversation_service.py` - `enhanced_emit_callback`
Ignore all post-tool content updates:
```python
# Only process content updates that are NOT post-tools
# Post-tool content is often unformatted and duplicative
if event.get("is_post_tools", False):
    logger.info(f"📝 Ignoring post-tool content update to preserve formatting")
    return
```

## Result
- Only the initial, properly formatted text is saved to the database
- Post-tool text (which is often unformatted duplicate) is completely ignored
- The frontend still receives text_delta events for real-time streaming
- The final message shown to users always has proper formatting

## Testing
1. Send a query that triggers tool use
2. Observe that the initial formatted response is preserved
3. Verify that no unformatted text appears after tools complete
4. Check that the final message maintains all formatting