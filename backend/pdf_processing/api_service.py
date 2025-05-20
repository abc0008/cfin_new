"""
Claude Service Module
====================

This module provides the main backend interface for interacting with the Anthropic Claude API for PDF and financial document analysis. It encapsulates all logic for:

- Submitting PDFs (and optionally text documents) to Claude for extraction, analysis, and Q&A.
- Extracting structured financial data, citations, and generating responses with or without visualization tools (charts/tables/metrics).
- Handling tool-based analysis for financial visualizations and citation mapping for downstream frontend highlighting.
- Acting as the primary AI/LLM service for document understanding, replacing legacy text extraction fallbacks.

**Key Responsibilities:**
- Process PDF files using Claude's native PDF support, including extracting raw text, structured data, and citations.
- Analyze documents and user queries, supporting tool-based visualizations (charts/tables/metrics) for financial analysis.
- Generate citation-aware Q&A responses for use with frontend highlighters.
- Convert and standardize citation data for downstream storage and frontend consumption.
- Provide fallback to LangGraph or LangChain-based analysis for non-PDF or text-only scenarios.

**Integration Points:**
- `models.document`, `models.citation`, `models.tools`: Data models for processed documents, citations, and tool schemas.
- `pdf_processing.langchain_service` and `pdf_processing.langgraph_service`: Fallbacks for text-based or advanced Q&A analysis.
- `repositories.document_repository`: Used to fetch PDF binary content from storage when preparing documents for citation.
- `services.conversation_service` and `pdf_processing.document_service`: Main consumers for document Q&A and PDF processing.

**Typical Usage:**
- Called by DocumentService for PDF processing and extraction.
- Used by ConversationService for generating responses to user queries with citation support.
- Used by AnalysisService for tool-based financial analysis and visualization generation.

**Design Notes:**
- This file is central to the backend's AI/LLM capabilities and is designed to be the single point of interaction with Anthropic Claude for all document analysis, extraction, and Q&A tasks.
- It is tightly integrated with the backend's document, citation, and analysis models, and is responsible for ensuring all downstream consumers (including the frontend) receive consistent, citation-rich, and structured data.
- Tool-based analysis (charts, tables, metrics) is prioritized when appropriate, with strict schema validation for frontend compatibility.
- Fallback logic ensures robust operation even if Claude or advanced services are unavailable.
"""



import os
import base64
import asyncio
import json
import re
import uuid
from typing import Dict, List, Optional, Any, Tuple, Union, TYPE_CHECKING, ForwardRef, AsyncGenerator, cast
import logging
from anthropic import AsyncAnthropic, APIStatusError, APITimeoutError, RateLimitError
from anthropic.types import Message as AnthropicMessage, ToolUseBlock, MessageStreamEvent, ContentBlockDeltaEvent, MessageDeltaEvent
import string
from datetime import datetime
import contextlib
import httpx
import backoff

from models.document import ProcessedDocument, Citation as DocumentCitation, DocumentContentType, DocumentMetadata, ProcessingStatus
from models.citation import Citation, CitationType, CharLocationCitation, PageLocationCitation, ContentBlockLocationCitation
from pdf_processing.langchain_service import LangChainService
from utils.database import get_db
from models.visualization import ChartData, TableData
from models.analysis import FinancialMetric
from models.tools import ALL_TOOLS_DICT, CLAUDE_API_TOOLS_LIST, ToolSchema # Ensure this import is present

# Set up logger
logger = logging.getLogger(__name__)

# Create a ToolSchema type reference for type checking
if TYPE_CHECKING:
    from models.tools import ToolSchema
else:
    ToolSchema = ForwardRef('ToolSchema')

# Import tool models
try:
    from models.tools import ToolSchema, ALL_TOOLS_SCHEMAS, ALL_TOOLS_DICT
    TOOLS_SUPPORT = True
except ImportError as e:
    TOOLS_SUPPORT = False
    logger.warning(f"Tools import failed: {e}. Tools features will be disabled.")
except Exception as e:
    TOOLS_SUPPORT = False
    logger.warning(f"Tools unexpected error: {e}. Tools features will be disabled.")

# Refined System Prompt for Tool Usage
FINANCIAL_ANALYSIS_SYSTEM_PROMPT = """You are an expert financial analyst. Your primary task is to analyze the provided financial document(s) and respond to the user's query.

CRITICAL INSTRUCTIONS:
1. You MUST use the provided tools for data presentation whenever appropriate:
    - 'generate_graph_data' for charts and graphs.
    - 'generate_table_data' for structured tabular data.
    - 'generate_financial_metric' for individual key financial figures (e.g., Total Revenue, Net Income, EPS, specific ratios not part of a larger table).
   Do NOT describe chart data, table data, or individual metrics in plain text if a tool can represent it. Use the tools to generate the structured JSON required, matching their input schemas precisely.

2. You MUST ALWAYS provide a separate, comprehensive textual analysis as a standard text response. This textual summary is your primary output for conveying insights and should ideally be the *first* part of your response, or at least a distinct and clearly separated section. It must discuss key findings, directly answer the user's query, and reference any charts, tables, or metrics generated by the tools (e.g., "As shown in the Revenue Trend chart...", "The extracted Net Income metric indicates..."). The textual analysis is mandatory and distinct from tool outputs; do not omit it even if tools are used extensively or if no specific tool seems applicable.

3. Your response MUST be a sequence of content blocks. The VERY FIRST block in your response MUST be a 'text' block containing your comprehensive textual financial analysis. ONLY AFTER this initial 'text' block can you include 'tool_use' blocks for `generate_table_data`, `generate_graph_data`, or `generate_financial_metric` as appropriate.

4. For 'generate_financial_metric', use it for *individual* key figures that stand alone and are important enough to be called out. For collections of related figures, 'generate_table_data' is usually more appropriate.

5. Ensure all tool inputs, especially for 'config' objects within tables and charts, adhere strictly to the Pydantic models provided in the tool descriptions. Pay close attention to required fields and data types. For example, table and chart descriptions within their config objects are always required.

6. If the user query is very broad (e.g., "analyze this document"), provide a balanced overview that includes a textual summary, at least one relevant table, and a few key individual metrics. Do not just default to only one type of output.

7. If the user's query *explicitly requests* the use of specific tools (e.g., 'generate_table_data', 'generate_financial_metric') OR a certain number of outputs from a tool (e.g., "extract at least two key financial metrics"), you MUST make every effort to fulfill these explicit requests by using EACH mentioned tool and generating the requested number of outputs for them, in addition to providing the mandatory textual analysis.

Analysis Steps:
1. Thoroughly understand the user's query in the context of the provided document(s).
2. **Identify ALL tools explicitly requested in the user's query (e.g., 'generate_table_data', 'generate_financial_metric', 'generate_graph_data'). Plan to use each of these tools if the query and document content support their use.**
3. Extract relevant financial figures, metrics, trends, and other data from the document(s) to support both the textual analysis and the inputs for any identified tools.

4. **CRUCIAL PRELIMINARY STEP: Construct your comprehensive textual analysis. This is mandatory and will be the VERY FIRST 'text' block in your response.**

5. After formulating the textual analysis (which you will output first), proceed to use the identified tools sequentially as planned:
    a. If 'generate_financial_metric' was identified and the query asks for specific metrics or a number of metrics (e.g., "extract at least two key financial metrics"), use this tool for each distinct metric. Ensure category, name, period, value, and unit match the tool's input schema.
    b. If 'generate_table_data' was identified (e.g., query asks for "a summary table") OR if a collection of structured data is best represented as a table, use this tool. Ensure the tableType, config, columns, and data match the tool's input schema precisely.
    c. If 'generate_graph_data' was identified (e.g., query asks for "a chart or graph visualization") OR if one is clearly appropriate for the data and query, use this tool. Ensure the chartType, config, data, and chartConfig match the tool's input schema precisely.

6. In your textual analysis, refer to any generated visualizations, tables, and metrics where appropriate (e.g., "As detailed in the Key Metrics table and the Revenue Growth chart... The standalone metric for EPS was X.").

7. **FINAL CHECK: Ensure your response begins with the 'text' block containing the comprehensive textual analysis, followed by any 'tool_use' blocks.**

8. **If you determine that the document(s) do not contain any relevant financial data for the query, or if extraction fails for specific parts, clearly state this in your textual analysis with a warning such as: '⚠️ Warning: The document appears to be processed but may not contain the specific financial data requested, or extraction was incomplete. This could be due to data absence or an unsupported format for that particular data point.'**
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
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            logger.error("ANTHROPIC_API_KEY not found.")
            raise ValueError("ANTHROPIC_API_KEY is required for ClaudeService")

        # Initialize tools for API calls - expects list of dicts
        self.tools_for_api = CLAUDE_API_TOOLS_LIST # CORRECTED: Use CLAUDE_API_TOOLS_LIST
        
        # Store the new ALL_TOOLS_DICT (Dict[str, ToolSchema]) for processor lookup
        self.tool_schemas_map = ALL_TOOLS_DICT # This maps name to ToolSchema instance

        try:
            # Using Claude 3.7 Sonnet for token-efficient tool use and enhanced PDF support
            self.model = "claude-3-7-sonnet-20250219"  # Updated model
            self.client = AsyncAnthropic(
                api_key=self.api_key,
                timeout=httpx.Timeout(90.0, connect=5.0), # Set overall timeout to 90s
                max_retries=5 # Set max retries to 5
            )
            logger.info(f"ClaudeService initialized with model: {self.model}, PDF support, timeout=90s, max_retries=5")
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

    async def _extract_full_text_from_pdf_claude(self, pdf_content_base64: str, filename: str) -> str:
        """
        Extracts the full text content from a PDF using Claude.

        Args:
            pdf_content_base64: Base64 encoded PDF content.
            filename: Name of the PDF file (for logging).

        Returns:
            The extracted full text as a string, or an error message / empty string on failure.
        """
        if not self.client:
            logger.error(f"Claude client not available for full text extraction from {filename}.")
            return f"Error: Claude client not initialized for {filename}."

        try:
            logger.info(f"Requesting full text extraction from Claude for: {filename}")
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": pdf_content_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": "Extract all text content from this PDF document. Present the text clearly and completely."
                        }
                    ]
                }
            ]
            system_prompt = "You are an efficient text extraction assistant. Your sole task is to extract all text from the provided PDF and present it clearly."

            response = await self.client.messages.create(
                model=self.model, # Or a model optimized for speed/text extraction if available
                max_tokens=4000,  # Should be large enough for most documents
                system=system_prompt,
                messages=messages
            )

            processed_content = self._process_claude_response(response)
            full_text = processed_content.get("text", "").strip()
            if not full_text:
                logger.warning(f"Claude returned no text for full text extraction of {filename}.")
                return f"Warning: Claude returned no text for {filename}. Document might be image-only or unreadable."
            
            logger.info(f"Successfully extracted full text ({len(full_text)} chars) from {filename} using Claude.")
            return full_text
        except Exception as e:
            logger.error(f"Error during Claude full text extraction for {filename}: {str(e)}", exc_info=True)
            return f"Error extracting full text from {filename}: {str(e)}"

    async def process_pdf(self, pdf_data: bytes, filename: str) -> Tuple[str, ProcessedDocument, List[DocumentCitation]]:
        """
        Process a PDF using Claude's PDF support. Extracts full text, structured data, and citations.
        
        Args:
            pdf_data: Raw bytes of the PDF file
            filename: Name of the PDF file
            
        Returns:
            A tuple containing the full raw text, the processed document object, and a list of citations.
        """
        if not self.client:
            logger.error("Cannot process PDF because Claude API client is not available")
            # Return a placeholder for full_text as well in the error case
            # Construct minimal ProcessedDocument for error reporting
            document_id = str(uuid.uuid4())
            metadata = DocumentMetadata(
                id=uuid.UUID(document_id),
                filename=filename,
                upload_timestamp=datetime.now(),
                file_size=len(pdf_data) if pdf_data else 0,
                mime_type="application/pdf",
                user_id="system"
            )
            error_message_text = "Claude API client is not available. Check your API key."
            processed_document_error = ProcessedDocument(
                metadata=metadata,
                content_type=DocumentContentType.OTHER,
                extraction_timestamp=datetime.now(),
                extracted_data={"error": error_message_text, "claude_textual_output_accompanying_json": error_message_text},
                confidence_score=0.0,
                processing_status=ProcessingStatus.FAILED
            )
            raise ValueError(error_message_text) # Or return error tuple: (error_message_text, processed_document_error, [])
        
        true_full_pdf_text = ""
        processed_document: Optional[ProcessedDocument] = None
        citations_list: List[DocumentCitation] = []

        try:
            logger.info(f"Processing PDF: {filename} with Claude API for full text, structured data, and citations.")
            
            pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')
            
            # Step 0: Extract true full raw text using Claude
            true_full_pdf_text = await self._extract_full_text_from_pdf_claude(pdf_base64, filename)
            if "Error:" in true_full_pdf_text or "Warning:" in true_full_pdf_text:
                logger.warning(f"Full text extraction for {filename} resulted in an issue: {true_full_pdf_text}")
                # Decide if we should proceed or raise error / return early
                # For now, let's proceed but ensure this problematic text is what gets stored if nothing better comes up

            # Step 1: Analyze document to determine type and periods
            logger.info(f"Analyzing document type for {filename}")
            document_type, periods = await self._analyze_document_type(pdf_base64, filename)
            logger.info(f"Document {filename} classified as: {document_type.value} with periods: {periods}")
            
            # Step 2: Extract structured financial data and citations
            logger.info(f"Extracting structured financial data and citations for {filename}")
            # This call now returns structured_data (JSON-like dict) and citations_list
            structured_financial_data, citations_from_extraction = await self._extract_financial_data_with_citations(
                pdf_content_base64=pdf_base64,
                filename=filename, 
                document_type=document_type
            )
            citations_list = citations_from_extraction # Assuming _extract_financial_data_with_citations returns List[Any] for citations
            logger.info(f"Extracted {len(citations_list)} citations for {filename}")

            # Log if structured_financial_data indicates an error from its own process
            if isinstance(structured_financial_data, dict) and "error_extracting_structured_data" in structured_financial_data:
                logger.warning(f"Structured data extraction for {filename} had an error: {structured_financial_data['error_extracting_structured_data']}")
            elif not structured_financial_data:
                 logger.warning(f"Structured data extraction for {filename} returned empty or None.")
                 structured_financial_data = {} # Ensure it's a dict
            
            logger.info(f"Structured financial data keys for {filename}: {list(structured_financial_data.keys())}")
            
            if structured_financial_data.get('financial_data') and structured_financial_data['financial_data']:
                if document_type != DocumentContentType.FINANCIAL_REPORT:
                    logger.info(f"Updating document type for {filename} from {document_type.value} to FINANCIAL_REPORT based on extracted financial data")
                    document_type = DocumentContentType.FINANCIAL_REPORT
            
            document_id_str = str(uuid.uuid4())
            confidence_score = 0.8  # Default confidence score, consider adjusting based on extraction success
            
            metadata = DocumentMetadata(
                id=uuid.UUID(document_id_str),
                filename=filename,
                upload_timestamp=datetime.now(),
                file_size=len(pdf_data),
                mime_type="application/pdf",
                user_id="system" 
            )
            
            processed_document = ProcessedDocument(
                metadata=metadata,
                content_type=document_type,
                extraction_timestamp=datetime.now(),
                periods=periods,
                extracted_data=structured_financial_data, # This is now purely structured data
                confidence_score=confidence_score,
                processing_status=ProcessingStatus.COMPLETED
            )
            
            # Return the true_full_pdf_text along with other results
            return true_full_pdf_text, processed_document, citations_list
            
        except Exception as e:
            logger.exception(f"Critical error in process_pdf for {filename}: {e}")
            # Construct minimal ProcessedDocument for error reporting
            document_id_err = str(uuid.uuid4())
            metadata_err = DocumentMetadata(
                id=uuid.UUID(document_id_err),
                filename=filename,
                upload_timestamp=datetime.now(),
                file_size=len(pdf_data) if pdf_data else 0,
                mime_type="application/pdf",
                user_id="system"
            )
            error_text = f"Error processing PDF {filename}: {str(e)}"
            processed_document_err = ProcessedDocument(
                metadata=metadata_err,
                content_type=DocumentContentType.OTHER,
                extraction_timestamp=datetime.now(),
                extracted_data={"error": error_text, "claude_textual_output_accompanying_json": error_text},
                confidence_score=0.0,
                processing_status=ProcessingStatus.FAILED
            )
            # Return the error text as true_full_pdf_text in this failure case
            return error_text, processed_document_err, []

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

    async def _extract_financial_data_with_citations(self, pdf_content_base64: str, filename: str, document_type: DocumentContentType) -> Tuple[Dict[str, Any], List[Any]]:
        """
        Extract financial data from a PDF with citations.
        The primary output is the structured financial data as a JSON-compatible dictionary.
        Any textual output from Claude accompanying the JSON is secondary and captured.
        
        Args:
            pdf_content_base64: Base64 encoded PDF content
            filename: Name of the PDF file
            document_type: Type of document being processed
            
        Returns:
            Tuple of extracted structured data dictionary and list of citations
        """
        if not self.client:
            logger.error("Cannot extract financial data because Claude API client is not available")
            raise ValueError("Claude API client is not available. Check your API key.")
        
        try:
            logger.info(f"Extracting structured financial data with citations from: {filename}")
            
            doc_type_str = document_type.value if document_type else "financial document"
            
            system_prompt = """You are a specialized financial document analysis assistant. Extract structured financial data from the document accurately.
Follow these guidelines:
1. Identify all financial tables and metrics.
2. Extract values with their correct time periods, labels, and units.
3. Present the data primarily in a structured JSON format.
4. Provide citations for all extracted data points within the JSON structure if possible, or as a separate list if not directly applicable within the JSON values.
5. Any textual narrative you provide before the JSON block must be extremely brief, clearly separated, or omitted entirely if the JSON is self-explanatory."""
            
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": pdf_content_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": (
                                f"From this {doc_type_str} document, provide a comprehensive JSON object "
                                "containing all extracted financial data. The JSON should include key metrics, "
                                "time periods, and values. Structure the JSON clearly. "
                                "If you provide any introductory text before the JSON, keep it very brief and separate, or omit it."
                            )
                        }
                    ]
                }
            ]
            
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4000, # Consider making this configurable or dynamic
                system=system_prompt,
                messages=messages
            )
            
            processed_response_content = self._process_claude_response(response) # Gets text, citations, tool_calls, raw_response
            text_output_from_claude = processed_response_content.get("text", "").strip()
            citations = processed_response_content.get("citations", [])
            
            claude_preamble_text = ""
            parsed_financial_json = {}
            
            json_pattern = re.compile(r"^(.*?)(```json\s*(\{[\s\S]*?\})\s*```|(\{[\s\S]*\}))[\s\S]*$", re.DOTALL | re.MULTILINE)
            match = json_pattern.search(text_output_from_claude)

            if match:
                claude_preamble_text = match.group(1).strip()
                json_str_from_regex = match.group(3) if match.group(3) else match.group(4)
                
                if json_str_from_regex:
                    try:
                        parsed_financial_json = json.loads(json_str_from_regex)
                        logger.info("Successfully parsed financial JSON from Claude's response.")
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON from extracted part: {e}. JSON string: {json_str_from_regex[:200]}...")
                        claude_preamble_text = text_output_from_claude # Fallback: all of Claude's text is preamble
                        parsed_financial_json = {"error_parsing_financial_json": f"Failed to parse: {str(e)}", "original_text_payload": json_str_from_regex}
                else: 
                    logger.warning("JSON regex matched but no JSON string was captured. Treating all as preamble text.")
                    claude_preamble_text = text_output_from_claude
            else:
                logger.warning("Could not find a distinct JSON block in Claude's response using regex. Assuming all is preamble/non-JSON text.")
                claude_preamble_text = text_output_from_claude

            # Ensure parsed_financial_json is always a dict for the return type.
            if not isinstance(parsed_financial_json, dict):
                logger.warning(f"Parsed financial data was not a dictionary (type: {type(parsed_financial_json)}). Wrapping it or using an error structure.")
                parsed_financial_json = {"financial_data_payload": parsed_financial_json, "parsing_error_occurred": True}
            
            # If there was preamble text from Claude, include it in the structured data under a specific key.
            if claude_preamble_text:
                parsed_financial_json['claude_textual_output_accompanying_json'] = claude_preamble_text
                logger.info(f"Captured Claude's preamble text, length: {len(claude_preamble_text)}")
            
            # This function's primary return is the structured JSON and citations.
            # It no longer attempts to provide the "full raw text" of the PDF.
            return parsed_financial_json, citations
            
        except Exception as e:
            logger.error(f"Error extracting structured financial data: {str(e)}", exc_info=True)
            return {"error_extracting_structured_data": str(e)}, []

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
        knowledge_base: str = "",
        document_base64: Optional[str] = None,
        document_filename: Optional[str] = "document.pdf"
    ) -> Dict[str, Any]:
        """
        Analyze a financial document using Claude with tool support for visualizations.

        Args:
            document_text: Text content of the financial document (can be a summary).
            user_query: The user's specific question or analysis request.
            knowledge_base: Optional additional context or domain knowledge.
            document_base64: Optional base64 encoded full PDF content.
            document_filename: Optional filename for the PDF, used if document_base64 is provided.

        Returns:
            A dictionary containing:
            - "analysis_text": The textual analysis from Claude.
            - "visualizations": A dict with "charts": [...] and "tables": [...]
                                containing the structured JSON data generated by tools.
            - "metrics": A list of extracted financial metrics.
        """
        if not self.client:
            logger.error("Cannot analyze document because Claude API client is not available.")
            return {
                "analysis_text": "Error: Claude API client not configured.",
                "visualizations": {"charts": [], "tables": []},
                "metrics": []
            }

        try:
            logger.info(f"Starting analysis with visualization tools for query: '{user_query[:50]}...'")

            user_content_parts = []

            if document_base64:
                logger.info(f"Using base64 PDF content for tool-based analysis of '{document_filename}'.")
                user_content_parts.append({
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": document_base64
                    }
                    # title field is not directly supported here, filename is for logging/context
                })
                # Optionally, still include the document_text if it's a summary or different context
                if document_text and len(document_text.strip()) > 0:
                    user_content_parts.append({"type": "text", "text": f"""<document_summary_text>
{document_text}
</document_summary_text>"""})
            elif document_text and len(document_text.strip()) > 0:
                logger.info("Using provided text content for tool-based analysis.")
                user_content_parts.append({
                    "type": "text",
                    "text": f"""<financial_document>
{document_text}
</financial_document>"""
                })
            else:
                logger.warning("No document content (neither base64 PDF nor text) provided for tool-based analysis.")
                return {
                    "analysis_text": "Error: No document content provided for analysis.",
                    "visualizations": {"charts": [], "tables": []},
                    "metrics": []
                }

            # Add knowledge base if provided
            if knowledge_base:
                user_content_parts.append({
                    "type": "text",
                    "text": f"""<knowledge_base>
{knowledge_base}
</knowledge_base>"""
                })

            # Add the main user query
            user_content_parts.append({
                "type": "text",
                "text": f"User Query: {user_query}"
            })
            
            # Ensure there's at least one part before creating the message
            if not user_content_parts:
                 logger.error("No content parts to send to Claude for analysis.")
                 return {
                    "analysis_text": "Error: Internal error preparing analysis request (no content).",
                    "visualizations": {"charts": [], "tables": []},
                    "metrics": []
                }

            messages = [{"role": "user", "content": user_content_parts}]

            # Log request details
            logger.debug(f"Sending request to Claude with {len(messages)} message(s) and {len(ALL_TOOLS_DICT)} tools.")

            # Call Claude API with tools
            response = await self.client.messages.create(
                model=self.model,
                system=FINANCIAL_ANALYSIS_SYSTEM_PROMPT,  # Use the refined system prompt
                messages=messages,
                tools=self.tools_for_api, # Use self.tools_for_api (CLAUDE_API_TOOLS_LIST)
                tool_choice={"type": "auto"},
                temperature=0.3, # Lower temp for more factual/structured output
                max_tokens=4096,  # Maximize token limit for complex responses
                extra_headers={"anthropic-beta": "token-efficient-tools-2025-02-19"} # Add beta header here
            )

            logger.info("Received response from Claude API.")
            #logger.debug(f"Claude Raw Response: {response}") # Careful logging raw response
            # --- START DEBUG LOG ---
            if response and response.content:
                logger.info(f"analyze_with_visualization_tools - Claude API Full Response Content (First 500 chars per block):")
                for i, block in enumerate(response.content):
                    logger.info(f"  Block {i+1} Type: {block.type}")
                    if block.type == "text":
                        logger.info(f"    Text: {block.text[:500]}{'...' if len(block.text) > 500 else ''}")
                    elif block.type == "tool_use":
                        logger.info(f"    Tool Name: {block.name}")
                        logger.info(f"    Tool Input (First 500 chars): {str(block.input)[:500]}{'...' if len(str(block.input)) > 500 else ''}")
            else:
                logger.info("analyze_with_visualization_tools - Claude API Response or content is empty.")
            # --- END DEBUG LOG ---

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
                "visualizations": {"charts": [], "tables": []},
                "metrics": []
            }

    async def analyze_with_financial_analysis_template(
        self,
        system_prompt: str,
        document_text: str,
        user_query: str,
        knowledge_base: str = "",
        document_base64: Optional[str] = None,
        document_filename: Optional[str] = "document.pdf"
    ) -> Dict[str, Any]:
        """
        Analyze a financial document using a custom system prompt (template) with tool support for visualizations.

        Args:
            system_prompt: The system prompt/template to use for the analysis.
            document_text: Text content of the financial document (can be a summary).
            user_query: The user's specific question or analysis request.
            knowledge_base: Optional additional context or domain knowledge.
            document_base64: Optional base64 encoded full PDF content.
            document_filename: Optional filename for the PDF, used if document_base64 is provided.

        Returns:
            A dictionary containing:
            - "analysis_text": The textual analysis from Claude.
            - "visualizations": A dict with "charts": [...] and "tables": [...]
                                containing the structured JSON data generated by tools.
            - "metrics": A list of extracted financial metrics.
        """
        if not self.client:
            logger.error("Cannot analyze document because Claude API client is not available.")
            return {
                "analysis_text": "Error: Claude API client not configured.",
                "visualizations": {"charts": [], "tables": []},
                "metrics": []
            }

        try:
            logger.info(f"Starting analysis with custom template for query: '{user_query[:50]}...'")

            user_content_parts = []

            if document_base64:
                logger.info(f"Using base64 PDF content for tool-based analysis of '{document_filename}'.")
                user_content_parts.append({
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": document_base64
                    }
                })
                if document_text and len(document_text.strip()) > 0:
                    user_content_parts.append({"type": "text", "text": f"""<document_summary_text>\n{document_text}\n</document_summary_text>"""})
            elif document_text and len(document_text.strip()) > 0:
                logger.info("Using provided text content for tool-based analysis.")
                user_content_parts.append({
                    "type": "text",
                    "text": f"""<financial_document>\n{document_text}\n</financial_document>"""
                })
            else:
                logger.warning("No document content (neither base64 PDF nor text) provided for tool-based analysis.")
                return {
                    "analysis_text": "Error: No document content provided for analysis.",
                    "visualizations": {"charts": [], "tables": []},
                    "metrics": []
                }

            if knowledge_base:
                user_content_parts.append({
                    "type": "text",
                    "text": f"""<knowledge_base>\n{knowledge_base}\n</knowledge_base>"""
                })

            user_content_parts.append({
                "type": "text",
                "text": f"User Query: {user_query}"
            })

            if not user_content_parts:
                logger.error("No content parts to send to Claude for analysis.")
                return {
                    "analysis_text": "Error: Internal error preparing analysis request (no content).",
                    "visualizations": {"charts": [], "tables": []},
                    "metrics": []
                }

            messages = [{"role": "user", "content": user_content_parts}]

            logger.debug(f"Sending request to Claude with {len(messages)} message(s) and {len(ALL_TOOLS_DICT)} tools (custom template).")

            response = await self.client.messages.create(
                model=self.model,
                system=system_prompt,  # Use the provided custom system prompt
                messages=messages,
                tools=self.tools_for_api, # Use self.tools_for_api (CLAUDE_API_TOOLS_LIST)
                tool_choice={"type": "auto"},
                temperature=0.3,
                max_tokens=4096,
                extra_headers={"anthropic-beta": "token-efficient-tools-2025-02-19"} # Add beta header here
            )

            logger.info("Received response from Claude API (custom template).")
            if response and response.content:
                logger.info(f"analyze_with_financial_analysis_template - Claude API Full Response Content (First 500 chars per block):")
                for i, block in enumerate(response.content):
                    logger.info(f"  Block {i+1} Type: {block.type}")
                    if block.type == "text":
                        logger.info(f"    Text: {block.text[:500]}{'...' if len(block.text) > 500 else ''}")
                    elif block.type == "tool_use":
                        logger.info(f"    Tool Name: {block.name}")
                        logger.info(f"    Tool Input (First 500 chars): {str(block.input)[:500]}{'...' if len(str(block.input)) > 500 else ''}")
            else:
                logger.info("analyze_with_financial_analysis_template - Claude API Response or content is empty.")

            processed_result = self._process_tool_calls(response)

            logger.info(f"Analysis complete (custom template). Text length: {len(processed_result['analysis_text'])}. "
                        f"Charts: {len(processed_result['visualizations']['charts'])}. "
                        f"Tables: {len(processed_result['visualizations']['tables'])}.")

            return processed_result

        except Exception as e:
            logger.exception(f"Error during analysis with custom template: {e}")
            return {
                "analysis_text": f"An error occurred during analysis: {e}",
                "visualizations": {"charts": [], "tables": []},
                "metrics": []
            }

    def _process_tool_calls(self, response: AnthropicMessage) -> Dict[str, Any]:
        """
        Processes Claude's response, extracting text and structured data from tool calls.
        The method transforms the raw tool_input into properly formatted chart, table, and metric data
        that can be correctly rendered by the frontend components or used in analysis.

        Args:
            response: The AnthropicMessage object received from the API.

        Returns:
            A dictionary containing 'analysis_text', 'visualizations' (with 'charts' and 'tables'),
            and 'metrics'.
        """
        analysis_text = ""
        charts = []
        tables = []
        metrics = [] # Initialize metrics list

        if not response.content:
            logger.warning("Claude response has no content.")
            return {
                "analysis_text": "No content received from analysis.",
                "visualizations": {"charts": [], "tables": []},
                "metrics": []
            }

        for block in response.content:
            if block.type == "text":
                analysis_text += block.text + "\n"
            elif block.type == "tool_use":
                tool_name = block.name
                tool_input = block.input
                tool_use_id = block.id # Get tool_use_id

                logger.info(f"Processing tool use: {tool_name} (ID: {tool_use_id})")
                
                tool_schema = self.tool_schemas_map.get(tool_name)
                processed_data = None

                if tool_schema and tool_schema.processor:
                    try:
                        # Pass tool_input and block_id if processor expects it
                        # Current processors in tool_processing.py only take tool_input.
                        # If block_id is needed for logging within processor, 
                        # processor signature and ToolSchema.processor type hint must change.
                        # For now, assume tool_input is sufficient for the processor itself.
                        processed_data = tool_schema.processor(tool_input)
                        if processed_data is None:
                            logger.warning(f"Processor for {tool_name} (ID: {tool_use_id}) returned None.")
                    except Exception as e:
                        logger.error(f"Error in processor for tool {tool_name} (ID: {tool_use_id}): {e}")
                        processed_data = None # Ensure it's None on processor error
                else:
                    logger.warning(f"No processor for tool: {tool_name} (ID: {tool_use_id}) or tool not found in schema map. Raw input: {tool_input}")
                    # Fallback or specific handling for tools without processors, if any.
                    # For now, similar to before, this will lead to processed_data being None.

                # The old call was: self._process_visualization_input(tool_name, tool_input, block.id)
                # This has been replaced by the processor logic above.
                                
                if processed_data:
                    if tool_name == "generate_graph_data":
                        charts.append(processed_data)
                        logger.info(f"Successfully processed chart data for tool ID {block.id}")
                    elif tool_name == "generate_table_data":
                        tables.append(processed_data)
                        logger.info(f"Successfully processed table data for tool ID {block.id}")
                    elif tool_name == "generate_financial_metric": # Handle financial metrics
                        metrics.append(processed_data)
                        logger.info(f"Successfully processed financial metric data for tool ID {block.id}")
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
            },
            "metrics": metrics # Include metrics in the return
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
            Processed chart, table, or metric data, or None if processing failed
        """
        try:
            if tool_name == "generate_graph_data":
                return self._process_chart_input(tool_input)
            elif tool_name == "generate_table_data":
                return self._process_table_input(tool_input)
            elif tool_name == "generate_financial_metric": # New case for financial metrics
                return self._process_financial_metric_input(tool_input)
            else:
                logger.warning(f"Unsupported tool: {tool_name} (ID: {block_id})") # Log block_id here
                return None
        except Exception as e:
            logger.error(f"Error processing {tool_name} input (ID: {block_id}): {e}")
            return None
    
    def _process_financial_metric_input(self, tool_input: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process the raw financial metric input from the tool into a dictionary 
        compatible with the FinancialMetric Pydantic model.
        
        Args:
            tool_input: The raw input provided to the generate_financial_metric tool.
            
        Returns:
            Processed financial metric data or None if processing failed.
        """
        required_keys = ["category", "name", "period", "value", "unit"]
        # isEstimated is optional in the tool schema, defaults to False in Pydantic model
        
        if not isinstance(tool_input, dict):
            logger.warning(f"Financial metric input is not a dictionary: {type(tool_input)}")
            return None

        # Check for essential keys. Note: tool_input keys are camelCase from Claude.
        # The Pydantic model FinancialMetric expects snake_case or camelCase if populate_by_name=True
        # but the tool schema itself uses camelCase for 'isEstimated'.
        # Let's check for the keys Claude would use (likely matching the tool schema directly).
        expected_input_keys = {
            "category": "category",
            "name": "name",
            "period": "period",
            "value": "value",
            "unit": "unit",
            "isEstimated": "isEstimated" # from tool's input_schema definition
        }

        processed_metric = {}
        missing_required_keys = []

        for pydantic_key, tool_key in expected_input_keys.items():
            if tool_key in tool_input:
                processed_metric[pydantic_key] = tool_input[tool_key]
            elif pydantic_key in required_keys: # Check against snake_case required keys for the model
                missing_required_keys.append(tool_key)
        
        if missing_required_keys:
            logger.warning(f"Financial metric input missing required keys: {missing_required_keys}. Input: {tool_input}")
            return None
        
        # Type check for value
        if "value" in processed_metric and not isinstance(processed_metric["value"], (int, float)):
            logger.warning(f"Financial metric 'value' is not a number: {processed_metric['value']}. Input: {tool_input}")
            # Attempt conversion if it's a string that looks like a number
            if isinstance(processed_metric["value"], str):
                try:
                    processed_metric["value"] = float(processed_metric["value"].replace(',', '')) # Handle commas
                except ValueError:
                    logger.error(f"Could not convert metric value '{processed_metric['value']}' to float.")
                    return None # or handle as error, e.g. by setting value to 0 or a specific error indicator
            else:
                return None

        # Ensure isEstimated defaults to False if not provided or not a boolean
        if "isEstimated" not in processed_metric or not isinstance(processed_metric.get("isEstimated"), bool):
            processed_metric["isEstimated"] = False

        # Validate with FinancialMetric model before returning dictionary for AnalysisResult
        try:
            # Import locally to avoid circular dependency at module level if models.analysis imports this service
            from models.analysis import FinancialMetric 
            FinancialMetric(**processed_metric) # This validates types and structure
            logger.info(f"Successfully processed financial metric: {processed_metric.get('name')}")
            return processed_metric # Return the dict, as FinancialMetric objects are created later
        except Exception as e: # Catch Pydantic ValidationError or other issues
            logger.error(f"FinancialMetric validation failed for {processed_metric.get('name')}: {e}. Input: {tool_input}")
            return None
    
    def _process_chart_input(self, tool_input: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process the raw chart input from the tool into a properly formatted chart data structure
        that can be rendered by the frontend.
        
        Args:
            tool_input: The raw input provided to the generate_chart_data tool
            
        Returns:
            Processed chart data for frontend rendering
        """
        # Basic validation
        if not isinstance(tool_input, dict):
            logger.warning("Chart input is not a dictionary")
            return None
            
        if not all(key in tool_input for key in ["chartType", "config", "data", "chartConfig"]):
            logger.warning("Chart input missing required keys")
            return None
        
        # Create a copy to avoid modifying the original
        processed_chart = tool_input.copy()
        
        # Ensure config and description exist with defaults if necessary
        config = processed_chart.get("config", {})
        if "description" not in config or config["description"] is None:
            config["description"] = config.get("title", "") # Use title as description, or empty string
        processed_chart["config"] = config
        
        try:
            # --- Strict validation with Pydantic ---
            validated_chart = ChartData(**processed_chart)
            return validated_chart.model_dump(by_alias=True)
        except Exception as e:
            logger.error(f"ChartData validation failed: {e}")
            logger.error(f"Failed tool_input for ChartData: {json.dumps(tool_input, indent=2)}")
            return tool_input # Fall back to the original input if processing fails
    
    def _process_table_input(self, tool_input: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process the raw table input from the tool into a properly formatted table data structure
        that can be rendered by the frontend.
        
        Args:
            tool_input: The raw input provided to the generate_table_data tool
            
        Returns:
            Processed table data for frontend rendering
        """
        # Create a copy to avoid modifying the original
        processed_table = tool_input.copy()

        # Ensure tableType exists, defaulting if missing
        if "tableType" not in processed_table or processed_table.get("tableType") is None:
            logger.warning(f"Missing 'tableType' in tool_input from Claude. Defaulting to 'comparison'. Input: {tool_input}")
            processed_table["tableType"] = "comparison"
        
        # Validate and default tableType if necessary (this handles if it exists but is invalid)
        allowed_table_types = ["simple", "matrix", "comparison"]
        current_table_type = processed_table.get("tableType")
        if current_table_type not in allowed_table_types:
            logger.warning(f"Invalid tableType '{current_table_type}' received from Claude. Defaulting to 'comparison'. Input: {tool_input}")
            processed_table["tableType"] = "comparison"
        
        try:
            # Ensure config and description exist with defaults if necessary
            config = processed_table.get("config", {})
            if "description" not in config or config["description"] is None:
                # Use title as description, or empty string if title also missing
                config["description"] = config.get("title", "") 
            processed_table["config"] = config

            # Provide defaults for TableColumnConfig fields if they are None
            if "columns" in config and isinstance(config["columns"], list):
                for column_config_item in config["columns"]:
                    if isinstance(column_config_item, dict):
                        if column_config_item.get("header") is None:
                            column_config_item["header"] = column_config_item.get("label", "")
                        if column_config_item.get("format") is None:
                            column_config_item["format"] = "text"
                        if column_config_item.get("width") is None:
                            # Frontend expects a number, not null.
                            # Check if 'key' is 'metric', which has width 200 in example, else 150
                            if column_config_item.get("key") == "metric":
                                column_config_item["width"] = 200
                            else:
                                column_config_item["width"] = 150 # Default width
                        if column_config_item.get("formatter") is None:
                            column_config_item["formatter"] = ""
            
            # Validate config and columns
            # ... (additional validation logic would be implemented here)

            # --- Strict validation with Pydantic ---
            validated_table = TableData(**processed_table)
            return validated_table.model_dump(by_alias=True)
        except Exception as e:
            logger.error(f"TableData validation failed: {e}")
            logger.error(f"Failed tool_input for TableData: {json.dumps(tool_input, indent=2)}")
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
            doc_content = None
            content_source = None
            logger.info(f"Document fields: {list(document.keys())}")
            if document.get("content"):
                doc_content = document.get("content")
                content_source = "content field"
            elif document.get("raw_text"):
                doc_content = document.get("raw_text")
                content_source = "raw_text field"
                doc_type = "text/plain"
            elif document.get("extracted_data") and isinstance(document.get("extracted_data"), dict) and document.get("extracted_data").get("raw_text"):
                doc_content = document.get("extracted_data").get("raw_text")
                content_source = "extracted_data.raw_text field"
                doc_type = "text/plain"
            elif document.get("text"):
                doc_content = document.get("text")
                content_source = "text field"
                doc_type = "text/plain"
            elif document.get("id"):
                try:
                    from repositories.document_repository import DocumentRepository
                    async for db in get_db():
                        document_repository = DocumentRepository(db)
                        doc_content = await document_repository.get_document_file_content(document.get('id'))
                        if doc_content and len(doc_content) > 0:
                            content_source = "direct PDF from storage"
                            doc_type = "application/pdf"
                            logger.info(f"Retrieved PDF content directly from storage for document {doc_id}")
                except Exception as storage_e:
                    logger.warning(f"Failed to get PDF directly from storage for document {doc_id}: {storage_e}")
            if not doc_content:
                logger.warning(f"No document content found for {doc_id} - using fallback placeholder")
                doc_content = f"Document content unavailable for {doc_title}. Please try re-uploading the document."
                content_source = "fallback placeholder"
                doc_type = "text/plain"
            if content_source:
                logger.info(f"Using {content_source} for document {doc_id}")
            if "pdf" in doc_type or doc_type == "application/pdf":
                if not isinstance(doc_content, bytes):
                    if isinstance(doc_content, str) and doc_content.startswith(('data:application/pdf;base64,', 'data:;base64,')):
                        base64_content = doc_content.split('base64,')[1]
                        doc_content = base64.b64decode(base64_content)
                    elif isinstance(doc_content, str) and len(doc_content) > 0:
                        try:
                            if all(c in string.ascii_letters + string.digits + '+/=' for c in doc_content):
                                try:
                                    doc_content = base64.b64decode(doc_content)
                                    logger.info(f"Successfully decoded base64 content for document {doc_id}")
                                except:
                                    logger.warning(f"Content for {doc_id} looks like base64 but couldn't be decoded")
                                    doc_content = doc_content.encode('utf-8')
                            else:
                                doc_content = doc_content.encode('utf-8')
                        except Exception as e:
                            logger.warning(f"Failed to convert string content to bytes for {doc_id}: {e}")
                            return None
                    else:
                        logger.warning(f"Invalid PDF content for {doc_id} - not bytes or base64 string")
                        return None
                if len(doc_content) < 10:
                    logger.warning(f"PDF content for {doc_id} is too small ({len(doc_content)} bytes)")
                    return None
                if not doc_content.startswith(b'%PDF'):
                    logger.warning(f"Content for {doc_id} doesn't start with PDF signature")
                try:
                    base64_data = base64.b64encode(doc_content).decode()
                    logger.info(f"Successfully encoded PDF content for document {doc_id} ({len(doc_content)} bytes)")
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
            if not text_content.strip():
                text_content = f"Empty document content for {doc_title}"
            if len(text_content) > 30000:
                text_content = text_content[:30000] + f"\n\n[Document truncated due to length. Original size: {len(text_content)} characters]"
            logger.info(f"Prepared text document for Claude API: {doc_id}, length: {len(text_content)} chars")
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

    @backoff.on_exception(backoff.expo,
                          (APIStatusError, APITimeoutError, RateLimitError), # Target specific Anthropic errors
                          max_tries=5,
                          jitter=backoff.full_jitter)
    async def execute_tool_interaction_turn(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None, # Changed type hint to List[Dict[str, Any]]
        max_tokens: int = 4096,
        temperature: float = 0.3
    ) -> AnthropicMessage:
        """
        Executes a single turn of interaction with the Claude API, supporting tool use.

        Args:
            system_prompt: The system prompt to guide Claude.
            messages: The list of messages in the conversation so far.
            tools: Optional list of ToolSchema objects to provide to Claude.
                   Defaults to ALL_TOOLS if None.
            max_tokens: The maximum number of tokens to generate.
            temperature: The sampling temperature.

        Returns:
            The raw AnthropicMessage response from Claude.
        
        Raises:
            ConnectionError: If the Anthropic client is not initialized.
            httpx.HTTPStatusError: For API errors from Claude.
            Exception: For other unexpected errors during the API call.
        """
        if not self.client:
            logger.error("Anthropic client not initialized. Cannot execute tool interaction.")
            raise ConnectionError("Anthropic client not initialized.")

        actual_tools_for_api_call: Optional[List[Dict[str, Any]]] = None
        if tools is not None: # 'tools' is already Optional[List[Dict[str, Any]]] from method signature
            actual_tools_for_api_call = tools
            logger.debug(f"Using explicitly provided tools: {len(actual_tools_for_api_call)} tools.")
        elif TOOLS_SUPPORT and self.tools_for_api: # self.tools_for_api is CLAUDE_API_TOOLS_LIST
            actual_tools_for_api_call = self.tools_for_api
            logger.debug(f"Using default tools_for_api: {len(actual_tools_for_api_call)} tools.")
        else:
            logger.warning("No tools explicitly provided and self.tools_for_api not available or TOOLS_SUPPORT is False. Proceeding without tools for this turn.")
            # actual_tools_for_api_call remains None, client handles it as no tools provided.

        try:
            # Basic logging; avoid logging full messages/tools for brevity/PII
            logger.debug(
                f"Executing tool interaction turn with model {self.model}, "
                f"max_tokens={max_tokens}, temperature={temperature}, "
                f"{len(actual_tools_for_api_call) if actual_tools_for_api_call else 0} tools. System prompt (first 100 chars): '{system_prompt[:100]}...'"
            )
            
            # --- BEGIN DEBUG LOG --- 
            if actual_tools_for_api_call:
                try:
                    logger.info(f"ClaudeService: actual_tools_for_api_call[0] structure: {json.dumps(actual_tools_for_api_call[0], indent=2)}")
                except Exception as log_e:
                    logger.error(f"ClaudeService: Error logging actual_tools_for_api_call[0]: {log_e}")
            # --- END DEBUG LOG ---
            
            # Ensure messages conform to expected structure if necessary, though typically handled by caller.
            # For instance, ensuring 'content' is correctly formatted (string or list of blocks).

            response = await self.client.messages.create(
                model=self.model,
                system=system_prompt,
                messages=messages, # type: ignore
                tools=actual_tools_for_api_call, # Pass the list of dicts or None
                tool_choice={"type": "auto"},
                max_tokens=max_tokens,
                temperature=temperature,
                extra_headers={"anthropic-beta": "token-efficient-tools-2025-02-19"} # Add beta header here
            )
            return response
        except httpx.HTTPStatusError as e:
            # Log more detailed error information if possible
            error_details = "Unknown error"
            try:
                error_details = e.response.json() # Or e.response.text if not JSON
            except Exception:
                error_details = e.response.text
            logger.error(
                f"HTTPStatusError during Claude API call in execute_tool_interaction_turn: "
                f"{e.response.status_code} - Details: {error_details}", 
                exc_info=True
            )
            raise
        except Exception as e:
            logger.error(f"Unexpected error during Claude API call in execute_tool_interaction_turn: {e}", exc_info=True)
            raise