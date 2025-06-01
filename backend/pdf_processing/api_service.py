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

# Claude API optimization imports
import settings
from settings import ANTHROPIC_BETA
from utils.claude_bucket import ClaudeBucket
from pdf_processing.claude_file_client import upload_pdf
from pdf_processing.model_router import choose_model
from utils.hashlib_utils import sha256_str
from utils.token_utils import count_tokens

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
            self.model = settings.MODEL_SONNET
            self.client = AsyncAnthropic(
                api_key=self.api_key,
                timeout=httpx.Timeout(90.0, connect=5.0), # Set overall timeout to 90s
                max_retries=5 # Set max retries to 5
            )
            
            # Token efficiency headers for Claude API optimization
            self._extra_headers = {"anthropic-beta": ANTHROPIC_BETA}
            self._tools_for_api = CLAUDE_API_TOOLS_LIST  # existing list
            
            logger.info(f"ClaudeService initialized with model: {self.model}, PDF support, timeout=90s, max_retries=5, headers: {self._extra_headers}")
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

    async def _claude_call(self, **kwargs) -> AnthropicMessage:
        """
        Central wrapper for all Claude API calls with rate limiting and token efficiency.
        
        Args:
            **kwargs: Arguments to pass to client.messages.create
            
        Returns:
            Claude API response
        """
        # Estimate tokens for rate limiting
        messages = kwargs.get("messages", [])
        tokens_in = count_tokens(messages)
        
        # Apply rate limiting based on current token bucket state
        await ClaudeBucket.throttle(tokens_in)

        try:
            # Make the API call with token efficiency headers
            resp = await self.client.messages.create(
                extra_headers=self._extra_headers,
                **kwargs
            )
        except RateLimitError as e:
            # Re-raise rate limit errors for upstream handling
            raise
        
        # Update rate limit state from response headers if available
        if hasattr(resp, 'response_headers') and resp.response_headers:
            ClaudeBucket.update(resp.response_headers)
        return resp

    def _process_claude_response(self, response: AnthropicMessage) -> Dict[str, Any]:
        """
        Process Claude API response and extract text, tool calls, and citations.
        
        Args:
            response: Raw Claude API response
            
        Returns:
            Processed response with text, tool_calls, and citations
        """
        result = {
            "text": "",
            "tool_calls": [],
            "citations": []
        }
        
        if not response.content:
            return result
            
        for content_block in response.content:
            if hasattr(content_block, 'text'):
                # Text content
                result["text"] += content_block.text
            elif hasattr(content_block, 'type') and content_block.type == 'tool_use':
                # Tool use content
                tool_call = {
                    "id": content_block.id,
                    "name": content_block.name,
                    "input": content_block.input
                }
                result["tool_calls"].append(tool_call)
        
        # Extract citations if available (Claude's citation format may vary)
        if hasattr(response, 'citations') and response.citations:
            result["citations"] = response.citations
            
        return result

    async def execute_tool_interaction_turn(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 4000,
        temperature: float = 0.7
    ) -> AnthropicMessage:
        """
        Execute a single turn of tool-based interaction with Claude.
        
        Args:
            system_prompt: System prompt for the interaction
            messages: Conversation messages
            tools: Available tools for Claude to use
            max_tokens: Maximum tokens to generate
            temperature: Generation temperature
            
        Returns:
            Claude API response
        """
        if not self.client:
            raise ValueError("Claude API client is not available")
            
        # Use provided tools or default to instance tools
        tools_to_use = tools if tools is not None else self.tools_for_api
        
        # Choose optimal model based on tool complexity
        tool_names = {tool.get("name", "") for tool in tools_to_use} if tools_to_use else set()
        estimated_tokens = sum(len(str(msg.get("content", ""))) for msg in messages) // 4
        optimal_model = choose_model(tool_names, estimated_tokens)
        
        logger.info(f"Executing tool interaction turn with {optimal_model}, {len(tools_to_use)} tools available")
        
        # Build request parameters
        request_params = {
            "model": optimal_model,
            "system": system_prompt,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        # Add tools if available
        if tools_to_use:
            request_params["tools"] = tools_to_use
            
        # Execute the API call
        return await self._claude_call(**request_params)

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

    # Removed: _extract_full_text_from_pdf_claude method 
    # Using Claude's native PDF support via Files API instead of manual text extraction

    async def _extract_full_text(self, *, doc, pdf_bytes: bytes, prompt: str) -> str:
        """
        Extract full text using Claude Files API for token efficiency.
        Uses cached file ID if available, otherwise uploads the PDF first.
        
        Args:
            doc: Document database model with claude_file_id, full_text, text_sha256 fields
            pdf_bytes: Raw PDF bytes  
            prompt: Extraction prompt to use
            
        Returns:
            Extracted full text
        """
        if not self.client:
            logger.error(f"Claude client not available for full text extraction from {doc.filename}.")
            return f"Error: Claude client not initialized for {doc.filename}."
            
        # Upload to Files API if not already done
        if not doc.claude_file_id:
            doc.claude_file_id = await upload_pdf(doc.filename, pdf_bytes)
            # Note: We'll save the document after extracting text to also cache the text
            
        # Build message using Files API reference
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {"type": "file", "file_id": doc.claude_file_id},
                        "citations": {"enabled": True}
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ],
            }
        ]

        # Use Sonnet for text extraction (high quality, but this is a one-time cost)
        resp = await self._claude_call(
            model=settings.MODEL_SONNET,
            messages=messages,
            max_tokens=4096,
        )
        
        # Extract text from response
        text = resp.content[0].text if resp.content else ""
        
        # Cache the extracted text and its hash
        doc.full_text = text
        doc.text_sha256 = sha256_str(text)
        # Note: Repository save should be done by caller
        
        logger.info(f"Successfully extracted full text ({len(text)} chars) from {doc.filename} using Files API.")
        return text

    async def get_document_text(self, doc_id: str, document_repo) -> str:
        """
        Get document text, using cache if available or extracting via Files API.
        
        Args:
            doc_id: Document ID
            document_repo: Document repository instance for database operations
            
        Returns:
            Full text of the document
        """
        doc = await document_repo.get_document(doc_id)
        if not doc:
            raise ValueError(f"Document {doc_id} not found")
            
        # Return cached text if available
        if doc.full_text:
            logger.info(f"Using cached text for document {doc_id} ({len(doc.full_text)} chars)")
            return doc.full_text
            
        # Extract text using Files API
        pdf_bytes = await document_repo.storage_service.get_file(f"{doc_id}.pdf")
        if not pdf_bytes:
            raise ValueError(f"PDF content not found for document {doc_id}")
            
        from settings import PDF_EXTRACT_PROMPT
        prompt = PDF_EXTRACT_PROMPT
        text = await self._extract_full_text(doc=doc, pdf_bytes=pdf_bytes, prompt=prompt)
        
        # Save the updated document with cached text and file ID
        await document_repo.update_document(doc_id, {
            "full_text": doc.full_text,
            "text_sha256": doc.text_sha256,
            "claude_file_id": doc.claude_file_id
        })
        
        return text

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
            logger.info(f"Processing PDF: {filename} with Claude API using native PDF support.")
            
            pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')
            
            # Step 1: Analyze document to determine type and periods
            # Claude's PDF support automatically extracts text and provides visual understanding
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
            
            # Claude's native PDF support handles text extraction automatically via Files API
            # No manual text extraction needed - Claude processes PDFs natively
            processing_note = f"PDF {filename} processed using Claude's native PDF support with token optimization"
            return processing_note, processed_document, citations_list
            
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
        Uses Claude's native PDF support - no manual text extraction needed.
        
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
            
            # Upload to Files API for Claude's native PDF support
            from pdf_processing.claude_file_client import upload_pdf
            file_id = await upload_pdf(filename, base64.b64decode(pdf_base64))
            
            # Create messages using Claude's native PDF support via Files API
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {"type": "file", "file_id": file_id}
                        },
                        {
                            "type": "text",
                            "text": "Analyze this financial document. Determine if it's a balance sheet, income statement, cash flow statement, or other type of document. Also identify the time periods covered (e.g., Q1 2023, FY 2022, etc.). Return ONLY a JSON response in this format:\n\n{\n  \"document_type\": \"balance_sheet|income_statement|cash_flow|notes|other\",\n  \"periods\": [\"period1\", \"period2\", ...]\n}"
                        }
                    ]
                }
            ]
            
            # Use model router for cost optimization (document type analysis is simple, use Haiku)
            optimal_model = choose_model(set(), 1000)  # Simple task, low token estimate  
            logger.info(f"Model router selected {optimal_model} for document type analysis")
            
            # Call Claude API
            response = await self._claude_call(
                model=optimal_model,
                max_tokens=1000,
                messages=messages
            )
            
            # Extract JSON from the response
            result_text = response.content[0].text
            json_match = re.search(r'{.*}', result_text, re.DOTALL)
            if not json_match:
                logger.error(f"Could not extract JSON from response: {result_text[:100]}...")
                return DocumentContentType.OTHER, []
            
            result = json.loads(json_match.group(0))
            doc_type_str = result.get("document_type", "other")
            
            # Handle document type parsing
            if "|" in doc_type_str:
                doc_types = doc_type_str.split("|")
                for dt in doc_types:
                    dt = dt.strip()
                    try:
                        document_type = DocumentContentType(dt)
                        logger.info(f"Selected document type '{dt}' from combined types: {doc_type_str}")
                        break
                    except ValueError:
                        pass
                else:
                    document_type = DocumentContentType.OTHER
            else:
                try:
                    document_type = DocumentContentType(doc_type_str)
                except ValueError:
                    logger.warning(f"Invalid document type '{doc_type_str}', using OTHER")
                    document_type = DocumentContentType.OTHER
            
            periods = result.get("periods", [])
            logger.info(f"Document {filename} classified as {document_type.value} with periods: {periods}")
            return document_type, periods
            
        except Exception as e:
            logger.exception(f"Error in document type analysis: {e}")
            return DocumentContentType.OTHER, []

    async def _extract_financial_data_with_citations(self, pdf_content_base64: str, filename: str, document_type: DocumentContentType) -> Tuple[Dict[str, Any], List[Any]]:
        """
        Extract financial data from a PDF using Claude's native PDF support.
        Claude automatically extracts text and converts pages to images.
        
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
            
            system_prompt = """You are a specialized financial document analysis assistant. Extract structured financial data from the document accurately using Claude's native PDF support.

Follow these guidelines:
1. Analyze both the text and visual elements (charts, tables, graphs) in the document.
2. Extract values with their correct time periods, labels, and units.
3. Present the data in a structured JSON format.
4. Provide citations for extracted data points when possible.
5. Any textual narrative should be brief and clearly separated from the JSON structure."""
            
            # Upload to Files API for Claude's native PDF support
            from pdf_processing.claude_file_client import upload_pdf
            file_id = await upload_pdf(filename, base64.b64decode(pdf_content_base64))
            
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {"type": "file", "file_id": file_id}
                        },
                        {
                            "type": "text",
                            "text": (
                                f"From this {doc_type_str} document, provide a comprehensive JSON object "
                                "containing all extracted financial data. The JSON should include key metrics, "
                                "time periods, and values. Structure the JSON clearly with categories like "
                                "revenue, expenses, assets, liabilities, etc. "
                                "Include any visual data from charts and tables."
                            )
                        }
                    ]
                }
            ]
            
            # Use Sonnet for complex financial analysis
            response = await self._claude_call(
                model=settings.MODEL_SONNET,
                max_tokens=4000,
                system=system_prompt,
                messages=messages
            )
            
            processed_response_content = self._process_claude_response(response)
            text_output_from_claude = processed_response_content.get("text", "").strip()
            citations = processed_response_content.get("citations", [])
            
            claude_preamble_text = ""
            parsed_financial_json = {}
            
            # Extract JSON from Claude's response
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
                        claude_preamble_text = text_output_from_claude
                        parsed_financial_json = {"error_parsing_financial_json": f"Failed to parse: {str(e)}", "original_text_payload": json_str_from_regex}
                else: 
                    logger.warning("JSON regex matched but no JSON string was captured. Treating all as preamble text.")
                    claude_preamble_text = text_output_from_claude
            else:
                logger.warning("Could not find a distinct JSON block in Claude's response using regex. Assuming all is preamble/non-JSON text.")
                claude_preamble_text = text_output_from_claude

            # Ensure parsed_financial_json is always a dict
            if not isinstance(parsed_financial_json, dict):
                logger.warning(f"Parsed financial data was not a dictionary (type: {type(parsed_financial_json)}). Wrapping it.")
                parsed_financial_json = {"financial_data_payload": parsed_financial_json, "parsing_error_occurred": True}
            
            # Include Claude's textual output if present
            if claude_preamble_text:
                parsed_financial_json['claude_textual_output_accompanying_json'] = claude_preamble_text
                logger.info(f"Captured Claude's preamble text, length: {len(claude_preamble_text)}")
            
            return parsed_financial_json, citations
            
        except Exception as e:
            logger.error(f"Error extracting structured financial data: {str(e)}", exc_info=True)
            return {"error_extracting_structured_data": str(e)}, []

    async def analyze_pdf_content(self, pdf_data: bytes, filename: str, use_cached_file_id: str = None) -> ProcessedDocument:
        """
        Lightweight PDF analysis using Claude's native PDF support.
        Uses cached file ID when available, otherwise uploads the PDF.
        
        Args:
            pdf_data: Raw PDF bytes
            filename: Name of the PDF file
            use_cached_file_id: Optional cached Claude file ID
            
        Returns:
            ProcessedDocument with analysis results
        """
        try:
            logger.info(f"Performing lightweight analysis for {filename} with cached file_id={use_cached_file_id}")
            
            # Use cached file ID if available, otherwise convert to base64
            if use_cached_file_id:
                file_id = use_cached_file_id
                logger.info(f"Using cached file_id {file_id} for analysis")
                
                # Lightweight document type analysis using file ID
                document_type, periods = await self._analyze_document_type_with_file_id(file_id, filename)
            else:
                # Convert to base64 and analyze directly
                logger.info(f"No cached file_id, analyzing {filename} directly")
                pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')
                document_type, periods = await self._analyze_document_type(pdf_base64, filename)
            
            # Basic metadata 
            document_id_str = str(uuid.uuid4())
            confidence_score = 0.8
            
            metadata = DocumentMetadata(
                id=uuid.UUID(document_id_str),
                filename=filename,
                upload_timestamp=datetime.now(),
                file_size=len(pdf_data),
                mime_type="application/pdf",
                user_id="system"
            )
            
            # Return lightweight analysis result
            processed_document = ProcessedDocument(
                metadata=metadata,
                content_type=document_type,
                extraction_timestamp=datetime.now(),
                periods=periods,
                extracted_data={"analysis_type": "lightweight", "file_id": use_cached_file_id},
                confidence_score=confidence_score,
                processing_status=ProcessingStatus.COMPLETED
            )
            
            logger.info(f"Completed lightweight analysis for {filename} as {document_type.value}")
            return processed_document
            
        except Exception as e:
            logger.exception(f"Error in lightweight PDF analysis for {filename}: {e}")
            # Return minimal error result
            document_id_err = str(uuid.uuid4())
            metadata_err = DocumentMetadata(
                id=uuid.UUID(document_id_err),
                filename=filename,
                upload_timestamp=datetime.now(),
                file_size=len(pdf_data) if pdf_data else 0,
                mime_type="application/pdf",
                user_id="system"
            )
            
            return ProcessedDocument(
                metadata=metadata_err,
                content_type=DocumentContentType.OTHER,
                extraction_timestamp=datetime.now(),
                extracted_data={"error": f"Lightweight analysis error: {str(e)}"},
                confidence_score=0.0,
                processing_status=ProcessingStatus.FAILED
            )

    async def _analyze_document_type_with_file_id(self, file_id: str, filename: str) -> Tuple[DocumentContentType, List[str]]:
        """
        Analyze document type using Files API file ID (token-efficient).
        Uses Claude's native PDF support through the Files API.
        
        Args:
            file_id: Claude file ID
            filename: Name of the PDF file
            
        Returns:
            Tuple of document type and periods
        """
        try:
            logger.info(f"Analyzing document type for {filename} using file_id={file_id}")
            
            # Use file reference with Claude's native PDF support via Files API
            messages = [
                {
                    "role": "user", 
                    "content": [
                        {
                            "type": "document",
                            "source": {"type": "file", "file_id": file_id}
                        },
                        {
                            "type": "text",
                            "text": "Analyze this financial document. Determine if it's a balance sheet, income statement, cash flow statement, or other type of document. Also identify the time periods covered (e.g., Q1 2023, FY 2022, etc.). Return ONLY a JSON response in this format:\n\n{\n  \"document_type\": \"balance_sheet|income_statement|cash_flow|notes|other\",\n  \"periods\": [\"period1\", \"period2\", ...]\n}"
                        }
                    ]
                }
            ]
             
            # Use model router for cost optimization 
            optimal_model = choose_model(set(), 1000)  # Simple task, low token estimate  
            logger.info(f"Model router selected {optimal_model} for document type analysis")
             
            # Call Claude API with Files API support
            response = await self._claude_call(
                model=optimal_model,
                max_tokens=1000,
                messages=messages
            )
            
            # Extract JSON from the response
            result_text = response.content[0].text
            json_match = re.search(r'{.*}', result_text, re.DOTALL)
            if not json_match:
                logger.error(f"Could not extract JSON from response: {result_text[:100]}...")
                return DocumentContentType.OTHER, []
            
            result = json.loads(json_match.group(0))
            doc_type_str = result.get("document_type", "other")
            
            # Handle document type parsing (same logic as base method)
            if "|" in doc_type_str:
                doc_types = doc_type_str.split("|")
                for dt in doc_types:
                    dt = dt.strip()
                    try:
                        document_type = DocumentContentType(dt)
                        logger.info(f"Selected document type '{dt}' from combined types: {doc_type_str}")
                        break
                    except ValueError:
                        pass
                else:
                    document_type = DocumentContentType.OTHER
            else:
                try:
                    document_type = DocumentContentType(doc_type_str)
                except ValueError:
                    logger.warning(f"Invalid document type '{doc_type_str}', using OTHER")
                    document_type = DocumentContentType.OTHER
            
            periods = result.get("periods", [])
            logger.info(f"Document {filename} classified as {document_type.value} with periods: {periods}")
            return document_type, periods
            
        except Exception as e:
            logger.exception(f"Error in file-based document type analysis: {e}")
            return DocumentContentType.OTHER, []