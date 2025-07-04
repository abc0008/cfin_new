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
import json
import re
import uuid
from typing import Dict, List, Optional, Any, Tuple, TYPE_CHECKING, ForwardRef
import logging
import asyncio
from anthropic import AsyncAnthropic, RateLimitError
from anthropic.types import Message as AnthropicMessage
from datetime import datetime
import contextlib
import httpx
import copy

# Claude API optimization imports
import settings
from settings import ANTHROPIC_BETA
from utils.claude_bucket import ClaudeBucket
from pdf_processing.claude_file_client import upload_pdf
from pdf_processing.model_router import choose_model
from utils.hashlib_utils import sha256_str
from utils.token_utils import count_tokens

from models.document import ProcessedDocument, Citation as DocumentCitation, DocumentContentType, DocumentMetadata, ProcessingStatus
from pdf_processing.langchain_service import LangChainService
from models.tools import ALL_TOOLS_DICT, CLAUDE_API_TOOLS_LIST # Ensure this import is present

import os
import base64
import json
import re
import uuid
from typing import Dict, List, Optional, Any, Tuple, TYPE_CHECKING, ForwardRef
import logging
from importlib.resources import files # Added for this change
from anthropic import AsyncAnthropic, RateLimitError
from anthropic.types import Message as AnthropicMessage
from datetime import datetime
import contextlib
import httpx
import copy

# Claude API optimization imports
import settings
from settings import ANTHROPIC_BETA
from utils.claude_bucket import ClaudeBucket
from pdf_processing.claude_file_client import upload_pdf
from pdf_processing.model_router import choose_model
from utils.hashlib_utils import sha256_str
from utils.token_utils import count_tokens

from models.document import ProcessedDocument, Citation as DocumentCitation, DocumentContentType, DocumentMetadata, ProcessingStatus
from pdf_processing.langchain_service import LangChainService
from models.tools import ALL_TOOLS_DICT, CLAUDE_API_TOOLS_LIST # Ensure this import is present

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

# Load the default financial analysis prompt from file
try:
    PROMPT_PATH = files('pdf_processing').joinpath('prompts/default_financial_analysis_prompt.md')
    LOADED_DEFAULT_FINANCIAL_PROMPT = PROMPT_PATH.read_text(encoding='utf-8')
except Exception as e:
    logger.error(f"Error loading default_financial_analysis_prompt.md: {e}", exc_info=True)
    LOADED_DEFAULT_FINANCIAL_PROMPT = "Error: Default financial analysis prompt could not be loaded. Please check system configuration." # Fallback prompt

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
            self.max_tokens = 4000  # Default max tokens
            self.temperature = 0.0  # Default temperature for deterministic outputs
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

    async def _claude_call(self, stream: bool = False, **kwargs):
        """
        Central wrapper for all Claude API calls with rate limiting and token efficiency.
        Supports both streaming and non-streaming modes.
        
        Args:
            stream: Whether to stream the response
            **kwargs: Arguments to pass to client.messages.create
            
        Returns:
            Claude API response (AnthropicMessage if stream=False, AsyncStream if stream=True)
        """
        # Estimate tokens for rate limiting
        messages = kwargs.get("messages", [])
        tokens_in = count_tokens(messages) # Custom estimator

        # --- BEGIN SDK TOKEN COUNTING (AWAITED AND ALIGNED V4) ---
        sdk_actual_tokens = None # Initialize to ensure it's defined
        try:
            actual_messages_for_count = messages if isinstance(messages, list) else []
            if not actual_messages_for_count and isinstance(messages, dict):
                actual_messages_for_count = [messages]

            # Sanitize messages so the count_tokens endpoint accepts them
            sanitized_messages_for_count = self._sanitize_messages_for_token_count(actual_messages_for_count)

            params_for_count = {
                "model": kwargs.get("model", self.model),
                "messages": sanitized_messages_for_count  # use sanitized copy
            }

            if "tools" in kwargs and kwargs.get("tools"):
                params_for_count["tools"] = kwargs.get("tools")
            
            if "system" in kwargs and kwargs.get("system"):
                params_for_count["system"] = kwargs.get("system")
            
            sdk_token_count_result = await self.client.messages.count_tokens(**params_for_count)
            sdk_actual_tokens = sdk_token_count_result.input_tokens
            logger.info(f"Anthropic SDK estimated input tokens ({'streaming' if stream else 'non-streaming'}): {sdk_actual_tokens} (Custom estimate: {tokens_in})")
        except Exception as e:
            logger.error(f"Error during SDK token counting ({'streaming' if stream else 'non-streaming'}): {e}", exc_info=True)
        # --- END SDK TOKEN COUNTING (AWAITED AND ALIGNED V4) ---

        # Apply rate limiting based on current token bucket state
        # Use SDK token count if available for more accurate throttling, otherwise fall back to custom estimate
        tokens_for_throttling = sdk_actual_tokens if sdk_actual_tokens is not None else tokens_in
        logger.info(f"Throttling based on token count: {tokens_for_throttling} (SDK count: {sdk_actual_tokens}, Custom estimate: {tokens_in})")
        await ClaudeBucket.throttle(tokens_for_throttling)

        try:
            # Make the API call with token efficiency headers
            if stream:
                # Use streaming mode - returns AsyncMessageStreamManager
                resp = self.client.messages.stream(
                    extra_headers=self._extra_headers,
                    **kwargs
                )
            else:
                # Use non-streaming mode (existing behavior)
                resp = await self.client.messages.create(
                    extra_headers=self._extra_headers,
                    **kwargs
                )
        except RateLimitError as e:
            # Re-raise rate limit errors for upstream handling
            raise
        except Exception as e:
            # Check for credit balance errors
            if "credit balance is too low" in str(e).lower():
                logger.error(f"Anthropic API credit balance too low: {str(e)}")
                raise ValueError("Anthropic API credit balance is insufficient. Please add credits to your account.")
            # Re-raise other errors
            raise
        
        # Update rate limit state from response headers if available (non-streaming only)
        if not stream and hasattr(resp, 'response_headers') and resp.response_headers:
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

    async def _process_streaming_response(self, stream_manager, emit_callback=None):
        """
        Process streaming Claude API response and emit events for real-time updates.
        Implements hybrid streaming: text content streams immediately, tools buffer until complete.
        
        Args:
            stream_manager: AsyncMessageStreamManager from Claude API
            emit_callback: Optional callback function to emit streaming events
            
        Returns:
            Processed response dict with accumulated text, tool_calls, and citations
        """
        accumulated_text = ""
        initial_text = ""  # Track initial text before tools
        post_tool_text = ""  # Track text after tools
        tools_started = False  # Track if we've started processing tools
        received_streaming_text = False  # Track if we received any streaming text
        last_content_update_length = 0  # Track last content update to avoid duplicates
        tool_calls = []
        tool_buffer = {}  # Buffer incomplete tool calls by ID
        citations = []
        message_id = None  # Track message ID for consistent event emission
        
        try:
            async with stream_manager as stream:
                async for chunk in stream:
                    if chunk.type == "message_start":
                        # Message started - capture message ID and emit initial event
                        message_id = chunk.message.id
                        if emit_callback:
                            await emit_callback({
                                "type": "message_start",
                                "message_id": message_id
                            })
                    
                    elif chunk.type == "content_block_start":
                        if chunk.content_block.type == "text":
                            # Text block started - emit event
                            if emit_callback:
                                await emit_callback({
                                    "type": "text_start",
                                    "block_index": chunk.index,
                                    "message_id": message_id
                                })
                        elif chunk.content_block.type == "tool_use":
                            # Tool use block started - buffer it
                            tool_id = chunk.content_block.id
                            tool_buffer[tool_id] = {
                                "id": tool_id,
                                "name": chunk.content_block.name,
                                "input": {}
                            }
                            # Mark that tools have started
                            if not tools_started:
                                tools_started = True
                                # Save the initial text before tools
                                initial_text = accumulated_text
                            if emit_callback:
                                await emit_callback({
                                    "type": "tool_start",
                                    "tool_id": tool_id,
                                    "tool_name": chunk.content_block.name,
                                    "message_id": message_id
                                })
                    
                    elif chunk.type == "content_block_delta":
                        if chunk.delta.type == "text_delta":
                            text_delta = chunk.delta.text
                            
                            # IMPORTANT: Only accumulate and stream text BEFORE tools
                            # Post-tool text is often unformatted duplicate content
                            if not tools_started:
                                # Stream text content immediately
                                accumulated_text += text_delta
                                received_streaming_text = True  # Mark that we received streaming text
                                
                                if emit_callback:
                                    await emit_callback({
                                        "type": "text_delta",
                                        "text": text_delta,
                                        "accumulated_text": accumulated_text,
                                        "message_id": message_id
                                    })
                                    
                                    # Only send content_update if we have significant new content
                                    # This prevents duplicate updates for single character additions
                                    content_length_diff = len(accumulated_text) - last_content_update_length
                                    if content_length_diff >= 50 or (content_length_diff > 0 and text_delta.endswith('\n')):
                                        await emit_callback({
                                            "type": "content_update",
                                            "accumulated_text": accumulated_text,
                                            "message_id": message_id,
                                            "is_post_tools": False,
                                            "post_tool_text": None
                                        })
                                        last_content_update_length = len(accumulated_text)
                            else:
                                # Track post-tool text separately but DON'T accumulate or send it
                                post_tool_text += text_delta
                                logger.info(f"Ignoring post-tool text delta: {len(text_delta)} chars")
                        elif chunk.delta.type == "input_json_delta":
                            # Buffer tool input (don't stream incomplete JSON)
                            # This accumulates the tool parameters - we'll process when complete
                            pass
                    
                    elif chunk.type == "content_block_stop":
                        if chunk.index is not None:
                            # Content block completed - send final content_update if needed
                            if not tools_started and last_content_update_length < len(accumulated_text):
                                # Send final content update for any remaining text
                                if emit_callback:
                                    await emit_callback({
                                        "type": "content_update",
                                        "accumulated_text": accumulated_text,
                                        "message_id": message_id,
                                        "is_post_tools": False,
                                        "post_tool_text": None
                                    })
                                    last_content_update_length = len(accumulated_text)
                            
                            if emit_callback:
                                await emit_callback({
                                    "type": "content_block_stop",
                                    "block_index": chunk.index,
                                    "message_id": message_id
                                })
                    
                    elif chunk.type == "message_delta":
                        # Message metadata updates
                        if hasattr(chunk.delta, 'stop_reason') and chunk.delta.stop_reason:
                            if emit_callback:
                                await emit_callback({
                                    "type": "message_delta",
                                    "stop_reason": chunk.delta.stop_reason,
                                    "message_id": message_id
                                })
                    
                    elif chunk.type == "message_stop":
                        # Message completed
                        if emit_callback:
                            # Send any accumulated post-tool textual analysis before signaling completion
                            if post_tool_text.strip():
                                await emit_callback({
                                    "type": "content_update",
                                    "is_post_tools": True,
                                    "post_tool_text": post_tool_text.strip(),
                                    "message_id": message_id
                                })

                            await emit_callback({
                                "type": "message_stop",
                                "message_id": message_id
                            })
                
                # After stream completes, get the final message with complete tool calls
                # IMPORTANT: We only use final_message for extracting tool calls, NOT text content
                # This prevents duplicate unformatted text that Claude sends in final_message
                # All text content should come from the streaming deltas above
                if received_streaming_text:
                    logger.info(f"Received {len(accumulated_text)} chars during streaming, will ignore text in final_message")
                final_message = await stream.get_final_message()
                
                # Extract tool calls and *any* new text from final message (concluding insights often appear here)
                concluding_text = ""
                if final_message and final_message.content:
                    for content_block in final_message.content:
                        if hasattr(content_block, 'type') and content_block.type == 'tool_use':
                            # Convert tool input (Pydantic model -> dict) for later processing
                            tool_input = content_block.input
                            if hasattr(tool_input, 'model_dump'):
                                tool_input = tool_input.model_dump()
                            elif hasattr(tool_input, 'dict'):
                                tool_input = tool_input.dict()

                            tool_call = {
                                "id": content_block.id,
                                "name": content_block.name,
                                "input": tool_input
                            }
                            tool_calls.append(tool_call)
                            # Debug
                            logger.info(f"Queued tool_call from final_message: {tool_call['name']} (ID: {tool_call['id']})")
                        elif hasattr(content_block, 'text'):
                            concluding_text += content_block.text

                # Emit concluding insights even if similar to accumulated_text – frontend will handle deduplication
                if concluding_text:
                    if emit_callback:
                        await emit_callback({
                            "type": "content_update",
                            "is_post_tools": True,
                            "post_tool_text": concluding_text,
                            "message_id": message_id
                        })
                
                return {
                    "text": accumulated_text,
                    "tool_calls": tool_calls,
                    "citations": citations
                }
                
        except Exception as e:
            logger.error(f"Error processing streaming response: {e}", exc_info=True)
            # Return what we have so far
            return {
                "text": accumulated_text,
                "tool_calls": tool_calls,
                "citations": citations,
                "error": str(e)
            }

    def _is_substantially_new_content(self, new_text: str, existing_text: str, similarity_threshold: float = 0.15) -> bool:
        """
        Check if new_text contains substantially new content compared to existing_text.
        Uses multiple methods to detect duplicates and near-duplicates.
        
        Args:
            new_text: The new text content to evaluate
            existing_text: The accumulated text content so far
            similarity_threshold: Minimum proportion of new content required (0.15 = 15% new)
            
        Returns:
            True if the new text is substantially different and should be added
        """
        if not new_text or not new_text.strip():
            return False
            
        if not existing_text:
            return True
            
        new_text_clean = new_text.strip().lower()
        existing_text_clean = existing_text.strip().lower()
        
        # Method 1: Check if new text is completely contained in existing text
        if new_text_clean in existing_text_clean:
            return False
            
        # Method 2: Check if substantial portion (>85%) of new text already exists
        new_words = set(new_text_clean.split())
        existing_words = set(existing_text_clean.split())
        
        if new_words:
            overlap_ratio = len(new_words.intersection(existing_words)) / len(new_words)
            if overlap_ratio > (1 - similarity_threshold):  # More than 85% overlap
                return False
        
        # Method 3: Check for repeated sentence patterns
        new_sentences = [s.strip() for s in new_text_clean.split('.') if s.strip()]
        existing_sentences = [s.strip() for s in existing_text_clean.split('.') if s.strip()]
        
        if new_sentences and existing_sentences:
            # Count how many new sentences are similar to existing ones
            similar_count = 0
            for new_sent in new_sentences:
                if len(new_sent) > 10:  # Only check substantial sentences
                    for existing_sent in existing_sentences:
                        if new_sent in existing_sent or existing_sent in new_sent:
                            similar_count += 1
                            break
            
            similarity_ratio = similar_count / len(new_sentences) if new_sentences else 0
            if similarity_ratio > (1 - similarity_threshold):
                return False
        
        # If we made it here, the content appears to be substantially new
        return True

    async def execute_tool_interaction_turn(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 4000,
        temperature: float = 0.7,
        model_override: Optional[str] = None,
        stream: bool = False,
        emit_callback=None
    ):
        """
        Execute a single turn of tool-based interaction with Claude.
        Supports both streaming and non-streaming modes.
        
        Args:
            system_prompt: System prompt for the interaction
            messages: Conversation messages
            tools: Available tools for Claude to use
            max_tokens: Maximum tokens to generate
            temperature: Generation temperature
            model_override: Optional model override
            stream: Whether to stream the response
            emit_callback: Optional callback for streaming events
            
        Returns:
            Claude API response (AnthropicMessage if stream=False, processed dict if stream=True)
        """
        if not self.client:
            raise ValueError("Claude API client is not available")
            
        # Use provided tools or default to instance tools
        tools_to_use = tools if tools is not None else self.tools_for_api
        
        # Choose optimal model based on tool complexity or override
        if model_override:
            optimal_model = model_override
            logger.info(f"Executing tool interaction turn with overridden model: {optimal_model}, {len(tools_to_use) if tools_to_use else 0} tools available, streaming: {stream}")
        else:
            tool_names = {tool.get("name", "") for tool in tools_to_use} if tools_to_use else set()
            estimated_tokens = sum(len(str(msg.get("content", ""))) for msg in messages) // 4
            optimal_model = choose_model(tool_names, estimated_tokens)
            logger.info(f"Executing tool interaction turn with model_router selected model: {optimal_model}, {len(tools_to_use) if tools_to_use else 0} tools available, streaming: {stream}")
        
        # Build request parameters
        request_params = {
            "model": optimal_model,
            "system": system_prompt,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream
        }
        
        # Add tools if available
        if tools_to_use:
            request_params["tools"] = tools_to_use
            
        # Execute the API call
        response = await self._claude_call(**request_params)
        
        if stream:
            # Process streaming response
            return await self._process_streaming_response(response, emit_callback)
        else:
            # Return non-streaming response as before
            return response

    async def generate_response(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 4000,
        model: Optional[str] = None,
        stream: bool = False,
        emit_callback=None
    ):
        """
        Generate a response from Claude based on a conversation with a system prompt.
        Supports both streaming and non-streaming modes.
        
        Args:
            system_prompt: System prompt that guides Claude's behavior
            messages: List of message dictionaries with 'role' and 'content' keys
            temperature: Temperature for generation (0.0 to 1.0)
            max_tokens: Maximum number of tokens to generate
            model: Optional model override (e.g., "claude-3-5-haiku-20241022")
            stream: Whether to stream the response
            emit_callback: Optional callback for streaming events
            
        Returns:
            Generated response text (str if stream=False, dict if stream=True)
        """
        if not self.client:
            # Mock response for testing or when API key is not available
            logger.warning("Using mock response because Claude API client is not available")
            error_msg = "I'm sorry, I cannot process your request because the Claude API is not configured properly. Please check the API key."
            if stream:
                return {"text": error_msg, "tool_calls": [], "citations": []}
            return error_msg
        
        try:
            # Convert message format to Anthropic's format
            formatted_messages = []
            for msg in messages:
                role = "user" if msg["role"] == "user" else "assistant"
                formatted_messages.append({"role": role, "content": msg["content"]})
            
            logger.info(f"Sending request to Claude API with {len(formatted_messages)} messages, streaming: {stream}")

            # Use provided model or default to instance model
            used_model = model or self.model
            
            # --- BEGIN SDK TOKEN COUNTING (AWAITED AND ALIGNED V4) ---
            try:
                params_for_count_native = {
                    "model": used_model,
                    "messages": self._sanitize_messages_for_token_count(list(formatted_messages))
                }

                if system_prompt and isinstance(system_prompt, str):
                    params_for_count_native["system"] = system_prompt
                
                sdk_token_count_result_native = await self.client.messages.count_tokens(**params_for_count_native)
                sdk_actual_tokens_native = sdk_token_count_result_native.input_tokens
                logger.info(f"Anthropic SDK estimated input tokens (generate_response {'streaming' if stream else 'non-streaming'}): {sdk_actual_tokens_native}")
            except Exception as e:
                logger.error(f"Error during SDK token counting (generate_response {'streaming' if stream else 'non-streaming'}): {e}", exc_info=True)
            # --- END SDK TOKEN COUNTING (AWAITED AND ALIGNED V4) ---
            
            # Call Claude API
            response = await self._claude_call(
                model=used_model,
                system=system_prompt,
                messages=formatted_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream
            )
            
            if stream:
                # Process streaming response
                return await self._process_streaming_response(response, emit_callback)
            else:
                # Return non-streaming response as before
                return response.content[0].text
                
        except Exception as e:
            logger.error(f"Error calling Claude API: {str(e)}")
            error_message = f"I apologize, but there was an error processing your request: {str(e)}"
            if stream:
                return {"text": error_message, "tool_calls": [], "citations": [], "error": str(e)}
            return error_message

    # Removed: _extract_full_text_from_pdf_claude method 
    # Using Claude's native PDF support via Files API instead of manual text extraction

    async def _extract_full_text(self, *, doc, pdf_bytes: bytes, prompt: str) -> str:
        """
        DEPRECATED: This method is deprecated in favor of using Claude's native PDF support.
        
        Manual text extraction is no longer recommended when using Anthropic's Files API.
        Instead, pass the file_id directly to Claude for native PDF processing.
        
        This method will be removed in a future version.
        """
        logger.warning("_extract_full_text is deprecated. Use Claude's native PDF support with Files API instead.")
        raise DeprecationWarning(
            "_extract_full_text is deprecated. Use Claude's native PDF support via Files API. "
            "Pass file_id directly to Claude instead of extracting text manually."
        )

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
        Process a PDF using Claude's native PDF support via Files API.
        No manual text extraction - relies on Files API for full document access.
        
        Args:
            pdf_data: Raw bytes of the PDF file
            filename: Name of the PDF file
            
        Returns:
            A tuple containing a processing note, the processed document object, and a list of citations.
        """
        if not self.client:
            logger.error("Cannot process PDF because Claude API client is not available")
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
            raise ValueError(error_message_text)
        
        processed_document: Optional[ProcessedDocument] = None
        citations_list: List[DocumentCitation] = []
        claude_file_id: Optional[str] = None

        try:
            logger.info(f"Processing PDF: {filename} with Claude API using native PDF support.")
            
            pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')
            
            # Step 1: Upload to Files API once and reuse the file_id
            from pdf_processing.claude_file_client import upload_pdf
            claude_file_id = await upload_pdf(filename, pdf_data)
            logger.info(f"Generated Claude file_id {claude_file_id} for {filename}")
            
            # Step 2: Analyze document to determine type and periods using file_id
            logger.info(f"Analyzing document type for {filename}")
            document_type, periods = await self._analyze_document_type_with_file_id(claude_file_id, filename)
            logger.info(f"Document {filename} classified as: {document_type.value} with periods: {periods}")
            
            # Step 3: Extract structured financial data and citations using file_id
            logger.info(f"Extracting structured financial data and citations for {filename}")
            # This call now returns structured_data (JSON-like dict) and citations_list
            structured_financial_data, citations_from_extraction = await self._extract_financial_data_with_citations_by_file_id(
                file_id=claude_file_id,
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
            
            # Add the file_id to extracted_data for database storage
            if structured_financial_data and isinstance(structured_financial_data, dict):
                structured_financial_data['claude_file_id'] = claude_file_id
                logger.info(f"Added claude_file_id {claude_file_id} to extracted_data for {filename}")
            
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
                extracted_data=structured_financial_data, # This now includes claude_file_id
                confidence_score=confidence_score,
                processing_status=ProcessingStatus.COMPLETED
            )
            
            # Claude's native PDF support handles text extraction automatically via Files API
            # No manual text extraction needed - Claude processes PDFs natively
            processing_note = f"PDF {filename} processed using Claude's native PDF support via Files API"
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
            # Return the error text as processing note in this failure case
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
            if "credit balance is too low" in str(e).lower() or "anthropic api credit balance" in str(e).lower():
                logger.warning(f"Claude API unavailable due to credit balance. Using fallback classification for {filename}")
                # Fallback: simple filename-based classification
                filename_lower = filename.lower()
                if "balance" in filename_lower or "bs" in filename_lower:
                    return DocumentContentType.BALANCE_SHEET, ["Unknown Period"]
                elif "income" in filename_lower or "profit" in filename_lower or "loss" in filename_lower:
                    return DocumentContentType.INCOME_STATEMENT, ["Unknown Period"] 
                elif "cash" in filename_lower or "flow" in filename_lower:
                    return DocumentContentType.CASH_FLOW, ["Unknown Period"]
                else:
                    return DocumentContentType.OTHER, ["Unknown Period"]
            else:
                logger.exception(f"Error in document type analysis: {e}")
                return DocumentContentType.OTHER, []

    async def _extract_financial_data_with_citations_by_file_id(self, file_id: str, filename: str, document_type: DocumentContentType) -> Tuple[Dict[str, Any], List[Any]]:
        """
        Extract financial data from a PDF using Claude's native PDF support with existing file_id.
        Optimized version that reuses uploaded file_id instead of uploading again.
        
        Args:
            file_id: Existing Claude file ID from previous upload
            filename: Name of the PDF file
            document_type: Type of document being processed
            
        Returns:
            Tuple of extracted structured data dictionary and list of citations
        """
        if not self.client:
            logger.error("Cannot extract financial data because Claude API client is not available")
            raise ValueError("Claude API client is not available. Check your API key.")
        
        try:
            logger.info(f"Extracting structured financial data with citations from: {filename} using file_id {file_id}")
            
            doc_type_str = document_type.value if document_type else "financial document"
            
            system_prompt = """You are a specialized financial document analysis assistant. Extract structured financial data from the document accurately using Claude's native PDF support.

Follow these guidelines:
1. Analyze both the text and visual elements (charts, tables, graphs) in the document.
2. Extract values with their correct time periods, labels, and units.
3. Present the data in a structured JSON format.
4. Provide citations for extracted data points when possible.
5. Any textual narrative should be brief and clearly separated from the JSON structure."""
            
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
            if "credit balance is too low" in str(e).lower() or "anthropic api credit balance" in str(e).lower():
                logger.warning(f"Claude API unavailable due to credit balance. Returning minimal financial data for {filename}")
                return {
                    "error_extracting_structured_data": "Claude API credit balance insufficient",
                    "fallback_note": f"Document {filename} uploaded successfully but structured analysis unavailable",
                    "document_readable": True
                }, []
            else:
                logger.error(f"Error extracting structured financial data: {str(e)}", exc_info=True)
                return {"error_extracting_structured_data": str(e)}, []

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
            if "credit balance is too low" in str(e).lower() or "anthropic api credit balance" in str(e).lower():
                logger.warning(f"Claude API unavailable due to credit balance. Returning minimal financial data for {filename}")
                return {
                    "error_extracting_structured_data": "Claude API credit balance insufficient",
                    "fallback_note": f"Document {filename} uploaded successfully but structured analysis unavailable",
                    "document_readable": True
                }, []
            else:
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

    async def analyze_with_visualization_tools(
        self,
        document_text: str,
        user_query: str,
        knowledge_base: Optional[str] = None,
        file_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze document with visualization tools using multi-turn conversation.
        This method provides a single-entry point for conversation service to use
        visualization tools similar to how analysis strategies work.
        
        Args:
            document_text: Combined document text for analysis
            user_query: User's question/request
            knowledge_base: Optional knowledge base context
            file_id: Optional Claude file ID for reference
            
        Returns:
            Dict with analysis_text and visualizations (charts, tables)
        """
        try:
            logger.info(f"Starting analyze_with_visualization_tools for query: '{user_query[:100]}...'")
            
            # Build initial messages
            initial_messages = []
            
            # Add file reference if available
            if file_id:
                initial_messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {"type": "file", "file_id": file_id}
                        },
                        {
                            "type": "text", 
                            "text": f"Document context and user query:\n\n{user_query}"
                        }
                    ]
                })
            else:
                # Use text content
                context = f"Financial Document Content:\n{document_text}\n\nUser Query: {user_query}"
                initial_messages.append({
                    "role": "user",
                    "content": context
                })
            
            # Initialize conversation tracking
            conversation_messages = initial_messages.copy()
            accumulated_text = ""
            accumulated_charts = []
            accumulated_tables = []
            accumulated_metrics = []
            
            max_turns = 5  # Limit iterations
            
            for turn in range(max_turns):
                logger.info(f"Visualization analysis turn {turn + 1}/{max_turns}")
                
                # Execute tool interaction turn
                api_response = await self.execute_tool_interaction_turn(
                    system_prompt=LOADED_DEFAULT_FINANCIAL_PROMPT, # Use loaded prompt
                    messages=conversation_messages,
                    tools=self.tools_for_api,
                    max_tokens=4000,
                    temperature=0.7
                )
                
                # Process response content
                assistant_content_blocks = []
                tool_results_for_next_turn = []
                contains_tool_use = False
                
                if api_response.content:
                    for block in api_response.content:
                        if block.type == "text":
                            accumulated_text += block.text + "\n"
                            assistant_content_blocks.append({
                                "type": "text",
                                "text": block.text
                            })
                        elif block.type == "tool_use":
                            contains_tool_use = True
                            tool_name = block.name
                            tool_input = block.input
                            tool_use_id = block.id
                            
                            logger.info(f"Processing tool {tool_name} (ID: {tool_use_id})")
                            
                            # Add tool_use block to assistant content
                            assistant_content_blocks.append({
                                "type": "tool_use",
                                "id": tool_use_id,
                                "name": tool_name,
                                "input": tool_input
                            })
                            
                            # Process the tool
                            try:
                                from utils import tool_processing
                                processed_data = tool_processing.process_visualization_input(
                                    tool_name, tool_input, tool_use_id
                                )
                                
                                if processed_data:
                                    # Collect processed data
                                    if tool_name == "generate_graph_data":
                                        accumulated_charts.append(processed_data)
                                    elif tool_name == "generate_table_data":
                                        accumulated_tables.append(processed_data)
                                    elif tool_name == "generate_financial_metric":
                                        accumulated_metrics.append(processed_data)
                                    
                                    # Prepare tool result for next turn
                                    tool_results_for_next_turn.append({
                                        "type": "tool_result",
                                        "tool_use_id": tool_use_id,
                                        "content": json.dumps(processed_data)
                                    })
                                else:
                                    tool_results_for_next_turn.append({
                                        "type": "tool_result", 
                                        "tool_use_id": tool_use_id,
                                        "content": "Tool processed but returned no data.",
                                        "is_error": True
                                    })
                                    
                            except Exception as e:
                                logger.error(f"Error processing tool {tool_name}: {e}")
                                tool_results_for_next_turn.append({
                                    "type": "tool_result",
                                    "tool_use_id": tool_use_id, 
                                    "content": f"Error: {str(e)}",
                                    "is_error": True
                                })
                
                # Add assistant response to conversation
                conversation_messages.append({
                    "role": "assistant",
                    "content": assistant_content_blocks
                })
                
                # Add tool results for next turn if any
                if tool_results_for_next_turn:
                    conversation_messages.append({
                        "role": "user",
                        "content": tool_results_for_next_turn
                    })
                
                # Check if we should continue
                if api_response.stop_reason in ["stop_sequence", "end_turn"] or not contains_tool_use:
                    logger.info(f"Visualization analysis completed: {api_response.stop_reason}")
                    break
                    
                if turn == max_turns - 1:
                    logger.warning(f"Reached maximum turns ({max_turns}) for visualization analysis")
                    break
            
            # Prepare analysis text, ensuring it's not empty
            current_analysis_text = accumulated_text.strip()
            if not current_analysis_text:
                logger.warning("accumulated_text was empty in analyze_with_visualization_tools. Using default fallback text.")
                current_analysis_text = "Here's the information based on your query and the provided documents."

            # Return structured result
            result = {
                "analysis_text": current_analysis_text,
                "visualizations": {
                    "charts": accumulated_charts,
                    "tables": accumulated_tables
                },
                "metrics": accumulated_metrics
            }
            
            logger.info(f"Visualization analysis completed: {len(accumulated_charts)} charts, {len(accumulated_tables)} tables, {len(accumulated_metrics)} metrics. Analysis text length: {len(current_analysis_text)}")
            return result
            
        except Exception as e:
            logger.error(f"Error in analyze_with_visualization_tools: {e}", exc_info=True)
            return {
                "analysis_text": f"Error during analysis: {str(e)}",
                "visualizations": {"charts": [], "tables": []},
                "metrics": []
            }

    async def analyze_with_visualization_tools_streaming(
        self,
        document_text: str,
        user_query: str,
        knowledge_base: Optional[str] = None,
        file_id: Optional[str] = None,
        emit_callback=None,
        message_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Streaming version of analyze_with_visualization_tools.
        Provides real-time updates as text and tools are processed.
        
        Args:
            document_text: Combined document text for analysis
            user_query: User's question/request
            knowledge_base: Optional knowledge base context
            file_id: Optional Claude file ID for reference
            emit_callback: Callback function for streaming events
            
        Returns:
            Dict with analysis_text and visualizations (charts, tables)
        """
        try:
            logger.info(f"Starting streaming analyze_with_visualization_tools for query: '{user_query[:100]}...'")
            
            # Build initial messages (same as non-streaming)
            initial_messages = []
            
            if file_id:
                initial_messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {"type": "file", "file_id": file_id}
                        },
                        {
                            "type": "text", 
                            "text": f"Document context and user query:\n\n{user_query}"
                        }
                    ]
                })
            else:
                context = f"Financial Document Content:\n{document_text}\n\nUser Query: {user_query}"
                initial_messages.append({
                    "role": "user",
                    "content": context
                })
            
            # Initialize conversation tracking
            conversation_messages = initial_messages.copy()
            accumulated_text = ""
            accumulated_charts = []
            accumulated_tables = []
            accumulated_metrics = []
            
            max_turns = 5  # Limit iterations
            
            for turn in range(max_turns):
                logger.info(f"Streaming visualization analysis turn {turn + 1}/{max_turns}")
                
                # Execute tool interaction turn WITH streaming and retry logic for 500 errors
                retries = 0
                max_retries = 2
                while retries <= max_retries:
                    try:
                        # Create a filtering callback for subsequent turns
                        # Only allow tool events, block all text/content events to prevent duplicates
                        async def filtered_emit_callback(event: Dict[str, Any]):
                            if turn > 0:
                                # After first turn, allow tool-related events and the single concluding content_update
                                if not (
                                    (event.get('type') == 'content_update' and event.get('is_post_tools') and event.get('post_tool_text')) or
                                    event.get('type') in {'tool_start', 'tool_complete', 'chart_ready', 'table_ready', 'metric_ready', 'message_stop'}
                                ):
                                    logger.info(
                                        f"Turn {turn + 1}: Blocking {event.get('type')} event to prevent duplicate content"
                                    )
                                    return
                            # Pass through allowed events
                            if emit_callback:
                                await emit_callback(event)
                        
                        response = await self.execute_tool_interaction_turn(
                            system_prompt=LOADED_DEFAULT_FINANCIAL_PROMPT,
                            messages=conversation_messages,
                            tools=self.tools_for_api,
                            max_tokens=4000,
                            temperature=0.7,
                            stream=True,  # Enable streaming to get real-time text updates
                            emit_callback=filtered_emit_callback  # Use filtered callback
                        )
                        break  # Success, exit retry loop
                    except Exception as e:
                        if "500" in str(e) or "Internal server error" in str(e):
                            retries += 1
                            if retries <= max_retries:
                                logger.warning(f"Received 500 error on turn {turn + 1}, retry {retries}/{max_retries}: {str(e)}")
                                await asyncio.sleep(2 * retries)  # Exponential backoff
                                continue
                        # Re-raise if not a 500 error or out of retries
                        raise
                
                # Handle streaming response (response is now a dict from _process_streaming_response)
                if isinstance(response, dict):
                    # Extract text and tool calls from streaming response
                    response_text = response.get("text", "")
                    tool_calls = response.get("tool_calls", [])
                    
                    # CRITICAL: For streaming, the text has ALREADY been sent to frontend
                    # We should NOT re-accumulate it here as that causes duplication
                    # The 'response' from execute_tool_interaction_turn contains the full text
                    # but it's already been streamed piece by piece to the frontend
                    if response_text:
                        if turn == 0:
                            # First turn - save for analysis result but DON'T re-stream
                            accumulated_text = response_text
                            logger.info(f"Turn {turn + 1}: Captured streamed text ({len(response_text)} chars) - already sent to frontend")
                        else:
                            # Subsequent turns - check if this is new content
                            logger.info(f"Turn {turn + 1}: Received {len(response_text)} chars")
                            
                            # Only accumulate if this is genuinely new content, not a duplicate
                            response_plain = response_text.replace('\n', ' ').replace('  ', ' ').strip()
                            accumulated_plain = accumulated_text.replace('\n', ' ').replace('  ', ' ').strip()
                            
                            if response_plain[:min(100, len(response_plain))] in accumulated_plain:
                                logger.warning(f"Turn {turn + 1}: Detected duplicate content - ignoring to prevent duplication")
                            else:
                                # This appears to be new content, accumulate it
                                accumulated_text = accumulated_text + "\n\n" + response_text
                                logger.info(f"Turn {turn + 1}: Added new content to accumulated_text")
                    
                    # Log tool calls for debugging
                    if tool_calls:
                        logger.info(f"Received {len(tool_calls)} tool calls from streaming response")
                        for tc in tool_calls:
                            logger.info(f"Tool call: {tc.get('name')} (ID: {tc.get('id')})")
                else:
                    # Fallback for unexpected response format
                    logger.warning(f"Unexpected response format from streaming execute_tool_interaction_turn: {type(response)}")
                    tool_calls = []
                    response_text = ""
                
                contains_tool_use = len(tool_calls) > 0
                
                # Build assistant content blocks for conversation history
                assistant_content_blocks = []
                tool_results_for_next_turn = []
                
                # Add text content if any
                if response_text:
                    assistant_content_blocks.append({
                        "type": "text",
                        "text": response_text
                    })
                
                # Process tool calls
                for tool_call in tool_calls:
                    tool_name = tool_call["name"]
                    tool_input = tool_call["input"]
                    tool_use_id = tool_call["id"]
                    
                    logger.info(f"Processing streaming tool {tool_name} (ID: {tool_use_id})")
                    
                    # Add tool_use block to assistant content
                    assistant_content_blocks.append({
                        "type": "tool_use",
                        "id": tool_use_id,
                        "name": tool_name,
                        "input": tool_input
                    })
                    
                    # Process the tool
                    try:
                        from utils import tool_processing
                        
                        # Debug logging for tool input type and content
                        logger.info(f"Tool {tool_name} (ID: {tool_use_id}) - input type: {type(tool_input)}")
                        if isinstance(tool_input, str):
                            logger.info(f"Tool {tool_name} (ID: {tool_use_id}) - string input preview: {tool_input[:200]}...")
                        elif isinstance(tool_input, dict):
                            logger.info(f"Tool {tool_name} (ID: {tool_use_id}) - dict input keys: {list(tool_input.keys())}")
                        else:
                            logger.warning(f"Tool {tool_name} (ID: {tool_use_id}) - unexpected input type: {type(tool_input)}")
                        
                        processed_data = tool_processing.process_visualization_input(
                            tool_name, tool_input, tool_use_id
                        )
                        
                        if processed_data:
                            # Collect processed data
                            if tool_name == "generate_graph_data":
                                accumulated_charts.append(processed_data)
                            elif tool_name == "generate_table_data":
                                accumulated_tables.append(processed_data)
                            elif tool_name == "generate_financial_metric":
                                accumulated_metrics.append(processed_data)
                            
                            # Prepare tool result for next turn
                            tool_results_for_next_turn.append({
                                "type": "tool_result",
                                "tool_use_id": tool_use_id,
                                "content": json.dumps(processed_data)
                            })
                            
                            # Emit tool completion event
                            if emit_callback:
                                await emit_callback({
                                    "type": "tool_complete",
                                    "tool_id": tool_use_id,
                                    "tool_name": tool_name,
                                    "tool_input": tool_input,
                                    "result": processed_data,
                                    "message_id": message_id
                                })
                        else:
                            tool_results_for_next_turn.append({
                                "type": "tool_result", 
                                "tool_use_id": tool_use_id,
                                "content": "Tool processed but returned no data.",
                                "is_error": True
                            })
                            
                    except Exception as e:
                        logger.error(f"Error processing streaming tool {tool_name}: {e}")
                        tool_results_for_next_turn.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use_id, 
                            "content": f"Error: {str(e)}",
                            "is_error": True
                        })
                
                # Add assistant response to conversation
                conversation_messages.append({
                    "role": "assistant",
                    "content": assistant_content_blocks
                })
                
                # Add tool results for next turn if any
                if tool_results_for_next_turn:
                    conversation_messages.append({
                        "role": "user",
                        "content": tool_results_for_next_turn
                    })
                
                # Check if we should continue (same logic as non-streaming)
                if not contains_tool_use:
                    logger.info(f"Streaming visualization analysis completed: no more tools")
                    break
                    
                if turn == max_turns - 1:
                    logger.warning(f"Reached maximum turns ({max_turns}) for streaming visualization analysis")
                    break
            
            # CRITICAL: For streaming, we should NOT return accumulated_text
            # The frontend already has the properly formatted text from streaming
            # Returning accumulated_text causes duplication
            current_analysis_text = ""  # Empty for streaming mode
            
            logger.info(f"Streaming mode: NOT returning accumulated_text to prevent duplication")

            # Return structured result with empty analysis_text
            result = {
                "analysis_text": current_analysis_text,  # Empty to prevent duplication
                "visualizations": {
                    "charts": accumulated_charts,
                    "tables": accumulated_tables
                },
                "metrics": accumulated_metrics
            }
            
            logger.info(f"Streaming visualization analysis completed: {len(accumulated_charts)} charts, {len(accumulated_tables)} tables, {len(accumulated_metrics)} metrics. Analysis text length: {len(current_analysis_text)}")
            return result
            
        except Exception as e:
            logger.error(f"Error in streaming analyze_with_visualization_tools: {e}", exc_info=True)
            return {
                "analysis_text": f"Error during streaming analysis: {str(e)}",
                "visualizations": {"charts": [], "tables": []},
                "metrics": []
            }

    async def generate_response_with_langgraph(
        self,
        question: str,
        document_texts: List[Dict[str, Any]],
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Generate a response using LangGraph service for document Q&A with citations.
        This method provides the interface expected by the conversation service.
        
        Args:
            question: User's question
            document_texts: List of document text dictionaries
            conversation_history: Previous conversation messages
            
        Returns:
            Dict with content and citations
        """
        try:
            logger.info(f"Generating LangGraph response for question: '{question[:100]}...'")
            
            # Check if LangGraph service is available
            if not self.langgraph_service:
                logger.warning("LangGraph service not available, falling back to basic response")
                # Fall back to basic Claude response
                system_prompt = """You are a financial document analysis assistant. 
                Analyze the provided financial documents and answer the user's question accurately.
                
                Documents:
                """
                
                for i, doc in enumerate(document_texts):
                    if 'raw_text' in doc:
                        system_prompt += f"\n\nDocument {i+1}: {doc.get('title', 'Untitled')}\n{doc['raw_text'][:2000]}..."
                
                messages = conversation_history or []
                messages.append({"role": "user", "content": question})
                
                response = await self.generate_response(
                    system_prompt=system_prompt,
                    messages=messages
                )
                
                return {
                    "content": response,
                    "citations": []
                }
            
            # Use LangGraph service for document Q&A
            logger.info("Using LangGraph service for document Q&A")
            result = await self.langgraph_service.simple_document_qa(
                question=question,
                documents=document_texts,
                conversation_history=conversation_history
            )
            
            logger.info(f"LangGraph returned result with {len(result.get('citations', []))} citations")
            return result
            
        except Exception as e:
            logger.error(f"Error in generate_response_with_langgraph: {e}", exc_info=True)
            # Fall back to basic response on error
            try:
                basic_response = await self.generate_response(
                    system_prompt="You are a financial document analysis assistant.",
                    messages=[{"role": "user", "content": question}]
                )
                return {
                    "content": basic_response,
                    "citations": []
                }
            except Exception as fallback_error:
                logger.error(f"Fallback response also failed: {fallback_error}")
                return {
                    "content": "I apologize, but I'm unable to process your request at this time. Please try again later.",
                    "citations": []
                }

    async def _validate_file_id(self, file_id: str, filename: str) -> bool:
        """
        Validate that a Claude Files API file_id is still valid.
        
        Args:
            file_id: Claude file ID to validate
            filename: Filename for logging purposes
            
        Returns:
            True if file_id is valid, False if expired or invalid
        """
        try:
            # Make a simple request to check if file exists
            # This is a lightweight way to validate without full document processing
            test_messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {"type": "file", "file_id": file_id}
                        },
                        {
                            "type": "text",
                            "text": "Can you confirm this document is accessible? Just respond with 'Yes' or 'No'."
                        }
                    ]
                }
            ]
            
            response = await self._claude_call(
                model=settings.MODEL_HAIKU,  # Use fast model for validation
                messages=test_messages,
                max_tokens=10,
                temperature=0
            )
            
            # If we get any response, the file_id is valid
            logger.info(f"File ID {file_id} for {filename} is valid")
            return True
            
        except Exception as e:
            # Common error patterns for expired/invalid file IDs
            error_str = str(e).lower()
            if any(keyword in error_str for keyword in ["file not found", "expired", "invalid file", "not accessible"]):
                logger.warning(f"File ID {file_id} for {filename} appears to be expired or invalid: {str(e)}")
                return False
            else:
                # Other errors might be temporary - assume file_id is valid
                logger.warning(f"Could not validate file ID {file_id} for {filename} due to error: {str(e)}")
                return True

    def _sanitize_messages_for_token_count(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prepare messages for the count_tokens endpoint by removing/transforming unsupported
        document references (e.g. {'source': {'type': 'file', ...}}) so the request does not
        fail with a 400 error.

        We replace any such PDF references with a placeholder text block so that the overall
        structure of the conversation is preserved while avoiding validation errors.
        The placeholder contributes a negligible number of tokens, so the count remains an
        approximation, but it lets us successfully call the endpoint instead of skipping
        token counting entirely.
        """
        sanitized: List[Dict[str, Any]] = []
        for msg in messages:
            msg_copy = copy.deepcopy(msg)
            content_block = msg_copy.get("content")
            if isinstance(content_block, list):
                new_content = []
                for item in content_block:
                    if (
                        isinstance(item, dict)
                        and item.get("type") == "document"
                        and isinstance(item.get("source"), dict)
                        and item["source"].get("type") == "file"
                    ):
                        # Replace the unsupported file reference with a minimal text placeholder
                        new_content.append({"type": "text", "text": "[PDF document]"})
                    else:
                        new_content.append(item)
                msg_copy["content"] = new_content
            sanitized.append(msg_copy)
        return sanitized