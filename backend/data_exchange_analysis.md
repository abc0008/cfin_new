# Data Exchange Analysis Report: Frontend-Backend API

## Executive Summary
This report provides a comprehensive analysis of the data exchange between the NextJS frontend and FastAPI backend, focusing on API endpoints, data models, and potential mismatches.

## 1. API Endpoints Overview

### Backend Routes (FastAPI)
- **Documents**: `/api/documents/*`
- **Conversations**: `/api/conversation/*`
- **Analysis**: `/api/analysis/*`

### Frontend API Calls
- Using `apiService` wrapper for all HTTP requests
- Base URL: `http://localhost:8000`
- Consistent error handling across all services

## 2. Data Model Comparison

### 2.1 Document Models

#### Backend (Pydantic)
```python
class DocumentUploadResponse(BaseModel):
    document_id: UUID4
    filename: str
    status: ProcessingStatus
    message: str
    contentType: str  # camelCase in response
    fileSize: int     # camelCase in response
```

#### Frontend (TypeScript/Zod)
```typescript
interface DocumentUploadResponse {
  document_id: string;  // Backend uses snake_case
  filename: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  message: string;
  contentType: string;  // Frontend expects camelCase
  fileSize: number;
}
```

**Issues Found:**
- Backend model doesn't use camelCase aliasing for `contentType` and `fileSize`
- Frontend expects these fields in camelCase but backend sends them without alias

### 2.2 Analysis Models

#### Backend (Pydantic)
```python
class AnalysisApiResponse(BaseModel):
    id: str
    document_ids: List[str] = Field(alias="documentIds")
    analysis_type: str = Field(alias="analysisType")
    timestamp: str
    analysis_text: Optional[str] = Field(alias="analysisText")
    visualization_data: VisualizationDataResponse = Field(alias="visualizationData")
    # ... other fields with proper aliases
```

#### Frontend (TypeScript)
```typescript
interface AnalysisResult {
  id: string;
  documentIds: string[];
  analysisType: string;
  timestamp: string;
  analysisText?: string;
  visualizationData: Record<string, any>;
  // ... matching fields
}
```

**Status:** ✅ Properly aligned with camelCase aliases

### 2.3 Message/Conversation Models

#### Backend (Pydantic)
```python
class MessageResponse(BaseModel):
    id: str
    session_id: str = Field(validation_alias=AliasChoices('session_id', 'conversation_id'))
    timestamp: datetime = Field(validation_alias=AliasChoices('timestamp', 'created_at'))
    role: MessageRole
    content: str
    # ... other fields
```

#### Frontend (TypeScript)
```typescript
interface Message {
  id: string;
  sessionId: string;  // Frontend uses camelCase
  timestamp: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  // ... other fields
}
```

**Issues Found:**
- Backend sends `session_id` but frontend expects `sessionId`
- Backend MessageResponse doesn't use camelCase alias generator

### 2.4 Visualization Models

#### Backend (Pydantic)
```python
class ChartData(BaseModel):
    chart_type: str = Field(alias="chartType")
    config: ChartConfig
    data: Union[List[ChartDataItem], List[PydanticMultiSeriesChartDataItem]]
    chart_config: Dict[str, Any] = Field(alias="chartConfig")
    
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        validate_assignment=True
    )
```

**Status:** ✅ Properly configured with camelCase aliases

## 3. Critical Issues Identified

### 3.1 Inconsistent Aliasing
1. **DocumentUploadResponse**: Missing camelCase aliases for `contentType` and `fileSize`
2. **MessageResponse**: Not using consistent camelCase aliasing
3. **Citation models**: Some fields may have naming mismatches

### 3.2 Type Mismatches
1. **UUID handling**: Backend uses `UUID4` type, frontend expects `string`
2. **Datetime handling**: Backend uses `datetime`, frontend expects ISO strings
3. **Optional fields**: Some optional fields in backend are required in frontend

### 3.3 API Request/Response Format Issues

#### Document Upload
- Frontend sends FormData with file
- Backend expects specific field names in snake_case
- Response format mismatch for some fields

#### Conversation Messages
- Frontend sends `session_id` in snake_case (correctly)
- But expects response in camelCase
- Backend response doesn't properly convert all fields

## 4. Recommendations

### 4.1 Immediate Fixes Required

1. **Update DocumentUploadResponse** in backend:
```python
class DocumentUploadResponse(BaseModel):
    document_id: UUID4
    filename: str
    status: ProcessingStatus
    message: str
    content_type: str = Field(alias="contentType")
    file_size: int = Field(alias="fileSize")
    
    class Config:
        alias_generator = to_camel
        allow_population_by_field_name = True
```

2. **Update MessageResponse** to use consistent aliasing:
```python
class MessageResponse(BaseModel):
    # ... existing fields
    
    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "alias_generator": to_camel  # Add this
    }
```

3. **Standardize Citation models** across frontend and backend

### 4.2 Best Practices

1. **Use Pydantic's `alias_generator`** consistently across all API response models
2. **Document field mappings** between snake_case (Python) and camelCase (JavaScript)
3. **Add integration tests** to validate API contracts
4. **Use shared schemas** or code generation to ensure consistency

### 4.3 Testing Strategy

1. Create API contract tests that validate:
   - Field names match expected format
   - Required/optional fields align
   - Data types are compatible
   - Nested structures are properly formatted

2. Add request/response logging to identify mismatches in production

## 5. Action Items

1. **High Priority:**
   - Fix DocumentUploadResponse aliasing
   - Fix MessageResponse aliasing
   - Add missing aliases to Citation-related models

2. **Medium Priority:**
   - Audit all Pydantic models for consistent aliasing
   - Update frontend types to handle backend response variations
   - Add comprehensive API tests

3. **Low Priority:**
   - Consider using OpenAPI schema generation
   - Implement shared type definitions
   - Add response transformation middleware

## 6. Validation Checklist

- [ ] All Pydantic models use `alias_generator = to_camel`
- [ ] All Field definitions with snake_case names have camelCase aliases
- [ ] Frontend Zod schemas match backend Pydantic models
- [ ] API integration tests pass for all endpoints
- [ ] Response transformation handles edge cases