# Test Plan for Streaming Message Fixes

## Test Checklist

### Frontend Tests

1. **Message Start Protection**
   - [ ] Send multiple message_start events rapidly
   - [ ] Verify only the first one is processed
   - [ ] Confirm streaming text is not reset by duplicate events

2. **Phase Transitions**
   - [ ] Initial phase: Text accumulates in streamingText
   - [ ] Tool start: Initial message completes, phase transitions to 'tools'
   - [ ] Post-tools: New text accumulates in postVisualizationText
   - [ ] Message complete: All 3 messages are created

3. **Three-Message Architecture**
   - [ ] Message 1: Initial streaming response (before tools)
   - [ ] Message 2: Tool/visualization results (charts, tables, metrics)
   - [ ] Message 3: Post-visualization explanation text

### Backend Tests

1. **Session Tracking**
   - [ ] Verify session is created for each streaming request
   - [ ] Confirm duplicate message_start events are filtered
   - [ ] Check message_id consistency throughout session

2. **Tool Events**
   - [ ] Verify tool_start events are emitted when tools begin
   - [ ] Confirm tool_id and tool_name are included
   - [ ] Check events have correct message_id

## Test Scenarios

### Scenario 1: Full Tool Flow
**Input**: "How has credit trended?"
**Expected**:
1. Initial streaming message appears with analysis text
2. When tools start, Message 1 completes and remains visible
3. Message 2 appears with visualizations
4. Message 3 appears with post-analysis text
5. All 3 messages persist

### Scenario 2: No Tools Flow
**Input**: "What is your name?"
**Expected**:
1. Single streaming message appears
2. Message completes as streaming-only
3. No visualization messages created

### Scenario 3: Rapid Messages
**Input**: Send 3 messages quickly
**Expected**:
1. Each message maintains separate state
2. No cross-contamination between messages
3. Phase tracking remains independent

## Debug Logging

Monitor these log patterns:

### Frontend
```
🚀 Starting new message: <id>
🛡️ IGNORING duplicate message_start
📝 Building initial streaming: X chars
🔧 Tool started: <name> in phase initial
✅ Completing initial streaming message: X chars
📊 Transitioning to post-tools phase
💬 Building post-visualization content: X chars
🏁 Message complete in phase: <phase>
📊 Creating visualization message with X items
💬 Creating post-visualization message: X chars
🧹 Cleaning up after phase transitions: initial → tools → post-tools
```

### Backend
```
WEBSOCKET_FLOW: Created streaming session <key> with message_id: <id>
WEBSOCKET_FLOW: Sent initial message_start event
WEBSOCKET_FLOW: Filtering out duplicate message_start event
WEBSOCKET_FLOW: Emitting tool_start event
WEBSOCKET_FLOW: Emitting message_complete event
```

## Verification Steps

1. **Start Backend**
   ```bash
   cd backend
   python -m uvicorn app.main:app --reload --port 8000
   ```

2. **Start Frontend**
   ```bash
   cd nextjs-fdas
   npm run dev
   ```

3. **Open Browser Console**
   - Enable verbose logging
   - Filter for streaming-related messages

4. **Test Each Scenario**
   - Upload a financial document
   - Send test queries
   - Monitor console logs
   - Verify message rendering

## Success Criteria

- ✅ Initial streaming message never disappears
- ✅ Visualizations render 100% of the time
- ✅ Post-visualization text appears as separate message
- ✅ No duplicate or lost content
- ✅ Clean phase transitions in logs
- ✅ Smooth user experience