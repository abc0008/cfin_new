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
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete, func
from sqlalchemy.orm import selectinload
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
        from models.database_models import MessageCitation

        result = await self.db.execute(
            select(Citation)
            .options(selectinload(Citation.messages).selectinload(MessageCitation.message))
            .where(Citation.id == citation_id)
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
        from models.database_models import MessageCitation

        result = await self.db.execute(
            select(Citation)
            .options(selectinload(Citation.messages).selectinload(MessageCitation.message))
            .where(Citation.document_id == document_id)
            .order_by(Citation.created_at.asc(), Citation.id.asc())
        )
        citations = result.scalars().all()

        # Build a best-effort marker index hint per message.
        # This allows citation-to-marker context extraction to remain stable when
        # multiple citations share similar cited_text content.
        citations_by_message: Dict[str, List[Citation]] = {}
        for citation in citations:
            for link in getattr(citation, "messages", None) or []:
                message_id = str(getattr(link, "message_id", "") or "")
                if not message_id:
                    continue
                citations_by_message.setdefault(message_id, []).append(citation)

        for _, group in citations_by_message.items():
            ordered = sorted(
                group,
                key=lambda c: (
                    getattr(c, "created_at", None) or datetime.min,
                    str(getattr(c, "id", "")),
                ),
            )
            for marker_index, citation in enumerate(ordered, start=1):
                setattr(citation, "_marker_index_hint", marker_index)

        return citations
    
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
    
    # Process-lifetime cache of computed citation payloads. Auto-bbox rect
    # search is expensive (PyMuPDF scan per citation), and the same citations
    # are re-requested every time a document's citation list loads — cache the
    # final payload after the first computation.
    _citation_payload_cache: Dict[str, Dict[str, Any]] = {}
    _CITATION_PAYLOAD_CACHE_MAX = 4000

    def citation_to_api_schema(self, citation: Citation) -> Dict[str, Any]:
        """Convert a database Citation to an API schema."""
        # Import here to avoid circular imports
        from models.citation import CitationPayload, CitationType, CitationRect
        import json
        import re

        cache_key = str(citation.id)
        cached_payload = DocumentRepository._citation_payload_cache.get(cache_key)
        if cached_payload is not None:
            return cached_payload
        
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

        # Provenance of the selected highlight rect ("table" | "text" | None).
        # Set when the auto-bbox search below picks a match; None for stored rects.
        citation_source_type: Optional[str] = None

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
                import fitz
                from pdf_processing.rect_finder import find_rects_for_text
                from pdf_processing.rect_finder import _normalise_whitespace

                pdf_path = self.get_document_file_path(citation.document_id)

                # Build list of pages to try – start_page_number .. end_page_number (inclusive)
                start_pg = citation.start_page_number or citation.page or 1
                end_pg = citation.end_page_number or start_pg
                pages_to_try = list(range(start_pg, end_pg + 1))

                STOP_WORDS = {
                    "the", "and", "for", "with", "that", "this", "from", "into", "over",
                    "under", "were", "was", "are", "has", "had", "have", "its", "our",
                    "their", "than", "then", "also", "per", "all", "one", "two", "three",
                    "ended", "quarter", "months", "month", "year", "years"
                }

                def _is_generic_year_token(value: str) -> bool:
                    cleaned = _normalise_whitespace(value).strip().strip(".")
                    return bool(re.fullmatch(r"(?:19|20)\d{2}", cleaned))

                def _tokenize_alpha(text: str) -> List[str]:
                    tokens = re.findall(r"[A-Za-z]{3,}", text.lower())
                    return [t for t in tokens if t not in STOP_WORDS]

                def _extract_value_tokens(text: str) -> List[str]:
                    tokens: List[str] = []
                    # Capture common financial tokens: currency, percentages, ratios/multipliers.
                    pattern = re.compile(r"\$?\(?-?\d[\d,]*\.?\d*\)?(?:%|[MBKmbk]|x|×)?")
                    for match in pattern.finditer(text):
                        token = _normalise_whitespace(match.group(0))
                        if not token:
                            continue
                        numeric_only = re.sub(r"[^\d]", "", token)
                        if not numeric_only:
                            continue
                        # Skip footnote-style tiny numerals and raw year tokens.
                        if len(numeric_only) <= 1:
                            continue
                        if len(numeric_only) == 4 and _is_generic_year_token(numeric_only):
                            continue
                        tokens.append(token)
                    return tokens

                def _canonical_numeric_token(value: str) -> Optional[str]:
                    """Normalize numeric strings so table-row comparisons are format-insensitive."""
                    cleaned = _normalise_whitespace(value)
                    if not cleaned:
                        return None
                    negative = bool(
                        (cleaned.startswith("(") and cleaned.endswith(")"))
                        or cleaned.startswith("-")
                        or cleaned.startswith("−")
                    )
                    numeric = re.sub(r"[^0-9.]", "", cleaned).strip(".")
                    if not numeric:
                        return None
                    if numeric.count(".") > 1:
                        first_num = re.search(r"\d+(?:\.\d+)?", numeric)
                        if not first_num:
                            return None
                        numeric = first_num.group(0)
                    if negative and numeric != "0":
                        return f"-{numeric}"
                    return numeric

                def _is_informative_term(value: str) -> bool:
                    cleaned = _normalise_whitespace(value)
                    if not cleaned:
                        return False
                    if len(cleaned) < 2:
                        return False
                    if re.fullmatch(r"[\W_]+", cleaned):
                        return False
                    # Avoid matching isolated years as table values.
                    if _is_generic_year_token(cleaned):
                        return False
                    if re.fullmatch(r"\(?\d\)?", cleaned):
                        return False
                    return True

                def _is_low_information_numeric_token(value: str) -> bool:
                    """
                    Identify very short standalone numeric hints (for example day-of-month
                    artifacts like "29") that are too ambiguous to use as primary anchors.
                    """
                    cleaned = _normalise_whitespace(value)
                    if not cleaned:
                        return False
                    canonical = _canonical_numeric_token(cleaned)
                    if not canonical:
                        return False
                    if "." in canonical:
                        return False
                    digits = re.sub(r"\D", "", canonical)
                    if len(digits) <= 2:
                        return True
                    # Also treat patterns like 1,2023 as date-like and ambiguous.
                    if re.fullmatch(r"\d{1,2}(?:19|20)\d{2}", digits):
                        return True
                    return False

                def _format_numeric_key(value: float) -> Optional[str]:
                    if value != value or value in (float("inf"), float("-inf")):
                        return None
                    if abs(value - round(value)) < 1e-9:
                        return str(int(round(value)))
                    formatted = f"{value:.6f}".rstrip("0").rstrip(".")
                    return formatted if formatted else None

                def _derive_numeric_hint_keys(raw_value: str, table_text: str) -> set:
                    keys: set = set()
                    canonical = _canonical_numeric_token(raw_value)
                    if not canonical:
                        return keys
                    keys.add(canonical)
                    try:
                        base_value = float(canonical)
                    except Exception:
                        return keys

                    unit_scale: Optional[float] = None
                    lower_table = table_text.lower()
                    if "in thousands" in lower_table:
                        unit_scale = 1_000.0
                    elif "in millions" in lower_table:
                        unit_scale = 1_000_000.0
                    elif "in billions" in lower_table:
                        unit_scale = 1_000_000_000.0

                    if unit_scale:
                        scaled_down = _format_numeric_key(base_value / unit_scale)
                        if scaled_down:
                            keys.add(scaled_down)
                        scaled_up = _format_numeric_key(base_value * unit_scale)
                        if scaled_up:
                            keys.add(scaled_up)
                    return keys

                def _expand_search_variants(base: str) -> List[str]:
                    variants: List[str] = []

                    def _add_variant(v: str) -> None:
                        cleaned = _normalise_whitespace(v)
                        if _is_informative_term(cleaned) and cleaned not in variants:
                            variants.append(cleaned)

                    _add_variant(base)

                    if "$" in base:
                        no_dollar = base.replace("$", "").strip()
                        _add_variant(no_dollar)
                        if no_dollar and no_dollar[-1] in "MBKmbk":
                            _add_variant(no_dollar[:-1].strip())
                            _add_variant(f"{no_dollar[:-1].strip()} {no_dollar[-1]}")

                    if "%" in base:
                        _add_variant(base.replace("%", "").strip())
                        _add_variant(base.replace("%", " %").strip())

                    if "," in base:
                        no_commas = base.replace(",", "")
                        _add_variant(no_commas)
                        if "$" in no_commas:
                            _add_variant(no_commas.replace("$", "").strip())

                    if base.startswith("(") and base.endswith(")"):
                        no_parens = base[1:-1].strip()
                        _add_variant(no_parens)
                        _add_variant(f"-{no_parens}")
                    elif base.startswith("-") or base.startswith("−"):
                        _add_variant(base.lstrip("-−").strip())

                    if base.endswith("x") or base.endswith("×"):
                        no_mult = base.rstrip("x×").strip()
                        _add_variant(no_mult)
                        _add_variant(f"{no_mult} x")
                        _add_variant(f"{no_mult}×")

                    numeric_match = re.search(r"\d[\d,]*\.?\d*", base)
                    if numeric_match:
                        number = numeric_match.group(0)
                        no_commas_num = number.replace(",", "")
                        if not _is_generic_year_token(no_commas_num):
                            _add_variant(number)
                            _add_variant(no_commas_num)

                    if len(base.split()) > 12:
                        _add_variant(" ".join(base.split()[:8]))

                    return variants

                def _line_score(line: str) -> int:
                    text = _normalise_whitespace(line)
                    if not text:
                        return -10
                    lower = text.lower()
                    score = 0
                    if re.search(r"\d", text):
                        score += 2
                    if "$" in text:
                        score += 3
                    if "%" in text:
                        score += 2
                    keywords = (
                        "revenue", "sales", "income", "earnings", "eps", "cash",
                        "debt", "assets", "liabilities", "equity", "margin", "tax",
                        "operating", "interest", "profit", "loss", "attributable"
                    )
                    score += sum(1 for kw in keywords if kw in lower)
                    if 20 <= len(text) <= 220:
                        score += 1
                    # Penalize likely header/date-only lines.
                    if re.fullmatch(r"(?:q[1-4]\s*)?(?:19|20)\d{2}(?:\s+(?:q[1-4]|(?:19|20)\d{2}))*", lower):
                        score -= 3
                    return score

                def _extract_column_hint_terms(text: str) -> set:
                    terms: set = set()
                    normalized = _normalise_whitespace(text).lower()
                    if not normalized:
                        return terms
                    for year in re.findall(r"(?:19|20)\d{2}", normalized):
                        terms.add(year)
                    for quarter in re.findall(r"\bq[1-4]\b", normalized):
                        terms.add(quarter)
                    for month in re.findall(
                        r"\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
                        r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b",
                        normalized,
                    ):
                        terms.add(month)
                    return terms

                def _extract_primary_column_terms(text: str) -> set:
                    """
                    Return the first explicit column term (year/quarter/month) in reading order.
                    Prefer years over quarters over months.
                    """
                    normalized = _normalise_whitespace(text).lower()
                    if not normalized:
                        return set()
                    years = re.findall(r"(?:19|20)\d{2}", normalized)
                    if years:
                        return {years[0]}
                    quarters = re.findall(r"\bq[1-4]\b", normalized)
                    if quarters:
                        return {quarters[0]}
                    months = re.findall(
                        r"\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
                        r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b",
                        normalized,
                    )
                    if months:
                        return {months[0]}
                    return set()

                def _extract_primary_strong_column_terms(text: str) -> set:
                    """
                    Return the first year/quarter term only (exclude month-only hints).
                    """
                    normalized = _normalise_whitespace(text).lower()
                    if not normalized:
                        return set()
                    years = re.findall(r"(?:19|20)\d{2}", normalized)
                    if years:
                        return {years[0]}
                    quarters = re.findall(r"\bq[1-4]\b", normalized)
                    if quarters:
                        return {quarters[0]}
                    return set()

                def _extract_last_column_terms(text: str) -> set:
                    """
                    Return the closest explicit column term from trailing context
                    (used for mapping a numeric token to its nearest table column cue).
                    """
                    normalized = _normalise_whitespace(text).lower()
                    if not normalized:
                        return set()
                    years = re.findall(r"(?:19|20)\d{2}", normalized)
                    if years:
                        return {years[-1]}
                    quarters = re.findall(r"\bq[1-4]\b", normalized)
                    if quarters:
                        return {quarters[-1]}
                    months = re.findall(
                        r"\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
                        r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b",
                        normalized,
                    )
                    if months:
                        return {months[-1]}
                    return set()

                def _collapse_numeric_spacing(value: str) -> str:
                    # Claude table text can include spaces between digits and punctuation
                    # (e.g. "( 1 , 0 9 5 )"), which breaks downstream matching.
                    collapsed = _normalise_whitespace(value)
                    collapsed = re.sub(r"(?<=[\d(])\s+(?=[\d,.)])", "", collapsed)
                    collapsed = re.sub(r"(?<=[,$-])\s+(?=\d)", "", collapsed)
                    return _normalise_whitespace(collapsed)

                def _extract_message_context_hint() -> Dict[str, Any]:
                    """
                    Extract a value/year hint from the linked assistant message near the
                    citation marker (e.g. "... was $715. [1]").
                    """
                    hint: Dict[str, Any] = {
                        "value": None,
                        "column_terms": set(),
                        "row_terms": set(),
                    }
                    linked_messages = citation.__dict__.get("messages") or []
                    explicit_message_context = getattr(citation, "_message_context_text", None)
                    marker_index_hint = getattr(citation, "_marker_index_hint", None)
                    if marker_index_hint is None:
                        marker_index_hint = getattr(citation, "section", None)
                    try:
                        marker_index_hint = int(marker_index_hint) if marker_index_hint is not None else None
                    except Exception:
                        marker_index_hint = None
                    number_pattern = re.compile(r"\(?\$?\s*[−-]?\d(?:[\d,\s]*\d)?(?:\.\d+)?\)?")
                    assignment_pattern = re.compile(
                        r"([A-Za-z][A-Za-z\s/&-]{2,100}?)\s*=\s*(\$?\s*\(?[−-]?\d(?:[\d,\s]*\d)?(?:\.\d+)?\)?)"
                    )

                    def _extract_assignment_value_hints(message_text: str) -> List[Dict[str, Any]]:
                        hints: List[Dict[str, Any]] = []
                        normalized_text = _normalise_whitespace(message_text)
                        if not normalized_text:
                            return hints
                        for match in assignment_pattern.finditer(normalized_text):
                            raw_label = str(match.group(1) or "")
                            raw_value = str(match.group(2) or "")
                            value = _collapse_numeric_spacing(raw_value)
                            if not _canonical_numeric_token(value):
                                continue

                            # Keep the trailing phrase closest to "=" to avoid carrying
                            # long sentence prefixes into row-label hints.
                            label_tail = re.split(r"[.!?;:]", raw_label)[-1]
                            label = _normalise_whitespace(label_tail).strip(" :-,")
                            row_terms = set(_tokenize_alpha(label))
                            if not row_terms:
                                continue

                            local_context = normalized_text[max(0, match.start() - 120):min(len(normalized_text), match.end() + 120)]
                            col_terms = set(_extract_column_hint_terms(local_context))
                            if not col_terms:
                                col_terms = set(_extract_last_column_terms(local_context))

                            hints.append(
                                {
                                    "value": value,
                                    "row_terms": row_terms,
                                    "column_terms": col_terms,
                                }
                            )
                        return hints

                    focus_terms = set(
                        _tokenize_alpha(
                            " ".join(
                                [
                                    str(citation.display_text or ""),
                                    str(citation.searchable_text or ""),
                                    str(citation.cited_text or ""),
                                ]
                            )
                        )
                    )
                    best_hint: Optional[Dict[str, Any]] = None
                    best_hint_score = float("-inf")

                    message_contexts = []
                    if explicit_message_context:
                        message_contexts.append(str(explicit_message_context))
                    for link in linked_messages:
                        msg = getattr(link, "message", None)
                        message_contexts.append(str(getattr(msg, "content", "") or ""))

                    for content in message_contexts:
                        if not content:
                            continue

                        assignment_hints = _extract_assignment_value_hints(content)
                        if marker_index_hint and marker_index_hint > 0 and marker_index_hint <= len(assignment_hints):
                            chosen_hint = assignment_hints[marker_index_hint - 1]
                            return {
                                "value": chosen_hint.get("value"),
                                "column_terms": set(chosen_hint.get("column_terms") or set()),
                                "row_terms": set(chosen_hint.get("row_terms") or set()),
                            }

                        markers = list(re.finditer(r"\[(\d+)\]", content))
                        has_explicit_markers = bool(markers)
                        marker_spans: List[Tuple[int, int, Optional[int]]] = []
                        if markers:
                            if marker_index_hint and 1 <= marker_index_hint <= len(markers):
                                marker = markers[marker_index_hint - 1]
                                marker_spans = [(marker.start(), marker.end(), marker_index_hint)]
                            else:
                                marker_spans = [
                                    (marker.start(), marker.end(), idx + 1)
                                    for idx, marker in enumerate(markers)
                                ]
                        else:
                            # Streaming responses can expose citations as clickable chips
                            # without inline "[n]" markers. In that case we still need to
                            # mine value/row hints from the assistant answer text.
                            marker_spans = [(len(content), len(content), None)]

                        for marker_start, marker_end, marker_number in marker_spans:
                            # Markers are often appended at the very end of long responses;
                            # inspect the full pre-marker text to avoid dropping the primary
                            # answer value from consideration.
                            before_slice_start = 0
                            if (
                                has_explicit_markers
                                and marker_index_hint
                                and marker_number
                                and marker_number > 1
                                and (marker_number - 2) < len(markers)
                            ):
                                before_slice_start = markers[marker_number - 2].end()

                            before_segment = content[before_slice_start:marker_start]
                            before = _normalise_whitespace(before_segment)
                            # If local marker segment has no numbers, fall back to full
                            # pre-marker text so we still get usable hints.
                            if not re.search(r"\d", before):
                                before = _normalise_whitespace(content[:marker_start])
                            after = _normalise_whitespace(content[marker_end:marker_end + 120])
                            context = _normalise_whitespace(f"{before} {after}")
                            marker_col_terms = _extract_column_hint_terms(context)
                            marker_row_terms = set(_tokenize_alpha(context))
                            first_numeric_in_before: Optional[Any] = None
                            for early_match in number_pattern.finditer(before):
                                early_raw_match = early_match.group(0)
                                early_raw = _collapse_numeric_spacing(early_raw_match)
                                early_canonical = _canonical_numeric_token(early_raw)
                                if not early_canonical:
                                    continue
                                early_raw_compact = re.sub(r"\s+", "", early_raw_match).lstrip("$")
                                if re.fullmatch(r"\(?\d{1,2},(?:19|20)\d{2}\)?", early_raw_compact):
                                    continue
                                early_digits = re.sub(r"\D", "", early_raw_compact)
                                early_left_char = before[max(0, early_match.start() - 1):early_match.start()].lower()
                                if (
                                    early_left_char == "q"
                                    and re.fullmatch(r"[1-4](?:19|20)\d{2}", early_digits)
                                ):
                                    continue
                                early_numeric_only = re.sub(r"\D", "", early_canonical)
                                if len(early_numeric_only) <= 1:
                                    continue
                                if len(early_numeric_only) == 4 and _is_generic_year_token(early_numeric_only):
                                    continue
                                first_numeric_in_before = early_match
                                break
                            marker_focus_prefix = (
                                before[:first_numeric_in_before.start()]
                                if first_numeric_in_before
                                else before
                            )
                            marker_primary_col_terms: set = set()
                            if has_explicit_markers:
                                # Prefer the nearest column cue around the first
                                # answer-like numeric value rather than the first
                                # year that appears in an answer heading.
                                if first_numeric_in_before:
                                    numeric_left_context = before[
                                        max(0, first_numeric_in_before.start() - 220):first_numeric_in_before.start()
                                    ]
                                    numeric_right_context = before[
                                        first_numeric_in_before.end():min(len(before), first_numeric_in_before.end() + 140)
                                    ]
                                else:
                                    numeric_left_context = marker_focus_prefix
                                    numeric_right_context = before
                                marker_primary_col_terms = (
                                    _extract_last_column_terms(numeric_left_context)
                                    or _extract_primary_strong_column_terms(numeric_right_context)
                                    or _extract_last_column_terms(marker_focus_prefix)
                                    or _extract_primary_strong_column_terms(marker_focus_prefix)
                                    or _extract_last_column_terms(before)
                                    or _extract_primary_strong_column_terms(before)
                                    or _extract_primary_column_terms(numeric_right_context)
                                    or _extract_primary_column_terms(marker_focus_prefix)
                                    or _extract_primary_column_terms(before)
                                )

                            ranked_numeric_candidates: List[Tuple[float, int, str, set, set, bool]] = []
                            for match in number_pattern.finditer(before):
                                raw_match = match.group(0)
                                raw = _collapse_numeric_spacing(raw_match)
                                canonical = _canonical_numeric_token(raw)
                                if not canonical:
                                    continue
                                raw_compact = re.sub(r"\s+", "", raw_match).lstrip("$")
                                # Skip date-like fragments such as "1, 2023" and "29, 2024"
                                # that can appear in quarter header text.
                                if re.fullmatch(r"\(?\d{1,2},(?:19|20)\d{2}\)?", raw_compact):
                                    continue
                                # Skip quarter+year fragments like "Q2 2024" that collapse to 22024.
                                qy_digits = re.sub(r"\D", "", raw_compact)
                                left_char = before[max(0, match.start() - 1):match.start()].lower()
                                if (
                                    left_char == "q"
                                    and re.fullmatch(r"[1-4](?:19|20)\d{2}", qy_digits)
                                ):
                                    continue
                                numeric_only = re.sub(r"\D", "", canonical)
                                if len(numeric_only) <= 1:
                                    continue
                                if len(numeric_only) == 4 and _is_generic_year_token(numeric_only):
                                    continue
                                # Skip date-like tokens such as "1,2023" from "July 1, 2023".
                                if re.fullmatch(r"\d{1,2},(?:19|20)\d{2}", raw):
                                    continue

                                # Score candidates so value-like tokens beat date fragments.
                                score = 0.0
                                if "$" in match.group(0):
                                    score += 4.0
                                if "(" in match.group(0) and ")" in match.group(0):
                                    score += 2.0
                                left_context = before[max(0, match.start() - 32):match.start()].lower()
                                right_context = before[match.end():min(len(before), match.end() + 28)].lower()
                                # Prefer direct answer statements ("... was $X ...")
                                # over comparison fragments ("from $X to $Y").
                                if re.search(r"\b(?:was|is|were|equals?|equaled)\b", left_context):
                                    score += 5.5
                                elif re.search(r"\b(?:amounted|amounting|came|stood|reported)\b", left_context):
                                    score += 3.0
                                if re.search(r"\b(?:at|of)\b", left_context):
                                    score += 1.2
                                if re.search(r"\b(?:thousand|million|billion|m|b|k)\b", right_context):
                                    score += 1.2
                                if re.search(r"\b(?:january|february|march|april|may|june|july|august|"
                                             r"september|october|november|december)\b", left_context):
                                    score -= 1.0
                                local_start = max(0, match.start() - 160)
                                local_end = min(len(before), match.end() + 120)
                                local_context = _normalise_whitespace(before[local_start:local_end])
                                local_context_lower = local_context.lower()
                                sentence_breaks = [".", "!", "?", "\n", ";"]
                                sentence_start = 0
                                for token in sentence_breaks:
                                    idx = before.rfind(token, 0, match.start())
                                    if idx >= 0:
                                        sentence_start = max(sentence_start, idx + 1)
                                sentence_end = len(before)
                                for token in sentence_breaks:
                                    idx = before.find(token, match.end())
                                    if idx >= 0:
                                        sentence_end = min(sentence_end, idx)
                                sentence_context = _normalise_whitespace(before[sentence_start:sentence_end]).lower()
                                if re.search(r"\bfor context\b|\bmost recent quarter\b|\bfor comparison\b", sentence_context):
                                    score -= 6.5
                                if re.search(
                                    r"\b(?:year[-\s]?over[-\s]?year|yoy|versus|vs\.?|compared|comparison|"
                                    r"worth noting|shifted|negative swing|as for the quarter ended)\b",
                                    sentence_context,
                                ):
                                    score -= 4.2
                                sentence_numbers = number_pattern.findall(sentence_context)
                                has_from_to_comparison = bool(
                                    len(sentence_numbers) >= 2
                                    and re.search(r"\bfrom\b", sentence_context)
                                    and re.search(r"\bto\b", sentence_context)
                                )
                                if (
                                    has_from_to_comparison
                                ):
                                    score -= 6.0
                                if re.search(r"\bquarter ended\b", sentence_context):
                                    sentence_years = re.findall(r"(?:19|20)\d{2}", sentence_context)
                                    if len(set(sentence_years)) >= 2:
                                        # A sentence that mixes two years is usually contrastive context,
                                        # not the primary answer value for a single-year citation.
                                        score -= 2.8
                                if re.search(r"\bquarter ended\b", local_context_lower):
                                    score += 1.0
                                position_ratio = match.start() / max(len(before), 1)
                                score += (1.0 - position_ratio) * 2.6

                                local_row_terms = set(_tokenize_alpha(local_context))
                                local_col_terms = _extract_column_hint_terms(local_context)
                                left_col_terms = _extract_last_column_terms(before[max(0, match.start() - 160):match.start()])
                                right_col_terms = _extract_primary_column_terms(
                                    before[match.end():min(len(before), match.end() + 120)]
                                )
                                proximal_col_terms = left_col_terms or right_col_terms or local_col_terms

                                if marker_primary_col_terms:
                                    if proximal_col_terms & marker_primary_col_terms:
                                        score += 3.0
                                    elif proximal_col_terms:
                                        score -= 2.6

                                is_answer_like = bool(
                                    re.search(r"\b(?:was|is|were|equals?|equaled)\b", left_context)
                                    and not has_from_to_comparison
                                )
                                ranked_numeric_candidates.append(
                                    (score, match.start(), raw, local_row_terms, proximal_col_terms, is_answer_like)
                                )

                            if ranked_numeric_candidates:
                                answer_like_candidates = [
                                    item for item in ranked_numeric_candidates if bool(item[5])
                                ]
                                if answer_like_candidates:
                                    ranked_numeric_candidates = answer_like_candidates
                                if marker_primary_col_terms:
                                    aligned_numeric_candidates = [
                                        item
                                        for item in ranked_numeric_candidates
                                        if set(item[4]) & marker_primary_col_terms
                                    ]
                                    if aligned_numeric_candidates:
                                        best_overall_score = max(
                                            float(item[0]) for item in ranked_numeric_candidates
                                        )
                                        best_aligned_score = max(
                                            float(item[0]) for item in aligned_numeric_candidates
                                        )
                                        # Apply hard column filtering only when aligned options
                                        # are plausibly competitive with the global best score.
                                        # This prevents trailing contextual comparisons from
                                        # overriding the primary answer value.
                                        if best_aligned_score >= (best_overall_score - 1.5):
                                            ranked_numeric_candidates = aligned_numeric_candidates
                                ranked_numeric_candidates.sort(key=lambda item: (item[0], -item[1]), reverse=True)
                                top = ranked_numeric_candidates[0]
                                top_row_terms = set(top[3]) if top[3] else set(marker_row_terms)
                                top_col_terms = set(top[4]) if top[4] else set(marker_col_terms)
                                focus_overlap = len(focus_terms & top_row_terms) if focus_terms else 0
                                total_score = top[0] + min(focus_overlap, 5) * 0.9
                                if total_score > best_hint_score:
                                    best_hint = {
                                        "value": top[2],
                                        "column_terms": top_col_terms,
                                        "row_terms": top_row_terms,
                                    }
                                    best_hint_score = total_score
                                continue

                            # Fallback when no numeric token is found near marker.
                            focus_overlap = len(focus_terms & marker_row_terms) if focus_terms else 0
                            fallback_score = float(focus_overlap) + (0.8 if marker_col_terms else 0.0)
                            if fallback_score > best_hint_score:
                                best_hint = {
                                    "value": None,
                                    "column_terms": set(marker_col_terms),
                                    "row_terms": set(marker_row_terms),
                                }
                                best_hint_score = fallback_score

                    if best_hint:
                        return best_hint

                    return hint

                cited_text_raw = str(citation.cited_text or citation.text or "")
                cited_text_norm = _normalise_whitespace(cited_text_raw)
                cited_lines = [
                    _normalise_whitespace(line)
                    for line in cited_text_raw.splitlines()
                    if _normalise_whitespace(line)
                ]
                if not cited_lines and cited_text_norm:
                    cited_lines = [cited_text_norm]

                row_anchor_phrase: Optional[str] = None

                # Extract potential column headers (years/quarters) for table context scoring.
                column_headers: List[str] = []
                for line in cited_lines[:8]:
                    years = [y.lower() for y in re.findall(r"(?:19|20)\d{2}", line)]
                    quarters = [q.lower() for q in re.findall(r"\bq[1-4]\b", line, flags=re.IGNORECASE)]
                    if len(years) >= 2:
                        column_headers = years
                        break
                    if len(quarters) >= 2:
                        column_headers = quarters
                        break

                # Build structured candidates with row and column context.
                candidates: List[Dict[str, Any]] = []
                candidate_seen: set = set()
                global_col_hint_terms: set = set()
                global_row_hint_terms: set = set()
                message_hint = _extract_message_context_hint()

                def _add_candidate(
                    term: str,
                    priority: float,
                    row_terms: Optional[set] = None,
                    col_terms: Optional[set] = None,
                    col_index: Optional[int] = None,
                    row_values: Optional[List[str]] = None,
                    source: str = ""
                ) -> None:
                    normalized = _normalise_whitespace(term)
                    if not _is_informative_term(normalized):
                        return
                    row_terms = set(row_terms or set())
                    col_terms = set(col_terms or set())
                    row_values = [v for v in (row_values or []) if v]
                    is_numeric = _canonical_numeric_token(normalized) is not None
                    key = (
                        normalized,
                        tuple(sorted(row_terms)),
                        tuple(sorted(col_terms)),
                        int(col_index) if col_index is not None else None,
                        tuple(row_values),
                        bool(is_numeric),
                        source,
                    )
                    if key in candidate_seen:
                        return
                    candidate_seen.add(key)
                    candidates.append({
                        "term": normalized,
                        "priority": float(priority),
                        "row_terms": row_terms,
                        "col_terms": col_terms,
                        "col_index": int(col_index) if col_index is not None else None,
                        "row_values": row_values,
                        "numeric": bool(is_numeric),
                        "source": source,
                    })

                # 1) Searchable text from citation processor, but only if specific.
                if hasattr(citation, "searchable_text") and citation.searchable_text:
                    searchable = _normalise_whitespace(str(citation.searchable_text))
                    searchable_col_hints = _extract_column_hint_terms(searchable)
                    global_col_hint_terms |= searchable_col_hints
                    searchable_row_terms = set(_tokenize_alpha(searchable))
                    global_row_hint_terms |= searchable_row_terms
                    if _is_informative_term(searchable) and not _is_low_information_numeric_token(searchable):
                        _add_candidate(searchable, 10.0, source="searchable_text")
                        logger.info("🔍 Using searchable_text candidate: '%s'", searchable)
                    elif searchable_col_hints:
                        logger.info(
                            "🔍 Using searchable_text as column hints for citation %s: %s",
                            citation.id,
                            sorted(searchable_col_hints),
                        )
                    else:
                        logger.info(
                            "⚠️ Skipping low-information searchable_text '%s' for citation %s",
                            searchable,
                            citation.id,
                        )

                # 1b) Message-context fallback (answer text near "[n]" marker).
                message_hint_value = _normalise_whitespace(str(message_hint.get("value") or ""))
                message_hint_cols = set(message_hint.get("column_terms") or set())
                message_hint_rows = set(message_hint.get("row_terms") or set())
                global_col_hint_terms |= message_hint_cols
                global_row_hint_terms |= message_hint_rows
                message_hint_numeric_keys = (
                    _derive_numeric_hint_keys(message_hint_value, cited_text_raw)
                    if message_hint_value
                    else set()
                )

                if message_hint_numeric_keys:
                    matched_label_terms: set = set()
                    matched_label_phrase: Optional[str] = None
                    for line in cited_lines[:80]:
                        values = _extract_value_tokens(line)
                        if not values:
                            continue
                        value_keys = {
                            _canonical_numeric_token(v)
                            for v in values
                            if _canonical_numeric_token(v)
                        }
                        if not (value_keys & message_hint_numeric_keys):
                            continue
                        first_numeric = re.search(r"\$?\(?-?\d", line)
                        label_text = (
                            _normalise_whitespace(line[:first_numeric.start()])
                            if first_numeric
                            else _normalise_whitespace(line)
                        ).strip(":-,")
                        matched_label_terms = set(_tokenize_alpha(label_text))
                        if not matched_label_terms:
                            matched_label_terms = set(_tokenize_alpha(line))
                        label_words = label_text.split()
                        if len(label_words) >= 2:
                            matched_label_phrase = " ".join(label_words[:10])
                        break
                    if matched_label_terms:
                        message_hint_rows = set(matched_label_terms)
                        global_row_hint_terms |= message_hint_rows
                    if matched_label_phrase:
                        row_anchor_phrase = matched_label_phrase
                        logger.info(
                            "🔍 Using numeric-matched row-anchor phrase for citation %s: '%s'",
                            citation.id,
                            row_anchor_phrase,
                        )

                if message_hint_rows and not row_anchor_phrase:
                    best_anchor_line = ""
                    best_anchor_score = 0
                    for line in cited_lines[:60]:
                        if not _extract_value_tokens(line):
                            continue
                        line_terms = set(_tokenize_alpha(line))
                        if not line_terms:
                            continue
                        overlap_count = len(message_hint_rows & line_terms)
                        if overlap_count == 0:
                            continue
                        score = overlap_count
                        if _extract_value_tokens(line):
                            score += 2
                        if score > best_anchor_score:
                            best_anchor_score = score
                            best_anchor_line = line

                    if best_anchor_line:
                        first_numeric = re.search(r"\$?\(?-?\d", best_anchor_line)
                        candidate_label = (
                            best_anchor_line[:first_numeric.start()]
                            if first_numeric
                            else best_anchor_line
                        )
                        candidate_label = _normalise_whitespace(candidate_label).strip(":-,")
                        words = candidate_label.split()
                        if len(words) >= 2:
                            row_anchor_phrase = " ".join(words[:10])
                            logger.info(
                                "🔍 Using row-anchor phrase for citation %s: '%s'",
                                citation.id,
                                row_anchor_phrase,
                            )
                if message_hint_value and not _is_low_information_numeric_token(message_hint_value):
                    _add_candidate(
                        message_hint_value,
                        10.25,
                        row_terms=message_hint_rows if message_hint_rows else None,
                        col_terms=message_hint_cols if message_hint_cols else None,
                        source="message_context_value",
                    )
                    logger.info(
                        "🔍 Using message-context value candidate for citation %s: value='%s', col_hints=%s",
                        citation.id,
                        message_hint_value,
                        sorted(message_hint_cols),
                    )
                elif message_hint_value:
                    logger.info(
                        "⚠️ Skipping low-information message-context value '%s' for citation %s",
                        message_hint_value,
                        citation.id,
                    )
                elif message_hint_cols:
                    logger.info(
                        "🔍 Using message-context column hints for citation %s: %s",
                        citation.id,
                        sorted(message_hint_cols),
                    )
                if message_hint_rows:
                    logger.info(
                        "🔍 Using message-context row hints for citation %s: %s",
                        citation.id,
                        sorted(message_hint_rows),
                    )

                # 2) Display text candidates, if available.
                display_text = _normalise_whitespace(str(citation.display_text or ""))
                if display_text:
                    global_col_hint_terms |= _extract_column_hint_terms(display_text)
                    display_row_terms = set(_tokenize_alpha(display_text))
                    global_row_hint_terms |= display_row_terms
                    display_tail = display_text.split(":", 1)[1].strip() if ":" in display_text else display_text
                    low_quality_display = display_tail in {"", ",", "-", "—"}
                    if not low_quality_display and len(display_text) <= 160 and not _is_generic_year_token(display_text):
                        _add_candidate(display_text, 9.0, row_terms=display_row_terms, source="display_text")
                    for token in _extract_value_tokens(display_text):
                        _add_candidate(token, 9.5, row_terms=display_row_terms, source="display_value")

                # 3) Line-driven table candidates with row/column placement context.
                previous_row_terms: set = set()
                for line_idx, line in enumerate(cited_lines[:40]):
                    row_terms = set(_tokenize_alpha(line))
                    values = _extract_value_tokens(line)
                    if row_terms:
                        previous_row_terms = row_terms
                    elif values:
                        row_terms = set(previous_row_terms)

                    # Add a short phrase candidate for text-centric citations.
                    if row_terms and len(line.split()) >= 3 and not values:
                        line_lower = line.lower()
                        if re.search(
                            r"\b(?:unaudited|for the quarter ended|for the six months ended|in thousands|per share data)\b",
                            line_lower,
                        ):
                            continue
                        _add_candidate(
                            " ".join(line.split()[:10]),
                            6.0 - min(line_idx, 12) * 0.25,
                            row_terms=row_terms,
                            source="row_phrase",
                        )

                    if not values:
                        continue

                    row_value_keys = [
                        _canonical_numeric_token(value) or _normalise_whitespace(value).lower()
                        for value in values
                    ]
                    for col_idx, value in enumerate(values):
                        col_terms = set()
                        if col_idx < len(column_headers):
                            col_terms.add(column_headers[col_idx])
                        base_priority = 8.0 - min(line_idx, 12) * 0.35 - min(col_idx, 5) * 0.15
                        if col_idx == 0:
                            base_priority += 0.35
                        if global_col_hint_terms:
                            if col_terms:
                                if col_terms & global_col_hint_terms:
                                    base_priority += 1.2
                                else:
                                    base_priority -= 2.2
                            else:
                                col_terms = set(global_col_hint_terms)
                        if global_row_hint_terms:
                            row_hint_overlap = len(global_row_hint_terms & row_terms) / max(len(global_row_hint_terms), 1)
                            base_priority += row_hint_overlap * 2.0
                            if row_terms and row_hint_overlap == 0:
                                base_priority -= 0.9
                        _add_candidate(
                            value,
                            base_priority,
                            row_terms=row_terms,
                            col_terms=col_terms,
                            col_index=col_idx,
                            row_values=row_value_keys,
                            source="table_value",
                        )

                # 4) Ranked-line fallback candidates.
                ranked_lines = sorted(cited_lines, key=_line_score, reverse=True)
                for idx, line in enumerate(ranked_lines[:6]):
                    line_terms = set(_tokenize_alpha(line))
                    ranked_values = _extract_value_tokens(line)[:4]
                    ranked_row_value_keys = [
                        _canonical_numeric_token(value) or _normalise_whitespace(value).lower()
                        for value in ranked_values
                    ]
                    for col_idx, value in enumerate(ranked_values):
                        ranked_priority = 7.0 - idx * 0.3
                        if global_row_hint_terms:
                            row_hint_overlap = len(global_row_hint_terms & line_terms) / max(len(global_row_hint_terms), 1)
                            ranked_priority += row_hint_overlap * 1.8
                            if line_terms and row_hint_overlap == 0:
                                ranked_priority -= 0.75
                        _add_candidate(
                            value,
                            ranked_priority,
                            row_terms=line_terms,
                            col_terms=set(global_col_hint_terms) if global_col_hint_terms else None,
                            col_index=col_idx,
                            row_values=ranked_row_value_keys,
                            source="ranked_line_value",
                        )
                    if not ranked_values:
                        _add_candidate(
                            " ".join(line.split()[:8]),
                            5.5 - idx * 0.25,
                            row_terms=line_terms,
                            source="ranked_line_phrase",
                        )

                # Final fallback.
                if not candidates and cited_text_norm:
                    _add_candidate(" ".join(cited_text_norm.split()[:8]), 4.0, source="fallback_prefix")

                # Keep the highest-priority candidates to control runtime.
                candidates.sort(key=lambda c: c["priority"], reverse=True)
                candidate_limit = 40 if global_row_hint_terms else 24
                candidates = candidates[:candidate_limit]
                numeric_candidates = [c for c in candidates if c.get("numeric")]
                phrase_candidates = [c for c in candidates if not c.get("numeric")]

                logger.info(
                    "🔍 Built %d search candidates for citation %s (pages %s-%s)",
                    len(candidates),
                    citation.id[:8],
                    start_pg,
                    end_pg,
                )

                # Contextual scoring uses row/column proximity around each matched rectangle.
                page_words_cache: Dict[int, List[Dict[str, Any]]] = {}
                page_height_cache: Dict[int, float] = {}
                row_anchor_center_cache: Dict[int, Optional[float]] = {}
                all_citation_terms = set(_tokenize_alpha(cited_text_raw))

                def _load_page_words(doc: Any, page_number: int) -> List[Dict[str, Any]]:
                    if page_number in page_words_cache:
                        return page_words_cache[page_number]
                    page = doc.load_page(page_number - 1)
                    page_height_cache[page_number] = float(page.rect.height)
                    words = []
                    for x0, y0, x1, y1, text, blk, line, wno in page.get_text("words"):
                        words.append({
                            "x0": float(x0),
                            "y0": float(y0),
                            "x1": float(x1),
                            "y1": float(y1),
                            "cx": float((x0 + x1) / 2.0),
                            "cy": float((y0 + y1) / 2.0),
                            "text": str(text),
                            "norm": str(text).lower(),
                            "block": int(blk),
                            "line": int(line),
                            "word_no": int(wno),
                        })
                    page_words_cache[page_number] = words
                    return words

                def _to_pdfjs_rect(rect: Dict[str, float], page_height: Optional[float]) -> Dict[str, float]:
                    """
                    Convert a PyMuPDF rectangle (top-left origin) to PDF.js coordinates
                    (bottom-left origin) used by react-pdf-highlighter when
                    usePdfCoordinates=true.
                    """
                    converted = dict(rect)
                    if page_height is None:
                        return converted
                    try:
                        top = float(converted["y1"])
                        bottom = float(converted["y2"])
                    except Exception:
                        return converted
                    # PyMuPDF rectangles are top-left based (y1 < y2 for normal text).
                    # Convert only that representation; leave already-converted rects as-is.
                    if top <= bottom:
                        converted["y1"] = float(page_height - bottom)
                        converted["y2"] = float(page_height - top)
                    return converted

                def _extract_terms_from_words(words: List[Dict[str, Any]]) -> set:
                    terms: set = set()
                    for w in words:
                        low = w["norm"]
                        for token in re.findall(r"(?:19|20)\d{2}|q[1-4]|[a-z]{3,}", low):
                            if token in STOP_WORDS:
                                continue
                            terms.add(token)
                    return terms

                def _overlap(expected: set, observed: set) -> float:
                    if not expected:
                        return 0.0
                    return len(expected & observed) / max(len(expected), 1)

                def _rect_word_overlap_area(rect: Dict[str, float], word: Dict[str, Any]) -> float:
                    x_overlap = max(
                        0.0,
                        min(float(rect["x2"]), float(word["x1"])) - max(float(rect["x1"]), float(word["x0"])),
                    )
                    y_overlap = max(
                        0.0,
                        min(float(rect["y2"]), float(word["y1"])) - max(float(rect["y1"]), float(word["y0"])),
                    )
                    return x_overlap * y_overlap

                def _extract_numeric_row_words(words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
                    numeric_words: List[Dict[str, Any]] = []
                    for word in words:
                        canonical = _canonical_numeric_token(str(word.get("text", "")))
                        if not canonical:
                            continue
                        if len(re.sub(r"\D", "", canonical)) <= 1:
                            continue
                        numeric_words.append({**word, "numeric": canonical})
                    numeric_words.sort(key=lambda w: float(w["x0"]))
                    return numeric_words

                def _load_row_anchor_center(page_number: int) -> Optional[float]:
                    if page_number in row_anchor_center_cache:
                        return row_anchor_center_cache[page_number]
                    if not row_anchor_phrase:
                        row_anchor_center_cache[page_number] = None
                        return None

                    anchor_center: Optional[float] = None
                    for variant in _expand_search_variants(row_anchor_phrase)[:8]:
                        anchor_hits = find_rects_for_text(
                            pdf_path=pdf_path,
                            page_number=page_number,
                            cited_text=variant,
                            max_hits=3,
                        )
                        if anchor_hits:
                            anchor_center = float(anchor_hits[0]["y1"] + anchor_hits[0]["y2"]) / 2.0
                            break

                    row_anchor_center_cache[page_number] = anchor_center
                    return anchor_center

                def _score_rect(
                    rect: Dict[str, float],
                    candidate: Dict[str, Any],
                    variant: str,
                    page_words: List[Dict[str, Any]],
                    page_number: int,
                ) -> Tuple[float, Dict[str, Any]]:
                    rect_mid_y = (float(rect["y1"]) + float(rect["y2"])) / 2.0
                    rect_mid_x = (float(rect["x1"]) + float(rect["x2"])) / 2.0
                    rect_h = max(float(rect["height"]), 1.0)

                    anchor_word: Optional[Dict[str, Any]] = None
                    best_anchor_overlap = 0.0
                    for word in page_words:
                        overlap_area = _rect_word_overlap_area(rect, word)
                        if overlap_area > best_anchor_overlap:
                            best_anchor_overlap = overlap_area
                            anchor_word = word

                    line_center_y = float(anchor_word["cy"]) if anchor_word and best_anchor_overlap > 0.0 else rect_mid_y
                    row_band = max(5.0, rect_h * 0.85)
                    row_words = [
                        w for w in page_words
                        if abs(w["cy"] - line_center_y) <= row_band
                    ]
                    row_words.sort(key=lambda w: w["x0"])
                    row_terms = _extract_terms_from_words(row_words)
                    row_top = min((float(w["y0"]) for w in row_words), default=float(rect["y1"]))

                    col_words = [
                        w for w in page_words
                        if w["cy"] < row_top
                        and (row_top - w["cy"]) <= 120.0
                        and abs(w["cx"] - rect_mid_x) <= max(90.0, float(rect["width"]) * 2.0)
                    ]
                    col_words.sort(key=lambda w: (w["y0"], w["x0"]))
                    col_terms = _extract_terms_from_words(col_words)
                    row_numeric_words = _extract_numeric_row_words(row_words)
                    observed_row_values = [str(w["numeric"]) for w in row_numeric_words]
                    matched_col_index: Optional[int] = None
                    if row_numeric_words:
                        overlap_scores = [
                            _rect_word_overlap_area(rect, word)
                            for word in row_numeric_words
                        ]
                        best_overlap = max(overlap_scores) if overlap_scores else 0.0
                        if best_overlap > 0.0:
                            matched_col_index = int(overlap_scores.index(best_overlap))
                        else:
                            matched_col_index = min(
                                range(len(row_numeric_words)),
                                key=lambda idx: abs(float(row_numeric_words[idx]["cx"]) - rect_mid_x),
                            )

                    row_overlap = _overlap(candidate["row_terms"], row_terms)
                    col_overlap = _overlap(candidate["col_terms"], col_terms)
                    row_hint_overlap = _overlap(global_row_hint_terms, row_terms)
                    global_hits = len(all_citation_terms & row_terms)

                    row_text = " ".join(w["norm"] for w in row_words)
                    score = candidate["priority"]
                    score += row_overlap * 8.0
                    score += col_overlap * 6.0
                    score += row_hint_overlap * 7.5
                    score += min(global_hits, 4) * 0.6

                    if candidate["row_terms"] and row_overlap == 0:
                        score -= 5.6 if candidate.get("numeric") else 2.8
                    if candidate["col_terms"] and col_overlap == 0:
                        score -= 1.0
                    if global_row_hint_terms and row_hint_overlap == 0:
                        score -= 5.0 if candidate.get("numeric") else 3.2
                    if numeric_candidates and not candidate.get("numeric"):
                        source_name = str(candidate.get("source", ""))
                        if source_name.endswith("phrase"):
                            score -= 18.0
                        else:
                            score -= 6.0
                    candidate_col_index = candidate.get("col_index")
                    candidate_row_values = list(candidate.get("row_values") or [])
                    if candidate_col_index is not None:
                        if matched_col_index is None:
                            score -= 1.8
                        else:
                            delta = abs(int(candidate_col_index) - int(matched_col_index))
                            if delta == 0:
                                score += 4.0
                            elif delta == 1:
                                score += 0.9
                            else:
                                score -= 1.4 + min(delta, 3) * 0.7

                            if (
                                0 <= int(candidate_col_index) < len(candidate_row_values)
                                and 0 <= int(matched_col_index) < len(observed_row_values)
                            ):
                                expected_value = str(candidate_row_values[int(candidate_col_index)])
                                observed_value = str(observed_row_values[int(matched_col_index)])
                                if expected_value and expected_value == observed_value:
                                    score += 1.8
                                elif expected_value:
                                    score -= 1.2
                    if re.search(r"(adjusted|retroactively|stock|split)", row_text) and "split" not in candidate["row_terms"]:
                        score -= 2.0
                    if variant.lower() in row_text:
                        score += 0.8
                    if _is_generic_year_token(variant):
                        score -= 8.0

                    row_anchor_center = _load_row_anchor_center(page_number)
                    if row_anchor_center is not None:
                        row_delta = abs(line_center_y - float(row_anchor_center))
                        if row_delta <= max(6.0, rect_h * 1.2):
                            score += 8.0
                        elif row_delta <= 60.0:
                            score += 2.0
                        else:
                            score -= min(12.0, row_delta / 10.0)

                    variant_numeric_key = _canonical_numeric_token(variant)
                    if message_hint_numeric_keys:
                        if variant_numeric_key:
                            if variant_numeric_key in message_hint_numeric_keys:
                                score += 30.0
                            else:
                                score -= 35.0
                        else:
                            # If the assistant explicitly gave a numeric answer for this
                            # marker, non-numeric variants should be de-prioritized.
                            score -= 12.0
                    if message_hint_numeric_keys and not candidate.get("numeric"):
                        score -= 24.0

                    # ── Table-source preference ───────────────────────────────
                    # FP&A users want highlights anchored to financial-table
                    # cells, not the narrative sentence that repeats the same
                    # figure. Rows containing several aligned numeric cells are
                    # table rows; long alpha-heavy rows with at most one number
                    # are prose. Boost the former, penalize the latter, so when
                    # the same value matches in both places the table cell wins.
                    row_numeric_count = len(row_numeric_words)
                    row_alpha_words = [w for w in row_words if re.search(r"[A-Za-z]{2,}", w["norm"])]
                    if row_numeric_count >= 2:
                        # Up to +7.0 for dense table rows (e.g., multi-period columns).
                        score += min(row_numeric_count, 5) * 1.4
                    elif len(row_alpha_words) >= 10 and row_numeric_count <= 1:
                        # Sentence-like line: many words, lone embedded figure.
                        score -= 4.0

                    rect_meta = {
                        "row_numeric_count": row_numeric_count,
                        "row_word_count": len(row_words),
                        "row_alpha_count": len(row_alpha_words),
                    }
                    return score, rect_meta

                best_match: Optional[Dict[str, Any]] = None
                tried_pages = set(p for p in pages_to_try if p >= 1)

                with fitz.open(pdf_path) as doc_tmp:
                    total_pages = doc_tmp.page_count
                    fallback_pages = [p for p in range(1, total_pages + 1) if p not in tried_pages]
                    page_sets = [pages_to_try, fallback_pages]

                    candidate_groups: List[List[Dict[str, Any]]] = []
                    if numeric_candidates:
                        candidate_groups.append(numeric_candidates)
                        if phrase_candidates:
                            candidate_groups.append(phrase_candidates)
                    else:
                        candidate_groups.append(candidates)

                    for page_set in page_sets:
                        if not page_set:
                            continue
                        for group_idx, candidate_group in enumerate(candidate_groups):
                            if not candidate_group:
                                continue
                            group_best_before = best_match
                            for candidate in candidate_group:
                                variants = _expand_search_variants(candidate["term"])[:10]
                                for variant in variants:
                                    for pg in page_set:
                                        rect_hits = find_rects_for_text(
                                            pdf_path=pdf_path,
                                            page_number=pg,
                                            cited_text=variant,
                                            max_hits=20,
                                        )
                                        if not rect_hits:
                                            continue
                                        page_words = _load_page_words(doc_tmp, pg)
                                        for r in rect_hits:
                                            score, rect_meta = _score_rect(r, candidate, variant, page_words, pg)
                                            if best_match is None or score > best_match["score"]:
                                                best_match = {
                                                    "rect": r,
                                                    "score": score,
                                                    "page": pg,
                                                    "variant": variant,
                                                    "candidate": candidate,
                                                    "meta": rect_meta,
                                                }
                            # If we found any numeric match, do not allow phrase-only
                            # candidates to override it.
                            if (
                                numeric_candidates
                                and group_idx == 0
                                and best_match is not None
                                and best_match != group_best_before
                            ):
                                break

                        # If we already have a confident in-range match, skip fallback pages.
                        if best_match and (
                            best_match["score"] >= 7.5
                            or (numeric_candidates and best_match["candidate"].get("numeric"))
                        ):
                            break

                if best_match:
                    selected_rect = dict(best_match["rect"])
                    selected_page = int(best_match["page"])
                    page_height = page_height_cache.get(selected_page)
                    if page_height is None:
                        with fitz.open(pdf_path) as doc_height:
                            if 1 <= selected_page <= doc_height.page_count:
                                page_height = float(doc_height.load_page(selected_page - 1).rect.height)
                    selected_rect = _to_pdfjs_rect(selected_rect, page_height)
                    rects = [CitationRect(**selected_rect)]
                    match_meta = best_match.get("meta") or {}
                    citation_source_type = (
                        "table"
                        if int(match_meta.get("row_numeric_count") or 0) >= 2
                        else "text"
                    )
                    logger.info(
                        "✅ Auto-bbox selected rect for citation %s via '%s' (source=%s, score=%.2f, page=%s, source_type=%s, row_numeric_count=%s)",
                        citation.id,
                        best_match["variant"],
                        best_match["candidate"]["source"],
                        best_match["score"],
                        best_match["page"],
                        citation_source_type,
                        match_meta.get("row_numeric_count"),
                    )
                else:
                    logger.warning(
                        "❌ No rects found for citation %s after table-aware row/column search",
                        citation.id[:8],
                    )
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
            analysis_id=str(citation.analysis_id) if hasattr(citation, 'analysis_id') and citation.analysis_id else None,
            source_type=citation_source_type
        )
        
        # Return as dict with camelCase keys
        logger.info("↩️ Returning citation %s with %d rect(s)", citation.id, len(payload.rects))
        # Dump to a plain JSON-serialisable dict (including nested CitationRect models)
        result = payload.model_dump(mode="json", by_alias=True)

        # Cache the computed payload so subsequent loads skip the expensive
        # auto-bbox search (hit or miss — repeated failed searches are just as
        # costly as successful ones).
        if len(DocumentRepository._citation_payload_cache) >= DocumentRepository._CITATION_PAYLOAD_CACHE_MAX:
            DocumentRepository._citation_payload_cache.clear()
        DocumentRepository._citation_payload_cache[cache_key] = result

        return result
        
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
            
            # If we don't have binary data in the DB, read it from the configured
            # storage backend. This covers Supabase/S3 as well as local storage.
            stored_file = await self.storage_service.get_file(f"{document_id}.pdf")
            if stored_file:
                return stored_file

            # Fall back to direct filesystem reads for legacy local paths.
            file_path = self.get_document_file_path(document_id)
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    return f.read()
            
            # No binary data found
            return None
        except Exception as e:
            logging.error(f"Error getting document binary data: {str(e)}", exc_info=True)
            return None
