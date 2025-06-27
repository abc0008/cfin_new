# Streaming Message Visibility Fix

## Problem
When tools started (`tool_start` event), the initial streaming message disappeared from the UI because:
- `setStreamingText('')` was called, clearing the displayed text
- The UI only checks `streamingText` to display content
- `frozenInitialText` was saved but not used by the UI

## Solution
Keep `streamingText` visible throughout the entire tool execution phase.

### Change in useStreamingChat.ts (line 215-217)

```typescript
// BEFORE: Cleared streaming text, causing message to disappear
setStreamingText('');
setIsStreaming(false);

// AFTER: Keep streaming text visible
// DON'T clear streaming text - we want it to stay visible!
// Just stop streaming for new content
setIsStreaming(false);
```

## How It Works

1. **Initial Phase**: 
   - `text_delta` events accumulate in `streamingText`
   - Message displays in real-time with formatting

2. **When Tools Start**:
   - `streamingText` is frozen into `frozenInitialText` (backup)
   - `streamingText` REMAINS UNCHANGED (stays visible)
   - `isStreaming` set to false (stops cursor/animation)
   - Phase transitions to 'tools'

3. **During Tools Phase**:
   - Initial message remains visible via `streamingText`
   - Any new text goes to `postVisualizationText`
   - Tools execute in the background

4. **Message Complete**:
   - All state is cleaned up (including `streamingText`)
   - Final messages are displayed properly

## Benefits

- No message disappearing when tools start
- Smooth transition from streaming to tool execution
- User sees their formatted response throughout
- No flashing or content replacement

## Note
The UI component doesn't need to be modified because it already displays `streamingText`. By not clearing it, the message naturally stays visible.