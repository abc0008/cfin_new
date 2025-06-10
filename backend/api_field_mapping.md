# API Field Mapping Analysis

## Critical Mismatches Found

### 1. Document Upload Response
**Backend sends:**
```json
{
  "document_id": "uuid-here",
  "filename": "file.pdf",
  "status": "completed",
  "message": "Success",
  "contentType": "application/pdf",  // ❌ Not using snake_case or proper alias
  "fileSize": 1234567                 // ❌ Not using snake_case or proper alias
}
```

**Frontend expects:**
```json
{
  "document_id": "uuid-here",
  "filename": "file.pdf", 
  "status": "completed",
  "message": "Success",
  "contentType": "application/pdf",  // ✅ Expects camelCase
  "fileSize": 1234567                // ✅ Expects camelCase
}
```

### 2. Message Response
**Backend sends:**
```json
{
  "id": "msg-123",
  "session_id": "sess-456",        // ❌ Snake case
  "timestamp": "2024-01-01T00:00:00",
  "role": "assistant",
  "content": "Hello",
  "referenced_documents": [],       // ❌ Snake case
  "referenced_analyses": [],        // ❌ Snake case
  "citation_links": []             // ❌ Snake case
}
```

**Frontend expects:**
```json
{
  "id": "msg-123",
  "sessionId": "sess-456",         // ✅ Camel case
  "timestamp": "2024-01-01T00:00:00",
  "role": "assistant",
  "content": "Hello",
  "referencedDocuments": [],        // ✅ Camel case
  "referencedAnalyses": [],         // ✅ Camel case
  "citationLinks": []              // ✅ Camel case
}
```

### 3. Processed Document
**Backend model fields:**
- `content_type` → should alias to `contentType`
- `extraction_timestamp` → should alias to `extractionTimestamp`
- `extracted_data` → should alias to `extractedData`
- `confidence_score` → should alias to `confidenceScore`
- `processing_status` → should alias to `processingStatus`
- `error_message` → should alias to `errorMessage`

### 4. Document Metadata
**Backend model fields:**
- `upload_timestamp` → should alias to `uploadTimestamp`
- `file_size` → should alias to `fileSize`
- `mime_type` → should alias to `mimeType`
- `user_id` → should alias to `userId`
- `citation_links` → should alias to `citationLinks`

## Frontend Adaptation Patterns

The frontend currently handles some mismatches by:

1. **Document Response Handling:**
```typescript
// In documents.ts
document = {
  ...document,
  processingStatus: response.processingStatus || response.processing_status || document.processingStatus,
  contentType: response.contentType || response.content_type || document.contentType,
  extractedData: response.extractedData || response.extracted_data || document.extractedData,
  // ... checking both formats
};
```

2. **Message Field Mapping:**
```typescript
// Frontend expects sessionId but may receive session_id
session_id: str = Field(validation_alias=AliasChoices('session_id', 'conversation_id'))
```

## Required Backend Fixes

### Priority 1: Document Models
```python
class DocumentUploadResponse(BaseModel):
    document_id: UUID4
    filename: str
    status: ProcessingStatus
    message: str
    content_type: str = Field(alias="contentType")  # Add explicit alias
    file_size: int = Field(alias="fileSize")        # Add explicit alias
    
    class Config:
        alias_generator = to_camel
        populate_by_name = True  # Updated from allow_population_by_field_name

class ProcessedDocument(BaseModel):
    metadata: DocumentMetadata
    content_type: DocumentContentType = Field(default=DocumentContentType.OTHER, alias="contentType")
    extraction_timestamp: datetime = Field(default_factory=datetime.now, alias="extractionTimestamp")
    periods: List[str] = Field(default_factory=list)
    extracted_data: Dict[str, Any] = Field(default_factory=dict, alias="extractedData")
    citations: List[Citation] = Field(default_factory=list)
    confidence_score: float = Field(default=0.0, alias="confidenceScore")
    processing_status: ProcessingStatus = Field(default=ProcessingStatus.PENDING, alias="processingStatus")
    error_message: Optional[str] = Field(default=None, alias="errorMessage")
    
    class Config:
        alias_generator = to_camel
        populate_by_name = True
```

### Priority 2: Message Models
```python
class MessageResponse(BaseModel):
    id: str
    session_id: str = Field(alias="sessionId")
    timestamp: datetime
    role: MessageRole
    content: str
    referenced_documents: List[str] = Field(default_factory=list, alias="referencedDocuments")
    referenced_analyses: List[str] = Field(default_factory=list, alias="referencedAnalyses")
    citation_links: List[str] = Field(default_factory=list, alias="citationLinks")
    citations_data: List[Any] = Field(default_factory=list, alias="citations")
    content_blocks: Optional[List[ContentBlock]] = Field(default=None, alias="contentBlocks")
    analysis_blocks: Optional[List[Dict[str, Any]]] = Field(default=None, alias="analysisBlocks")
    
    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "alias_generator": to_camel  # Add this!
    }
```

## Testing Requirements

1. **Integration Tests Needed:**
   - Document upload flow with field validation
   - Message send/receive with proper field mapping
   - Analysis creation and retrieval
   - Citation handling

2. **Field Mapping Tests:**
   - Verify all snake_case fields have camelCase aliases
   - Confirm frontend receives expected format
   - Test backward compatibility with populate_by_name

3. **Error Case Handling:**
   - Missing fields
   - Extra fields
   - Type mismatches
   - Null/undefined handling