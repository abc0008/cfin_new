# Citation Flow Fixes Summary

## Issues Identified

### 1. **Backend API Error**
- The conversation history endpoint was failing with citation validation errors
- The Message model expected specialized citation types (PageLocationCitation, etc.) but was receiving simple Citation objects
- Fixed by creating proper citation type objects based on the stored citation type

### 2. **Field Name Mismatch**
- Backend sends snake_case fields (cited_text, start_page_number)
- Frontend expects camelCase fields (citedText, startPageNumber)
- Created transformation functions to handle both formats

### 3. **Document Reference Issue**
- Backend sends document_index (integer) during streaming
- Frontend expects documentId (UUID string)
- Used documentMap to convert indices to IDs

### 4. **Missing Citation Display**
- Citations were being saved but not displayed
- API endpoint errors prevented frontend from fetching messages with citations
- Fixed the API endpoint and added citation transformation

## Solutions Implemented

### 1. **Backend Fix** (`/backend/app/routes/conversation.py`)
```python
# Create appropriate citation type based on stored type
if citation_type == 'page_location':
    citation_obj = PageLocationCitation(
        type=CitationType.PAGE_LOCATION,
        cited_text=citation.cited_text or "",
        document_index=0,
        document_title=doc_title,
        start_page_number=citation.start_page_number or 1,
        # ... other fields
    )
```

### 2. **Frontend Transformation** (`/src/lib/pdf/citationTransform.ts`)
```typescript
// Transform citations to handle field name differences
export const transformClaudeCitation = (
  claudeCitation: ClaudeCitation,
  documentMap: Map<number, string>,
  citationIndex?: number
): Citation => {
  // Handle both snake_case and camelCase
  return {
    citedText: claudeCitation.cited_text || claudeCitation.citedText || '',
    startPageNumber: claudeCitation.start_page_number || claudeCitation.startPageNumber,
    // ... other fields
  };
};
```

### 3. **Updated Citation Handling** (`/src/lib/pdf/citationService.ts`)
```typescript
// Use transformation function
const newCitation = transformClaudeCitation(
  delta.citation, 
  documentMap,
  citations.length
);
```

### 4. **API Response Processing** (`/src/lib/api/conversations.ts`)
```typescript
// Transform citations when fetching history
citations: transformCitations(msg.citations || []),
```

## Current Status

### Working ✅
1. Citations are generated during streaming
2. Citations are stored in the database
3. Citations can be fetched via API
4. Field name differences are handled
5. Frontend builds successfully

### Still Needs Work ⚠️
1. **Visualizations not rendering** - Analysis blocks are stored but not displayed
2. **Post-visualization content** - Content after tools is not shown separately
3. **Citation highlighting** - Rects/bounding boxes are not provided by backend
4. **Document index mapping** - Currently hardcoded to 0, should be dynamic

## Next Steps

### 1. Fix Visualization Rendering
- Ensure Canvas component checks for analysis_blocks in messages
- Verify the visualization data format matches frontend expectations

### 2. Fix Post-Tool Content Display
- Separate the three message phases properly
- Show initial analysis → visualizations → post-tool insights

### 3. Add Citation Highlighting
- Backend should calculate and send bounding box coordinates
- Frontend should use these to highlight text in PDFs

### 4. Improve Document Mapping
- Backend should send proper document indices or IDs
- Frontend should maintain consistent document references

## Testing Recommendations

1. **Upload a document** and verify it processes correctly
2. **Ask a question** that triggers analysis with visualizations
3. **Check that**:
   - Citations appear as [1], [2] markers in the text
   - Clicking citations navigates to the PDF (even without highlighting)
   - Visualizations render properly
   - Post-visualization insights appear after the tools

The citation infrastructure is now properly connected from backend to frontend, but visualizations and content phasing still need attention.