# Streaming Text Duplication Fix

## Problem Description

The backend WebSocket streaming was sending accumulated text that included both initial message content and post-visualization content together. This caused several issues:

1. **Backend Behavior**: During the post-tools phase, `content_update` events contained the FULL accumulated text (initial message + post-visualization text)
2. **Frontend Issue**: The frontend was treating this full text as just post-visualization content, leading to duplication
3. **Display Problem**: Messages appeared with correct formatting followed by unformatted duplicated content

### Example from logs:
- Initial message: 1203 chars  
- Post-visualization: 859 chars
- Backend sends: 1203 + 859 = 2062 chars total in content_update during post-tools phase

## Solution Implementation

### 1. Fixed Content Extraction in useStreamingChat.ts

#### content_update Handler
```typescript
if (event.accumulated_text) {
  if (messagePhase === 'initial' || (!messagePhase && !toolsStarted)) {
    setStreamingText(event.accumulated_text);
  } else if (messagePhase === 'tools' || messagePhase === 'post-tools' || toolsStarted) {
    // Backend sends full accumulated text including initial message
    // Extract only the post-visualization part
    if (frozenInitialText && event.accumulated_text.startsWith(frozenInitialText)) {
      const postVizOnly = event.accumulated_text.substring(frozenInitialText.length).trim();
      setPostVisualizationText(postVizOnly);
    } else {
      setPostVisualizationText(event.accumulated_text);
    }
  }
}
```

#### text_delta Handler
```typescript
// Handle accumulated_text in text_delta events
if (event.accumulated_text) {
  if (messagePhase === 'initial') {
    setStreamingText(event.accumulated_text);
  } else if ((messagePhase === 'tools' || messagePhase === 'post-tools') && frozenInitialText) {
    // Extract only post-viz content from accumulated text
    if (event.accumulated_text.startsWith(frozenInitialText)) {
      const postVizOnly = event.accumulated_text.substring(frozenInitialText.length).trim();
      setPostVisualizationText(postVizOnly);
    }
  }
}
```

### 2. Enhanced Duplicate Detection in MessageRenderer.tsx

Added three levels of duplicate detection:

1. **Exact Duplicate Check**: Detects when content is literally repeated twice
2. **Formatted vs Unformatted Check**: Removes unformatted duplicates at the end
3. **Pattern-Based Detection**: Finds repeated patterns within the content

```typescript
const detectDuplicateText = (content: string): string => {
  // Level 1: Check for exact duplicates
  const halfLength = Math.floor(content.length / 2);
  if (content.length > 100) {
    const firstHalf = content.substring(0, halfLength);
    const secondHalf = content.substring(halfLength);
    if (firstHalf.trim() === secondHalf.trim()) {
      return firstHalf.trim();
    }
  }
  
  // Level 2: Check for formatted + unformatted versions
  // (existing logic)
  
  // Level 3: Pattern-based duplicate detection
  if (content.length > 200) {
    const plainContent = getPlainText(content);
    const searchPattern = plainContent.substring(0, Math.min(100, Math.floor(plainContent.length / 4)));
    const secondOccurrence = plainContent.indexOf(searchPattern, searchPattern.length);
    if (secondOccurrence > searchPattern.length) {
      return content.substring(0, secondOccurrence).trim();
    }
  }
  
  return content;
};
```

## Key Technical Details

1. **frozenInitialText**: Stores the initial message content when tools start, allowing accurate extraction of post-visualization content
2. **Phase Tracking**: Uses messagePhase to determine how to handle accumulated text
3. **Multiple Detection Strategies**: Handles various duplication patterns that might occur

## Testing Recommendations

1. Test with messages that have both initial content and post-visualization content
2. Verify that formatting is preserved in both message parts
3. Check edge cases where initial message might be very short or very long
4. Test rapid message sending to ensure no race conditions

## Benefits

- Eliminates duplicate content in displayed messages
- Preserves proper formatting throughout
- Handles backend's accumulated text behavior correctly
- Provides fallback mechanisms for edge cases