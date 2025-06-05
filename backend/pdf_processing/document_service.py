import logging
from typing import Dict, List, Optional, Any
import asyncio
import settings

from models.document import (
    Citation as CitationSchema,
    DocumentUploadResponse
)
from models.database_models import DocumentType, ProcessingStatusEnum, Citation
from pdf_processing.api_service import ClaudeService
from repositories.document_repository import DocumentRepository


logger = logging.getLogger(__name__)


class DocumentService:
    def __init__(self, document_repository: DocumentRepository):
        """
        Initialize the document service.
        
        Args:
            document_repository: Repository for document operations
        """
        self.document_repository = document_repository
        self.claude_service = ClaudeService()
        
    async def upload_document(self, file_data: bytes, filename: str, user_id: str) -> DocumentUploadResponse:
        """
        Upload and process a document using Claude Files API optimizations.
        
        Args:
            file_data: Raw bytes of the PDF file
            filename: Name of the file
            user_id: ID of the user uploading the document
            
        Returns:
            Document upload response with status and document ID
        """
        try:
            # Create the document record
            document = await self.document_repository.create_document(
                file_data=file_data,
                filename=filename,
                user_id=user_id,
                mime_type="application/pdf"
            )
            
            # Start background processing with Files API optimization
            asyncio.create_task(self._process_document_optimized(document.id, file_data, filename))
            
            # Return upload response
            return self.document_repository.document_to_upload_response(document)
        
        except Exception as e:
            logger.error(f"Error uploading document: {str(e)}", exc_info=True)
            raise
    
    async def _process_document_optimized(self, document_id: str, pdf_data: bytes, filename: str):
        """
        Process a document with Claude API optimizations using Files API and cached text.
        
        Args:
            document_id: ID of the document
            pdf_data: Raw bytes of the PDF file
            filename: Name of the file
        """
        try:
            # Update status to processing
            await self.document_repository.update_document_status(document_id, ProcessingStatusEnum.PROCESSING)
            logger.info(f"Starting optimized processing of document {document_id} ({filename}) with Claude Files API")
            
            # Get the document record to use with Files API optimization
            doc = await self.document_repository.get_document(document_id)
            if not doc:
                raise ValueError(f"Document {document_id} not found")
            
            # Extract text using Files API optimization
            full_text = await self.claude_service._extract_full_text(
                doc=doc,
                pdf_bytes=pdf_data,
                prompt=settings.PDF_EXTRACT_PROMPT
            )
            
            # Process with Claude service for structured data
            true_full_raw_text, processed_document_model, citations_list = await self.claude_service.process_pdf(pdf_data, filename)
            
            if not processed_document_model:
                raise ValueError("Claude service returned None for processed_document_model")
            
            # Use the better text extraction (prefer longer, more complete text)
            # Files API sometimes returns truncated results, so prefer the fuller extraction
            if full_text and len(full_text) > 500:  # Files API extracted substantial content
                final_raw_text_to_store = full_text
                logger.info(f"Using Files API text extraction ({len(full_text)} chars)")
            elif true_full_raw_text and len(true_full_raw_text) > len(full_text):
                final_raw_text_to_store = true_full_raw_text  # Use Claude extraction as fallback
                logger.info(f"Using Claude text extraction as fallback ({len(true_full_raw_text)} chars)")
            else:
                final_raw_text_to_store = full_text or true_full_raw_text  # Last resort
                logger.warning(f"Using minimal text extraction ({len(final_raw_text_to_store)} chars)")
            
            # Check if we have cached file_id and can use Files API optimization
            if doc.claude_file_id and doc.full_text:
                logger.info(f"Using cached Files API file_id={doc.claude_file_id} for document {document_id}")
                final_raw_text_to_store = doc.full_text
                
                # For cached files, we need to do analysis only (not full processing)
                # Use the lightweight analysis approach to avoid redundant API calls
                processed_document_model = await self.claude_service.analyze_pdf_content(
                    pdf_data, filename, use_cached_file_id=doc.claude_file_id
                )
                citations_list = []  # Citations from cache if needed
                
            else:
                logger.info(f"No cached file_id for document {document_id}, performing full processing")
                # Only do full processing if we don't have cached content
                true_full_raw_text, processed_document_model, citations_list = await self.claude_service.process_pdf(pdf_data, filename)
                
                if not processed_document_model:
                    raise ValueError("Claude service returned None for processed_document_model")
                
                # Use the extraction result
                final_raw_text_to_store = true_full_raw_text
                logger.info(f"Using full processing extraction ({len(final_raw_text_to_store)} chars)")
                
                # Update document with new cached data
                await self.document_repository.update_document(document_id, {
                    "full_text": doc.full_text,
                    "text_sha256": doc.text_sha256, 
                    "claude_file_id": doc.claude_file_id
                })
            
            # Determine document type from the processed model
            document_type_enum = DocumentType[processed_document_model.content_type.upper()] if processed_document_model.content_type else DocumentType.OTHER
            
            # Update document with extracted content and Claude optimizations
            logger.info(f"Updating document {document_id} content with Claude optimizations. Raw text length: {len(final_raw_text_to_store)}")
            await self.document_repository.update_document_content(
                document_id=document_id,
                document_type=document_type_enum,
                periods=processed_document_model.periods,
                extracted_data=processed_document_model.extracted_data,
                raw_text=final_raw_text_to_store,
                confidence_score=processed_document_model.confidence_score
            )
            
            logger.info(f"Document {document_id} processed with Claude optimizations. File ID: {doc.claude_file_id}")
            
            # Store citations as before
            added_db_citations: List[Citation] = []
            logger.info(f"Storing {len(citations_list)} citations for document {document_id}")
            for citation_schema_item in citations_list:
                if not isinstance(citation_schema_item, CitationSchema):
                    logger.warning(f"Skipping non-CitationSchema item in citations_list: {type(citation_schema_item)}")
                    continue

                bounding_box = citation_schema_item.bounding_box or {
                    "top": 0, "left": 0, "width": 0, "height": 0
                }
                
                db_citation = await self.document_repository.add_citation(
                    document_id=document_id,
                    page=citation_schema_item.page,
                    text=citation_schema_item.text,
                    section=citation_schema_item.section,
                    bounding_box=bounding_box
                )
                if db_citation:
                    added_db_citations.append(db_citation)
            
            # Update status to completed
            await self.document_repository.update_document_status(document_id, ProcessingStatusEnum.COMPLETED)
            logger.info(f"Successfully completed optimized processing for document {document_id}")
            
        except Exception as e:
            logger.error(f"Error in optimized document processing for {document_id}: {str(e)}", exc_info=True)
            await self.document_repository.update_document_status(
                document_id=document_id,
                status=ProcessingStatusEnum.FAILED,
                error_message=f"Optimized processing error: {str(e)}"
            )
    
    async def get_document_text_optimized(self, document_id: str) -> str:
        """
        Get document text using Claude Files API optimizations with caching.
        
        Args:
            document_id: ID of the document
            
        Returns:
            Full text of the document
        """
        try:
            return await self.claude_service.get_document_text(document_id, self.document_repository)
        except Exception as e:
            logger.error(f"Error getting optimized document text for {document_id}: {e}")
            # Fallback to traditional method
            doc_content = await self.get_document_content(document_id)
            return doc_content.get("raw_text", "") if doc_content else ""
    
    async def get_document_financial_data(self, document_id: str) -> Dict[str, Any]:
        """
        Get content from a document that can be used for financial analysis.
        Now more flexible - returns any available content rather than requiring 
        specific financial_data structure.
        
        Args:
            document_id: ID of the document
                
        Returns:
            Dictionary containing document content suitable for analysis
        """
        document = await self.document_repository.get_document(document_id)
        
        if not document:
            logger.warning(f"Document {document_id} not found")
            return {"error": "Document not found"}
        
        result = {}
        
        # Add financial_data if it exists
        if document.extracted_data and isinstance(document.extracted_data, dict) and "financial_data" in document.extracted_data:
            result["financial_data"] = document.extracted_data["financial_data"]
        
        # Add raw_text if available
        if document.raw_text:
            result["raw_text"] = document.raw_text
            logger.info(f"Found {len(document.raw_text)} characters of raw text in document {document_id}")
        elif document.extracted_data and isinstance(document.extracted_data, dict) and "raw_text" in document.extracted_data:
            result["raw_text"] = document.extracted_data["raw_text"]
            logger.info(f"Found {len(document.extracted_data['raw_text'])} characters of raw text in extracted_data")
        
        # If we have any content, consider it valid
        if result:
            result["has_content"] = True
            return result
        
        # Return empty structure if no content found
        logger.warning(f"No analyzable content found in document {document_id}")
        return {
            "has_content": False,
            "raw_text": f"No content extracted from document {document_id}. The document may be empty or contain only images.",
            "revenue": {},
            "expenses": {},
            "profit": {},
            "assets": {},
            "liabilities": {},
            "equity": {}
        }
    
    async def get_document_content(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the full content of a document including extracted data.
        
        Args:
            document_id: ID of the document
            
        Returns:
            Dictionary containing document content if found, None otherwise
        """
        document = await self.document_repository.get_document(document_id)
        
        if not document:
            return None
        
        # Get citations
        citations = await self.document_repository.get_document_citations(document_id)
        citation_schemas = [self.document_repository.citation_to_api_schema(citation) for citation in citations]
        
        return {
            "metadata": self.document_repository.document_to_metadata_schema(document).model_dump(),
            "content_type": document.document_type.value if document.document_type else "other",
            "periods": document.periods or [],
            "extracted_data": document.extracted_data or {},
            "citations": [citation.model_dump() for citation in citation_schemas],
            "confidence_score": document.confidence_score or 0.0
        }
        
    async def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a document by ID. This is an alias for get_document_content for backwards compatibility.
        
        Args:
            document_id: ID of the document
            
        Returns:
            Dictionary containing document content if found, None otherwise
        """
        # This method should match what's being expected by the calling code
        return await self.get_document_content(document_id)

    async def extract_structured_financial_data(self, document_id: str, text: str = None) -> Dict[str, Any]:
        """
        Extract structured financial data from document text using Claude and update the document.
        
        Args:
            document_id: ID of the document to update
            text: Raw document text to analyze. If None, will be retrieved from the document.
            
        Returns:
            Dictionary with extraction results
        """
        try:
            logger.info(f"Extracting structured financial data for document {document_id}")
            
            # Get document from database to retrieve raw PDF data if available
            document = await self.document_repository.get_document(document_id)
            if not document:
                return {"error": f"Document {document_id} not found"}
            
            # If text not provided, use the one from the document
            if text is None and document.raw_text:
                text = document.raw_text
                logger.info(f"Using document's raw text ({len(text)} chars) for financial data extraction")
            elif text is None:
                return {"error": "No text available for document analysis"}
            
            # Get raw PDF data from storage if available
            pdf_data = None
            filename = document.filename if document else f"document_{document_id}.pdf"
            
            try:
                # Try to get the raw PDF data from storage
                pdf_data = await self.document_repository.get_document_binary(document_id)
                if pdf_data:
                    logger.info(f"Retrieved raw PDF data ({len(pdf_data)} bytes) for financial data extraction")
            except Exception as e:
                logger.warning(f"Could not retrieve PDF binary data: {str(e)}")
                # Continue with text-only extraction if PDF data is not available
            
            # Call Claude service to extract structured data - passing both text and PDF data
            structured_data = await self.claude_service.extract_structured_financial_data(
                text=text,
                pdf_data=pdf_data,
                filename=filename
            )
            
            # If error in extraction, return it
            if structured_data.get("error"):
                logger.error(f"Error extracting structured data: {structured_data['error']}")
                return structured_data
            
            # Prepare financial data structure
            financial_data = {}
            
            # Copy metrics if available
            if "metrics" in structured_data and structured_data["metrics"]:
                financial_data["metrics"] = structured_data["metrics"]
                
            # Copy ratios if available
            if "ratios" in structured_data and structured_data["ratios"]:
                financial_data["ratios"] = structured_data["ratios"]
                
            # Copy insights if available
            if "key_insights" in structured_data and structured_data["key_insights"]:
                financial_data["insights"] = structured_data["key_insights"]
            
            # Get periods from structured data
            periods = structured_data.get("periods", [])
            
            # Update the document with new financial data
            logger.info(f"Updating document {document_id} with structured financial data")
            
            # Create a merged extracted_data object that keeps existing data
            extracted_data = {
                "financial_data": financial_data
            }
            
            # Update document content
            await self.document_repository.update_document_content(
                document_id=document_id,
                document_type=DocumentType.FINANCIAL_REPORT,  # Force update to financial report type
                periods=periods if periods else None,
                extracted_data=extracted_data,
                update_existing=True  # Merge with existing data rather than replacing
            )
            
            # Return success with extracted data
            return {
                "document_id": document_id,
                "metrics_count": len(financial_data.get("metrics", [])),
                "ratios_count": len(financial_data.get("ratios", [])),
                "insights_count": len(financial_data.get("insights", [])),
                "periods": periods
            }
            
        except Exception as e:
            logger.exception(f"Error in structured financial data extraction: {e}")
            return {"error": str(e)}

    async def delete_document(
        self,
        document_id: str,
        analysis_repository: "AnalysisRepository",
    ) -> bool:
        """Delete a document unless referenced by an analysis."""
        if await analysis_repository.is_document_referenced(document_id):
            raise ValueError("Document is referenced by an analysis")
        return await self.document_repository.delete_document(document_id)
