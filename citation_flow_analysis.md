# Complete Citation Flow Analysis

## Overview
This document provides a comprehensive analysis of the citation flow from backend to frontend, identifying all connection points and issues.

## Backend Citation Flow

### 1. Citation Generation (Claude API)
**Location**: `/backend/pdf_processing/api_service.py`

During streaming (`_process_streaming_response`):
```python
# When Claude sends a citation during streaming
elif hasattr(chunk.delta, 'type') and chunk.delta.type == "citation_delta":
    citation_data = {
        "type": getattr(citation, 'type', 'page_location'),
        "cited_text": getattr(citation, 'cited_text', ''),
        "document_index": getattr(citation, 'document_index', 0),
        "document_title": getattr(citation, 'document_title', ''),
        "start_page_number": getattr(citation, 'start_page_number', None),
        # ... other fields
    }
    citations.append(citation_data)
    
    # Emit citation event for frontend
    if emit_callback:
        await emit_callback({
            "type": "citations_delta",
            "citation": citation_data,
            "block_index": chunk.index if hasattr(chunk, 'index') else 0,
            "message_id": message_id
        })
```

**Issues**:
- Uses `document_index` (integer) instead of `document_id` (UUID)
- Field names are in snake_case
- No `id` or `highlightId` generated at this stage

### 2. Citation Storage
**Location**: `/backend/services/conversation_service.py`

After streaming completes:
```python
# Store citations in database
if citations and message_id:
    for idx, citation_data in enumerate(citations):
        citation_id = str(uuid.uuid4())
        document_index = citation_data.get('document_index', 0)
        
        # Get document_id from document_blocks
        document_id = None
        if document_blocks and document_index < len(document_blocks):
            doc_block = document_blocks[document_index]
            if doc_block.get('type') == 'document' and 'document_id' in doc_block:
                document_id = doc_block['document_id']
        
        if document_id:
            await self.document_repository.create_citation_with_message(
                citation_id=citation_id,
                message_id=message_id,
                document_id=document_id,
                citation_data=citation_data,
                position=idx
            )
```

**Storage Format** (SQLAlchemy model):
```python
class Citation(Base):
    id = Column(String, primary_key=True)
    document_id = Column(String, ForeignKey("documents.id"))
    type = Column(String(50))  # 'page_location', 'char_location', 'content_block_location'
    cited_text = Column(Text)
    document_title = Column(String(255))
    start_page_number = Column(Integer)
    end_page_number = Column(Integer)
    # ... other fields
```

### 3. Citation Retrieval
**Location**: `/backend/app/routes/conversation.py`

When fetching conversation history:
```python
# Get citations for each message
citations = await conversation_service.conversation_repository.get_message_citations(msg.id)

for citation in citations:
    # Get document for title
    document = await conversation_service.document_repository.get_document(citation.document_id)
    doc_title = document.filename if document else "Unknown Document"
    
    # Create appropriate citation type based on citation.type
    if citation_type == 'page_location':
        citation_obj = PageLocationCitation(
            type=CitationType.PAGE_LOCATION,
            cited_text=citation.cited_text or "",
            document_index=0,  # TODO: Get proper document index
            document_title=doc_title,
            start_page_number=citation.start_page_number or 1,
            end_page_number=citation.end_page_number or 1,
            highlight_id=citation.highlight_id or citation.id,
            rects=[]  # TODO: Parse rects from citation.rects
        )
```

**Issues**:
- Hardcoded `document_index=0` (should be dynamic)
- Empty `rects=[]` array (no bounding box data)
- Citation types must match the union type expected by Message model

## Frontend Citation Flow

### 1. Citation Reception During Streaming
**Location**: `/src/hooks/useStreamingChatWithCitations.ts`

```typescript
case 'citations_delta':
  if (event.citation && event.block_index !== undefined) {
    handleStreamingCitation(
      { type: 'citations_delta', citation: event.citation },
      event.block_index,
      pendingCitations,
      documentMap
    );
  }
  break;
```

### 2. Citation Processing
**Location**: `/src/lib/pdf/citationService.ts`

```typescript
export const handleStreamingCitation = (
  delta: { type: 'citations_delta'; citation: ClaudeCitation },
  currentBlockIndex: number,
  pendingCitations: Map<number, Citation[]>,
  documentMap: Map<number, string>
): void => {
  const documentId = documentMap.get(delta.citation.document_index);
  
  const newCitation: Citation = {
    id: `cite-${Date.now()}-${Math.random()}`,
    highlightId: `hl-${Date.now()}-${Math.random()}`,
    documentId,
    documentTitle: delta.citation.document_title,
    type: delta.citation.type as Citation['type'],
    citedText: delta.citation.cited_text,  // Snake case!
    rects: [],
    startPageNumber: delta.citation.start_page_number,  // Snake case!
    // ... other fields with snake_case
  };
```

**Issues**:
- Frontend generates temporary IDs (not consistent with backend)
- Field names remain in snake_case (not transformed to camelCase)
- Empty `rects` array (no highlight coordinates)

### 3. Citation Storage
**Location**: `/src/context/CitationContext.tsx`

On message completion:
```typescript
// In useStreamingChatWithCitations
case 'message_complete':
  const allCitations: Citation[] = [];
  pendingCitations.forEach(citations => {
    allCitations.push(...citations);
  });
  
  if (allCitations.length > 0) {
    addCitations(allCitations);  // Add to context
  }
```

### 4. Citation Display
**Location**: `/src/components/chat/MessageRenderer.tsx`

```typescript
// Look for citation markers [1], [2], etc.
const citationPattern = /\[(\d+)\]/g;

while ((match = citationPattern.exec(content)) !== null) {
  const citationIndex = parseInt(match[1], 10) - 1;
  
  if (citations[citationIndex]) {
    const citation = citations[citationIndex];
    parts.push(
      <button
        key={`cite-${citation.id}`}
        className="citation-link..."
        onClick={() => onCitationClick?.(citation)}
      >
        <sup className="font-medium">{citationIndex + 1}</sup>
      </button>
    );
  }
}
```

## Key Disconnects

### 1. Field Name Mismatch
- **Backend sends**: snake_case (`cited_text`, `start_page_number`)
- **Frontend expects**: camelCase (`citedText`, `startPageNumber`)
- **Impact**: Citations have undefined fields in the UI

### 2. Document Reference Mismatch
- **Backend sends**: `document_index` (integer)
- **Frontend expects**: `documentId` (UUID string)
- **Current workaround**: `documentMap` converts index to ID, but this is fragile

### 3. Missing Data
- **Rects/Bounding Boxes**: Backend doesn't send highlight coordinates
- **IDs**: Frontend generates temporary IDs that don't match backend

### 4. Type System Issues
- Backend must create specialized citation types (PageLocationCitation, etc.)
- Frontend expects simpler Citation interface
- Mismatch causes validation errors

## Recommended Fixes

### 1. Backend Changes
```python
# In api_service.py, transform citation data before emitting
citation_event = {
    "type": "citations_delta",
    "citation": {
        "id": str(uuid.uuid4()),
        "highlightId": str(uuid.uuid4()),
        "documentId": document_id,  # Not document_index
        "documentTitle": citation.document_title,
        "type": citation.type,
        "citedText": citation.cited_text,  # Transform to camelCase
        "startPageNumber": citation.start_page_number,
        # ... transform all fields to camelCase
    },
    "block_index": block_index,
    "message_id": message_id
}
```

### 2. Frontend Changes
```typescript
// Add field transformation if backend can't change
const transformCitation = (claudeCitation: ClaudeCitation): Citation => {
  return {
    id: claudeCitation.id || `cite-${Date.now()}`,
    highlightId: claudeCitation.highlightId || `hl-${Date.now()}`,
    documentId: claudeCitation.documentId || documentMap.get(claudeCitation.document_index),
    documentTitle: claudeCitation.document_title,
    type: claudeCitation.type as Citation['type'],
    citedText: claudeCitation.cited_text || claudeCitation.citedText,
    startPageNumber: claudeCitation.start_page_number || claudeCitation.startPageNumber,
    // ... handle both snake_case and camelCase
  };
};
```

### 3. API Response Changes
```python
# In conversation.py, ensure consistent format
citation_dict = {
    "id": citation.id,
    "highlightId": citation.highlight_id or citation.id,
    "documentId": citation.document_id,
    "documentTitle": doc_title,
    "type": citation.type,
    "citedText": citation.cited_text,
    "startPageNumber": citation.start_page_number,
    # ... use camelCase for API responses
}
```

## Actions Taken to Fix Citation Flow

### 1. Backend API Fix (`/backend/app/routes/conversation.py`)
**Problem**: Message model validation errors - expected specialized citation types but received simple Citation objects

**Solution**: Updated to create proper citation type objects based on stored type:
```python
# Changed from simple Citation to specialized types
if citation_type == 'page_location' or citation_type == CitationType.PAGE_LOCATION:
    citation_obj = PageLocationCitation(
        type=CitationType.PAGE_LOCATION,
        cited_text=citation.cited_text or citation.text or "",
        document_index=0,  # TODO: Get proper document index
        document_title=doc_title,
        start_page_number=citation.start_page_number or citation.page or 1,
        end_page_number=citation.end_page_number or citation.start_page_number or citation.page or 1,
        highlight_id=citation.highlight_id or citation.id,
        rects=[]
    )
elif citation_type == 'char_location':
    # Similar for CharLocationCitation
else:
    # Similar for ContentBlockLocationCitation
```

### 2. Frontend Citation Transformation (`/src/lib/pdf/citationTransform.ts`)
**Problem**: Field name mismatch between backend (snake_case) and frontend (camelCase)

**Solution**: Created transformation utilities:
```typescript
export const transformClaudeCitation = (
  claudeCitation: ClaudeCitation,
  documentMap: Map<number, string>,
  citationIndex?: number
): Citation => {
  // Handle document ID conversion
  const documentId = (claudeCitation as any).documentId || 
    documentMap.get(claudeCitation.document_index) || '';
    
  return {
    id: (claudeCitation as any).id || `cite-${Date.now()}-${citationIndex}`,
    highlightId: (claudeCitation as any).highlightId || `hl-${Date.now()}-${citationIndex}`,
    documentId,
    documentTitle: claudeCitation.document_title || '',
    type: (claudeCitation.type || 'page_location') as Citation['type'],
    // Handle both snake_case and camelCase
    citedText: claudeCitation.cited_text || (claudeCitation as any).citedText || '',
    startPageNumber: claudeCitation.start_page_number || 
      (claudeCitation as any).startPageNumber || undefined,
    // ... other fields with fallbacks
  };
};
```

### 3. Updated Citation Service (`/src/lib/pdf/citationService.ts`)
**Problem**: Citations not properly transformed during streaming

**Solution**: Updated to use transformation function:
```typescript
export const handleStreamingCitation = (
  delta: { type: 'citations_delta'; citation: ClaudeCitation },
  currentBlockIndex: number,
  pendingCitations: Map<number, Citation[]>,
  documentMap: Map<number, string>
): void => {
  const { transformClaudeCitation } = require('./citationTransform');
  const citations = pendingCitations.get(currentBlockIndex) || [];
  
  // Transform citation with proper field mapping
  const newCitation = transformClaudeCitation(
    delta.citation, 
    documentMap,
    citations.length
  );
  
  if (!newCitation.documentId) {
    console.warn(`No document found for citation:`, delta.citation);
    return;
  }
  
  // ... deduplication and storage
};
```

### 4. API Response Processing (`/src/lib/api/conversations.ts`)
**Problem**: Citations from API not transformed to frontend format

**Solution**: Added transformation when fetching conversation history:
```typescript
async getConversationHistory(sessionId: string, limit: number = 50): Promise<Message[]> {
  try {
    const response = await apiService.get<any[]>(
      `/api/conversation/${sessionId}/history?limit=${limit}`
    );
    
    // Import and apply citation transformation
    const { transformCitations } = await import('@/lib/pdf/citationTransform');
    
    return response.map(msg => ({
      // ... other fields
      citations: transformCitations(msg.citations || []),
      // ... rest of mapping
    }));
  } catch (error) {
    console.error('Error getting conversation history:', error);
    return [];
  }
}
```

## Results

### ✅ Fixed
1. **API Validation Errors**: Backend now creates proper citation type objects
2. **Field Name Mismatches**: Frontend handles both snake_case and camelCase
3. **Document Reference Issues**: documentMap properly converts indices to IDs
4. **Build Errors**: All TypeScript errors resolved

### ⚠️ Still Needs Work
1. **Visualization Rendering**: Analysis blocks stored but not displayed
   - Backend stores 4 analysis blocks in database
   - Repository loads with `selectinload(Message.analysis_blocks)`
   - API endpoint converts to dict format with correct keys
   - **Issue**: Frontend receives 0 analysis blocks
2. **Citation Display**: Citations saved but not showing in UI
   - Backend stores 3 citations successfully
   - Citations linked to message via MessageCitation table
   - Repository loads citations with eager loading
   - **Issue**: Frontend not rendering citation markers [1], [2], [3]
3. **Post-visualization Content**: Not shown as separate message phase
4. **Citation Highlighting**: No bounding box coordinates from backend
5. **Dynamic Document Index**: Currently hardcoded to 0

## Conclusion

The citation system infrastructure is properly connected with fixes for:
- Type validation issues  
- Field naming inconsistencies
- Document reference mapping
- API response processing

**Current Status (Based on Latest Test Logs):**
1. **Backend Processing**: ✅ Working
   - Citations generated and stored in database
   - Analysis blocks created and stored
   - Proper relationships established

2. **Data Retrieval**: ❓ Unclear
   - Repository has eager loading configured
   - API endpoint transforms data correctly
   - Need to verify actual response payload

3. **Frontend Rendering**: ❌ Not Working
   - Citations not appearing as [1], [2], [3] markers
   - Analysis blocks not being rendered
   - Canvas component logs "0 analysis blocks"

**Next Debugging Steps:**
1. Add logging to conversation history endpoint to verify response payload
2. Check network tab to see actual API response structure
3. Verify frontend is correctly accessing nested properties
4. Check if citations are in response but not being processed by MessageRenderer

## Latest Investigation Findings (2025-06-29)

### Key Issues from Test Logs

1. **Frontend Logs Show:**
   ```
   [Log] Fetched updated message with 0 analysis blocks
   [Log] No structured visualization data found in messages or analysis results
   ```

2. **Backend Logs Show:**
   ```
   INFO:services.conversation_service:ATOMIC: Transaction complete - message has 4 analysis blocks
   INFO:services.conversation_service:Storing 3 citations for message
   ```

3. **API Route Issue:**
   - Frontend calls: `GET /api/conversation/{id}/history`
   - Backend route: `@router.get("/{conversation_id}/history")`
   - The `/api` prefix suggests there might be a base path configuration

### Root Cause Analysis

The data is being saved correctly in the backend but not reaching the frontend. Issues found:

1. **Frontend Property Mapping**: Fixed - The frontend was not checking for camelCase `analysisBlocks`
2. **Citation Markers Missing**: The backend saves citations but doesn't add [1], [2] markers to the message content
3. **MessageRenderer Logic**: Expects citation markers in content to render clickable citations
4. **API Response**: Need to verify if backend is sending camelCase or snake_case

### Fixes Applied

1. **Updated conversations.ts** to check both snake_case and camelCase:
   ```typescript
   analysis_blocks: msg.analysis_blocks || msg.analysisBlocks || []
   citations: transformCitations(msg.citations || [])
   ```

2. **Added debug logging** to verify response structure

### Remaining Issues

1. **Backend needs to add citation markers**: When storing message content, the backend should:
   - Add [1], [2], [3] markers where citations occur
   - Match the citation index to the stored citations array
   
2. **Alternative approach**: Frontend could inject citation markers based on citation positions if backend provides text positions