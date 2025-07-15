# Citation Flow: Backend to Frontend

## 1. Backend Citation Generation

### `/backend/pdf_processing/api_service.py`
**Method:** `generate_response_streaming()`
- Collects citations during Claude API streaming
- Fields: `accumulated_citations` (list)
- Yields citation events: `{"type": "citations_delta", "citation": {...}}`

### `/backend/services/conversation_service.py`
**Method:** `process_user_message_streaming()`
- Line 950: Detects citation markers in text: `re.search(r'\[\d+\]', text_content)`
- Line 955: Updates `last_good_content` with citation markers
- Line 1177: Checks for citations: `bool(re.search(r'\[\d+\]', content))`
- Fields:
  - `has_good_content` (bool)
  - `last_good_content` (str)
  - `tool_start_processed_in_current_stream` (bool)

### `/backend/app/routes/websocket.py`
**Method:** `conversation_handler()`
- Forwards streaming events from conversation service
- Maintains `message_id` consistency
- Allows new message IDs for post-visualization content

## 2. WebSocket Event Flow

### Citation-Related Events:
1. `text_delta` - Contains citation markers like "[1] [2] [3]"
2. `citations_delta` - Citation metadata: 
   ```json
   {
     "type": "citations_delta",
     "citation": {
       "document_id": "...",
       "start_page_number": 2,
       "end_page_number": 3,
       "cited_text": "..."
     },
     "block_index": 0
   }
   ```
3. `message_complete` - May include all citations in payload

## 3. Frontend Citation Processing

### `/nextjs-fdas/src/hooks/useStreamingChatWithCitations.ts`

**State Variables:**
- `pendingCitations: Map<number, Citation[]>` - Citations by block index
- `citationCounter: number` - Display counter
- `streamingText: string` - Contains citation markers
- `frozenInitialText: string` - Preserved text with citations

**Key Methods:**

**`handleStreamingEvent()`**
- Line 155: `case 'text_delta'` - Handles citation markers
- Line 159: Detects markers: `/\[\d+\]/.test(event.text)`
- Line 196: Updates frozen text with citations
- Line 212: `case 'citations_delta'` - Processes citation metadata
- Line 283: `case 'message_complete'` - Collects all citations

**Citation Collection (Lines 323-334):**
```typescript
const allCitations: Citation[] = [];
pendingCitations.forEach(citations => {
  allCitations.push(...citations);
});
```

### `/nextjs-fdas/src/lib/pdf/citationService.ts`
**Method:** `handleStreamingCitation()`
- Processes `citations_delta` events
- Maps document indices to document IDs
- Adds to `pendingCitations` map

### `/nextjs-fdas/src/context/CitationContext.tsx`
**Method:** `addCitations()`
- Stores citations globally for PDF highlighting
- Used by PDF viewer for clickable citations

## 4. Citation Data Models

### Backend Citation Model
```python
# /backend/models/database_models.py
class Citation:
    id: str
    message_id: str
    document_id: str
    start_page_number: int
    end_page_number: int
    cited_text: str
    start_char_index: Optional[int]
    end_char_index: Optional[int]
```

### Frontend Citation Type
```typescript
// /nextjs-fdas/src/types/citation.ts
interface Citation {
    id: string;
    messageId: string;
    documentId: string;
    documentTitle: string;
    citedText: string;
    startPageNumber: number;
    endPageNumber: number;
    startCharIndex?: number;
    endCharIndex?: number;
    highlightRects: HighlightRect[];
}
```

## 5. Message Display with Citations

### `/nextjs-fdas/src/components/chat/MessageList.tsx`
- Renders messages with citation markers
- Citation markers are part of `message.content`

### `/nextjs-fdas/src/components/chat/Message.tsx`
- Displays message content with clickable citation links
- Uses regex to convert "[1]" to hyperlinks

## 6. PDF Highlighting Integration

### `/nextjs-fdas/src/components/document/PDFViewer.tsx`
- Subscribes to CitationContext
- Highlights cited passages when citations are clicked
- Uses `highlightRects` to position highlights

## 7. Updated Event Flow (2025-07-05)

This section describes **how the citation + post-visualization pipeline works _after_ the July 2025 fixes** to
`/nextjs-fdas/src/hooks/useStreamingChatWithCitations.ts` and related backend flags.  It supplements – not
replaces – the reference material above.

### 7.1  Back-to-Front Message Timeline

| Step | WebSocket Event | Key Fields / Flags | Frontend Hook Reaction |
|------|-----------------|--------------------|------------------------|
| ① | `message_start` *(initial)* | `message_id: M1` `role: assistant`<br/>`is_post_tools: false` | • Create **streaming message** `M1`.<br/>• Initialise `streamingTextRef`, `frozenInitialTextRef` and state counters. |
| ② | `text_delta` (0‥N) | `message_id: M1` | • Append `event.text` → `streamingTextRef`.<br/>• If delta contains citation markers ( `/\[\d+\]/` ) also patch `frozenInitialTextRef` so citations are preserved even if we later skip small deltas. |
| ③ | `citations_delta` (0‥N) | `message_id: M1` `block_index` | • Add citation object to `pendingCitations[block_index]`. |
| ④ | `tool_start` | `message_id: M1` `tool_id` | • Set `toolsStarted = true`.<br/>• Analysis pane renders *loading* placeholder. |
| ⑤ | `tool_complete` / `chart_ready` / `table_ready` / … | `message_id: M1` | • Push chart / table / metric payloads to analysis pane UI. |
| ⑥ | `message_complete` *(for M1)* | `message_id: M1` | • Determine `finalContent` → choose _version with citation markers_ preferentially.<br/>• Freeze message `M1` (status=`complete`).<br/>• Flush `pendingCitations` → `CitationContext.addCitations`.<br/>• **Set `awaitingPostVisualization = true`** so the next narrative delta spawns a fresh message if the backend forgets to send `new_message_start`. |
| ⑦ | _Option A_ – backend behaves | `new_message_start` | `message_id: M2` `is_post_tools: true` | • Create **post-visualization message** `M2`.<br/>• Clear streaming buffers. |
| ⑦ | _Option B_ – backend omits event | `text_delta` (first narrative chunk) | `message_id: (M1 _or_ blank)` `is_post_tools: true` <br/>`awaitingPostVisualization == true` | • Hook **bootstrap-creates M2 on the fly**:<br/>  – Allocate synthetic `message_id` if absent.<br/>  – Push `M2` through `onMessageUpdate`.<br/>  – Reset `awaitingPostVisualization = false`.<br/>  – Append delta text to `M2`. |
| ⑧ | `text_delta` / `citations_delta` (0‥N) | `message_id: M2` | • Normal streaming → `streamingTextRef` of `M2`.<br/>• Citation handling identical to steps ②/③. |
| ⑨ | `message_complete` *(for M2)* | `message_id: M2` | • Finalise post-viz narrative.<br/>• Flush any remaining citations. |

### 7.2  Important Frontend Flags / Refs

* **`streamingTextRef` / `frozenInitialTextRef`** – always hold the *latest* text.  `message_complete` now
  consults these refs instead of potentially-stale React state, guaranteeing citation markers are available
  for the final merge.
* **`awaitingPostVisualization`** – boolean that becomes `true` right after step ⑥; consumed at step ⑦ to
  decide whether an unsolicited `text_delta` should start a new message.
* **`toolsStarted`** – set by the first `tool_start`; signals that the initial answer **will** be followed by
  tool output and a narrative wrap-up.
* **`postToolMessageId`** – stores backend-supplied ID (if any) for the post-viz message so subsequent
  deltas can be routed correctly.

### 7.3  `StreamingEvent` Interface Additions

```ts
export interface StreamingEvent {
  type:
    | 'message_start'
    | 'new_message_start'
    | 'text_delta'
    | 'tool_start'
    | 'tool_complete'
    | 'chart_ready'
    | 'table_ready'
    | 'metric_ready'
    | 'message_complete'
    | 'content_update'
    | 'citations_delta'
    | 'error'
    | 'content_block_delta';
  message_id?: string;
  text?: string;
  citation?: ClaudeCitation;
  citations?: ClaudeCitation[];
  is_post_tools?: boolean;          // ⬅ NEW
  is_post_visualization?: boolean;  // ⬅ NEW (alias from backend)
  /* …unchanged fields omitted… */
}
```

With these changes the user sees: 
1. **Immediate** replacement of the initial answer with citation-decorated text.
2. Charts/tables render in the analysis pane while the chat bubble remains unchanged.
3. A **separate** follow-up message appears once visuals are ready, even if the backend forgets
   `new_message_start`.

## Flow Summary

1. **Claude API** → Generates citations during streaming
2. **api_service.py** → Collects and yields citation events
3. **conversation_service.py** → Preserves citation markers in text
4. **WebSocket** → Forwards citation events to frontend
5. **useStreamingChat** → Processes events, updates state
6. **CitationContext** → Stores citations globally
7. **MessageList** → Displays text with citation markers
8. **PDFViewer** → Highlights cited passages

## 8. Three-Message Architecture (2025-07-07)

This section describes the **3-message architecture** implemented to fix message ordering issues where tool calls were sharing the same message_id as the initial message, causing timestamp problems.

### 8.1 Problem Statement

Previously, the system used the same `message_id` for:
- Initial assistant response with citations
- Tool/visualization execution events
- Analysis blocks storage

This caused the initial message's `message_complete` to be delayed until after all tools finished, resulting in incorrect timestamp ordering.

### 8.2 Solution: Three Distinct Messages

The system now creates **3 separate messages** with unique IDs:

| Message Type | Content | When Created | Message ID |
|--------------|---------|--------------|------------|
| **Initial Message** | Text response with citation markers `[1]`, `[2]`, etc. | At conversation start | `M1` (original streaming ID) |
| **Tools Message** | Analysis blocks only (charts, tables, metrics) | When first `tool_start` detected | `M2` (new ID) |
| **Post-Viz Message** | Concluding analysis narrative | After tools complete | `M3` (new ID) |

### 8.3 Backend Implementation Changes

#### `/backend/services/conversation_service.py`

**Initial Message Completion (Lines 929-959):**
- When `tool_start` is detected, checks if citation markers are present
- If citations exist: Immediately sends `message_complete` for initial message
- If no citations yet: Sets `waiting_for_citations = True` and defers completion

**Citation Race Condition Handling (Lines 1017-1040):**
- When citation markers arrive after `tool_start`:
  - Updates database with complete content
  - Sends deferred `message_complete` if waiting
  - Ensures initial message always includes its citations

**Tools Message Creation (Lines 1356-1377):**
```python
# Create a NEW message for tools/visualizations
tools_message = await self.conversation_repository.add_message(
    conversation_id=conversation_id,
    role="assistant",
    content="",  # Tools message has no text content
    referenced_documents=[],
    referenced_analyses=[]
)

# Emit new_message_start for the tools message
if emit_callback:
    await emit_callback({
        "type": "new_message_start",
        "message_id": str(tools_message.id),
        "role": "assistant",
        "is_tools_message": True
    })
```

**Analysis Blocks Storage (Lines 1403-1410):**
- Analysis blocks are now stored on the `tools_message`, not the initial message
- Tools message completion includes `is_tools_message: True` flag

#### `/backend/app/routes/websocket.py`

**StreamingSession Updates (Lines 28-29):**
```python
tools_message_id: Optional[str] = None  # Track tools message separately
```

**Message ID Routing (Lines 310-324):**
- Recognizes `is_tools_message` flag in `new_message_start` events
- Stores `tools_message_id` in session
- Prevents ID correction for tools message events

### 8.4 Frontend Implementation Changes

#### `/nextjs-fdas/src/hooks/useStreamingChatWithCitations.ts`

**StreamingEvent Interface (Line 33):**
```typescript
is_tools_message?: boolean;  // New flag for tools messages
```

**Tools Message Handling (Lines 142-162):**
```typescript
case 'new_message_start':
  // Handle new message for tools/visualization content
  if (event.is_tools_message && onMessageUpdate) {
    const toolsMessage: Message = {
      id: event.message_id || `tools-${Date.now()}`,
      sessionId: conversationId,
      timestamp: new Date().toISOString(),
      role: 'assistant',
      content: '',  // Tools message has no text content
      analysis_blocks: []  // Will be populated by tool events
    };
    onMessageUpdate(toolsMessage);
    setActiveMessageId(event.message_id || null);
  }
```

**Tools Message Completion (Lines 471-490):**
```typescript
if (event.is_tools_message) {
  // Update tools message with analysis blocks
  if (onMessageUpdate && event.message_id && event.analysis_blocks) {
    onMessageUpdate({
      id: event.message_id,
      content: '',  // Tools message has no text content
      analysis_blocks: event.analysis_blocks || []
    });
  }
  return;
}
```

### 8.5 Event Flow Timeline

| Time | Event | Message ID | Result |
|------|-------|------------|--------|
| T0 | User sends question | - | User message created |
| T1 | `message_start` | M1 | Initial assistant message created |
| T2 | `text_delta` + citations | M1 | Text streams with `[1]`, `[2]` markers |
| T3 | `citations_delta` | M1 | Citation metadata collected |
| T4 | `tool_start` detected | M1 | **Initial message completed** ✓ |
| T5 | `new_message_start` | M2 | **Tools message created** |
| T6 | `tool_complete` events | M2 | Visualizations added to tools message |
| T7 | `message_complete` | M2 | **Tools message completed** ✓ |
| T8 | `new_message_start` | M3 | **Post-viz message created** |
| T9 | `text_delta` | M3 | Concluding narrative streams |
| T10 | `message_complete` | M3 | **Post-viz message completed** ✓ |

### 8.6 Benefits

1. **Correct Timestamps**: Each message gets its timestamp when created, maintaining proper chronological order
2. **Clean Separation**: Initial text, visualizations, and conclusions are clearly separated
3. **Race Condition Handling**: Citations that arrive after `tool_start` are properly handled
4. **Backward Compatible**: Existing post-visualization logic remains intact

### 8.7 Key Invariants

1. Initial message ALWAYS completes with its citations before tools message starts
2. Tools message contains ONLY analysis blocks, no text content
3. Each message has a unique ID and timestamp
4. Citation markers are never lost, even if they arrive after `tool_start`