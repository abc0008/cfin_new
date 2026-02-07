# Citation Flow Verification

## Summary of Fixes Applied

### 1. Fixed Citation Persistence in Streaming Flow
- Added `create_citation_with_message` method to DocumentRepository
- This method creates citations and establishes the MessageCitation relationship
- Citations are now properly linked to messages in the database

### 2. Backend Citation Event Emission
- Fixed event type from "citation" to "citations_delta"
- Added support for citation_delta chunks during streaming
- Citations are emitted with proper block_index for frontend handling

### 3. Frontend Citation Reception
- Updated StreamingChatInterface to use `useStreamingChatWithCitations`
- Added document map creation and passing to the hook
- Citations are collected and stored in CitationContext

### 4. Citation Retrieval
- Backend fetches citations when returning conversation history
- Citations are included in Message response model
- Frontend receives citations with each message

## Complete Citation Flow

### 1. Document Upload
```
PDF → Claude Files API → file_id stored in document
```

### 2. User Query with Document
```
User Message → Backend → Claude API with citations enabled
```

### 3. Streaming Response
```
Claude Response → Backend extracts citations → Emits "citations_delta" events
```

### 4. Frontend Collection
```
WebSocket receives events → useStreamingChatWithCitations collects citations → Stores in pendingCitations Map
```

### 5. Citation Persistence
```
Backend saves citations to DB → Creates MessageCitation relationships → Citations linked to message
```

### 6. Citation Display
```
Frontend receives message_complete → Citations added to CitationContext → MessageRenderer displays [1], [2] markers
```

### 7. Citation Retrieval
```
Get conversation history → Backend fetches citations for each message → Frontend receives messages with citations
```

## Testing the Complete Flow

### Test 1: Real-time Citation Generation
1. Upload a PDF document
2. Ask a specific question (e.g., "What is the revenue for Q3 2023?")
3. Monitor browser console for:
   - "citations_delta" events
   - Citation collection logs
4. Verify citations appear as [1], [2] in the response
5. Click citation to verify navigation

### Test 2: Citation Persistence
1. After receiving a response with citations
2. Refresh the page
3. Load the same conversation
4. Verify citations are still present in messages
5. Verify citation clicks still work

### Test 3: Backend Verification
1. Check backend logs for:
   ```
   Found citation in streaming response: ...
   Created citation {id} for document {doc_id}
   ```
2. Check database for:
   - Citations in `citations` table
   - MessageCitation relationships in `message_citations` table

### Test 4: Multiple Documents
1. Upload multiple PDFs
2. Ask a question that requires information from multiple documents
3. Verify citations reference the correct documents
4. Verify each citation navigates to the correct PDF

## Database Verification Queries

```sql
-- Check citations for a message
SELECT c.* FROM citations c
JOIN message_citations mc ON c.id = mc.citation_id
WHERE mc.message_id = 'YOUR_MESSAGE_ID';

-- Check all citations for a document
SELECT * FROM citations 
WHERE document_id = 'YOUR_DOCUMENT_ID';

-- Verify message-citation relationships
SELECT m.id as message_id, m.content, c.id as citation_id, c.cited_text
FROM messages m
JOIN message_citations mc ON m.id = mc.message_id
JOIN citations c ON mc.citation_id = c.id
WHERE m.conversation_id = 'YOUR_CONVERSATION_ID';
```

## Common Issues and Solutions

### Citations Not Appearing
1. Ensure document has valid `claude_file_id`
2. Check WebSocket connection is active
3. Verify "citations_delta" events in browser console
4. Check backend logs for citation creation

### Citations Not Persisting
1. Check database for citation records
2. Verify MessageCitation relationships exist
3. Check for errors in backend logs during citation creation
4. Ensure transaction commits successfully

### Citations Not Loading on Refresh
1. Verify `/conversation/{id}/history` endpoint returns citations
2. Check frontend receives citations in message objects
3. Verify CitationContext is populated on load

## Success Indicators
- ✅ Citations appear in real-time during streaming
- ✅ Citations persist in database with message relationships
- ✅ Citations load when conversation history is fetched
- ✅ Citation clicks navigate to correct PDF location
- ✅ Multiple citations from different documents work correctly