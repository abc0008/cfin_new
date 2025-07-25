"""
Document Repository Module
=========================

This module provides the repository layer for document operations in the CFIN financial analysis platform.
It handles all database interactions related to documents, citations, and their associated metadata,
as well as storage operations for the actual document files.

Primary responsibilities:
- Store, retrieve, and manage document records in the database
- Handle file storage and retrieval operations (PDF binary content)
- Create and manage document citations
- Provide structured API for document operations used by service layers
- Convert between database models and API/Pydantic models

Key Components:
- DocumentRepository: Main repository class with methods for CRUD operations on documents and citations
- Document conversion methods: Transform database models to API schemas and vice versa

Interactions with other files:
-----------------------------
1. cfin/backend/models/database_models.py:
   - Uses Document, Citation, User, DocumentType, ProcessingStatusEnum database models
   - These SQLAlchemy models define the database schema for documents and citations

2. cfin/backend/models/document.py:
   - Uses ProcessedDocument, DocumentMetadata, DocumentUploadResponse, Citation (as CitationSchema)
   - These Pydantic models define the API schemas for documents and citations
   - Used for converting database models to API responses

3. cfin/backend/utils/storage.py:
   - Uses StorageService for file storage and retrieval operations
   - Methods used: save_file, get_file
   - Handles the actual storage of PDF binary content

4. cfin/backend/pdf_processing/document_service.py:
   - DocumentService initializes this repository and uses it for all document operations
   - Creates document records, updates processing status, and adds citations

5. cfin/backend/pdf_processing/langgraph_service.py:
   - LangGraphService uses this repository to retrieve document binary content
   - Uses get_document_binary method in simple_document_qa

6. cfin/backend/services/conversation_service.py:
   - ConversationService initializes this repository for document access during conversations
   - Uses get_document_content to retrieve document text for Q&A

7. cfin/backend/pdf_processing/claude_service.py:
   - ClaudeService indirectly uses this repository via _prepare_document_for_citation
   - If document binary isn't provided directly, fetches it via get_document_file_content

This repository acts as the central point for all document data access in the application,
ensuring consistent document handling across all services. It manages both the structured
data in the database and the binary content in the storage system.
"""

import logging
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete, func
import os
import json

from models.database_models import Document, Citation, DocumentType, ProcessingStatusEnum
from models.document import ProcessedDocument, DocumentMetadata, DocumentUploadResponse, Citation as CitationSchema
from utils.storage import StorageService

logger = logging.getLogger(__name__)

class DocumentRepository:
    """Repository for document operations."""
    
    def __init__(self, db: AsyncSession, storage_service: Optional[StorageService] = None):
        """
        Initialize the document repository.
        
        Args:
            db: Database session
            storage_service: Optional storage service for file operations
        """
        self.db = db
        self.storage_service = storage_service or StorageService.get_storage_service()
    
    async def create_document(self, file_data: bytes, filename: str, user_id: str, mime_type: str) -> Document:
        """
        Create a new document record.
        
        Args:
            file_data: Raw bytes of the file
            filename: Name of the file
            user_id: ID of the user uploading the document
            mime_type: MIME type of the file
            
        Returns:
            Created document record
        """
        # Generate a unique ID for the document
        document_id = str(uuid.uuid4())
        
        # Store the file
        file_path = await self.storage_service.save_file(
            file_data=file_data,
            file_id=f"{document_id}.pdf",
            content_type=mime_type
        )
        
        # Create document record
        document = Document(
            id=document_id,
            filename=filename,
            file_path=file_path,
            file_size=len(file_data),
            mime_type=mime_type,
            user_id=user_id,
            upload_timestamp=datetime.utcnow(),
            processing_status=ProcessingStatusEnum.PENDING
        )
        
        # Save to database
        self.db.add(document)
        await self.db.commit()
        await self.db.refresh(document)
        
        return document
    
    async def get_document(self, document_id: str) -> Optional[Document]:
        """
        Get a document by ID.
        
        Args:
            document_id: ID of the document
            
        Returns:
            Document if found, None otherwise
        """
        # Ensure document_id is a string, not a list
        if isinstance(document_id, list):
            # If it's a list with items, use the first one
            if document_id:
                document_id = document_id[0]
            else:
                logger.error("Empty document_id list provided to get_document")
                return None
                
        try:
            result = await self.db.execute(
                select(Document).where(Document.id == document_id)
            )
            return result.scalars().first()
        except Exception as e:
            logger.error(f"Error retrieving document {document_id}: {str(e)}")
            return None
    
    async def get_document_content(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the content of a document by ID.
        
        Args:
            document_id: ID of the document
            
        Returns:
            Document content dictionary with raw text and file content if found, None otherwise
        """
        document = await self.get_document(document_id)
        if not document:
            logger.warning(f"Document {document_id} not found in database")
            return None
            
        try:
            # Get the file path
            file_path = f"{document_id}.pdf"
            logger.info(f"Retrieving document content using file path: {file_path}")
            
            # Get the raw PDF content from storage
            logger.info(f"Requesting file from storage service for document {document_id}")
            pdf_content = await self.storage_service.get_file(file_path)
            
            # Log PDF content retrieval success
            if pdf_content:
                pdf_size = len(pdf_content) if pdf_content else 0
                logger.info(f"Retrieved PDF content for document {document_id}: {pdf_size} bytes")
            
            # Prepare the response data
            content_data = {
                "content": pdf_content,
                "id": document_id,
                "filename": document.filename,
                "mime_type": document.mime_type
            }
            
            # Priority: Add claude_file_id for Files API integration (native PDF support)
            if document.claude_file_id:
                content_data["claude_file_id"] = document.claude_file_id
                logger.info(f"Document {document_id} has claude_file_id: {document.claude_file_id} (native PDF support available)")
            else:
                logger.warning(f"Document {document_id} missing claude_file_id - cannot use native PDF support")
            
            # Add raw text if available (optional for PDFs with claude_file_id)
            # For PDFs, prefer claude_file_id over raw_text for native PDF support
            if document.mime_type == "application/pdf" and document.claude_file_id:
                logger.info(f"PDF document {document_id} uses claude_file_id for native support - raw_text not required")
                content_data["raw_text"] = None  # Explicitly set to None for PDFs with file_id
            elif document.raw_text:
                content_data["raw_text"] = document.raw_text
                logger.info(f"Using document.raw_text for document {document_id}: {len(document.raw_text)} characters")
            elif document.extracted_data and isinstance(document.extracted_data, dict) and "raw_text" in document.extracted_data:
                # Extract raw text from extracted_data as fallback
                content_data["raw_text"] = document.extracted_data["raw_text"]
                logger.info(f"Using extracted_data.raw_text for document {document_id}: {len(str(document.extracted_data['raw_text']))} characters")
            else:
                logger.warning(f"No raw text available for document {document_id}")
                content_data["raw_text"] = None
            
            # Add extracted data if available
            if document.extracted_data:
                content_data["extracted_data"] = document.extracted_data
                logger.info(f"Extracted data available for document {document_id}: {list(document.extracted_data.keys()) if isinstance(document.extracted_data, dict) else 'not a dict'}")
            else:
                logger.warning(f"No extracted data available for document {document_id}")
                content_data["extracted_data"] = {}
            
            # Log content retrieval success
            logger.info(f"Successfully retrieved content for document {document_id}")
            
            return content_data
        except Exception as e:
            logger.error(f"Error retrieving document content for {document_id}: {str(e)}")
            
            # Try to return just the document fields even if file retrieval failed
            if document:
                logger.info(f"Returning partial content for document {document_id} (file retrieval failed)")
                return {
                    "id": document_id,
                    "filename": document.filename,
                    "raw_text": document.raw_text or "Document text not available",
                    "extracted_data": document.extracted_data or {}
                }
            
            return None
    
    async def list_documents(self, user_id: str, limit: int = 10, offset: int = 0) -> List[Document]:
        """
        List documents for a user.
        
        Args:
            user_id: ID of the user
            limit: Maximum number of documents to return
            offset: Starting index
            
        Returns:
            List of documents
        """
        result = await self.db.execute(
            select(Document)
            .where(Document.user_id == user_id)
            .order_by(Document.upload_timestamp.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()
    
    async def count_documents(self, user_id: str) -> int:
        """
        Count the number of documents for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Number of documents
        """
        result = await self.db.execute(
            select(func.count()).select_from(Document).where(Document.user_id == user_id)
        )
        return result.scalar()
    
    async def update_document(self, document_id: str, update_data: Dict[str, Any]) -> Optional[Document]:
        """
        Update a document.
        
        Args:
            document_id: ID of the document
            update_data: Dictionary of fields to update
            
        Returns:
            Updated document if found, None otherwise
        """
        await self.db.execute(
            update(Document)
            .where(Document.id == document_id)
            .values(**update_data)
        )
        await self.db.commit()
        
        return await self.get_document(document_id)
    
    async def update_document_status(
        self, document_id: str, status: ProcessingStatusEnum, error_message: Optional[str] = None
    ) -> Optional[Document]:
        """
        Update a document's processing status.
        
        Args:
            document_id: ID of the document
            status: New processing status
            error_message: Optional error message if status is FAILED
            
        Returns:
            Updated document if found, None otherwise
        """
        update_data = {
            "processing_status": status,
            "processing_timestamp": datetime.utcnow()
        }
        
        if error_message:
            update_data["error_message"] = error_message
        
        return await self.update_document(document_id, update_data)
    
    async def update_document_content(
        self, 
        document_id: str, 
        document_type: Optional[DocumentType] = None, 
        periods: Optional[List[str]] = None,
        extracted_data: Optional[Dict[str, Any]] = None,
        raw_text: Optional[str] = None,
        confidence_score: Optional[float] = None,
        update_existing: bool = False
    ) -> Optional[Document]:
        """
        Update a document's content after processing.
        
        Args:
            document_id: ID of the document
            document_type: Type of financial document
            periods: List of time periods in the document
            extracted_data: Extracted structured data
            raw_text: Optional raw text of the document (potentially from LLM post-processing)
            confidence_score: Confidence score of the extraction
            update_existing: If True, merge with existing extracted_data instead of replacing
            
        Returns:
            Updated document if found, None otherwise
        """
        current_doc = await self.get_document(document_id)
        if not current_doc:
            logger.error(f"Document {document_id} not found for update_document_content.")
            return None

        update_data = {"extraction_timestamp": datetime.utcnow()}
        
        if document_type is not None:
            update_data["document_type"] = document_type
            
        if periods is not None:
            update_data["periods"] = periods
            
        if confidence_score is not None:
            update_data["confidence_score"] = confidence_score
        
        # Preserve existing full raw_text if the incoming one is significantly shorter
        if raw_text is not None:
            if current_doc.raw_text and len(current_doc.raw_text) > (len(raw_text) + 500): # Heuristic: existing is much longer
                logger.warning(
                    f"Document {document_id}: Preserving existing DB raw_text ({len(current_doc.raw_text)} chars) "
                    f"over shorter incoming raw_text ({len(raw_text)} chars)."
                )
                # The incoming raw_text (e.g., from Claude) will be placed into extracted_data if not already present
            else:
                update_data["raw_text"] = raw_text
        
        # Handle extracted_data
        final_extracted_data = {}
        if extracted_data is not None:
            if update_existing and current_doc.extracted_data:
                final_extracted_data = self._merge_dicts(current_doc.extracted_data, extracted_data)
            else:
                final_extracted_data = extracted_data
        elif update_existing and current_doc.extracted_data: # No new extracted_data, but update_existing is true
             final_extracted_data = current_doc.extracted_data


        # If incoming raw_text was from LLM and we decided to preserve the original document.raw_text,
        # ensure this LLM-generated raw_text is captured in extracted_data.
        if raw_text is not None and \
           (not current_doc.raw_text or len(current_doc.raw_text) <= (len(raw_text) + 500)) and \
           "raw_text" not in final_extracted_data:
            # This case means raw_text was updated in update_data or was shorter/non-existent in current_doc.raw_text
            # No need to add to final_extracted_data if it's going to be the main raw_text
            pass
        elif raw_text is not None and \
             current_doc.raw_text and len(current_doc.raw_text) > (len(raw_text) + 500) and \
             "claude_raw_text_snippet" not in final_extracted_data: # Use a different key
            logger.info(f"Document {document_id}: Storing incoming (shorter) raw_text ({len(raw_text)} chars) into extracted_data.claude_raw_text_snippet")
            final_extracted_data["claude_raw_text_snippet"] = raw_text

        if final_extracted_data: # Only update if there's something to put there
            update_data["extracted_data"] = final_extracted_data
        
        return await self.update_document(document_id, update_data)
    
    def _merge_dicts(self, dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep merge two dictionaries.
        Values from dict2 will override values in dict1 unless both are dictionaries,
        in which case they will be merged recursively.
        
        Args:
            dict1: First dictionary
            dict2: Second dictionary (takes precedence)
            
        Returns:
            Merged dictionary
        """
        result = dict1.copy()
        
        for key, value in dict2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Recursively merge nested dictionaries
                result[key] = self._merge_dicts(result[key], value)
            else:
                # Override or add the value
                result[key] = value
                
        return result
    
    async def delete_document(self, document_id: str) -> bool:
        """
        Delete a document.
        
        Args:
            document_id: ID of the document
            
        Returns:
            True if document was deleted, False otherwise
        """
        # Get document to get the file path
        document = await self.get_document(document_id)
        if not document:
            return False
        
        # Delete the file
        file_id = f"{document_id}.pdf"
        await self.storage_service.delete_file(file_id)
        
        # Delete from database
        await self.db.execute(
            delete(Document).where(Document.id == document_id)
        )
        await self.db.commit()
        
        return True
    
    async def add_citation(
        self, document_id: str, page: int, text: str, section: Optional[str] = None, bounding_box: Optional[Dict[str, Any]] = None
    ) -> Optional[Citation]:
        """
        Add a citation to a document.
        
        Args:
            document_id: ID of the document
            page: Page number
            text: Citation text
            section: Optional section name
            bounding_box: Optional bounding box coordinates
            
        Returns:
            Created citation if document found, None otherwise
        """
        # Check if document exists
        document = await self.get_document(document_id)
        if not document:
            return None
        
        # Create citation
        citation = Citation(
            id=str(uuid.uuid4()),
            document_id=document_id,
            page=page,
            text=text,
            section=section,
            bounding_box=bounding_box
        )
        
        # Save to database
        self.db.add(citation)
        await self.db.commit()
        await self.db.refresh(citation)
        
        return citation
    
    async def create_citation_with_message(
        self, document_id: str, citation_data: Dict[str, Any]
    ) -> Optional[Citation]:
        """
        Create a citation with full data including message relationship.
        
        Args:
            document_id: ID of the document
            citation_data: Dictionary containing all citation fields
            
        Returns:
            Created citation if successful, None otherwise
        """
        from models.database_models import MessageCitation
        
        # Check if document exists
        document = await self.get_document(document_id)
        if not document:
            return None
        
        # Extract message_id before creating citation
        message_id = citation_data.pop("message_id", None)
        
        # Create citation with provided ID or generate new one
        citation_id = citation_data.get("id") or citation_data.get("highlight_id") or str(uuid.uuid4())
        
        # Create citation object - filter out fields that don't exist in Citation model
        citation = Citation(
            id=citation_id,
            document_id=document_id,
            text=citation_data.get("text", ""),
            cited_text=citation_data.get("cited_text", citation_data.get("text", "")),
            display_text=citation_data.get("display_text"),  # Processed text for display
            searchable_text=citation_data.get("searchable_text"),  # Text for PDF rect finding
            document_title=citation_data.get("document_title", ""),
            type=citation_data.get("type", "page_location"),
            highlight_id=citation_data.get("highlight_id", citation_id),
            # Ensure rects is stored as JSON string, regardless of whether we
            # received a Python list or already-serialized string.
            rects=json.dumps(citation_data.get("rects", [])) if not isinstance(citation_data.get("rects"), str) else citation_data.get("rects"),
            page=citation_data.get("start_page_number"),
            start_page_number=citation_data.get("start_page_number"),
            end_page_number=citation_data.get("end_page_number"),
            start_char_index=citation_data.get("start_char_index"),
            end_char_index=citation_data.get("end_char_index"),
            start_block_index=citation_data.get("start_block_index"),
            end_block_index=citation_data.get("end_block_index"),
            section=citation_data.get("section")
            # Removed bounding_box field - not in Citation model
        )
        
        # Save citation to database
        self.db.add(citation)
        
        # Create message-citation relationship if message_id provided
        if message_id:
            message_citation = MessageCitation(
                message_id=message_id,
                citation_id=citation.id
            )
            self.db.add(message_citation)
        
        # Commit all changes
        await self.db.commit()
        await self.db.refresh(citation)
        
        return citation
    
    async def get_citation(self, citation_id: str) -> Optional[Citation]:
        """
        Get a citation by ID.
        
        Args:
            citation_id: ID of the citation
            
        Returns:
            Citation if found, None otherwise
        """
        result = await self.db.execute(
            select(Citation).where(Citation.id == citation_id)
        )
        return result.scalars().first()
    
    async def update_citation(self, citation_id: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update a citation's metadata.
        
        Args:
            citation_id: ID of the citation
            metadata: New metadata dictionary
            
        Returns:
            True if updated, False otherwise
        """
        # Get the citation
        citation = await self.get_citation(citation_id)
        if not citation:
            return False
        
        # Update metadata if provided
        if metadata is not None:
            citation.metadata = metadata
        
        # Save changes
        await self.db.commit()
        
        return True
    
    async def get_document_citations(self, document_id: str) -> List[Citation]:
        """
        Get citations for a document.
        
        Args:
            document_id: ID of the document
            
        Returns:
            List of citations
        """
        result = await self.db.execute(
            select(Citation).where(Citation.document_id == document_id)
        )
        return result.scalars().all()
    
    # Methods to convert between database models and API schemas
    
    def document_to_api_schema(self, document: Document) -> ProcessedDocument:
        """Convert a database document model to an API schema."""
        # Avoid lazy loading by not accessing citations directly
        
        # Create metadata
        metadata = DocumentMetadata(
            id=document.id,
            filename=document.filename,
            upload_timestamp=document.upload_timestamp,
            file_size=document.file_size,
            mime_type=document.mime_type,
            user_id=document.user_id,
            citation_links=[]  # Initialize with empty list to avoid lazy loading
        )
        
        # Create processed document
        processed_document = ProcessedDocument(
            metadata=metadata,
            content_type=document.document_type.value if document.document_type else "other",
            extraction_timestamp=document.extraction_timestamp or document.upload_timestamp,
            periods=document.periods or [],
            extracted_data=document.extracted_data or {},
            citations=[],  # Initialize with empty list to avoid lazy loading
            confidence_score=document.confidence_score or 0.0,
            processing_status=document.processing_status.value if document.processing_status else "pending",
            error_message=document.error_message
        )
        
        return processed_document
    
    def document_to_metadata_schema(self, document: Document) -> DocumentMetadata:
        """Convert a database document model to a metadata schema."""
        # Avoid lazy loading by not accessing citations directly
        metadata = DocumentMetadata(
            id=document.id,
            filename=document.filename,
            upload_timestamp=document.upload_timestamp,
            file_size=document.file_size,
            mime_type=document.mime_type,
            user_id=document.user_id,
            citation_links=[]  # Initialize with empty list to avoid lazy loading
        )
        
        return metadata
    
    def document_to_upload_response(self, document: Document) -> DocumentUploadResponse:
        """Convert a database document model to an upload response schema."""
        return DocumentUploadResponse(
            document_id=document.id,  # Keep as UUID object for proper validation
            filename=document.filename,
            status=document.processing_status.value if document.processing_status else "pending",
            message=f"Document uploaded and processing has {'started' if document.processing_status == ProcessingStatusEnum.PENDING else 'completed'}",
            content_type=document.mime_type,
            file_size=document.file_size
        )
    
    def citation_to_api_schema(self, citation: Citation) -> Dict[str, Any]:
        """Convert a database Citation to an API schema."""
        # Import here to avoid circular imports
        from models.citation import CitationPayload, CitationType, CitationRect
        import json
        
        # Parse rects from JSON if stored as string. If none found, attempt to
        # compute bounding box automatically for page_location citations.
        rects = []
        if citation.rects:
            try:
                rects_data = json.loads(citation.rects) if isinstance(citation.rects, str) else citation.rects
                rects = [CitationRect(**rect) for rect in rects_data]
            except Exception:
                logger.warning(f"Failed to parse rects for citation {citation.id}")
        
        def _is_zero_area(r: CitationRect) -> bool:
            """Return True if the rectangle has no visible area (height or width == 0)."""
            return (r.width == 0 or r.height == 0)  # any dimension zero -> fallback rectangle

        has_only_zero_area = rects and all(_is_zero_area(r) for r in rects)

        # Determine citation type value (handles both Enum and plain string)
        citation_type_val: str
        try:
            # Enum case
            from models.citation import CitationType  # local import to avoid circular deps
            if isinstance(citation.type, CitationType):
                citation_type_val = citation.type.value  # e.g. "page_location"
            else:
                citation_type_val = str(citation.type)
        except Exception:
            citation_type_val = str(citation.type)

        # Normalise possible Enum string such as "CitationType.page_location" → "page_location"
        if "." in citation_type_val:
            citation_type_val = citation_type_val.split(".")[-1]

        # Auto-compute if we have no rects OR only zero-area placeholders and citation is page-level
        needs_autocompute = bool(
            (not rects or has_only_zero_area)
            and citation_type_val == "page_location"
            and citation.cited_text
        )

        logger.info(
            "citation %s – needs_autocompute=%s (rects_before=%d, zero_area=%s, type=%s, cited_text_present=%s)",
            citation.id,
            needs_autocompute,
            len(rects),
            has_only_zero_area,
            citation_type_val,
            bool(citation.cited_text),
        )

        if needs_autocompute:
            try:
                from pdf_processing.rect_finder import find_rects_for_text
                pdf_path = self.get_document_file_path(citation.document_id)

                # Build list of pages to try – start_page_number .. end_page_number (inclusive)
                start_pg = citation.start_page_number or citation.page or 1
                end_pg = citation.end_page_number or start_pg
                pages_to_try = list(range(start_pg, end_pg + 1))

                # Use a shorter search string for very long cited_text to avoid
                # grabbing entire tables.  We keep only the first 4 whitespace-
                # separated tokens if the original text is longer than 120 chars.
                from pdf_processing.rect_finder import _normalise_whitespace

                # Check if citation has a searchable_text field set by the citation processor
                if hasattr(citation, 'searchable_text') and citation.searchable_text:
                    raw_search_text = str(citation.searchable_text)
                    logger.info("🔍 Using searchable_text from citation processor: '%s'", raw_search_text)
                else:
                    raw_search_text = str(citation.cited_text or "")
                
                # For citations that look like processed financial values (e.g., "Cash & Due: $4000M"),
                # try to extract just the value part for better rect finding
                # More robust check: ensure it's likely a financial metric with colon separator
                if ":" in raw_search_text:
                    parts = raw_search_text.split(":", 1)
                    if len(parts) == 2:
                        label_part = parts[0].strip()
                        value_part = parts[1].strip()
                        
                        # Check if this looks like a financial citation
                        # Common patterns: contains $, %, ends with M/B/K/x, contains numbers, or is a ratio
                        financial_indicators = [
                            "$" in value_part,
                            "%" in value_part,
                            any(value_part.endswith(suffix) for suffix in ["M", "B", "K", "k", "m", "b", "x", "×"]),
                            any(char.isdigit() for char in value_part),
                            "/" in label_part  # Common in ratios like "Debt/Equity"
                        ]
                        
                        if any(financial_indicators):
                            # Try finding just the value first
                            logger.info("🔍 Detected financial metric - searching for value part: '%s' from citation '%s'", value_part, raw_search_text)
                            search_text = value_part
                        else:
                            search_text = raw_search_text
                    else:
                        search_text = raw_search_text
                elif len(raw_search_text) > 120:
                    search_text = " ".join(_normalise_whitespace(raw_search_text).split(" ")[:4])
                else:
                    search_text = raw_search_text

                rects_found = []  # Initialize rects_found
                
                # Try multiple search strategies for financial values
                search_strategies = [search_text]
                
                # If searching for a financial value like "$4000M", also try variants
                if "$" in search_text:
                    # Try without dollar sign
                    no_dollar = search_text.replace("$", "").strip()
                    search_strategies.append(no_dollar)
                    
                    # Try without suffix (M, B, K)
                    if no_dollar and no_dollar[-1] in "MBK":
                        no_suffix = no_dollar[:-1].strip()
                        search_strategies.append(no_suffix)
                        
                    # Also try with spaces around the number (e.g., "4000 M" or "4,000")
                    if no_dollar and no_dollar[-1] in "MBK":
                        with_space = no_dollar[:-1].strip() + " " + no_dollar[-1]
                        search_strategies.append(with_space)
                
                # Handle percentages (e.g., "15.2%")
                if "%" in search_text:
                    # Try without percentage sign
                    no_percent = search_text.replace("%", "").strip()
                    search_strategies.append(no_percent)
                    
                    # Try with space before percentage
                    with_space_percent = search_text.replace("%", " %")
                    if with_space_percent != search_text:
                        search_strategies.append(with_space_percent)
                
                # Handle comma-separated numbers (e.g., "$4,000M" or "1,234,567")
                if "," in search_text:
                    # Try without commas
                    no_commas = search_text.replace(",", "")
                    search_strategies.append(no_commas)
                    
                    # For dollar amounts with commas, also try variants without dollar sign
                    if "$" in no_commas:
                        no_dollar_no_commas = no_commas.replace("$", "").strip()
                        search_strategies.append(no_dollar_no_commas)
                
                # Handle negative values (e.g., "-$30M", "($30M)", "−$30M")
                if search_text.startswith("-") or search_text.startswith("−") or (search_text.startswith("(") and search_text.endswith(")")):
                    # Try without negative sign
                    positive_value = search_text.lstrip("-−").strip()
                    search_strategies.append(positive_value)
                    
                    # Try parentheses format for negatives
                    if search_text.startswith("-") and "$" in search_text:
                        parentheses_format = "(" + search_text.lstrip("-").strip() + ")"
                        search_strategies.append(parentheses_format)
                    
                    # Try removing parentheses if present
                    if search_text.startswith("(") and search_text.endswith(")"):
                        no_parens = search_text[1:-1].strip()
                        search_strategies.append(no_parens)
                        # Also try with minus sign
                        with_minus = "-" + no_parens
                        search_strategies.append(with_minus)
                
                # Handle ratios and multipliers (e.g., "2.5x", "3.2×")
                if search_text.endswith("x") or search_text.endswith("×"):
                    # Try without the x suffix
                    no_x = search_text.rstrip("x×").strip()
                    search_strategies.append(no_x)
                    
                    # Try with space before x
                    with_space_x = no_x + " x"
                    search_strategies.append(with_space_x)
                    
                    # Try with multiplication symbol
                    with_mult_symbol = no_x + "×"
                    search_strategies.append(with_mult_symbol)
                
                # Final fallback: extract just the numeric value
                # This helps with edge cases where formatting is inconsistent
                import re
                numeric_match = re.search(r'[\d,]+\.?\d*', search_text)
                if numeric_match and numeric_match.group() not in search_strategies:
                    pure_number = numeric_match.group()
                    search_strategies.append(pure_number)
                    # Also try without commas if present
                    if "," in pure_number:
                        search_strategies.append(pure_number.replace(",", ""))
                
                # Remove duplicates while preserving order
                seen = set()
                unique_strategies = []
                for strategy in search_strategies:
                    if strategy not in seen:
                        seen.add(strategy)
                        unique_strategies.append(strategy)
                search_strategies = unique_strategies
                
                logger.info("🔍 Search strategies for citation '%s': %s", citation.id[:8], search_strategies)
                logger.debug("📍 Citation details - Page: %s-%s, Original text: '%s'", 
                            citation.start_page_number, citation.end_page_number, raw_search_text)
                
                for pg in pages_to_try:
                    for search_str in search_strategies:
                        rects_data_page = find_rects_for_text(
                            pdf_path=pdf_path,
                            page_number=pg,
                            cited_text=search_str,
                        )
                        if rects_data_page:
                            rects_found = rects_data_page
                            logger.info("✅ Found rects using search strategy: '%s'", search_str)
                            break
                    if rects_found:
                        break  # Stop at the first page that yields a hit

                # 🛡️  Fallback: scan the rest of the document if nothing matched in
                # the declared page range.  This covers cases where Claude’s page
                # numbers are off-by-one or tables flowed onto an unexpected page.
                if rects_found:
                    # Convert dicts to CitationRect models
                    rects = [CitationRect(**r) if not isinstance(r, CitationRect) else r for r in rects_found]
                    logger.info("✅ Auto-bbox found %d rect(s) for citation %s on page %s", len(rects), citation.id, pg)
                elif not rects_found:
                    try:
                        import fitz
                        doc_tmp = fitz.open(pdf_path)
                        
                        # Try all search strategies on other pages
                        for pg in range(1, doc_tmp.page_count + 1):
                            if pg in pages_to_try:
                                continue  # already examined
                            
                            for search_str in search_strategies:
                                rects_data_page = find_rects_for_text(
                                    pdf_path=pdf_path,
                                    page_number=pg,
                                    cited_text=search_str,
                                )
                                if rects_data_page:
                                    rects_found = rects_data_page
                                    logger.info("✅ Found rects on page %d using fallback search: '%s'", pg, search_str)
                                    break
                            
                            if rects_found:
                                break
                        doc_tmp.close()
                        
                        # Convert found rects to CitationRect models
                        if rects_found:
                            rects = [CitationRect(**r) if not isinstance(r, CitationRect) else r for r in rects_found]
                            logger.info("✅ Fallback auto-bbox found %d rect(s) for citation %s", len(rects), citation.id)
                    except Exception as e:
                        logger.debug(f"Fallback search error for citation {citation.id}: {e}")
                        
                # Log if no rects found after all attempts
                if not rects_found:
                    logger.warning("❌ No rects found for citation %s after trying %d strategies: %s", 
                                 citation.id[:8], len(search_strategies), search_strategies[:3])
            except Exception as e:
                logger.warning(f"Auto-bbox failed for citation {citation.id}: {e}")
        
        # Build the CitationPayload
        # For cited_text field: use display_text if available (processed specific value),
        # otherwise fall back to original cited_text
        primary_citation_text = citation.display_text if citation.display_text else (citation.cited_text or citation.text)
        
        payload = CitationPayload(
            id=str(citation.id),
            document_id=str(citation.document_id),
            type=CitationType(citation.type) if citation.type else CitationType.PAGE_LOCATION,
            cited_text=primary_citation_text,  # Primary field for frontend display
            display_text=citation.display_text,  # Optional processed text (e.g., "Interest Income: $900.0M")
            searchable_text=citation.searchable_text,  # Optional text for PDF search (e.g., "900.0")
            document_title=citation.document_title or "",
            highlight_id=citation.highlight_id or str(citation.id),
            rects=rects,
            start_page_number=citation.start_page_number,
            end_page_number=citation.end_page_number,
            start_char_index=citation.start_char_index,
            end_char_index=citation.end_char_index,
            start_block_index=citation.start_block_index,
            end_block_index=citation.end_block_index,
            page=citation.page,  # Legacy field
            section=citation.section,
            message_id=str(citation.message_id) if hasattr(citation, 'message_id') and citation.message_id else None,
            analysis_id=str(citation.analysis_id) if hasattr(citation, 'analysis_id') and citation.analysis_id else None
        )
        
        # Return as dict with camelCase keys
        logger.info("↩️ Returning citation %s with %d rect(s)", citation.id, len(payload.rects))
        # Dump to a plain JSON-serialisable dict (including nested CitationRect models)
        return payload.model_dump(mode="json", by_alias=True)
        
    def get_document_file_path(self, document_id: str) -> str:
        """
        Get the physical file path for a document.
        
        Args:
            document_id: ID of the document
            
        Returns:
            Absolute path to the document file
        """
        # The storage service uses the document ID with a .pdf extension as the file ID
        file_id = f"{document_id}.pdf"
        return self.storage_service.get_file_path(file_id)
    
    async def get_document_binary(self, document_id: str) -> Optional[bytes]:
        """
        Get the binary data for a document.
        
        Args:
            document_id: ID of the document
            
        Returns:
            Binary data of the document file if available, None otherwise
        """
        try:
            # First check if we have the document in the database
            document = await self.get_document(document_id)
            if not document:
                return None
            
            # If we have binary_data stored in the database, return it
            if hasattr(document, 'binary_data') and document.binary_data:
                return document.binary_data
            
            # If we don't have binary data in the DB, try to read from file
            file_path = self.get_document_file_path(document_id)
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    return f.read()
            
            # No binary data found
            return None
        except Exception as e:
            logging.error(f"Error getting document binary data: {str(e)}", exc_info=True)
            return None