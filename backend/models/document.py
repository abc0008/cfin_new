"""
Document Models Module
===================

This module defines the Pydantic models for documents and citations in the CFIN financial
analysis platform. These models serve as the data transfer objects (DTOs) between the
API layer and the service layer, providing validation and serialization.

Primary responsibilities:
- Define document content types and processing status enums
- Provide schema for citation data with highlighting information
- Define metadata models for documents
- Define the processed document schema for API responses

Key Components:
- DocumentContentType: Enum defining types of financial documents
- ProcessingStatus: Enum defining document processing states
- Citation: Model for document citations with page, text, and highlighting information
- DocumentMetadata: Model for document metadata like filename, size, etc.
- ProcessedDocument: Main model for documents after processing, including extracted data
- DocumentUploadResponse: Model for API responses after document upload

Interactions with other files:
-----------------------------
1. cfin/backend/repositories/document_repository.py:
   - Uses these models for converting database entities to API responses
   - Methods like document_to_api_schema convert to ProcessedDocument

2. cfin/backend/pdf_processing/claude_service.py:
   - Uses ProcessedDocument for structured document data from Claude API
   - Uses Citation model to structure citations from AI responses

3. cfin/backend/pdf_processing/document_service.py:
   - Uses these models to structure document processing results
   - Returns ProcessedDocument from document processing methods

4. cfin/backend/pdf_processing/langgraph_service.py:
   - Uses ProcessedDocument for document state and content management
   - In simple_document_qa for handling document content

5. cfin/backend/app/routes/document.py:
   - Uses these models for API request/response validation
   - DocumentUploadResponse for document upload endpoints

These models define the core data structures for document handling throughout
the application, ensuring consistency between the database, service layer, and API.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid
from pydantic import BaseModel, Field, UUID4


class DocumentContentType(str, Enum):
    BALANCE_SHEET = "balance_sheet"
    INCOME_STATEMENT = "income_statement"
    CASH_FLOW = "cash_flow"
    NOTES = "notes"
    OTHER = "other"


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Citation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    page: int
    text: str
    bounding_box: Optional[Dict[str, float]] = None
    section: Optional[str] = None


class DocumentMetadata(BaseModel):
    id: UUID4 = Field(default_factory=uuid.uuid4)
    filename: str
    upload_timestamp: datetime = Field(default_factory=datetime.now)
    file_size: int
    mime_type: str
    user_id: str
    citation_links: List[str] = Field(default_factory=list)


class ProcessedDocument(BaseModel):
    metadata: DocumentMetadata
    content_type: DocumentContentType = DocumentContentType.OTHER
    extraction_timestamp: datetime = Field(default_factory=datetime.now)
    periods: List[str] = Field(default_factory=list)
    extracted_data: Dict[str, Any] = Field(default_factory=dict)
    citations: List[Citation] = Field(default_factory=list)
    confidence_score: float = 0.0
    processing_status: ProcessingStatus = ProcessingStatus.PENDING
    error_message: Optional[str] = None


class DocumentUploadResponse(BaseModel):
    document_id: UUID4
    filename: str
    status: ProcessingStatus
    message: str
    contentType: str
    fileSize: int