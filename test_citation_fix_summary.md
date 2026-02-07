# Citation Fix Summary

## Issues Fixed

### 1. Backend Citation Preservation
**Problem**: Backend was overwriting content with citations back to the version without citations
**Solution**: Modified `conversation_service.py` to check if current content has citations before restoring `last_good_content`

### 2. Frontend Message Disappearance
**Problem**: Message disappeared when tools started because `streamingText` was cleared
**Solution**: Removed the clearing of `streamingText` when `tool_start` event is received

### 3. Content Duplication
**Problem**: Final message showed content twice due to incorrect concatenation logic
**Solution**: Improved content selection logic to choose the most up-to-date content with citations

### 4. React State Warning
**Problem**: Calling `onMessageUpdate` inside `setStreamingText` caused side effects during render
**Solution**: Used `setTimeout` to defer the message update until after the state update

## Test Results

The WebSocket test confirms:
- Citations are properly received via `citation_marker` and `citations_delta` events
- Citation markers appear in the text stream
- Citations are preserved through the entire flow
- Post-visualization messages are handled separately

## Expected Behavior

1. User sends a message requiring document analysis
2. Initial streaming response appears and stays visible
3. When tools start, the message remains visible (no disappearing)
4. Citation markers are added to the initial message
5. Citation markers remain as clickable hyperlinks
6. Post-visualization content appears as a separate message
7. No content duplication or React warnings

## Files Modified

1. `/backend/services/conversation_service.py` - Lines 1175-1196
2. `/nextjs-fdas/src/hooks/useStreamingChatWithCitations.ts` - Lines 268-281, 337-373, 161-185