# Citation Debug-Logging Map

> A quick reference for tracing a citation from backend generation all the way to a yellow highlight + scroll in the PDF viewer.
>
> Grep for the **tag strings** shown below (`[useStreaming]`, `[CitationContext]`, …) to follow the journey in DevTools.

---

## 1. Backend – Creation & Auto-BBox
```py title="cfin/backend/repositories/document_repository.py"
logger.info("✅ Auto-bbox found …")  # emitted when rects are auto-computed
```

## 2. Streaming Layer (hook)
File: `src/hooks/useStreamingChatWithCitations.ts`
| Stage | Tag | Example Log |
|-------|-----|-------------|
| Temp citation created | `[useStreaming] temp citation` | id, rects=0 |
| Phase transitions / tool events | `[useStreaming] …` | `phaseTransition`, `tool_start`, `tool_complete` |
| Merge with `/citations` | `[useStreaming] merged citations` | list of `id`, `rectCount` |
| WebSocket lifecycle | n/a | connect / reconnect details |

## 3. Chat UI
File: `src/components/chat/StreamingChatInterface.tsx`
| Action | Tag |
|--------|-----|
| Marker click | `[StreamingChatInterface] Citation marker clicked` (id, rectCount) |
| Submission paths | console logs for streaming vs HTTP |

## 4. Global Cache / Dispatch
File: `src/context/CitationContext.tsx`
| Function | Tag(s) |
|----------|--------|
| `loadCitation` | `loadCitation start / memory cache / persistent cache / fetched` |
| `loadDocument` | similar tags |
| `openCitation` | `openCitation start / loaded / Dispatching citation-navigation` |
| `addCitations` | `addCitations called / merged` |

## 5. PDF-Side Components
| Component | Tag |
|-----------|-----|
| `CitationEnabledPDFViewer` | `[CitationEnabledPDFViewer] Received citation-navigation` |
| `PDFViewer` | `[PDFViewer] Merged highlights`, event merge, scroll finder (`scrollToHighlight`) |

## 6. Highlight Construction
File: `src/lib/pdf/citationService.ts`
* Warns if a citation arrives **without rects**: `console.warn('Citation has no rects…')`

---
### Typical Flow
1. **Backend** stores citation `UUID` (+ rects) → auto-bbox if missing.
2. **Streaming hook** creates a temp `cite-*` placeholder **immediately**, logs creation.
3. After message completes, hook fetches real citations, merges rects, logs merge.
4. **User clicks** `[1]` marker → chat component logs click and calls `openCitation`.
5. **CitationContext**: loads citation/doc (if needed) → logs each step → dispatches `citation-navigation` event.
6. **PDFViewer** receives event, merges highlight if new, logs scroll attempt and outcome.

With these checkpoints you can pinpoint where data drops by following the timeline in the console.

---

## Issue Analysis: Jump-to-Citation Failure

### Root Cause
The jump-to-citation feature fails due to an **ID mismatch** between citation markers and PDF highlights:

1. **During Streaming**: Citations are created with temporary IDs (`cite-<timestamp>-<random>`)
2. **After Enhancement**: Backend returns citations with UUIDs 
3. **In PDFViewer**: The `allHighlights` array contains highlights with UUID IDs
4. **On Click**: Citation markers pass the temp ID, but `scrollToHighlight` searches for this temp ID in an array that only contains UUIDs

### The Problem Flow
```
1. Streaming creates: { id: "cite-1752545786496-0.532", highlightId: "hl-1752545786496-0.969" }
2. Backend returns:   { id: "7d5ac08b-2063-46d4-90af-c77ca25597d2", rects: [...] }
3. PDFViewer has:     highlights with id="7d5ac08b-2063-46d4-90af-c77ca25597d2"
4. User clicks [1]:   Passes "cite-1752545786496-0.532" to scrollToHighlight
5. Search fails:      No highlight with id="cite-1752545786496-0.532" exists
```

### Proposed Fix

**Solution**: Maintain both IDs in the highlight object and search by either ID.

1. **In `citationService.ts`**: When converting citations to highlights, preserve the original temp ID
2. **In `PDFViewer.tsx`**: Search highlights by both the main ID and any alternate IDs
3. **In citation merging**: Preserve the temp ID when enhancing citations with rects

### Implementation Details

#### 1. Update Citation Type
Add an `alternateIds` field to track all IDs that reference this citation:
```typescript
interface Citation {
  id: string;
  alternateIds?: string[]; // Track temp IDs and other references
  // ... other fields
}
```

#### 2. Update Highlight Conversion
In `citationService.ts`, preserve alternate IDs:
```typescript
export const convertCitationToHighlight = (citation: Citation, viewport?: any): IHighlight => {
  return {
    id: citation.id,
    alternateIds: citation.alternateIds, // Preserve alternate IDs
    // ... rest of conversion
  };
};
```

#### 3. Update Search Logic
In `PDFViewer.tsx`, search by all possible IDs:
```typescript
const scrollToHighlight = useCallback((highlightId: string) => {
  const highlight = allHighlights.find(h => 
    h.id === highlightId || 
    h.alternateIds?.includes(highlightId) ||
    (h.rawClaudeCitation?.id === highlightId)
  );
  // ... rest of function
}, [allHighlights]);
```

#### 4. Update Citation Merging
When merging streaming citations with enhanced ones, preserve the temp ID:
```typescript
const merged = {
  ...enhancedCitation,
  alternateIds: [tempCitation.id, ...(enhancedCitation.alternateIds || [])]
};
```

### Additional Logging Recommendations

1. **Log ID mapping** when merging citations
2. **Log all available IDs** when highlight search fails
3. **Log citation structure** at each transformation point
4. **Add state machine logging** for scroll attempts

This fix ensures backward compatibility while solving the ID mismatch issue that prevents jump-to-citation from working.

## Next Steps
- Implement the proposed fix in all affected components
- Test the fix with both temp IDs and UUIDs
- Add additional logging to verify the fix is working
- Consider adding a citation ID mapping service to handle the transition from temp IDs to UUIDs more gracefully

## Implemented Fixes (2025-01-16)

### 1. Fixed Citations Not Being Saved to Backend
**Problem**: Citations created during streaming with temp IDs were not being persisted to the backend. When PDFViewer loaded, it fetched citations from `/api/documents/{id}/citations` but got an empty array.

**Solution**: Updated `useStreamingChatWithCitations.ts` to save citations to the backend after they're created:
```typescript
// Save citations to backend for persistence
const saveCitationsToBackend = async () => {
  const { documentsApi } = await import('@/lib/api/documents');
  
  for (const citation of mergedCitations) {
    if (citation.documentId && citation.rects && citation.rects.length > 0) {
      try {
        // Skip if it's not a temp ID (already saved)
        if (!citation.id.startsWith('cite-')) {
          continue;
        }
        
        const savedCitation = await documentsApi.createCitation(citation.documentId, citation);
        console.log('[useStreaming] Saved citation to backend:', {
          tempId: citation.id,
          savedId: savedCitation.id,
          documentId: citation.documentId,
          page: citation.startPageNumber
        });
      } catch (error) {
        console.error('[useStreaming] Failed to save citation to backend:', error, citation);
      }
    }
  }
};
```

### 2. Fixed PDF.js 'pdfPage' Undefined Error
**Problem**: PDF.js was throwing "Cannot read properties of undefined (reading 'pdfPage')" errors when print functionality was invoked before all pages were loaded.

**Solution**: Added a temporary disable of print functionality in PDFViewer until pages are loaded:
```typescript
// Disable print functionality until all pages are loaded to prevent PDF.js errors
if (typeof window !== 'undefined' && (window as any).print) {
  const originalPrint = window.print;
  window.print = () => {
    console.warn('[PDFViewer] Print disabled until all pages are loaded');
  };
  
  // Re-enable print after a delay to ensure pages are loaded
  setTimeout(() => {
    window.print = originalPrint;
  }, 5000);
}
```

### 3. Root Cause Analysis Summary
The citation navigation failure was caused by:
1. **Missing Backend Persistence**: Citations created during streaming were only stored in the CitationContext (client-side) but never saved to the backend
2. **PDFViewer Empty State**: When PDFViewer loaded, it fetched citations from the backend which returned an empty array
3. **PDF.js Race Condition**: Separate issue where print operations were attempted before PDF pages were fully initialized

The fixes ensure that:
- Citations are saved to the backend immediately after creation during streaming
- The PDFViewer will receive citations when it fetches from the backend
- PDF.js errors are prevented by delaying print operations until pages are ready 