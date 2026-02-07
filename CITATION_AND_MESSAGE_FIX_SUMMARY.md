# Citation and Message Separation Fix Summary

## Issues Addressed

1. **Post-Visualization Message Separation**: Post-visualization content was being appended to the initial message instead of appearing as a separate message
2. **Content Duplication**: Initial message content was being duplicated when citations were added
3. **Citation Hyperlinks Lost**: Citation hyperlinks disappeared after message updates

## Changes Made

### Backend Changes

#### 1. **Post-Visualization Message Separation** (`services/conversation_service.py`)
- Modified the handling of post-tool content to create a NEW message instead of appending
- Added emission of `new_message_start`, `text_delta`, and `message_complete` events for post-visualization messages
- This ensures post-visualization content appears as a separate message in the chat

```python
# Create a new assistant message for post-visualization content
post_viz_message = await self.conversation_repository.add_message(
    conversation_id=conversation_id,
    role="assistant",
    content=post_tool_text,
    referenced_documents=[],
    referenced_analyses=[],
    citations=[]
)

# Emit new_message_start event for frontend
await emit_callback({
    "type": "new_message_start",
    "message_id": str(post_viz_message.id),
    "role": "assistant",
    "is_post_visualization": True
})
```

#### 2. **Fix Content Duplication** (`pdf_processing/api_service.py`)
- Removed `accumulated_text` field from citation marker text_delta events
- This prevents the frontend from seeing the full content again when citations are added

```python
# Send as text_delta to append to the initial streamed text
# IMPORTANT: Don't include accumulated_text to prevent content duplication
await emit_callback({
    "type": "text_delta",
    "text": markers_text,
    "message_id": message_id
})
```

### Frontend Changes

#### 1. **Handle New Message Events** (`src/hooks/useStreamingChatWithCitations.ts`)
- Added handler for `new_message_start` event to create separate post-visualization messages
- Updated `text_delta` handler to support updating specific messages by ID
- Modified `message_complete` handler to recognize post-visualization completions

```typescript
case 'new_message_start':
  // Handle new message for post-visualization content
  if (event.is_post_visualization && onMessageUpdate) {
    const postVizMessage: Message = {
      id: event.message_id || `post-viz-${Date.now()}`,
      sessionId: conversationId,
      timestamp: new Date().toISOString(),
      role: event.role || 'assistant',
      content: '',  // Will be filled by subsequent text_delta events
      // ... other fields
    };
    
    // Add the new message to the chat
    onMessageUpdate(postVizMessage);
  }
  break;
```

#### 2. **Citation Preservation**
- MessageRenderer component already handles citation rendering with clickable links
- Citations are preserved through all message updates since they're embedded in the content as markers

## How It Works Now

1. **Initial Streaming**: Claude streams the initial response with analysis
2. **Tool Execution**: When tools start, the initial content is frozen
3. **Citation Addition**: Citations are added as text_delta events (e.g., " [1] [2] [3]")
4. **Post-Visualization Content**: 
   - Backend creates a NEW message for post-tool insights
   - Frontend receives `new_message_start` and creates a separate message entry
   - Post-viz content streams into this new message
5. **Citation Rendering**: MessageRenderer automatically converts [1], [2], [3] markers into clickable buttons

## Testing

To verify the fixes:
1. Upload a PDF document
2. Ask a question that triggers visualization tools
3. Observe:
   - Initial message appears with citations as clickable links
   - Post-visualization insights appear as a SEPARATE message below
   - No content duplication
   - Citations remain clickable throughout all updates