# Citation System Upgrade Plan

## Overview
This document outlines the gaps and issues identified in the current citation system after comprehensive flow mapping, along with recommended solutions and implementation priorities.

## 1. Timing and Synchronization Issues

### Current Issues
- Frontend waits only 1 second before fetching citations (`setTimeout(..., 1000)`)
- If backend citation processing + rect computation takes longer, frontend might get incomplete citations
- No retry mechanism if citations aren't ready
- No way to know if citations are still being processed

### Proposed Solutions

#### 1.1 Implement Polling with Exponential Backoff
```typescript
const fetchCitationsWithRetry = async (
  messageId: string, 
  maxRetries = 5,
  initialDelay = 500
) => {
  let delay = initialDelay;
  
  for (let i = 0; i < maxRetries; i++) {
    const message = await conversationsApi.getMessage(messageId);
    
    // Check if citations are ready (all have rects)
    const pendingCitations = message.citations?.filter(c => !c.rects?.length) || [];
    if (pendingCitations.length === 0) {
      return message.citations;
    }
    
    // Wait with exponential backoff
    await new Promise(resolve => setTimeout(resolve, delay));
    delay *= 2; // Double the delay each time
  }
  
  // Return what we have after max retries
  return message.citations || [];
};
```

#### 1.2 Add Citation Processing Status to API
```python
# Add to message response
{
  "citations_status": "processing" | "ready" | "partial",
  "citations_ready_count": 5,
  "citations_total_count": 7
}
```

**Priority**: HIGH
**Effort**: Medium
**Impact**: Prevents missing citations due to timing issues

## 2. Error Handling and Visibility

### Current Issues
- Silent failures when rect finding fails
- Citations without rects are completely hidden
- No user feedback for processing failures
- No fallback display for citations without highlights

### Proposed Solutions

#### 2.1 Add Citation Status Tracking
```typescript
interface Citation {
  id: string;
  status: 'pending' | 'processing' | 'ready' | 'failed';
  errorMessage?: string;
  errorCode?: 'RECT_NOT_FOUND' | 'PDF_PARSE_ERROR' | 'INVALID_SEARCH_TEXT';
  // ... existing fields
}
```

#### 2.2 Show Citations Without Highlights
```typescript
// In CitationLink component
const CitationLink: React.FC<{citation: Citation, number: number}> = ({citation, number}) => {
  const hasHighlight = citation.rects && citation.rects.length > 0;
  
  return (
    <span 
      className={cn(
        "citation-link",
        !hasHighlight && "citation-no-highlight"
      )}
      onClick={() => handleCitationClick(citation)}
      title={!hasHighlight ? "Citation location not found in PDF" : citation.displayText}
    >
      [{number}]
      {!hasHighlight && <WarningIcon className="ml-1 h-3 w-3" />}
    </span>
  );
};
```

#### 2.3 Add Toast Notifications
```typescript
// When citations fail to load
toast.warning(`${failedCount} citations could not be highlighted in the PDF`);
```

**Priority**: HIGH
**Effort**: Low
**Impact**: Better user experience and debugging

## 3. Data Consistency and Type Safety

### Current Issues
- Mismatch between backend `text` field and frontend `citedText` expectation
- Optional fields not always checked before use
- No validation of citation data structure

### Proposed Solutions

#### 3.1 Standardize Field Names
```typescript
// Backend: Use consistent field naming
CitationPayload:
  citedText: str  # Primary field for all display purposes
  displayText: Optional[str]  # Enhanced display version
  searchableText: Optional[str]  # PDF search text
  
// Remove duplicate 'text' field to avoid confusion
```

#### 3.2 Add Runtime Validation
```typescript
import { z } from 'zod';

const CitationSchema = z.object({
  id: z.string(),
  documentId: z.string(),
  citedText: z.string(),
  displayText: z.string().optional(),
  searchableText: z.string().optional(),
  rects: z.array(RectSchema).optional(),
  startPageNumber: z.number(),
  // ... other fields
});

// Validate citations before use
const validateCitation = (data: unknown): Citation => {
  return CitationSchema.parse(data);
};
```

**Priority**: MEDIUM
**Effort**: Low
**Impact**: Prevents runtime errors

## 4. Search Strategy Improvements

### Current Issues
- Hardcoded search strategies only work for financial values
- No feedback when all strategies fail
- No learning from successful patterns

### Proposed Solutions

#### 4.1 Extensible Search Strategy System
```python
class SearchStrategy:
    def generate_variants(self, text: str) -> List[str]:
        raise NotImplementedError

class FinancialValueStrategy(SearchStrategy):
    def generate_variants(self, text: str) -> List[str]:
        variants = [text]
        # Remove currency symbols
        if "$" in text:
            variants.append(text.replace("$", ""))
        # Remove suffixes
        if text[-1] in "MBK":
            variants.append(text[:-1])
        return variants

class PercentageStrategy(SearchStrategy):
    def generate_variants(self, text: str) -> List[str]:
        variants = [text]
        if "%" in text:
            variants.append(text.replace("%", ""))
            variants.append(text.replace("%", " percent"))
        return variants

# Strategy registry
SEARCH_STRATEGIES = [
    FinancialValueStrategy(),
    PercentageStrategy(),
    DateStrategy(),
    GeneralTextStrategy()
]
```

#### 4.2 Learning from Successful Searches
```python
# Store successful search patterns
class CitationSearchLog(Base):
    id = Column(UUID)
    original_text = Column(String)
    successful_variant = Column(String)
    strategy_used = Column(String)
    document_type = Column(String)
    created_at = Column(DateTime)
```

**Priority**: MEDIUM
**Effort**: Medium
**Impact**: Better rect finding success rate

## 5. Performance Optimizations

### Current Issues
- Every citation triggers PDF parsing
- No caching of computed rects
- Synchronous rect computation blocks API response

### Proposed Solutions

#### 5.1 Cache Computed Rects
```python
# Add to Citation model
class Citation(Base):
    # ... existing fields
    computed_rects_hash = Column(String)  # Hash of searchable_text
    computed_at = Column(DateTime)
    rect_cache_valid = Column(Boolean, default=True)
    
    def should_recompute_rects(self):
        # Recompute if no hash or text changed
        current_hash = hashlib.md5(
            (self.searchable_text or self.cited_text).encode()
        ).hexdigest()
        return self.computed_rects_hash != current_hash
```

#### 5.2 Async Rect Computation
```python
# Queue rect computation as background task
async def create_citation(citation_data):
    citation = Citation(**citation_data)
    db.add(citation)
    await db.commit()
    
    # Queue async rect computation
    await rect_computation_queue.put({
        'citation_id': citation.id,
        'document_id': citation.document_id,
        'search_text': citation.searchable_text
    })
    
    return citation
```

**Priority**: MEDIUM
**Effort**: High
**Impact**: Faster API responses, better scalability

## 6. Enhanced User Experience Features

### Current Issues
- No citation preview on hover
- No indication of what's being cited without clicking
- Poor mobile experience

### Proposed Solutions

#### 6.1 Citation Preview Tooltips
```typescript
const CitationTooltip: React.FC<{citation: Citation}> = ({citation}) => {
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger>[{citation.number}]</TooltipTrigger>
        <TooltipContent className="max-w-sm">
          <div className="space-y-1">
            <p className="font-semibold">{citation.documentTitle}</p>
            <p className="text-sm">{citation.displayText || citation.citedText}</p>
            <p className="text-xs text-muted">Page {citation.startPageNumber}</p>
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
};
```

#### 6.2 Citation Summary Panel
```typescript
const CitationSummaryPanel: React.FC<{message: Message}> = ({message}) => {
  const citations = message.citations || [];
  
  return (
    <Collapsible>
      <CollapsibleTrigger>
        View {citations.length} citations
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="space-y-2">
          {citations.map((citation, idx) => (
            <CitationCard 
              key={citation.id}
              citation={citation}
              number={idx + 1}
            />
          ))}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
};
```

**Priority**: LOW
**Effort**: Low
**Impact**: Better user experience

## 7. Multi-Document Support

### Current Issues
- Citation processor assumes single document context
- Document ID mapping unreliable with multiple documents
- No visual distinction between documents

### Proposed Solutions

#### 7.1 Enhanced Document Context
```python
# Pass document context to citation processor
def process_citation_for_granularity(citation, document_context):
    # document_context includes:
    # - all_documents: List of documents in conversation
    # - primary_document_id: Main document being discussed
    # - document_types: Map of doc_id to type
```

#### 7.2 Document-Specific Citation Styling
```typescript
// Color-code citations by document
const getDocumentColor = (documentId: string, documents: Document[]) => {
  const colors = ['blue', 'green', 'purple', 'orange'];
  const index = documents.findIndex(d => d.id === documentId);
  return colors[index % colors.length];
};
```

**Priority**: LOW
**Effort**: Medium
**Impact**: Better multi-document workflows

## 8. Robustness and Edge Cases

### Current Issues
- No handling of cross-page citations
- Dynamic PDF content breaks cached rects
- Large citations timeout during processing

### Proposed Solutions

#### 8.1 Multi-Page Citation Support
```python
def find_multipage_citation(pdf_path, text, start_page, end_page):
    all_rects = []
    for page_num in range(start_page, end_page + 1):
        page_rects = find_rects_for_text(pdf_path, text, [page_num])
        all_rects.extend(page_rects)
    return merge_adjacent_rects(all_rects)
```

#### 8.2 PDF Change Detection
```python
class Document(Base):
    # ... existing fields
    pdf_checksum = Column(String)
    last_rect_validation = Column(DateTime)
    
    def has_pdf_changed(self):
        current_checksum = compute_file_checksum(self.file_path)
        return current_checksum != self.pdf_checksum
```

**Priority**: LOW
**Effort**: High
**Impact**: Handles edge cases

## Implementation Roadmap

### Phase 1: Critical Fixes (Week 1-2)
1. Implement retry logic for citation fetching
2. Add error visibility and fallback displays
3. Standardize field naming

### Phase 2: Performance (Week 3-4)
1. Add rect caching
2. Implement async processing
3. Optimize search strategies

### Phase 3: User Experience (Week 5-6)
1. Add citation previews
2. Implement citation summary panel
3. Enhance mobile experience

### Phase 4: Advanced Features (Week 7-8)
1. Multi-document support
2. Edge case handling
3. Learning search strategies

## Success Metrics

1. **Reliability**: >95% of citations successfully highlighted
2. **Performance**: <2s average citation processing time
3. **User Satisfaction**: <5% citation-related support tickets
4. **Error Rate**: <1% silent failures

## Testing Strategy

1. **Unit Tests**: Each search strategy tested independently
2. **Integration Tests**: Full citation flow with various document types
3. **Performance Tests**: Load testing with 100+ citations
4. **E2E Tests**: User flows including citation clicking and highlighting

## Conclusion

This upgrade plan addresses the major gaps in the current citation system while maintaining backward compatibility. Implementation should be phased to deliver value quickly while building toward a more robust long-term solution.