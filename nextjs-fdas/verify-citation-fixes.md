# Citation Fix Verification Guide

## Summary of Fixes Implemented

1. **Citation ID Mismatch Fix** ✅
   - Added temp-to-backend ID mapping in PDFViewer
   - Enhanced scrollToHighlight to check mapping before searching
   - Preserved tempId and tempHighlightId when merging citations

2. **Streaming Citation Mapping** ✅
   - Modified useStreamingChatWithCitations to preserve temp IDs during merging
   - Added tempId preservation in citationService.ts
   - Ensured mapping is maintained throughout the citation lifecycle

3. **Highlight Rendering Fix** ✅
   - Updated CitationContext to search for citations by multiple methods
   - Enhanced PDFViewer to handle various ID formats
   - Fixed API URLs to use backend endpoints

## Testing Instructions

### 1. Manual Testing Process

1. **Start the application**:
   ```bash
   # Terminal 1: Backend
   cd cfin/backend
   python run.py
   
   # Terminal 2: Frontend
   cd cfin/nextjs-fdas
   npm run dev
   ```

2. **Upload a PDF document** with financial data

3. **Ask a question** that will generate citations (e.g., "What are the revenue figures?")

4. **Open browser DevTools Console** and paste the test script:
   ```javascript
   // Copy contents from test-citation-mapping.js
   ```

5. **Click on citation markers** in the chat and verify:
   - The PDF scrolls to the correct page
   - The specific text is highlighted (not the entire page)
   - Console shows successful ID mapping

### 2. Expected Behavior

When clicking a citation marker (e.g., [1], [2]):

1. **Immediate Response**: PDF should scroll to the cited page
2. **Precise Highlighting**: Only the cited text should be highlighted, not the entire page
3. **ID Mapping**: Console should show successful temp-to-backend ID resolution

### 3. Console Verification

Run these commands in the browser console:

```javascript
// Check mapping exists
window.citationTempToBackendMap

// Check highlights have rects
window.citationHighlights?.filter(h => h.position.rects.length > 0)

// Test a specific citation click
testCitationClick("cite-XXXXXXXXXX-XXXX") // Use actual ID from chat
```

### 4. Common Issues and Solutions

| Issue | Solution | Verification |
|-------|----------|--------------|
| Citation not found | Check if temp-to-backend mapping exists | `window.citationTempToBackendMap.has(citationId)` |
| Entire page highlighted | Verify citation has rects | Check `citation.rects.length > 0` |
| 404 errors | Ensure backend is running on port 8000 | Check network tab for API calls |

## Implementation Details

### Key Files Modified:

1. **PDFViewer.tsx** (lines 383-432, 201-211)
   - Added `mergeCitations` function with temp-to-backend mapping
   - Enhanced `scrollToHighlight` to use mapping

2. **CitationContext.tsx** (lines 128-169)
   - Added multiple search methods for citations
   - Fixed API URLs to use backend

3. **citationService.ts** (line 97)
   - Added `tempId` preservation in `convertCitationToHighlight`

4. **useStreamingChatWithCitations.ts** (lines 756-770)
   - Preserved temp ID mapping during citation merging

### How the Fix Works:

1. **During Streaming**: Temp citations are created with IDs like `cite-1234567890-abcd`
2. **Backend Processing**: Backend creates citations with UUIDs and proper bounding rectangles
3. **Mapping Creation**: When merging, we map temp IDs to backend IDs
4. **Click Handling**: When a citation is clicked, we check the mapping to find the backend citation with rects
5. **Highlight Rendering**: The backend citation's rects are used to highlight specific text

## Debugging Tips

If citations still aren't working:

1. **Check Network Tab**: Ensure `/api/documents/{id}/citations` returns citations with rects
2. **Verify Mapping**: Run `window.citationTempToBackendMap` to see if mapping exists
3. **Check Citation Data**: Use `window.citationCtx.citations` to inspect citation data
4. **Test Navigation**: Manually dispatch event: 
   ```javascript
   window.dispatchEvent(new CustomEvent('citation-navigation', {
     detail: { citation: window.citationCtx.citations.get('CITATION_ID') }
   }));
   ```

## Success Criteria

✅ Clicking citation markers scrolls to correct page
✅ Only cited text is highlighted (not entire page)
✅ No console errors when clicking citations
✅ Temp-to-backend ID mapping is created and used
✅ Citations work for both streaming and completed messages