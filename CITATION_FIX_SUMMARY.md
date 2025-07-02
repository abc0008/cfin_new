# Citation Fix Summary

## Problem
Citations were not appearing in the interactive chat or analysis pane despite the citation infrastructure being in place.

## Root Causes Identified

1. **Backend not emitting proper citation events**: The backend was emitting events with type "citation" but the frontend expected "citations_delta"
2. **Frontend using wrong streaming hook**: StreamingChatInterface was using the basic `useStreamingChat` instead of `useStreamingChatWithCitations`
3. **Missing document mapping**: The document map needed to map document indices to document IDs wasn't being passed to the streaming hook
4. **Citations might not be captured during streaming chunks**: Added support for citation_delta chunks during streaming

## Changes Made

### Backend Changes

1. **Fixed citation event type** (`/backend/pdf_processing/api_service.py`):
   - Changed event type from "citation" to "citations_delta" (line 537)
   - Added block_index to citation events for proper frontend handling

2. **Added citation delta support during streaming** (`/backend/pdf_processing/api_service.py`):
   - Added handler for citation_delta chunk types during streaming (lines 436-462)
   - This captures citations that come through as separate streaming chunks

### Frontend Changes

1. **Updated StreamingChatInterface** (`/src/components/chat/StreamingChatInterface.tsx`):
   - Changed import from `useStreamingChat` to `useStreamingChatWithCitations`
   - Added document map creation from activeDocuments
   - Pass document map to the enhanced streaming hook

## How Citations Should Now Work

1. **Document Upload**: 
   - PDF uploaded to Claude Files API
   - File ID stored with document

2. **Streaming with Citations**:
   - Document blocks sent with `citations: {"enabled": true}`
   - Claude processes document and generates citations
   - Citations emitted as "citations_delta" events during streaming
   - Frontend collects citations in pendingCitations Map
   - On message completion, citations are added to CitationContext

3. **Citation Display**:
   - MessageRenderer converts [1], [2] markers to clickable elements
   - Clicking navigates to PDF location with highlighting

## Testing Steps

1. Upload a PDF document
2. Ask a specific question about the document content (e.g., "What are the revenue figures for Q3 2023?")
3. Watch the browser console for:
   - "citations_delta" events
   - Citation data being collected
4. Check if citations appear as [1], [2] in the response
5. Click citations to verify PDF navigation and highlighting

## Debugging

If citations still don't appear:

1. Check browser console for:
   ```
   Event: citations_delta
   Citation received: ...
   ```

2. Check backend logs for:
   ```
   Found citation in streaming response: ...
   Found citation delta during streaming: ...
   ```

3. Verify document has a valid claude_file_id
4. Ensure the question specifically asks for information that would require citations

## Next Steps

1. Test with actual financial PDFs
2. Monitor for citation events in browser and backend logs
3. Verify citation navigation and highlighting work correctly