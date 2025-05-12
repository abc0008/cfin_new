"""
Claude Service Module
====================

This module provides the main interface for interacting with the Anthropic Claude API for PDF and financial document analysis within the backend system. It encapsulates all logic for:
- Submitting PDFs (and optionally text documents) to Claude for extraction, analysis, and Q&A.
- Extracting structured financial data, citations, and generating responses with or without visualization tools.
- Handling tool-based analysis (charts/tables) and citation mapping for downstream frontend highlighting.
- Acting as the primary AI/LLM service for document understanding, replacing legacy text extraction fallbacks.

Key Responsibilities:
- Process PDF files using Claude's native PDF support, including extracting raw text, structured data, and citations.
- Analyze documents and user queries, supporting tool-based visualizations (charts/tables) for financial analysis.
- Generate responses for Q&A, including citation-aware answers for use with frontend highlighters.
- Convert and standardize citation data for downstream storage and frontend consumption.
- Provide fallback to LangGraph or LangChain-based analysis for non-PDF or text-only scenarios.

Interactions with other files:
-----------------------------
1. cfin/backend/models/document.py:
    - Uses ProcessedDocument, DocumentCitation, DocumentContentType, DocumentMetadata, ProcessingStatus for representing processed documents and their metadata.
    - These models define the structure for PDF processing results and citations.

2. cfin/backend/models/citation.py:
    - Uses Citation, CitationType, CharLocationCitation, PageLocationCitation, ContentBlockLocationCitation for citation data structures.
    - Provides models for storing and retrieving document citations with proper highlighting information.

3. cfin/backend/models/tools.py:
    - Imports ToolSchema, ALL_TOOLS, ALL_TOOLS_DICT for tool-based analysis (charts/tables) and visualization support.
    - Used in analyze_with_visualization_tools for generating financial charts and tables.

4. cfin/backend/pdf_processing/langchain_service.py:
    - Uses LangChainService as a fallback for text-based document analysis if LangGraph/Claude is unavailable.
    - Method used: analyze_document_content.
    - Called by generate_response_with_langgraph method.

5. cfin/backend/pdf_processing/langgraph_service.py:
    - Uses LangGraphService for advanced document Q&A and citation-aware responses.
    - Method used: simple_document_qa.
    - Called by generate_response_with_langgraph method.

6. cfin/backend/repositories/document_repository.py (indirect, via _prepare_document_for_citation):
    - Used to fetch PDF binary content from storage if not present in the document dictionary.
    - Method used: get_document_file_content.
    - Called when preparing documents for citation.

7. cfin/backend/services/conversation_service.py:
    - ConversationService initializes and uses this service for all document Q&A interactions.
    - Used for document understanding, response generation, and citation extraction in conversations.

8. cfin/backend/pdf_processing/document_service.py:
    - DocumentService initializes and uses this service for all PDF processing.
    - Uses process_pdf method to handle document upload processing.

Typical Usage in Application Flow:
- Called by DocumentService for PDF processing and extraction.
- Used by ConversationService for generating responses to user queries with citation support.
- Used by AnalysisService for tool-based financial analysis and visualization generation.

Note:
This file is central to the backend's AI/LLM capabilities and is designed to be the single point of interaction with Anthropic Claude for all document analysis, extraction, and Q&A tasks. It is tightly integrated with the backend's document, citation, and analysis models, and is responsible for ensuring all downstream consumers (including the frontend) receive consistent, citation-rich, and structured data.
"""



import os
import base64
import asyncio
import json
import re
import uuid
from typing import Dict, List, Optional, Any, Tuple, Union, TYPE_CHECKING, ForwardRef
import logging
from anthropic import AsyncAnthropic
from anthropic.types import Message as AnthropicMessage, ToolUseBlock
import string
from datetime import datetime
import contextlib
import httpx

from models.document import ProcessedDocument, Citation as DocumentCitation, DocumentContentType, DocumentMetadata, ProcessingStatus
from models.citation import Citation, CitationType, CharLocationCitation, PageLocationCitation, ContentBlockLocationCitation
from pdf_processing.langchain_service import LangChainService
from utils.database import get_db

# Set up logger
logger = logging.getLogger(__name__)

# Create a ToolSchema type reference for type checking
if TYPE_CHECKING:
    from models.tools import ToolSchema
else:
    ToolSchema = ForwardRef('ToolSchema')

# Import tool models
try:
    from models.tools import ToolSchema, ALL_TOOLS, ALL_TOOLS_DICT
    TOOLS_SUPPORT = True
except ImportError as e:
    TOOLS_SUPPORT = False
    logger.warning(f"Tools import failed: {e}. Tools features will be disabled.")
except Exception as e:
    TOOLS_SUPPORT = False
    logger.warning(f"Tools unexpected error: {e}. Tools features will be disabled.")

# Refined System Prompt for Tool Usage
FINANCIAL_ANALYSIS_SYSTEM_PROMPT = """You are an expert financial analyst. Your primary task is to analyze the provided financial document(s) and respond to the user's query.

CRITICAL INSTRUCTION: Whenever you need to present data in a chart, graph, or table format, you MUST use the provided tools ('generate_graph_data' for charts, 'generate_table_data' for tables). Do NOT describe chart data or table data in plain text. Use the tools to generate the structured JSON required for visualization based on their input schemas.

Analysis Steps:
1. Understand the user's query in the context of the provided document(s).
2. Extract relevant financial figures, metrics, trends, and tables from the document(s).
3. If the query requires a chart or graph visualization, use the 'generate_graph_data' tool. Ensure the chartType, config, data, and chartConfig match the tool's input schema precisely.
4. If the query requires presenting detailed data in a table, use the 'generate_table_data' tool. Ensure the tableType, config, columns, and data match the tool's input schema precisely.
5. Provide a concise textual analysis summarizing key findings and directly answering the user's query, referencing the generated visualizations/tables where appropriate (e.g., "As shown in the Revenue Trend chart...").
"""

@contextlib.asynccontextmanager
async def get_anthropic_client():
    """
    Context manager to get an Anthropic client.
    This function helps avoid circular imports between modules.
    
    Yields:
        AsyncAnthropic: An Anthropic API client
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
    
    client = AsyncAnthropic(api_key=api_key)
    try:
        yield client
    finally:
        # No need to close the client explicitly as AsyncAnthropic handles this
        pass

# Conditionally import LangGraphService
try:
    from pdf_processing.langgraph_service import LangGraphService
    LANGGRAPH_AVAILABLE = True
except ImportError as e:
    LANGGRAPH_AVAILABLE = False
    logger.warning(f"LangGraph import failed: {e}. LangGraph features will be disabled.")
except Exception as e:
    LANGGRAPH_AVAILABLE = False
    logger.warning(f"LangGraph unexpected error: {e}. LangGraph features will be disabled.")


class ClaudeService:
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Claude API service with API key from parameter or environment variable.
        Configures AsyncAnthropic client with the API key.
        
        Args:
            api_key: Optional API key to use instead of environment variable
        """
        # Try to get API key from parameter first, then environment
        self.api_key = api_key
        if not self.api_key:
            self.api_key = os.environ.get("ANTHROPIC_API_KEY")
            logger.info("Using ANTHROPIC_API_KEY from environment variables")
        
        if not self.api_key:
            logger.warning("Missing ANTHROPIC_API_KEY environment variable or API key parameter")
            self.client = None
            return
        
        # Mask API key for logging (show first 8 chars and last 4)
        if len(self.api_key) > 12:
            masked_key = f"{self.api_key[:8]}...{self.api_key[-4:]}"
        else:
            masked_key = "***masked***"
        
        logger.info(f"Initializing Claude API with key prefix: {masked_key}")
        
        # Using Claude 3.5 Sonnet for enhanced PDF support and citations
        self.model = "claude-3-5-sonnet-latest"  # Use the latest model version that supports citations
        try:
            self.client = AsyncAnthropic(
                api_key=self.api_key,
                # No longer need to specify the PDF beta feature - it's built into the API now
            )
            logger.info(f"ClaudeService initialized with model: {self.model} and PDF support")
        except Exception as e:
            logger.error(f"Failed to initialize AsyncAnthropic client: {str(e)}")
            self.client = None
        
        # Initialize LangChain service
        self.langchain_service = LangChainService()
        
        # Initialize LangGraph service if available
        if LANGGRAPH_AVAILABLE:
            try:
                self.langgraph_service = LangGraphService()
                logger.info("LangGraph service successfully initialized")
            except ValueError as e:
                logger.error(f"LangGraph service configuration error: {str(e)}")
                self.langgraph_service = None
            except Exception as e:
                logger.error(f"Failed to initialize LangGraph service: {str(e)}")
                self.langgraph_service = None
        else:
            logger.warning("LangGraph service not available, skipping initialization")
            self.langgraph_service = None

    async def generate_response(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 4000
    ) -> str:
        """
        Generate a response from Claude based on a conversation with a system prompt.
        
        Args:
            system_prompt: System prompt that guides Claude's behavior
            messages: List of message dictionaries with 'role' and 'content' keys
            temperature: Temperature for generation (0.0 to 1.0)
            max_tokens: Maximum number of tokens to generate
            
        Returns:
            Generated response text
        """
        if not self.client:
            # Mock response for testing or when API key is not available
            logger.warning("Using mock response because Claude API client is not available")
            return "I'm sorry, I cannot process your request because the Claude API is not configured properly. Please check the API key and try again."
        
        try:
            # Convert message format to Anthropic's format
            formatted_messages = []
            for msg in messages:
                role = "user" if msg["role"] == "user" else "assistant"
                formatted_messages.append({"role": role, "content": msg["content"]})
            
            logger.info(f"Sending request to Claude API with {len(formatted_messages)} messages")
            
            # Call Claude API
            response = await self.client.messages.create(
                model=self.model,
                system=system_prompt,
                messages=formatted_messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return response.content[0].text
        except Exception as e:
            logger.error(f"Error calling Claude API: {str(e)}")
            error_message = f"I apologize, but there was an error processing your request: {str(e)}"
            return error_message

    async def process_pdf(self, pdf_data: bytes, filename: str) -> Tuple[ProcessedDocument, List[DocumentCitation]]:
        """
        Process a PDF using Claude's PDF support and citation extraction.
        
        Args:
            pdf_data: Raw bytes of the PDF file
            filename: Name of the PDF file
            
        Returns:
            A tuple containing the processed document and a list of citations
        """
        if not self.client:
            logger.error("Cannot process PDF because Claude API client is not available")
            raise ValueError("Claude API client is not available. Check your API key.")
        
        try:
            logger.info(f"Processing PDF: {filename} with Claude API and citations support")
            
            # Encode PDF data as base64
            pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')
            
            # Step 1: Analyze document to determine type and periods (using pdf_base64)
            logger.info("Analyzing document type")
            document_type, periods = await self._analyze_document_type(pdf_base64, filename) # Ensure this uses pdf_base64
            logger.info(f"Document classified as: {document_type.value} with periods: {periods}")
            
            # Step 2: Extract financial data and citations (using pdf_content)
            # This method should be the source of truth for extracted_data, including any raw_text if provided by Claude.
            logger.info("Extracting financial data and citations")
            extracted_data, citations = await self._extract_financial_data_with_citations(
                pdf_content=pdf_data, 
                filename=filename, 
                document_type=document_type
            )
            logger.info(f"Extracted {len(citations)} citations")

            # Attempt to get raw_text from Claude's response if available
            raw_text = extracted_data.get("raw_text", "") # Default to empty string

            # Log and return a warning if we still couldn't get any text from Claude
            if not raw_text or len(raw_text.strip()) == 0:
                logger.warning(f"Claude did not return text content for PDF {filename}")
                # Create minimal raw text to avoid downstream issues, and ensure it's in extracted_data
                raw_text = f"No text content was returned by the AI for {filename}. The document might be image-based or have an unusual format."
                if not extracted_data: # Should not happen if _extract_financial_data_with_citations returns a dict
                    extracted_data = {}
                extracted_data["raw_text"] = raw_text # Ensure raw_text is part of extracted_data
            else:
                logger.info(f"Using raw text from Claude's response: {len(raw_text)} characters")

            # Ensure extracted_data is not None before proceeding
            if extracted_data is None: # Should be populated by _extract_financial_data_with_citations
                extracted_data = {"raw_text": raw_text} 
            elif "raw_text" not in extracted_data: # Ensure raw_text key exists
                 extracted_data["raw_text"] = raw_text
            
            logger.info(f"Extracted data keys: {list(extracted_data.keys())}")
            
            # If we have financial data, update document type to FINANCIAL_REPORT if it wasn't already
            if extracted_data.get('financial_data') and extracted_data['financial_data']:
                if document_type != DocumentContentType.FINANCIAL_REPORT:
                    logger.info(f"Updating document type from {document_type.value} to FINANCIAL_REPORT based on extracted financial data")
                    document_type = DocumentContentType.FINANCIAL_REPORT
            
            # Create document metadata and processed document object
            document_id = str(uuid.uuid4())
            confidence_score = 0.8  # Default confidence score
            
            # Create document metadata
            metadata = DocumentMetadata(
                id=uuid.UUID(document_id),
                filename=filename,
                upload_timestamp=datetime.now(),
                file_size=len(pdf_data),
                mime_type="application/pdf",
                user_id="system"  # Default user for API processing
            )
            
            # Create processed document
            processed_document = ProcessedDocument(
                metadata=metadata,  # Include the required metadata
                content_type=document_type,
                extraction_timestamp=datetime.now(),
                periods=periods,
                extracted_data=extracted_data,
                confidence_score=confidence_score,
                processing_status=ProcessingStatus.COMPLETED
            )
            
            return processed_document, citations
            
        except Exception as e:
            logger.exception(f"Error processing PDF: {e}")
            
            # Create minimal document with error information
            document_id = str(uuid.uuid4())
            metadata = DocumentMetadata(
                id=uuid.UUID(document_id),
                filename=filename,
                upload_timestamp=datetime.now(),
                file_size=len(pdf_data) if pdf_data else 0,
                mime_type="application/pdf",
                user_id="system"
            )
            
            error_message = f"Error processing PDF: {str(e)}"
            processed_document = ProcessedDocument(
                metadata=metadata,
                content_type=DocumentContentType.OTHER,
                extraction_timestamp=datetime.now(),
                extracted_data={"error": error_message, "raw_text": f"Failed to process document due to error: {str(e)}"},
                confidence_score=0.0,
                processing_status=ProcessingStatus.FAILED
            )
            
            return processed_document, []

    async def _analyze_document_type(self, pdf_base64: str, filename: str) -> Tuple[DocumentContentType, List[str]]:
        """
        Analyze the PDF to determine its document type and extract time periods.
        Uses the new document content format but doesn't need citations for this step.
        
        Args:
            pdf_base64: Base64 encoded PDF data
            filename: Name of the PDF file
            
        Returns:
            Tuple of document type and list of time periods
        """
        if not self.client:
            logger.error("Cannot analyze document type because Claude API client is not available")
            raise ValueError("Claude API client is not available. Check your API key.")
        
        try:
            logger.info(f"Analyzing document type for: {filename}")
            
            # Create messages using the new document format
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": pdf_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": "Analyze this financial document. Determine if it's a balance sheet, income statement, cash flow statement, or other type of document. Also identify the time periods covered (e.g., Q1 2023, FY 2022, etc.). Return ONLY a JSON response in this format:\n\n{\n  \"document_type\": \"balance_sheet|income_statement|cash_flow|notes|other\",\n  \"periods\": [\"period1\", \"period2\", ...]\n}"
                        }
                    ]
                }
            ]
            
            # Call Claude API
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=messages
            )
            
            # Extract JSON from the response
            result_text = response.content[0].text
            json_match = re.search(r'{.*}', result_text, re.DOTALL)
            if not json_match:
                logger.error(f"Could not extract JSON from response: {result_text[:100]}...")
                return DocumentContentType.OTHER, []
            
            # Parse the JSON response
            try:
                result = json.loads(json_match.group(0))
                
                # Handle pipe-separated document types (e.g., "balance_sheet|income_statement")
                doc_type_str = result.get("document_type", "other")
                logger.info(f"Raw document_type from Claude: {doc_type_str}")
                
                # Split by pipe if present and try each type
                if "|" in doc_type_str:
                    doc_types = doc_type_str.split("|")
                    # Try each type in order
                    for dt in doc_types:
                        dt = dt.strip()
                        try:
                            document_type = DocumentContentType(dt)
                            logger.info(f"Selected document type '{dt}' from combined types: {doc_type_str}")
                            break
                        except ValueError:
                            pass
                    else:
                        # If no valid type found, use OTHER
                        logger.warning(f"No valid document type found in '{doc_type_str}', using OTHER")
                        document_type = DocumentContentType.OTHER
                else:
                    # Single document type
                    try:
                        document_type = DocumentContentType(doc_type_str)
                    except ValueError:
                        logger.warning(f"Invalid document type '{doc_type_str}', using OTHER")
                        document_type = DocumentContentType.OTHER
                
                periods = result.get("periods", [])
                
                logger.info(f"Document classified as {document_type.value} with periods: {periods}")
                return document_type, periods
            except Exception as json_e:
                logger.error(f"Error parsing JSON response: {json_e}")
                return DocumentContentType.OTHER, []
            
        except Exception as e:
            logger.exception(f"Error in document type analysis: {e}")
            return DocumentContentType.OTHER, []

    async def _extract_financial_data_with_citations(self, pdf_content: bytes, filename: str = "document.pdf", document_type: DocumentContentType = None) -> Tuple[Dict[str, Any], List[Any]]:
        """
        Extract financial data from a PDF with citations.
        
        Args:
            pdf_content: PDF file content as bytes or base64 string
            filename: Name of the PDF file
            document_type: Type of document being processed
            
        Returns:
            Tuple of extracted data dictionary and list of citations
        """
        if not self.client:
            logger.error("Cannot extract financial data because Claude API client is not available")
            raise ValueError("Claude API client is not available. Check your API key.")
        
        try:
            logger.info(f"Extracting financial data with citations from: {filename}")
            
            # Convert to base64 if needed
            if isinstance(pdf_content, bytes):
                pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
            else:
                pdf_base64 = pdf_content
            
            # Prepare document type for the prompt
            doc_type_str = document_type.value if document_type else "financial document"
            
            # Financial analysis prompt with structured data extraction
            system_prompt = """You are a highly specialized financial document analysis assistant. Extract structured financial data from the document accurately.
Follow these guidelines:
1. Identify all financial tables and metrics
2. Extract values with their correct time periods, labels, and units
3. Present the data in a structured JSON format
4. Provide citations for all extracted data"""
            
            # Create messages with the PDF document
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": pdf_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": f"Analyze this {doc_type_str} and extract all financial data in a structured format. Include key metrics, time periods, and values. Return a comprehensive JSON with all the financial information."
                        }
                    ]
                }
            ]
            
            # Call Claude API with citations enabled
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                system=system_prompt,
                messages=messages
            )
            
            # Extract text content and citations
            content = self._process_claude_response(response)
            text = content.get("text", "")
            citations = content.get("citations", [])
            
            # Parse the extracted data from the response text
            extracted_data = {}
            try:
                # Check for JSON format in the response
                json_match = re.search(r'```json\s*([\s\S]*?)\s*```|{[\s\S]*}', text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1) if json_match.group(1) else json_match.group(0)
                    # Clean up the JSON string if needed
                    json_str = re.sub(r'^```json\s*|\s*```$', '', json_str)
                    json_data = json.loads(json_str)
                    extracted_data = json_data
                else:
                    logger.warning("Could not find JSON data in Claude's response")
                    extracted_data = {"raw_text": text}
            except Exception as e:
                logger.error(f"Error parsing extracted data JSON: {str(e)}")
                extracted_data = {"raw_text": text, "error": str(e)}
            
            return extracted_data, citations
            
        except Exception as e:
            logger.error(f"Error extracting financial data: {str(e)}")
            return {"error": str(e)}, []

    async def generate_response_with_langgraph(
        self,
        question: str,
        document_texts: List[Dict[str, Any]],
        conversation_history: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a response using LangGraph for document Q&A.
        This is a lighter-weight alternative to running the full conversation graph.
        Supports Claude's citation feature for accurate document references.
        
        Args:
            question: The user's question
            document_texts: List of documents with their text content
            conversation_history: Previous conversation messages
            
        Returns:
            Dictionary containing the response text and any extracted citations
        """
        # Critical logging for document processing diagnosis
        logger.info(f"===== Claude API document processing request =====")
        logger.info(f"Question: {question[:100]}" + ("..." if len(question) > 100 else ""))
        logger.info(f"Number of documents: {len(document_texts)}")
        logger.info(f"History length: {len(conversation_history) if conversation_history else 0}")
        
        # Log document IDs for tracing
        doc_ids = [doc.get('id', 'unknown') for doc in document_texts]
        logger.info(f"Document IDs in request: {doc_ids}")
        
        # Check document content existence 
        for i, doc in enumerate(document_texts):
            doc_id = doc.get('id', f'doc_{i}')
            has_content = False
            
            # Check various possible content fields
            if 'raw_text' in doc and doc['raw_text']:
                has_content = True
                logger.info(f"Document {doc_id} has raw_text content: {len(doc['raw_text'])} chars")
            elif 'content' in doc and isinstance(doc['content'], str) and doc['content']:
                has_content = True
                logger.info(f"Document {doc_id} has string content: {len(doc['content'])} chars")
            elif 'text' in doc and doc['text']:
                has_content = True
                logger.info(f"Document {doc_id} has text content: {len(doc['text'])} chars")
            elif 'extracted_data' in doc and doc['extracted_data']:
                extracted_type = type(doc['extracted_data']).__name__
                logger.info(f"Document {doc_id} has extracted_data of type: {extracted_type}")
                
                if isinstance(doc['extracted_data'], dict) and 'raw_text' in doc['extracted_data']:
                    has_content = True
                    logger.info(f"Document {doc_id} has extracted_data.raw_text: {len(doc['extracted_data']['raw_text'])} chars")
            
            if not has_content:
                logger.warning(f"⚠️ Document {doc_id} has no usable text content! This may cause visibility issues.")
                logger.warning(f"Available keys: {list(doc.keys())}")
        
        logger.info(f"===== End Claude API document request information =====")
        
        if not LANGGRAPH_AVAILABLE or not self.langgraph_service:
            logger.warning("LangGraph service is not available, falling back to LangChain")
            # Fall back to LangChain if LangGraph is not available
            if self.langchain_service:
                logger.info("Using LangChain for response generation")
                response_text = await self.langchain_service.analyze_document_content(
                    question=question,
                    # Use "raw_text" key, consistent with how document_texts is now prepared
                    document_extracts=[doc.get("raw_text", "") for doc in document_texts if doc.get("raw_text")], # Ensure we only pass non-empty raw_text
                    conversation_history=conversation_history
                )
                return {
                    "content": response_text,
                    "citations": []  # No citations with LangChain fallback
                }
            else:
                logger.warning("LangChain service is not available, falling back to direct Claude API")
                # Fall back to regular response generation
                system_prompt = "You are a financial document analysis assistant. Answer questions based on your knowledge."
                messages = []
                
                # Add conversation history to messages
                if conversation_history:
                    for msg in conversation_history:
                        messages.append(msg)
                
                # Add current question
                messages.append({"role": "user", "content": question})
                
                response_text = await self.generate_response(
                    system_prompt=system_prompt,
                    messages=messages
                )
                return {
                    "content": response_text,
                    "citations": []  # No citations with direct API fallback
                }
        
        try:
            logger.info(f"Using LangGraph for response generation with {len(document_texts)} documents")
            # Use LangGraph service for document QA with citation support
            response = await self.langgraph_service.simple_document_qa(
                question=question,
                documents=document_texts,
                conversation_history=conversation_history
            )
            
            # Handle the response, which should now be a dictionary with content and citations
            if isinstance(response, dict):
                content = response.get("content", "")
                citations = response.get("citations", [])
                
                logger.info(f"Generated response with {len(citations)} citations")
                
                # Return the structured response with citations
                return {
                    "content": content,
                    "citations": citations
                }
            elif isinstance(response, str):
                # Handle legacy response format (string only)
                logger.warning("Received legacy string response from simple_document_qa")
                return {
                    "content": response,
                    "citations": []
                }
            else:
                # Handle unexpected response type
                logger.error(f"Unexpected response type from simple_document_qa: {type(response)}")
                return {
                    "content": "I apologize, but there was an error processing your request.",
                    "citations": []
                }
                
        except Exception as e:
            logger.error(f"Error in generate_response_with_langgraph: {str(e)}", exc_info=True)
            return {
                "content": f"I apologize, but there was an error processing your request: {str(e)}",
                "citations": []
            }

    async def extract_structured_financial_data(self, text: str, pdf_data: bytes = None, filename: str = None) -> Dict[str, Any]:
        """
        Extract structured financial data from raw text using Claude.
        This is a fallback method when standard extraction fails to find financial tables.
        
        Args:
            text: Raw text from a document
            pdf_data: Optional raw bytes of the PDF file for improved extraction with native PDF support
            filename: Optional filename of the PDF
            
        Returns:
            Dictionary of structured financial data
        """
        if not self.client:
            logger.error("Cannot extract structured data because Claude API client is not available")
            return {"error": "Claude API client is not available"}
        
        try:
            logger.info("Attempting to extract structured financial data from text")
            
            # Create a specialized prompt for financial data extraction
            extraction_prompt = """Please analyze this financial document text and extract structured financial data.
            
            Output the data in the following JSON format:
            {
                "metrics": [
                    {"name": "Revenue", "value": 1000000, "period": "2023", "unit": "USD"},
                    {"name": "Net Income", "value": 200000, "period": "2023", "unit": "USD"}
                ],
                "ratios": [
                    {"name": "Profit Margin", "value": 0.2, "description": "Net income divided by revenue"}
                ],
                "periods": ["2023", "2022"],
                "key_insights": [
                    "Revenue increased by 15% from 2022 to 2023",
                    "Profit margin improved from 15% to 20%"
                ]
            }
            
            If you can identify any financial statements (income statement, balance sheet, cash flow), please structure them accordingly.
            Be sure to extract specific numbers, dates, and proper units.
            If you cannot find specific financial data, return an empty object for that category."""
            
            # Setup system prompt
            system_prompt = """You are a financial data extraction assistant. Your task is to extract structured financial data from text.
            Always output valid JSON. If specific financial metrics are not available, include empty arrays in those categories.
            Be precise with numbers and dates. Recognize financial statements and extract metrics, ratios, and insights."""
            
            # Prepare messages
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": extraction_prompt
                        }
                    ]
                }
            ]
            
            # If we have PDF data, use it with the document content type for better extraction
            if pdf_data:
                logger.info(f"Using native PDF document support for financial data extraction")
                
                # Prepare the document for citation using our enhanced method
                document = {
                    "id": "financial_document",
                    "title": filename if filename else "Financial Document",
                    "content": pdf_data,
                    "mime_type": "application/pdf"
                }
                
                prepared_document = await self._prepare_document_for_citation(document)
                if not prepared_document:
                    logger.warning("Failed to prepare document for financial data extraction, falling back to text")
                else:
                    # Add the prepared document as content in the user message
                    messages.append({
                        "role": "user",
                        "content": [prepared_document]
                    })
            else:
                # Fall back to using just the text content
                logger.info("Using text-only mode for financial data extraction")
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": text[:15000]  # Limit text length
                        }
                    ]
                })
            
            # Call Claude API
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=messages,
                system=system_prompt,
                temperature=0.0  # Use low temperature for factual extraction
            )
            
            # Extract the JSON from the response
            response_text = response.content[0].text if response.content else ""
            
            # Find JSON in the response
            json_pattern = r'```json\s*([\s\S]*?)\s*```|{[\s\S]*}'
            json_match = re.search(json_pattern, response_text)
            
            if json_match:
                json_str = json_match.group(1) if json_match.group(1) else json_match.group(0)
                try:
                    structured_data = json.loads(json_str)
                    logger.info(f"Successfully extracted structured financial data: {len(structured_data)} categories")
                    return structured_data
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON from Claude response: {e}")
                    return {"error": "Failed to parse financial data", "raw_response": response_text}
            else:
                logger.error("No JSON data found in Claude response")
                return {"error": "No structured data found in response", "raw_response": response_text}
        
        except Exception as e:
            logger.exception(f"Error in structured financial data extraction: {e}")
            return {"error": f"Extraction failed: {str(e)}"}

    # --- NEW METHOD for Tool-Based Analysis ---

    async def analyze_with_visualization_tools(
        self,
        document_text: str,
        user_query: str,
        knowledge_base: str = ""
    ) -> Dict[str, Any]:
        """
        Analyze a financial document using Claude with tool support for visualizations.

        Args:
            document_text: Text content of the financial document.
            user_query: The user's specific question or analysis request.
            knowledge_base: Optional additional context or domain knowledge.

        Returns:
            A dictionary containing:
            - "analysis_text": The textual analysis from Claude.
            - "visualizations": A dict with "charts": [...] and "tables": [...]
                                containing the structured JSON data generated by tools.
        """
        if not self.client:
            logger.error("Cannot analyze document because Claude API client is not available.")
            return {
                "analysis_text": "Error: Claude API client not configured.",
                "visualizations": {"charts": [], "tables": []}
            }

        try:
            logger.info(f"Starting analysis with visualization tools for query: '{user_query[:50]}...'")

            # Prepare the user message content, including the document text and knowledge base
            user_content_parts = [
                {"type": "text", "text": "Analyze the following financial document(s):"}
            ]

            # Add document text - using text type for simplicity here
            # In a more robust implementation, we might pass the PDF directly if available
            user_content_parts.append({
                "type": "text",
                "text": f"<financial_document>\n{document_text}\n</financial_document>"
            })

            if knowledge_base:
                user_content_parts.append({
                    "type": "text",
                    "text": f"<knowledge_base>\n{knowledge_base}\n</knowledge_base>"
                })

            user_content_parts.append({
                "type": "text",
                "text": f"\nUser Query: {user_query}"
            })

            # Prepare messages list for Claude API
            messages = [{"role": "user", "content": user_content_parts}]

            # Log request details
            logger.debug(f"Sending request to Claude with {len(messages)} message(s) and {len(ALL_TOOLS_DICT)} tools.")

            # Call Claude API with tools
            response = await self.client.messages.create(
                model=self.model,
                system=FINANCIAL_ANALYSIS_SYSTEM_PROMPT,  # Use the refined system prompt
                messages=messages,
                tools=ALL_TOOLS_DICT,
                tool_choice={"type": "any"},
                temperature=0.3, # Lower temp for more factual/structured output
                max_tokens=4096  # Maximize token limit for complex responses
            )

            logger.info("Received response from Claude API.")
            #logger.debug(f"Claude Raw Response: {response}") # Careful logging raw response

            # Process the response to extract text and tool uses
            processed_result = self._process_tool_calls(response)

            logger.info(f"Analysis complete. Text length: {len(processed_result['analysis_text'])}. "
                        f"Charts: {len(processed_result['visualizations']['charts'])}. "
                        f"Tables: {len(processed_result['visualizations']['tables'])}.")

            return processed_result

        except Exception as e:
            logger.exception(f"Error during analysis with visualization tools: {e}")
            return {
                "analysis_text": f"An error occurred during analysis: {e}",
                "visualizations": {"charts": [], "tables": []}
            }

    def _process_tool_calls(self, response: AnthropicMessage) -> Dict[str, Any]:
        """
        Processes Claude's response, extracting text and structured data from tool calls.
        The method transforms the raw tool_input into properly formatted chart and table data
        that can be correctly rendered by the frontend components.

        Args:
            response: The AnthropicMessage object received from the API.

        Returns:
            A dictionary containing 'analysis_text' and 'visualizations' (with 'charts' and 'tables').
        """
        analysis_text = ""
        charts = []
        tables = []

        if not response.content:
            logger.warning("Claude response has no content.")
            return {
                "analysis_text": "No content received from analysis.",
                "visualizations": {"charts": [], "tables": []}
            }

        for block in response.content:
            if block.type == "text":
                analysis_text += block.text + "\n"
            elif block.type == "tool_use":
                tool_name = block.name
                tool_input = block.input

                logger.info(f"Processing tool use: {tool_name}")
                #logger.debug(f"Tool Input: {json.dumps(tool_input, indent=2)}") # Log tool input for debugging

                processed_data = self._process_visualization_input(tool_name, tool_input, block.id)
                if processed_data:
                    if tool_name == "generate_graph_data":
                        charts.append(processed_data)
                        logger.info(f"Successfully processed chart data for tool ID {block.id}")
                    elif tool_name == "generate_table_data":
                        tables.append(processed_data)
                        logger.info(f"Successfully processed table data for tool ID {block.id}")
                else:
                    logger.warning(f"Failed to process {tool_name} data for tool ID {block.id}")
                    analysis_text += f"\n[Note: Failed to process visualization data for tool {block.id}]\n"
            else:
                logger.warning(f"Unsupported content block type: {block.type}")

        return {
            "analysis_text": analysis_text.strip(),
            "visualizations": {
                "charts": charts,
                "tables": tables
            }
        }
    
    def _process_visualization_input(self, tool_name: str, tool_input: Dict[str, Any], block_id: str) -> Optional[Dict[str, Any]]:
        """
        Process the raw input provided by Claude to the visualization tools and transform it
        into the final renderable structure expected by the frontend.
        
        Args:
            tool_name: The name of the tool being used
            tool_input: The raw input provided to the tool
            block_id: The ID of the tool_use block
            
        Returns:
            Processed chart or table data, or None if processing failed
        """
        try:
            if tool_name == "generate_graph_data":
                return self._process_chart_input(tool_input)
            elif tool_name == "generate_table_data":
                return self._process_table_input(tool_input)
            else:
                logger.warning(f"Unsupported tool: {tool_name}")
                return None
        except Exception as e:
            logger.error(f"Error processing {tool_name} input (ID: {block_id}): {e}")
            return None
    
    def _process_chart_input(self, tool_input: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process the raw chart input from the tool into a properly formatted chart data structure
        that can be rendered by the frontend.
        
        Args:
            tool_input: The raw input provided to the generate_graph_data tool
            
        Returns:
            Processed chart data for frontend rendering
        """
        # Basic validation
        if not isinstance(tool_input, dict):
            logger.warning("Chart input is not a dictionary")
            return None
            
        if not all(key in tool_input for key in ["chartType", "config", "data"]):
            logger.warning("Chart input missing required keys")
            return None
            
        # Create a copy to avoid modifying the original
        processed_chart = tool_input.copy()
        chart_type = processed_chart.get("chartType")
        
        # Define default chart colors for consistent visualization
        CHART_COLORS = [
            "#8884d8", "#82ca9d", "#ffc658", "#ff8042", "#0088fe", 
            "#00c49f", "#ffbb28", "#ff8042", "#a4de6c", "#d0ed57"
        ]
        
        # Process the chart based on its type
        try:
            if chart_type in ["line", "multiBar", "stackedArea"]:
                # Ensure data structure is correct for multi-series charts
                if not processed_chart.get("chartConfig"):
                    processed_chart["chartConfig"] = {}
                
                # Set default colors if not provided
                if "chartConfig" in processed_chart:
                    for i, (key, metric_config) in enumerate(processed_chart["chartConfig"].items()):
                        if not metric_config.get("color"):
                            color_index = i % len(CHART_COLORS)
                            metric_config["color"] = CHART_COLORS[color_index]
                
                # Ensure xAxisKey is set
                if "config" in processed_chart and not processed_chart["config"].get("xAxisKey"):
                    # Default to "name" or first key that looks like a category/period
                    if processed_chart["data"] and len(processed_chart["data"]) > 0:
                        possible_keys = ["name", "period", "category", "date", "month", "year", "quarter"]
                        data_keys = list(processed_chart["data"][0].keys())
                        
                        for possible_key in possible_keys:
                            if possible_key in data_keys:
                                processed_chart["config"]["xAxisKey"] = possible_key
                                break
                        
                        if not processed_chart["config"].get("xAxisKey"):
                            # Just use the first key that's not a value
                            for key in data_keys:
                                if not isinstance(processed_chart["data"][0][key], (int, float)):
                                    processed_chart["config"]["xAxisKey"] = key
                                    break
            
            elif chart_type == "pie":
                # Process pie chart data - ensure name/value structure and calculate total
                if "data" in processed_chart and processed_chart["data"]:
                    total_value = 0
                    
                    # Ensure each data item has name and value keys
                    for item in processed_chart["data"]:
                        # Sometimes pie data comes with 'segment' instead of 'name'
                        if "segment" in item and "name" not in item:
                            item["name"] = item["segment"]
                        
                        # Calculate total for all values
                        if "value" in item and isinstance(item["value"], (int, float)):
                            total_value += item["value"]
                    
                    # Add total to config
                    if "config" in processed_chart:
                        processed_chart["config"]["totalValue"] = total_value
                        if not processed_chart["config"].get("totalLabel"):
                            processed_chart["config"]["totalLabel"] = "Total"
                
                # Add default chartConfig with colors if missing
                if "chartConfig" not in processed_chart or not processed_chart["chartConfig"]:
                    processed_chart["chartConfig"] = {}
                    for i, item in enumerate(processed_chart["data"]):
                        color_index = i % len(CHART_COLORS)
                        key = item.get("name", f"segment{i}")
                        processed_chart["chartConfig"][key] = {
                            "label": key,
                            "color": CHART_COLORS[color_index]
                        }
            
            elif chart_type in ["bar", "scatter"]:
                # Ensure basic structure is valid
                if "chartConfig" not in processed_chart or not processed_chart["chartConfig"]:
                    processed_chart["chartConfig"] = {}
                    
                    # Find all possible data keys that aren't the x-axis key
                    x_axis_key = processed_chart["config"].get("xAxisKey", "name")
                    if processed_chart["data"] and len(processed_chart["data"]) > 0:
                        data_keys = [k for k in processed_chart["data"][0].keys() if k != x_axis_key]
                        
                        # Create chartConfig for each data key
                        for i, key in enumerate(data_keys):
                            if key not in processed_chart["chartConfig"]:
                                color_index = i % len(CHART_COLORS)
                                processed_chart["chartConfig"][key] = {
                                    "label": key.capitalize(),
                                    "color": CHART_COLORS[color_index]
                                }
            
            # Return the processed chart data
            return processed_chart
            
        except Exception as e:
            logger.error(f"Error processing chart data: {e}")
            return tool_input  # Fall back to the original input if processing fails
    
    def _process_table_input(self, tool_input: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process the raw table input from the tool into a properly formatted table data structure
        that can be rendered by the frontend.
        
        Args:
            tool_input: The raw input provided to the generate_table_data tool
            
        Returns:
            Processed table data for frontend rendering
        """
        # Basic validation
        if not isinstance(tool_input, dict):
            logger.warning("Table input is not a dictionary")
            return None
            
        if not all(key in tool_input for key in ["tableType", "config", "data"]):
            logger.warning("Table input missing required keys")
            return None
        
        # Create a copy to avoid modifying the original
        processed_table = tool_input.copy()
        
        try:
            # Validate config and columns
            if "config" in processed_table and "columns" in processed_table["config"]:
                # Ensure all columns have key and label
                for column in processed_table["config"]["columns"]:
                    if "key" not in column:
                        logger.warning("Column missing 'key' field")
                        if "label" in column:
                            # Use label as key if missing
                            column["key"] = column["label"].lower().replace(" ", "_")
                    
                    if "label" not in column:
                        # Use capitalized key as label if missing
                        column["label"] = column["key"].capitalize().replace("_", " ")
                    
                    # Set default format if not specified
                    if "format" not in column:
                        # Try to infer format from data
                        if processed_table["data"] and len(processed_table["data"]) > 0:
                            first_row = processed_table["data"][0]
                            if column["key"] in first_row:
                                value = first_row[column["key"]]
                                if isinstance(value, (int, float)):
                                    # Check if it looks like currency (has $ or is large number)
                                    if isinstance(value, int) and value > 1000:
                                        column["format"] = "currency"
                                    else:
                                        column["format"] = "number"
                                else:
                                    column["format"] = "text"
                            else:
                                column["format"] = "text"
                        else:
                            column["format"] = "text"
            
            # Return the processed table data
            return processed_table
            
        except Exception as e:
            logger.error(f"Error processing table data: {e}")
            return tool_input  # Fall back to the original input if processing fails

    async def _prepare_document_for_citation(self, document: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Prepare a document object for citation by Claude.
        
        Args:
            document: Document information dictionary
            
        Returns:
            Formatted document object for Claude API or None if invalid
        """
        try:
            # Extract document information
            doc_type = document.get("mime_type", "").lower()
            doc_id = document.get("id", "")
            doc_title = document.get("title", document.get("filename", f"Document {doc_id}"))
            
            # Try multiple sources for document content
            doc_content = None
            content_source = None
            
            # Log all available fields for debugging
            logger.info(f"Document fields: {list(document.keys())}")
            
            # First priority: "content" field
            if document.get("content"):
                doc_content = document.get("content")
                content_source = "content field"
            
            # Second priority: "raw_text" field
            elif document.get("raw_text"):
                doc_content = document.get("raw_text")
                content_source = "raw_text field"
                # For raw_text content, use text document type
                doc_type = "text/plain"
            
            # Third priority: "extracted_data.raw_text" field
            elif document.get("extracted_data") and isinstance(document.get("extracted_data"), dict) and document.get("extracted_data").get("raw_text"):
                doc_content = document.get("extracted_data").get("raw_text")
                content_source = "extracted_data.raw_text field"
                # For extracted text, use text document type
                doc_type = "text/plain"
            
            # Fourth priority: "text" field
            elif document.get("text"):
                doc_content = document.get("text")
                content_source = "text field"
                # For text content, use text document type
                doc_type = "text/plain"
                
            # Fifth priority: Try to get the raw PDF content from storage
            elif document.get("id"):
                try:
                    # Attempt to get the PDF data directly - this is a fallback mechanism
                    from repositories.document_repository import DocumentRepository
                    
                    # Get session and repository
                    async for db in get_db():
                        document_repository = DocumentRepository(db)
                        
                        # Get document content directly
                        doc_content = await document_repository.get_document_file_content(document.get('id'))
                        
                        if doc_content and len(doc_content) > 0:
                            content_source = "direct PDF from storage"
                            doc_type = "application/pdf"
                            logger.info(f"Retrieved PDF content directly from storage for document {doc_id}")
                except Exception as storage_e:
                    logger.warning(f"Failed to get PDF directly from storage for document {doc_id}: {storage_e}")
                    
            # If all attempts to get content failed, create a minimal document with placeholder text
            if not doc_content:
                logger.warning(f"No document content found for {doc_id} - using fallback placeholder")
                doc_content = f"Document content unavailable for {doc_title}. Please try re-uploading the document."
                content_source = "fallback placeholder"
                doc_type = "text/plain"
            
            if content_source:
                logger.info(f"Using {content_source} for document {doc_id}")
            
            # Handle PDF documents
            if "pdf" in doc_type or doc_type == "application/pdf":
                # Ensure PDF content is bytes
                if not isinstance(doc_content, bytes):
                    if isinstance(doc_content, str) and doc_content.startswith(('data:application/pdf;base64,', 'data:;base64,')):
                        # Handle base64 encoded PDF data URLs
                        base64_content = doc_content.split('base64,')[1]
                        doc_content = base64.b64decode(base64_content)
                    elif isinstance(doc_content, str) and len(doc_content) > 0:
                        try:
                            # Check if it might be base64 encoded
                            if all(c in string.ascii_letters + string.digits + '+/=' for c in doc_content):
                                try:
                                    doc_content = base64.b64decode(doc_content)
                                    logger.info(f"Successfully decoded base64 content for document {doc_id}")
                                except:
                                    # Not valid base64, treat as text
                                    logger.warning(f"Content for {doc_id} looks like base64 but couldn't be decoded")
                                    doc_content = doc_content.encode('utf-8')
                            else:
                                # Regular text, encode to bytes
                                doc_content = doc_content.encode('utf-8')
                        except Exception as e:
                            logger.warning(f"Failed to convert string content to bytes for {doc_id}: {e}")
                            return None
                    else:
                        logger.warning(f"Invalid PDF content for {doc_id} - not bytes or base64 string")
                        return None
                
                # Validate PDF content
                if len(doc_content) < 10:  # Arbitrary small size check
                    logger.warning(f"PDF content for {doc_id} is too small ({len(doc_content)} bytes)")
                    return None
                
                # Check if content starts with PDF signature
                if not doc_content.startswith(b'%PDF'):
                    logger.warning(f"Content for {doc_id} doesn't start with PDF signature")
                    # We'll still try to use it, as it might be a valid PDF despite missing the signature
                
                # Create PDF document object for Claude API
                try:
                    base64_data = base64.b64encode(doc_content).decode()
                    logger.info(f"Successfully encoded PDF content for document {doc_id} ({len(doc_content)} bytes)")
                    
                    # Format according to Anthropic's Citations documentation
                    return {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": base64_data
                        },
                        "title": doc_title,
                        "citations": {"enabled": True}
                    }
                except Exception as e:
                    logger.exception(f"Error encoding PDF content for {doc_id}: {e}")
                    return None
            
            # At this point, treat as text document (either originally or after conversion)
            # Ensure we have valid string content
            text_content = ""
            if isinstance(doc_content, str):
                text_content = doc_content
            elif isinstance(doc_content, bytes):
                try:
                    text_content = doc_content.decode('utf-8', errors='replace')
                except UnicodeDecodeError:
                    text_content = f"Binary content for {doc_title} (could not convert to text)"
            else:
                text_content = f"Content for {doc_title} in unsupported format: {type(doc_content)}"
            
            # Ensure we have some minimal content
            if not text_content.strip():
                text_content = f"Empty document content for {doc_title}"
            
            # Truncate very long text to avoid token limits (30,000 chars ~ 7,500 tokens)
            if len(text_content) > 30000:
                text_content = text_content[:30000] + f"\n\n[Document truncated due to length. Original size: {len(text_content)} characters]"
            
            logger.info(f"Prepared text document for Claude API: {doc_id}, length: {len(text_content)} chars")
            
            # Create proper text document format for Claude API
            return {
                "type": "document",
                "source": {
                    "type": "text",
                    "media_type": "text/plain",
                    "data": text_content
                },
                "title": doc_title,
                "citations": {"enabled": True}
            }
                
        except Exception as e:
            logger.exception(f"Error preparing document for citation: {e}")
            # Return a minimal valid document to prevent API errors
            return {
                "type": "document",
                "source": {
                    "type": "text",
                    "media_type": "text/plain",
                    "data": f"Error preparing document {document.get('id', 'unknown')} for citation: {str(e)}"
                },
                "title": document.get("title", document.get("filename", "Document")),
                "citations": {"enabled": True}
            }

    def _process_claude_response(self, response: AnthropicMessage) -> Dict[str, Any]:
        """
        Process Claude's response to extract content and citations.
        
        Args:
            response: Claude API response
            
        Returns:
            Processed response with text content and structured citations
        """
        result = {
            "text": "",
            "citations": []
        }
        
        # Extract text content
        if hasattr(response, "content") and response.content:
            # Combine all text content
            text_parts = []
            citations = []
            
            for block in response.content:
                if block.type == "text":
                    text_parts.append(block.text)
                    
                    # Process citations if available
                    if hasattr(block, "citations") and block.citations:
                        for citation in block.citations:
                            citation_obj = self._convert_claude_citation(citation)
                            if citation_obj:
                                citations.append(citation_obj)
            
            result["text"] = "\n".join(text_parts)
            result["citations"] = citations
        
        return result

    def _convert_claude_citation(self, citation: Any) -> Optional[Union[Dict[str, Any], Citation]]:
        """
        Convert Claude citation to our Citation model.
        
        Args:
            citation: Citation from Claude API
            
        Returns:
            Citation object or dictionary or None if conversion fails
        """
        try:
            # Handle both class attribute and dictionary access
            if hasattr(citation, 'type'):
                citation_type = citation.type
            elif isinstance(citation, dict):
                citation_type = citation.get('type')
            else:
                logger.warning(f"Unknown citation format: {type(citation)}")
                return None
            
            # Handle different citation types
            if citation_type == "page_citation" or citation_type == "page_location":
                # For PDF citations
                document_id = None
                # Only try to get document.id if the attribute exists
                if hasattr(citation, 'document') and hasattr(citation.document, 'id'):
                    document_id = citation.document.id
                elif isinstance(citation, dict) and 'document' in citation:
                    document_id = citation.get('document', {}).get('id')
                
                # Extract page information
                page_info = {}
                if hasattr(citation, 'page'):
                    page_info = {
                        'start_page': getattr(citation.page, 'start', 1),
                        'end_page': getattr(citation.page, 'end', 1)
                    }
                elif isinstance(citation, dict) and 'page' in citation:
                    page_info = {
                        'start_page': citation['page'].get('start', 1),
                        'end_page': citation['page'].get('end', 1)
                    }
                
                cited_text = ""
                if hasattr(citation, 'text'):
                    cited_text = citation.text
                elif isinstance(citation, dict):
                    cited_text = citation.get('text', '')
                
                return {
                    "type": "page_location",
                    "cited_text": cited_text,
                    "document_id": document_id,
                    "start_page_number": page_info.get('start_page', 1),
                    "end_page_number": page_info.get('end_page', 1)
                }
            
            elif citation_type in ["quote_citation", "text_citation", "char_location"]:
                # For text citations
                document_id = None
                # Only try to get document.id if the attribute exists
                if hasattr(citation, 'document') and hasattr(citation.document, 'id'):
                    document_id = citation.document.id
                elif isinstance(citation, dict) and 'document' in citation:
                    document_id = citation.get('document', {}).get('id')
                
                # Get cited text
                cited_text = ""
                if hasattr(citation, 'text'):
                    cited_text = citation.text
                elif hasattr(citation, 'cited_text'):
                    cited_text = citation.cited_text
                elif isinstance(citation, dict):
                    cited_text = citation.get('text', citation.get('cited_text', ''))
                
                # Get start and end indices if available
                start_index = 0
                end_index = 0
                
                # Handle different attribute names for character indices
                if hasattr(citation, 'start_index'):
                    start_index = citation.start_index
                elif hasattr(citation, 'start_char_index'):
                    start_index = citation.start_char_index
                elif isinstance(citation, dict):
                    start_index = citation.get('start_index', citation.get('start_char_index', 0))
                
                if hasattr(citation, 'end_index'):
                    end_index = citation.end_index
                elif hasattr(citation, 'end_char_index'):
                    end_index = citation.end_char_index
                elif isinstance(citation, dict):
                    end_index = citation.get('end_index', citation.get('end_char_index', 0))
                
                return {
                    "type": "char_location",
                    "cited_text": cited_text,
                    "document_id": document_id,
                    "start_char_index": start_index,
                    "end_char_index": end_index
                }
            
            else:
                logger.warning(f"Unknown citation type: {citation_type}")
                # Return a generic citation with available information
                if isinstance(citation, dict):
                    # Try to extract document info
                    document_id = citation.get('document', {}).get('id', 'unknown')
                    return {
                        "type": "unknown",
                        "document_id": document_id,
                        "cited_text": citation.get('text', '')
                    }
                return None
                
        except Exception as e:
            logger.exception(f"Error converting Claude citation: {e}")
            return None