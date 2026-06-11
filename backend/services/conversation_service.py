"""
Conversation Service Module
==========================

This module provides the service layer for managing conversations and messages in the CFIN financial 
analysis platform. It handles the logic for creating conversations, processing user messages, 
generating AI responses using Claude, and managing document-based Q&A with citations.

Primary responsibilities:
- Create and manage conversations between users and the AI assistant
- Process user messages and generate context-aware responses
- Integrate document content into conversations for document-based Q&A
- Manage citations and document references in AI responses
- Support visualization generation for financial analysis requests
- Decide on the appropriate processing approach for different types of queries

Key Components:
- ConversationService: Main service class for conversation management and message processing
- Methods for building prompts, processing responses, and managing conversation context

Interactions with other files:
-----------------------------
1. cfin/backend/repositories/conversation_repository.py:
   - Uses ConversationRepository for database operations on conversations and messages
   - Methods used: create_conversation, add_message, get_conversation_messages, etc.
   - Handles persistence of conversation data

2. cfin/backend/repositories/document_repository.py:
   - Uses DocumentRepository to access document content for Q&A
   - Methods used: get_document_content, get_document, get_citation
   - Retrieves document text and binary content for analysis

3. cfin/backend/repositories/analysis_repository.py:
   - Uses AnalysisRepository to store and retrieve analysis results
   - Manages persistence of financial analysis visualizations

4. cfin/backend/pdf_processing/api_service.py:
   - Uses ClaudeService for AI response generation and document analysis
   - Methods used: generate_response, process_pdf, extract_structured_financial_data
   - Primary interface for Claude AI capabilities

5. cfin/backend/models/database_models.py:
   - Uses Message, Conversation, Document, Citation, AnalysisBlock, User models
   - These define the database structure for conversation-related entities
   
6. cfin/backend/pdf_processing/langgraph_service.py:
   - Indirectly uses LangGraphService through ClaudeService
   - Used for document-based Q&A with citations in the _process_with_langgraph method

The conversation service orchestrates the user-AI interaction flow, connecting the repository 
layer with the AI processing capabilities. It's responsible for maintaining conversation 
context and ensuring that document references and citations are properly integrated into 
the AI responses.
"""

import os
import uuid
import json
import logging
import asyncio
import re
from threading import Lock
from datetime import datetime
from typing import Awaitable, List, Dict, Any, Optional, Tuple, Union, cast

from repositories.conversation_repository import ConversationRepository
from repositories.document_repository import DocumentRepository
from repositories.analysis_repository import AnalysisRepository
from pdf_processing.api_service import ClaudeService
from models.database_models import Message, Conversation, Citation
import settings

logger = logging.getLogger(__name__)

LLM_RESPONSE_TIMEOUT_SECONDS = float(os.getenv("CFIN_LLM_RESPONSE_TIMEOUT_SECONDS", "70"))
VISUALIZATION_RESPONSE_TIMEOUT_SECONDS = float(os.getenv("CFIN_VISUALIZATION_TIMEOUT_SECONDS", "110"))
LANGGRAPH_RESPONSE_TIMEOUT_SECONDS = float(os.getenv("CFIN_LANGGRAPH_TIMEOUT_SECONDS", "90"))
STREAMING_RESPONSE_TIMEOUT_SECONDS = float(os.getenv("CFIN_STREAMING_TIMEOUT_SECONDS", "180"))


def _assess_content_quality(content: str) -> float:
    """
    Assess the quality of content based on multiple criteria.
    Returns a score from 0.0 to 1.0 where 1.0 is highest quality.
    """
    if not content or not content.strip():
        return 0.0
    
    content = content.strip()
    score = 0.0
    
    # Length factor (substantial content gets higher score)
    if len(content) > 500:
        score += 0.3
    elif len(content) > 200:
        score += 0.2
    elif len(content) > 50:
        score += 0.1
    
    # Sentence completeness (complete sentences get higher score)
    sentences = content.split('.')
    complete_sentences = sum(1 for s in sentences if len(s.strip()) > 10)
    if complete_sentences > 3:
        score += 0.3
    elif complete_sentences > 1:
        score += 0.2
    elif complete_sentences > 0:
        score += 0.1
    
    # Content richness (varied vocabulary and structure)
    words = content.split()
    unique_words = set(word.lower() for word in words if len(word) > 3)
    if len(unique_words) > 50:
        score += 0.2
    elif len(unique_words) > 20:
        score += 0.1
    
    # Financial analysis indicators (specific to our use case)
    financial_keywords = ['analysis', 'trend', 'ratio', 'performance', 'financial', 'revenue', 'profit', 'growth', 'quarter']
    keyword_count = sum(1 for keyword in financial_keywords if keyword.lower() in content.lower())
    if keyword_count > 3:
        score += 0.2
    elif keyword_count > 1:
        score += 0.1
    
    return min(score, 1.0)


def _is_content_truncated(content: str) -> bool:
    """
    Detect if content appears to be truncated or incomplete.
    Returns True if content shows signs of truncation.
    """
    if not content or not content.strip():
        return True
    
    content = content.strip()
    
    # Check for common truncation patterns
    truncation_indicators = [
        # Mid-sentence cuts
        content.endswith(' The'),
        content.endswith(' Let me'),
        content.endswith(' Based on'),
        content.endswith(' Looking at'),
        content.endswith(' The analysis'),
        content.endswith(' This shows'),
        # Incomplete phrases
        content.endswith(' Quarter-over-Quarter'),
        content.endswith(' The line chart above'),
        content.endswith(' provide'),
        content.endswith(' shows'),
        content.endswith(' indicates'),
        # Very short content
        len(content) < 50,
        # Ends with incomplete conjunction
        content.endswith(' and'),
        content.endswith(' but'),
        content.endswith(' or'),
        content.endswith(' with'),
        content.endswith(' from'),
        content.endswith(' to'),
        # Mid-word cuts (very basic check)
        content.endswith(' ') and not content.endswith(('.', '!', '?', ':', ';'))
    ]
    
    # Also check if it ends abruptly without proper punctuation
    has_proper_ending = content.endswith(('.', '!', '?')) or content.endswith('.')
    
    # Check for minimum viable content length for financial analysis
    # But allow single complete sentences if they're substantial
    is_too_short = len(content) < 50 if has_proper_ending and '.' in content else len(content) < 100
    
    return any(truncation_indicators) or not has_proper_ending or is_too_short

def _to_str(value: Any) -> str:
    """Safely convert any value to a string for DB storage."""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, default=str)
    except Exception:
        return str(value)

class ConversationService:
    """Service for managing conversations and messages."""
    _shared_claude_service: Optional[ClaudeService] = None
    _shared_claude_lock: Lock = Lock()
    
    def __init__(
        self, 
        conversation_repository: ConversationRepository,
        document_repository: DocumentRepository,
        analysis_repository: Optional[AnalysisRepository] = None
    ):
        """
        Initialize the conversation service.
        
        Args:
            conversation_repository: Repository for conversation operations
            document_repository: Repository for document operations
            analysis_repository: Optional repository for analysis operations
        """
        self.conversation_repository = conversation_repository
        self.document_repository = document_repository
        self.analysis_repository = analysis_repository
        
        # Initialize Claude service with API key from environment variable
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not found in environment variables. Claude integration will not work.")
            logger.warning("Please ensure ANTHROPIC_API_KEY is set in your .env file or environment variables.")
        else:
            # Mask API key for logging (first 8 chars and last 4)
            if len(api_key) > 12:
                masked_key = f"{api_key[:8]}...{api_key[-4:]}"
            else:
                masked_key = "***masked***"
            logger.info(f"Found ANTHROPIC_API_KEY in environment variables: {masked_key}")
        
        if self.__class__._shared_claude_service is None:
            with self._shared_claude_lock:
                if self.__class__._shared_claude_service is None:
                    logger.info("Initializing shared ClaudeService instance for ConversationService")
                    self.__class__._shared_claude_service = ClaudeService(api_key=api_key)
        self.claude_service = self.__class__._shared_claude_service
        self.citation_repository: Optional[Any] = None  # may be injected later
    
    async def create_conversation(
        self,
        title: str,
        user_id: str,
        document_ids: Optional[List[str]] = None
    ) -> Conversation:
        """
        Create a new conversation.
        
        Args:
            title: Title of the conversation
            user_id: ID of the user creating the conversation
            document_ids: Optional list of document IDs to associate with the conversation
            
        Returns:
            Created conversation
        """
        # Verify that all documents exist and belong to the user
        if document_ids:
            for doc_id in document_ids:
                document = await self.document_repository.get_document(doc_id)
                if not document:
                    raise ValueError(f"Document {doc_id} not found")
                if document.user_id != user_id:
                    raise ValueError(f"User {user_id} does not have access to document {doc_id}")
        
        # Create the conversation
        conversation = await self.conversation_repository.create_conversation(
            title=title,
            user_id=user_id,
            document_ids=document_ids
        )
        
        # Create a welcome message
        welcome_message = f"Welcome to your conversation about "
        if document_ids and len(document_ids) > 0:
            doc_count = len(document_ids)
            welcome_message += f"the {doc_count} document{'s' if doc_count > 1 else ''} you've uploaded. "
        else:
            welcome_message += "financial documents. Please upload a document to begin analysis. "
        
        welcome_message += "You can ask me questions about the financial information in these documents, " \
                         "and I'll provide insights and analysis."
        
        # Add the welcome message
        await self.conversation_repository.add_message(
            conversation_id=conversation.id,
            content=welcome_message,
            role="assistant"
        )
        
        return conversation
    
    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """
        Get a conversation by ID.
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            Conversation if found, None otherwise
        """
        return await self.conversation_repository.get_conversation(conversation_id)
    
    async def list_conversations(
        self,
        user_id: str,
        limit: int = 10,
        offset: int = 0
    ) -> List[Conversation]:
        """
        List conversations for a user.
        
        Args:
            user_id: ID of the user
            limit: Maximum number of conversations to return
            offset: Starting index
            
        Returns:
            List of conversations
        """
        return await self.conversation_repository.list_conversations(user_id, limit, offset)
    
    async def get_message(self, message_id: str) -> Optional[Message]:
        """
        Get a message by ID.
        
        Args:
            message_id: ID of the message
            
        Returns:
            Message if found, None otherwise
        """
        return await self.conversation_repository.get_message(message_id)
    
    async def add_message(
        self,
        conversation_id: str,
        content: str,
        role: str,
        citation_ids: Optional[List[str]] = None,
        referenced_documents: Optional[List[str]] = None,
        referenced_analyses: Optional[List[str]] = None,
        message_id: Optional[str] = None
    ) -> Optional[Message]:
        """
        Add a message to a conversation.
        
        Args:
            conversation_id: ID of the conversation
            content: Message content
            role: Message role (user, assistant, system)
            citation_ids: Optional list of citation IDs to associate with the message
            
        Returns:
            Created message if conversation found, None otherwise
        """
        # Verify that the conversation exists
        conversation = await self.conversation_repository.get_conversation(conversation_id)
        if not conversation:
            logger.error(f"Conversation {conversation_id} not found when adding message")
            return None
        
        # Verify that the citation IDs are valid if provided
        if citation_ids:
            for citation_id in citation_ids:
                citation = await self.document_repository.get_citation(citation_id)
                if not citation:
                    logger.warning(f"Citation {citation_id} not found when adding message")

        # Auto-title: name the conversation after the first user question so the
        # session history sidebar shows meaningful titles instead of "New Conversation".
        try:
            default_titles = {"", "new conversation", "untitled", "untitled conversation"}
            if (
                role == "user"
                and content
                and (conversation.title or "").strip().lower() in default_titles
            ):
                auto_title = " ".join(content.split())
                if len(auto_title) > 60:
                    auto_title = auto_title[:57].rstrip() + "…"
                if auto_title:
                    await self.conversation_repository.update_conversation(
                        conversation_id, {"title": auto_title}
                    )
                    logger.info(f"Auto-titled conversation {conversation_id}: {auto_title!r}")
        except Exception as title_err:  # Never block message writes on titling
            logger.warning(f"Conversation auto-title failed for {conversation_id}: {title_err}")

        return await self.conversation_repository.add_message(
            conversation_id=conversation_id,
            content=content,
            role=role,
            citation_ids=citation_ids,
            referenced_documents=referenced_documents or [],
            referenced_analyses=referenced_analyses or [],
            message_id=message_id
        )
    
    async def get_conversation_messages(
        self,
        conversation_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Message]:
        """
        Get messages for a conversation.
        
        Args:
            conversation_id: ID of the conversation
            limit: Maximum number of messages to return
            offset: Starting index
            
        Returns:
            List of messages
        """
        return await self.conversation_repository.get_conversation_messages(
            conversation_id=conversation_id,
            limit=limit,
            offset=offset
        )
    
    async def get_conversation_context(
        self,
        conversation_id: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Get context information for a conversation, including documents and recent messages.
        
        Args:
            conversation_id: ID of the conversation
            limit: Maximum number of messages to include in context
            
        Returns:
            Dictionary containing conversation context
        """
        # Get the conversation
        conversation = await self.conversation_repository.get_conversation(conversation_id)
        if not conversation:
            return {}
        
        # Get recent messages
        messages = await self.conversation_repository.get_conversation_messages(
            conversation_id=conversation_id,
            limit=limit
        )
        
        # Format messages for context
        formatted_messages = []
        for msg in messages:
            # Get citations for this message
            citations = await self.conversation_repository.get_message_citations(msg.id)
            
            formatted_messages.append({
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat(),
                "citation_ids": [citation.id for citation in citations]
            })
        
        # Get associated documents
        documents = await self.conversation_repository.get_conversation_documents(conversation_id)
        
        # Format documents for context
        formatted_documents = []
        for doc in documents:
            try:
                # Check if doc is a dictionary or an ORM object
                doc_id = doc["id"] if isinstance(doc, dict) else doc.id
                
                # Get document content for citation processing
                content_obj = await self.document_repository.get_document_content(doc_id)
                content_data = None
                raw_text = None
                extracted_data = None
                
                # Extract content and raw text from the dictionary returned by repository
                if content_obj and isinstance(content_obj, dict):
                    content_data = content_obj.get("content")
                    raw_text = content_obj.get("raw_text")
                    extracted_data = content_obj.get("extracted_data")
                    
                    content_size = len(content_data) if content_data and isinstance(content_data, (str, bytes)) else 0
                    raw_text_size = len(raw_text) if raw_text else 0
                    
                    logger.info(f"Retrieved content for document {doc_id}: content size={content_size}, raw_text size={raw_text_size}")
                    
                    # If we have raw_text but it's empty, log a warning
                    if raw_text is not None and not raw_text:
                        logger.warning(f"Empty raw_text for document {doc_id}")
                    
                    # No fallback text extraction - use Files API claude_file_id instead
                else:
                    logger.warning(f"Document content not found for {doc_id}")
                
                # Log available content types
                available_content = []
                if content_data: available_content.append("content")
                if raw_text: available_content.append("raw_text")
                if extracted_data: available_content.append("extracted_data")
                logger.info(f"Document {doc_id} available content types: {', '.join(available_content)}")
                
                # Add document to the list with its content - both raw text and PDF bytes
                doc_title = doc["filename"] if isinstance(doc, dict) else doc.filename
                doc_type = doc.get("document_type", "unknown") if isinstance(doc, dict) else getattr(doc, "document_type", "unknown")
                
                formatted_doc = {
                    "id": doc_id,
                    "title": doc_title,
                    "filename": doc_title,
                    "document_type": doc_type,
                    "mime_type": doc.get("mime_type", "application/pdf") if isinstance(doc, dict) else getattr(doc, "mime_type", "application/pdf"),
                    "upload_timestamp": doc.get("upload_timestamp", "") if isinstance(doc, dict) else getattr(doc, "upload_timestamp", ""),
                    "claude_file_id": doc.get("claude_file_id") if isinstance(doc, dict) else getattr(doc, "claude_file_id", None),
                }
                if not formatted_doc["claude_file_id"]:
                    formatted_doc.pop("claude_file_id")
                
                # Add content data if available
                if content_data is not None:
                    formatted_doc["content"] = content_data
                
                # Add raw text if available
                if raw_text:
                    formatted_doc["raw_text"] = raw_text
                    
                # Add extracted data if available
                if extracted_data:
                    formatted_doc["extracted_data"] = extracted_data
                
                formatted_documents.append(formatted_doc)
                logger.info(f"Added document {doc_id} to context for conversation {conversation_id}")
            except Exception as e:
                logger.error(f"Error processing document: {str(e)}")
                logger.exception(e)
                continue
        
        # Build the context
        context = {
            "conversation_id": conversation.id,
            "title": conversation.title,
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat(),
            "messages": formatted_messages,
            "documents": formatted_documents
        }
        
        return context

    async def _await_with_timeout(
        self,
        operation_name: str,
        operation: Awaitable[Any],
        timeout_seconds: float,
    ) -> Any:
        """Await an operation with a strict timeout and consistent logging."""
        try:
            return await asyncio.wait_for(operation, timeout=timeout_seconds)
        except asyncio.TimeoutError:
            logger.warning("%s timed out after %.1fs", operation_name, timeout_seconds)
            raise

    def _build_document_texts_from_context_documents(
        self,
        context_documents: List[Dict[str, Any]],
        conversation_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Build document payloads for Claude using pre-fetched conversation context docs.

        This avoids repeated repository reads in both non-streaming and streaming paths.
        """
        document_texts: List[Dict[str, Any]] = []
        for doc_info in context_documents:
            try:
                doc_id = doc_info.get("id")
                doc_title = doc_info.get("filename") or doc_info.get("title") or "Document"
                mime_type = str(doc_info.get("mime_type") or "").lower()
                extracted_data = doc_info.get("extracted_data")

                doc_payload: Dict[str, Any] = {
                    "id": doc_id,
                    "title": doc_title,
                    "type": "document",
                }

                claude_file_id = doc_info.get("claude_file_id")
                if not claude_file_id and isinstance(extracted_data, dict):
                    claude_file_id = extracted_data.get("claude_file_id") or extracted_data.get("file_id")

                if claude_file_id:
                    doc_payload["claude_file_id"] = claude_file_id
                    doc_payload["filename"] = doc_title
                    document_texts.append(doc_payload)
                    logger.info(
                        "Added document %s with Files API file_id for conversation %s",
                        doc_id,
                        conversation_id,
                    )
                    continue

                raw_text = doc_info.get("raw_text")
                if raw_text and "pdf" not in mime_type:
                    doc_payload["raw_text"] = raw_text
                    document_texts.append(doc_payload)
                    logger.info(
                        "Added non-PDF document %s with raw_text (%d chars)",
                        doc_id,
                        len(raw_text),
                    )
                    continue

                content_data = doc_info.get("content")
                if isinstance(content_data, bytes) and "pdf" not in mime_type:
                    doc_payload["content"] = content_data
                    document_texts.append(doc_payload)
                    logger.info("Added non-PDF document %s with binary content", doc_id)
                    continue

                if "pdf" in mime_type:
                    logger.warning(
                        "PDF document %s missing claude_file_id - cannot use native PDF support",
                        doc_id,
                    )
                else:
                    logger.warning("No usable content available for document %s", doc_id)
            except Exception as exc:
                logger.error("Error preparing context document for Claude: %s", exc)
                logger.exception(exc)
                continue

        return document_texts
    
    async def process_user_message(
        self,
        conversation_id: str,
        content: str,
        citation_ids: Optional[List[str]] = None,
        referenced_documents: Optional[List[str]] = None,
        referenced_analyses: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Process a user message and generate an AI response.
        
        Args:
            conversation_id: ID of the conversation
            content: Message content
            citation_ids: Optional list of citation IDs to include as context
            
        Returns:
            Dict containing success status and the assistant message
        """
        # Get conversation and validate it exists
        conversation = await self.conversation_repository.get_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation with ID {conversation_id} not found")
        
        # Add user message to conversation
        user_message = await self.add_message(
            conversation_id=conversation_id,
            content=content,
            role="user",
            citation_ids=citation_ids,
            referenced_documents=referenced_documents,
            referenced_analyses=referenced_analyses
        )
        
        if not user_message:
            raise ValueError("Failed to add user message to conversation")
        
        # Get conversation context
        context = await self.get_conversation_context(conversation_id)
        
        # Reuse pre-fetched context docs to avoid duplicate repository lookups.
        document_texts = self._build_document_texts_from_context_documents(
            context_documents=context.get("documents", []),
            conversation_id=conversation_id,
        )
        
        # Get conversation messages
        messages = await self.conversation_repository.get_conversation_messages(
            conversation_id=conversation_id,
            limit=10  # Get last 10 messages for context
        )
        
        # Convert messages to the format expected by Claude API
        message_history = []
        for msg in messages:
            if msg.id != user_message.id:  # Skip the message we just added
                
                message_history.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        # Decide which processing approach to use
        approach = await self._decide_processing_approach(
            conversation_id=conversation_id,
            message_content=content,
            document_texts=document_texts,
            conversation_history=message_history
        )
        
        # Process using the selected approach
        if approach == "simple_qa":
            # Use LangGraph for simple document QA
            if hasattr(self.claude_service, "langgraph_service") and self.claude_service.langgraph_service:
                try:
                    logger.info(f"Using LangGraph for simple QA in conversation {conversation_id}")
                    response = await self._await_with_timeout(
                        "langgraph simple QA",
                        self._process_with_langgraph(
                            conversation_id=conversation_id,
                            content=content,
                            document_texts=document_texts,
                            messages=message_history,
                        ),
                        timeout_seconds=LANGGRAPH_RESPONSE_TIMEOUT_SECONDS,
                    )
                    return response
                except Exception as e:
                    logger.error(f"Error using LangGraph for simple QA: {str(e)}")
                    logger.info("Falling back to direct Claude API")
                    # Fall through to direct API approach
            
            # Use direct Claude API if LangGraph is not available or failed
            system_prompt = self._build_system_prompt(document_texts, [])
            
            # Generate response
            response_content = await self._await_with_timeout(
                "claude simple response",
                self.claude_service.generate_response(
                    system_prompt=system_prompt,
                    messages=message_history + [{"role": "user", "content": content}],
                ),
                timeout_seconds=LLM_RESPONSE_TIMEOUT_SECONDS,
            )
            
            # Add assistant message to conversation
            assistant_message = await self.add_message(
                conversation_id=conversation_id,
                content=_to_str(response_content),
                role="assistant"
            )
            
            if not assistant_message:
                raise ValueError("Failed to add assistant message to conversation")
            
            return {
                "success": True,
                "message": assistant_message
            }
            
        elif approach == "visualization_analysis":
            # Use specialized visualization tools flow
            logger.info(f"Using visualization tools approach for conversation {conversation_id}")
            
            # Extract file_id from first document if available (for Claude Files API optimization)
            file_id = None
            combined_doc_text = ""
            
            for doc in document_texts:
                # Priority 1: Use claude_file_id for Files API integration
                if "claude_file_id" in doc and doc["claude_file_id"]:
                    file_id = doc["claude_file_id"]
                    logger.info(f"Using Files API claude_file_id {file_id} for visualization analysis")
                    break  # Use first available file_id
                
                # Priority 2: Try to get file_id from extracted_data (legacy)
                elif "extracted_data" in doc and isinstance(doc["extracted_data"], dict):
                    if "claude_file_id" in doc["extracted_data"] and doc["extracted_data"]["claude_file_id"]:
                        file_id = doc["extracted_data"]["claude_file_id"]
                        logger.info(f"Using cached claude_file_id {file_id} from extracted_data for visualization analysis")
                        break  # Use first available file_id
                    elif "file_id" in doc["extracted_data"] and doc["extracted_data"]["file_id"]:
                        file_id = doc["extracted_data"]["file_id"]
                        logger.info(f"Using legacy file_id {file_id} from extracted_data for visualization analysis")
                        break  # Use first available file_id
                
                # Combine text as fallback
                if "raw_text" in doc:
                    combined_doc_text += f"\n\n{doc['raw_text']}"
            
            logger.info(f"Calling Claude with visualization tools for query: '{content[:50]}...', file_id={file_id}")
            
            # Call Claude with visualization tools (preferring file_id if available)
            result = await self._await_with_timeout(
                "claude visualization analysis",
                self.claude_service.analyze_with_visualization_tools(
                    document_text=combined_doc_text,
                    user_query=content,
                    file_id=file_id,
                ),
                timeout_seconds=VISUALIZATION_RESPONSE_TIMEOUT_SECONDS,
            )
            
            # Extract analysis text and visualization data
            analysis_text = result.get("analysis_text", "")
            # Ensure visualizations is a dict and provide defaults for charts, tables, and metrics
            visualizations = result.get("visualizations", {})
            if not isinstance(visualizations, dict): # Handle cases where visualizations might not be a dict
                visualizations = {}
            
            charts_data = visualizations.get("charts", [])
            tables_data = visualizations.get("tables", [])
            metrics_data = result.get("metrics", []) # Extract metrics from top level, not visualizations

            logger.info(f"Received visualization data: {len(charts_data)} charts, {len(tables_data)} tables, {len(metrics_data)} metrics")
            
            # Add assistant message to conversation
            assistant_message = await self.add_message(
                conversation_id=conversation_id,
                content=_to_str(analysis_text),
                role="assistant"
            )
            
            if not assistant_message:
                raise ValueError("Failed to add assistant message to conversation")
            
            # Process visualizations and store as analysis blocks
            items_for_analysis_blocks = []
            
            # Process charts
            for chart_item in charts_data:
                processed_chart_item = {
                    "title": chart_item.get("config", {}).get("title", "Chart"),
                    "visualization_type": "chart", # Frontend expects 'chart' as the block_type for all chart types
                    "data": chart_item or {}  # Store the entire chart item as data (includes chartType)
                }
                items_for_analysis_blocks.append(processed_chart_item)
            
            # Process tables
            for table_item in tables_data:
                processed_table_item = {
                    "title": table_item.get("config", {}).get("title", "Table"),
                    "visualization_type": "table", # Matches frontend expectations
                    "data": table_item or {}  # Store the entire table item as data
                }
                items_for_analysis_blocks.append(processed_table_item)

            # New: Process metrics
            for metric_item in metrics_data:
                processed_metric_item = {
                    "title": metric_item.get("name", metric_item.get("title", "Metric")), # Use 'name' or 'title'
                    "visualization_type": "metric", # Or "key_figure" - using "metric"
                    "data": metric_item or {}  # Store the entire metric item as data
                }
                items_for_analysis_blocks.append(processed_metric_item)
            
            # Store all items (charts, tables, metrics) as analysis blocks
            if items_for_analysis_blocks:
                logger.info(f"Storing {len(items_for_analysis_blocks)} analysis blocks for message {assistant_message.id}")
                await self._process_visualizations(
                    message_id=assistant_message.id,
                    visualizations=items_for_analysis_blocks # Pass the combined list
                )

                # New: Refresh assistant_message to load the analysis_blocks relationship
                try:
                    await self.conversation_repository.db.refresh(assistant_message, attribute_names=['analysis_blocks'])
                    logger.info(f"Refreshed assistant_message {assistant_message.id} to load analysis_blocks")
                except Exception as e:
                    logger.error(f"Failed to refresh assistant_message {assistant_message.id}: {str(e)}")
                    # Continue without refresh if it fails, though the response might be incomplete
            else:
                logger.warning(f"No visualization data (charts, tables, metrics) to store for message {assistant_message.id}")
            
            return {
                "success": True,
                "message": assistant_message
            }
        
        elif approach == "citations":
            # Use citation-aware processing with LangGraph
            logger.info(f"Using citation-based approach for conversation {conversation_id}")
            return await self._await_with_timeout(
                "langgraph citation response",
                self._process_with_langgraph(
                    conversation_id=conversation_id,
                    content=content,
                    document_texts=document_texts,
                    messages=message_history,
                ),
                timeout_seconds=LANGGRAPH_RESPONSE_TIMEOUT_SECONDS,
            )
        
        elif approach == "full_graph":
            # Implement full conversation graph approach here (future)
            logger.info(f"Full graph approach not yet implemented, falling back to citation approach for conversation {conversation_id}")
            return await self._await_with_timeout(
                "langgraph full-graph fallback",
                self._process_with_langgraph(
                    conversation_id=conversation_id,
                    content=content,
                    document_texts=document_texts,
                    messages=message_history,
                ),
                timeout_seconds=LANGGRAPH_RESPONSE_TIMEOUT_SECONDS,
            )
        
        else:
            # Unknown approach, fall back to simple QA
            logger.warning(f"Unknown processing approach '{approach}', falling back to simple QA for conversation {conversation_id}")
            system_prompt = self._build_system_prompt(document_texts, [])
            
            # Generate response
            response_content = await self._await_with_timeout(
                "claude fallback response",
                self.claude_service.generate_response(
                    system_prompt=system_prompt,
                    messages=message_history + [{"role": "user", "content": content}],
                ),
                timeout_seconds=LLM_RESPONSE_TIMEOUT_SECONDS,
            )
            
            # Add assistant message to conversation
            assistant_message = await self.add_message(
                conversation_id=conversation_id,
                content=_to_str(response_content),
                role="assistant"
            )
            
            if not assistant_message:
                raise ValueError("Failed to add assistant message to conversation")
            
            return {
                "success": True,
                "message": assistant_message
            }

    async def process_user_message_streaming(
        self,
        conversation_id: str,
        content: str,
        citation_ids: Optional[List[str]] = None,
        referenced_documents: Optional[List[str]] = None,
        referenced_analyses: Optional[List[str]] = None,
        emit_callback=None,
        message_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a user message with streaming support and real-time updates.
        
        Args:
            conversation_id: ID of the conversation
            content: Message content
            citation_ids: Optional list of citation IDs to include as context
            referenced_documents: Optional list of document IDs
            referenced_analyses: Optional list of analysis IDs
            emit_callback: Callback function for streaming events
            
        Returns:
            Dict containing success status and the assistant message
        """
        # Get conversation and validate it exists
        conversation = await self.conversation_repository.get_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation with ID {conversation_id} not found")
        
        # Add user message to conversation
        user_message = await self.add_message(
            conversation_id=conversation_id,
            content=content,
            role="user",
            citation_ids=citation_ids,
            referenced_documents=referenced_documents,
            referenced_analyses=referenced_analyses
        )
        
        if not user_message:
            raise ValueError("Failed to add user message to conversation")
        
        # Create assistant message immediately to establish correct chronological order
        # This ensures the assistant response timestamp is close to the user message timestamp
        assistant_message_placeholder = await self.add_message(
            conversation_id=conversation_id,
            content="Processing your request...",  # Placeholder content
            role="assistant",
            message_id=message_id
        )
        
        if not assistant_message_placeholder:
            raise ValueError("Failed to create assistant message placeholder")
        
        # Track content state to prevent overwrites
        has_good_content = False
        last_good_content = ""
        # A new flag to indicate tool_start has been processed by this callback
        # This is specific to the current streaming interaction via this callback instance.
        tool_start_processed_in_current_stream = False
        # Track whether we've already sent a message_complete for the initial streamed answer.
        initial_message_completed = False
        # Track the tools/visualization message if created
        tools_message = None
        # Track if we're waiting for citations to complete
        waiting_for_citations = False
        # Track pending citation markers
        pending_citation_markers = []
        # Track expected citation count based on highest marker seen
        highest_citation_marker = 0
        # Track received citation markers
        received_citation_markers = set()
        # Debounced citation completion task — allows multiple citation markers
        # to arrive before emitting message_complete
        citation_completion_task = None

        async def enhanced_emit_callback(event: Dict[str, Any]):
            nonlocal has_good_content, last_good_content, tool_start_processed_in_current_stream, initial_message_completed, waiting_for_citations, pending_citation_markers, highest_citation_marker, received_citation_markers, citation_completion_task
            
            event_type = event.get("type")
            app_message_id = message_id if message_id else (
                str(assistant_message_placeholder.id) if assistant_message_placeholder else "unknown"
            )

            # The transport layer already emits the app/database message_start.
            # Passing through Anthropic's raw msg_* start event causes the client to
            # split one assistant response across two IDs.
            if event_type == "message_start" and not event.get("is_post_visualization"):
                logger.info("Blocking nested Claude message_start; app message_start already emitted")
                return

            # Normalize initial-answer stream events to the database/app message id.
            # Post-visualization and synthetic tool messages keep their own IDs.
            if (
                app_message_id
                and event_type != "new_message_start"
                and not event.get("is_post_visualization")
                and not event.get("is_tools_message")
            ):
                event = {**event, "message_id": app_message_id}

            # Block early message_stop/message_complete events - we'll send our own when ready
            if (event_type in ["message_stop", "message_complete"]) and not event.get("is_post_tools") and not tool_start_processed_in_current_stream:
                logger.info(f"🚫 Blocking early {event_type} event - will send message_complete when appropriate")
                # We do *not* forward the original message_stop to frontend (to avoid confusion).
                return

            if event_type == "tool_start":
                tool_start_processed_in_current_stream = True  # Mark that tool_start was seen
                if assistant_message_placeholder.content and len(assistant_message_placeholder.content) > 100:
                    has_good_content = True
                    db_content = assistant_message_placeholder.content
                    # Don't overwrite last_good_content if it's already richer (has citation markers)
                    if last_good_content and len(last_good_content) > len(db_content):
                        logger.info(f"🔒 Keeping enriched last_good_content ({len(last_good_content)} chars) over DB version ({len(db_content)} chars)")
                    else:
                        last_good_content = db_content
                        logger.info(f"🔒 Freezing content at tool_start: {len(last_good_content)} chars")
                
                # Check if we have pending citations before completing the initial message
                import re
                current_content = assistant_message_placeholder.content or ""
                has_citation_markers = bool(re.search(r'\[\d+\]', current_content))
                
                # Extract all citation numbers to check if we have them all
                citation_numbers = re.findall(r'\[(\d+)\]', current_content)
                for num_str in citation_numbers:
                    citation_num = int(num_str)
                    received_citation_markers.add(citation_num)
                    highest_citation_marker = max(highest_citation_marker, citation_num)
                
                # Check if we have all expected citations
                expected_citations = set(range(1, highest_citation_marker + 1)) if highest_citation_marker > 0 else set()
                all_citations_received = expected_citations == received_citation_markers if expected_citations else False
                
                # Always defer completion when tool_start arrives to ensure we have all citations
                if not initial_message_completed:
                    logger.warning(f"⚠️ tool_start arrived. Have citations {sorted(received_citation_markers)}. Deferring message_complete to ensure all citations are received.")
                    waiting_for_citations = True
                    
                    # Update content with what we have so far including any citations
                    if has_good_content and last_good_content:
                        assistant_message_placeholder.content = last_good_content
                        await self.conversation_repository.update_message(assistant_message_placeholder)
            
            # Track citation markers as they arrive
            if event_type == "citation_marker" or event_type == "citations_delta":
                # Extract the citation index to track which citations we've received
                citation_index = event.get("citation_index") or event.get("citation", {}).get("citation_index")
                if citation_index:
                    received_citation_markers.add(citation_index)
                    highest_citation_marker = max(highest_citation_marker, citation_index)
                    logger.info(f"📍 Received citation marker {citation_index}. Total received: {len(received_citation_markers)}/{highest_citation_marker}")
            
            # DISABLED: Post-tool content_update events are now blocked by filtered_emit_callback
            # in api_service.py. If one somehow leaks through, just log and return — do NOT
            # create a database message. Claude's post-tool text is often confused ("I cannot
            # see any visualizations...") and the auto-generated summary in api_service.py
            # provides a proper post-tool narrative when needed.
            if event_type == "content_update" and event.get("is_post_tools") and event.get("post_tool_text", "").strip():
                post_tool_text = event.get("post_tool_text", "")
                logger.warning(
                    f"⚠️ Post-tool content_update leaked through filtered_emit_callback "
                    f"({len(post_tool_text)} chars) — blocking database creation to prevent "
                    f"duplicate message. Preview: '{post_tool_text[:120]}...'"
                )
                return
            
            # Block regular text_delta after tool_start, but not post-tool content or citations
            if tool_start_processed_in_current_stream and event_type == "text_delta" and not event.get("is_post_visualization"):
                text_content = event.get('text', '')
                # Check if this is a citation marker text_delta (format: " [1] [2] [3]")
                import re
                if re.search(r'\[\d+\]', text_content):
                    logger.info(f"✅ Allowing citation marker text_delta after tool_start: '{text_content}'")
                    # Don't block citation markers - let them pass through
                    # Also update our frozen content to include the citation markers
                    if has_good_content and last_good_content:
                        last_good_content += text_content
                        logger.info(f"📝 Updated frozen content with citation markers. New length: {len(last_good_content)}")
                    
                    # Store citation markers that arrive after tool_start
                    pending_citation_markers.append(text_content)
                    
                    # Extract citation numbers from the text to track progress
                    import re
                    citation_numbers = re.findall(r'\[(\d+)\]', text_content)
                    for num_str in citation_numbers:
                        citation_num = int(num_str)
                        received_citation_markers.add(citation_num)
                        highest_citation_marker = max(highest_citation_marker, citation_num)
                    
                    # If we were waiting for citations and haven't completed the initial message yet
                    if waiting_for_citations and not initial_message_completed:
                        # Check if we have all expected citations (1 through highest_citation_marker)
                        expected_citations = set(range(1, highest_citation_marker + 1))
                        all_citations_received = expected_citations == received_citation_markers
                        
                        logger.info(f"📊 Citation progress: received {sorted(received_citation_markers)}, expecting {sorted(expected_citations)}, complete: {all_citations_received}")
                        
                        # Use a heuristic: if we receive multiple citations at once or see a gap in the sequence being filled,
                        # assume we have all citations
                        citations_in_current_batch = len(citation_numbers)
                        
                        # Debounce citation completion — don't fire message_complete
                        # immediately because more citation markers may still arrive.
                        # Each new citation marker resets the 500ms timer.
                        async def _deferred_citation_complete():
                            """Wait 500ms then emit message_complete with all accumulated citations."""
                            nonlocal initial_message_completed, waiting_for_citations
                            await asyncio.sleep(0.5)
                            if initial_message_completed:
                                return  # Already completed via another path

                            # Update DB with full content including all citation markers
                            assistant_message_placeholder.content = last_good_content
                            await self.conversation_repository.update_message(assistant_message_placeholder)
                            logger.info(f"✅ Debounced DB update with {len(last_good_content)} chars (citations: {sorted(received_citation_markers)})")

                            initial_message_completed = True
                            waiting_for_citations = False
                            completion_msg_id = message_id if message_id else (
                                str(assistant_message_placeholder.id) if assistant_message_placeholder else "unknown"
                            )
                            if emit_callback:
                                await emit_callback({
                                    "type": "message_complete",
                                    "message_id": completion_msg_id,
                                    "timestamp": datetime.utcnow().isoformat() + 'Z',
                                    "is_post_tools": False,
                                    "is_post_visualization": False
                                })
                                logger.info(
                                    f"✅ Debounced message_complete emitted with {highest_citation_marker} citation markers (message_id={completion_msg_id})"
                                )

                        # Cancel any pending debounce task and start a new one
                        if citation_completion_task and not citation_completion_task.done():
                            citation_completion_task.cancel()
                            logger.info(f"🔄 Reset citation debounce timer — now have {len(received_citation_markers)} markers: {sorted(received_citation_markers)}")
                        else:
                            logger.info(f"⏱️ Starting citation debounce timer — have {len(received_citation_markers)} markers: {sorted(received_citation_markers)}")
                        citation_completion_task = asyncio.create_task(_deferred_citation_complete())

                    # Forward citation text_delta to the frontend so it can track
                    # expected citation count (the [1], [2], etc. markers must appear
                    # in streamingTextRef for expectedCitationCount > 0).
                    if emit_callback:
                        fwd_event = {
                            **event,
                            "message_id": message_id if message_id else (
                                str(assistant_message_placeholder.id) if assistant_message_placeholder else "unknown"
                            ),
                        }
                        await emit_callback(fwd_event)
                    return  # Handled — don't fall through to the text_delta blocker

                else:
                    logger.info(f"🚫 Blocking regular text_delta after tool_start. Text: '{text_content[:50]}...'")
                    return

            # Original logic for content_update (now primarily for pre-tool_start content)
            if event_type == "content_update" and "accumulated_text" in event:
                if tool_start_processed_in_current_stream: 
                     logger.warning("Content_update reached main processing block despite tool_start_processed_in_current_stream being true. This is unexpected.")
                     return

                # REMOVED: The has_good_content check that was blocking legitimate updates
                # We now handle content updates more intelligently
                
                if event.get("is_post_tools", False):
                    logger.info(f"📝 Ignoring post-tool content update as it should be handled by api_service. Content: '{event['accumulated_text'][:50]}...'")
                    return
                
                new_content = event["accumulated_text"]
                
                current_db_content = assistant_message_placeholder.content
                # Normalize whitespace for more robust comparison
                current_normalized = current_db_content.strip() if current_db_content else ""
                new_normalized = new_content.strip()
                
                if current_normalized and len(current_normalized) > 1000 and len(new_normalized) <= len(current_normalized) + 50:
                    logger.info(f"📝 Blocking content update to DB - already have {len(current_normalized)} chars, new content is {len(new_normalized)} chars")
                    if emit_callback: # Still forward pre-tool_start valid events
                        event_to_forward = {**event, "message_id": message_id if message_id else (str(assistant_message_placeholder.id) if assistant_message_placeholder else "unknown"), "content_length": len(new_content)}
                        await emit_callback(event_to_forward)
                    return

                assistant_message_placeholder.content = new_content
                await self.conversation_repository.update_message(assistant_message_placeholder)
                logger.info(f"📝 DB Content updated: {len(new_content)} chars")
                
                if new_content.count('\n') > 2 and len(new_content) > 500: 
                    if not tool_start_processed_in_current_stream: 
                        has_good_content = True
                        last_good_content = new_content
                        newline_count = new_content.count('\n')
                        logger.info(f"📝 Detected good formatted content with {newline_count} newlines (pre-tool_start)")
                
                if emit_callback:
                    enhanced_event = {**event, "message_id": message_id if message_id else (str(assistant_message_placeholder.id) if assistant_message_placeholder else "unknown"), "content_length": len(new_content)}
                    await emit_callback(enhanced_event)
                return

            # Fallback for text_delta events (if not blocked by tool_start_processed_in_current_stream)
            if event_type == "text_delta":
                # If this delta belongs to a post-visualisation message, always forward it.
                if event.get("is_post_visualization"):
                    if emit_callback:
                        await emit_callback(event)
                    return

                # Otherwise, respect the tool_start gating logic
                if tool_start_processed_in_current_stream:
                    logger.warning("Text_delta reached main processing block despite tool_start_processed_in_current_stream. This is unexpected.")
                    return
                logger.info(f"Passing through text_delta event (pre-tool_start): '{event.get('text', '')[:50]}...'")


            # Handle citation marker events
            if event_type == "citation_marker":
                logger.info(f"📍 Citation marker event received: {event.get('marker')} at index {event.get('citation_index')}")
                # IMPORTANT: Don't forward citation markers until citations are fully processed
                # This prevents showing empty citations to users
                logger.info(f"🚫 Blocking citation_marker event - citations will be shown after full processing")
                return
            
            # Forward ALL other events (or non-returned text_delta/content_update)
            if emit_callback:
                if event.get("type") not in ["error"] and not event.get("message_id"):
                    event = {**event, "message_id": message_id if message_id else (str(assistant_message_placeholder.id) if assistant_message_placeholder else "unknown")}
                await emit_callback(event)
        
        # Note: message_start event is already sent by WebSocket handler
        # Don't emit duplicate message_start event here to avoid frontend confusion
        # The WebSocket handler already sent message_start with the correct message_id
        
        # Get conversation context
        context = await self.get_conversation_context(conversation_id)
        
        # Reuse pre-fetched context docs to avoid duplicate repository lookups.
        document_texts = self._build_document_texts_from_context_documents(
            context_documents=context.get("documents", []),
            conversation_id=conversation_id,
        )
        
        # Get conversation messages
        messages = await self.conversation_repository.get_conversation_messages(
            conversation_id=conversation_id,
            limit=10
        )
        
        # Convert messages to the format expected by Claude API
        message_history = []
        for msg in messages:
            if msg.id != user_message.id:
                message_history.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        # UNIFIED APPROACH: Always use streaming with tools available
        # Let Claude decide whether to use visualization tools based on the query
        logger.info(f"Using unified streaming approach with tools available for conversation {conversation_id}")
        
        # Extract file_id from first document if available
        file_id = None
        combined_doc_text = ""
        
        for doc in document_texts:
            if "claude_file_id" in doc and doc["claude_file_id"]:
                file_id = doc["claude_file_id"]
                logger.info(f"Using Files API claude_file_id {file_id} for unified streaming analysis")
                break
            elif "extracted_data" in doc and isinstance(doc["extracted_data"], dict):
                if "claude_file_id" in doc["extracted_data"] and doc["extracted_data"]["claude_file_id"]:
                    file_id = doc["extracted_data"]["claude_file_id"]
                    logger.info(f"Using cached claude_file_id {file_id} from extracted_data for unified streaming analysis")
                    break
                elif "file_id" in doc["extracted_data"] and doc["extracted_data"]["file_id"]:
                    file_id = doc["extracted_data"]["file_id"]
                    logger.info(f"Using legacy file_id {file_id} from extracted_data for unified streaming analysis")
                    break
            if "raw_text" in doc:
                combined_doc_text += f"\n\n{doc['raw_text']}"
        
        # Use Claude's streaming with tools - let Claude decide whether to use visualization tools
        result = await self._await_with_timeout(
            "claude streaming visualization analysis",
            self.claude_service.analyze_with_visualization_tools_streaming(
                document_text=combined_doc_text,
                user_query=content,
                file_id=file_id,
                emit_callback=enhanced_emit_callback,
                message_id=message_id,
            ),
            timeout_seconds=STREAMING_RESPONSE_TIMEOUT_SECONDS,
        )
        
        # Extract results
        analysis_text = result.get("analysis_text", "")
        visualizations = result.get("visualizations", {})
        accumulated_metrics = result.get("metrics", [])
        accumulated_citations = result.get("citations", [])
        
        logger.info(f"🔍 conversation_service received from analyze_with_visualization_tools_streaming: {len(accumulated_citations)} citations")
        
        # Debug: Log the first few citations to see if they have processed cited_text
        for i, cit in enumerate(accumulated_citations[:3]):
            logger.info(f"📊 Citation {i+1} cited_text: '{cit.get('cited_text', 'NO CITED TEXT')[:100]}...'")
            logger.info(f"📊 Citation {i+1} was_processed: {cit.get('was_processed', False)}")
        
        # UPDATED: analysis_text now only contains initial content (not post-tool content)
        # Post-tool content is sent as a separate message via new_message_start event
        logger.info(f"Current assistant message content length: {len(assistant_message_placeholder.content) if assistant_message_placeholder.content else 0}")
        if analysis_text:
            logger.info(f"📊 Received analysis_text from API: {len(analysis_text)} chars (initial content only)")
            
            # Check if the analysis_text contains content not in our current message
            # This can happen if post-tool content wasn't properly streamed
            current_content = assistant_message_placeholder.content or ""
            if current_content == "Processing your request...":
                # No streaming content received, use analysis_text
                logger.warning(f"⚠️ No streaming content received, using analysis_text")
                assistant_message_placeholder.content = analysis_text
                await self.conversation_repository.update_message(assistant_message_placeholder)
            else:
                # Check if analysis_text contains citation markers or other new content
                import re
                analysis_has_citations = bool(re.search(r'\[\d+\]', analysis_text))
                current_has_citations = bool(re.search(r'\[\d+\]', current_content))
                
                # Update if:
                # 1. analysis_text has citations but current doesn't
                # 2. analysis_text is significantly longer (post-tool content)
                # 3. analysis_text contains genuinely new content
                if (analysis_has_citations and not current_has_citations):
                    logger.info(f"✅ analysis_text contains citation markers, updating message")
                    assistant_message_placeholder.content = analysis_text
                    await self.conversation_repository.update_message(assistant_message_placeholder)
                elif len(analysis_text) > len(current_content) + 100:
                    # analysis_text is significantly longer, might contain post-tool content
                    logger.info(f"📝 analysis_text is {len(analysis_text) - len(current_content)} chars longer than current content")
                    # Check if it's genuinely new content or just a duplicate
                    if not current_content or not analysis_text.startswith(current_content[:min(100, len(current_content))]):
                        logger.info(f"✅ analysis_text contains new content, updating message")
                        assistant_message_placeholder.content = analysis_text
                        await self.conversation_repository.update_message(assistant_message_placeholder)
        
        # IMPORTANT: Preserve the streaming content we already have
        if has_good_content and last_good_content:
            # Check if current content has citation markers that last_good_content doesn't
            current_has_citations = bool(re.search(r'\[\d+\]', assistant_message_placeholder.content or ''))
            last_good_has_citations = bool(re.search(r'\[\d+\]', last_good_content))
            
            # If current content has citations but last_good_content doesn't, use current
            if current_has_citations and not last_good_has_citations:
                logger.info(f"✅ Current content has citations, using it instead of last_good_content")
                final_content = assistant_message_placeholder.content
                assistant_message = assistant_message_placeholder
                # Update last_good_content to include citations for future use
                last_good_content = final_content
            # We had good formatted content - make sure it's preserved
            elif assistant_message_placeholder.content != last_good_content:
                logger.warning(f"📝 Content was overwritten! Restoring good formatted content ({len(last_good_content)} chars)")
                assistant_message_placeholder.content = last_good_content
                assistant_message = await self.conversation_repository.update_message(assistant_message_placeholder)
                final_content = last_good_content
            else:
                final_content = assistant_message_placeholder.content
                assistant_message = assistant_message_placeholder
                logger.info(f"✅ Good formatted content preserved ({len(final_content)} chars)")
        elif assistant_message_placeholder.content and assistant_message_placeholder.content != "Processing your request...":
            # Use whatever streaming content we have
            final_content = assistant_message_placeholder.content
            logger.info(f"📝 Using streaming content ({len(final_content)} chars)")
            assistant_message = assistant_message_placeholder
        else:
            # Only use this fallback if we truly have no content (should be rare)
            final_content = "Analysis completed. Please check the visualizations."
            logger.warning(f"⚠️ No streaming content received - using fallback message")
            assistant_message_placeholder.content = final_content
            assistant_message = await self.conversation_repository.update_message(assistant_message_placeholder)
        
        # Skip citation injection if we already added markers during streaming
        if accumulated_citations:
            logger.info(f"Found {len(accumulated_citations)} citations")

            # Check if markers were already injected during streaming
            has_streaming_markers = any(f"[{i+1}]" in final_content for i in range(len(accumulated_citations)))

            if has_streaming_markers:
                logger.info("✅ Citation markers already injected during streaming")
            else:
                # Do not append a trailing "Sources:" marker block. The
                # frontend renders every persisted citation inline beside
                # matching facts; a backend-only marker list can drift from
                # the saved citation count and create non-clickable markers.
                logger.info("Leaving content marker-free; frontend will reflow persisted citations inline")
        
        logger.info(f"✅ Database updated with final content: {len(final_content)} chars")
        
        if not assistant_message:
            logger.error("Failed to update assistant message with streamed content")
            assistant_message = assistant_message_placeholder
        else:
            # CRITICAL: Never send message_update events during streaming
            # The frontend will fetch the complete message from the database when needed
            # Sending updates here can cause formatting issues and duplicate content
            logger.info(f"✅ NOT sending message_update - frontend will fetch from DB when needed")
        
        # Store citations if any were found
        if accumulated_citations:
            marker_matches = [int(m) for m in re.findall(r"\[(\d+)\]", final_content or "")]
            expected_marker_count = max(marker_matches) if marker_matches else 0

            # Normalize and trim citations so marker order remains stable.
            # During long tool runs Claude can emit repeated citation deltas; keeping
            # only the first citation per marker index avoids ambiguous [n] mapping.
            deduped_citations: List[Dict[str, Any]] = []
            seen_marker_indexes: set[int] = set()
            for citation_data in accumulated_citations:
                marker_index = citation_data.get("citation_index")
                try:
                    marker_index = int(marker_index) if marker_index is not None else None
                except Exception:
                    marker_index = None

                if marker_index is not None and marker_index > 0:
                    if marker_index in seen_marker_indexes:
                        continue
                    seen_marker_indexes.add(marker_index)

                deduped_citations.append(citation_data)

            if expected_marker_count > 0:
                deduped_citations = [
                    c for c in deduped_citations
                    if (int(c.get("citation_index")) if c.get("citation_index") is not None else 0) <= expected_marker_count
                    or c.get("citation_index") is None
                ]

            if deduped_citations:
                deduped_citations.sort(
                    key=lambda c: (
                        int(c.get("citation_index")) if c.get("citation_index") is not None else 10_000,
                    )
                )

            logger.info(
                "Storing %s citations for message %s (raw=%s, markers=%s)",
                len(deduped_citations),
                assistant_message.id,
                len(accumulated_citations),
                expected_marker_count,
            )
            
            # We need to save citations through the document repository
            # Map document_index to actual document IDs
            doc_id_map = {}
            for idx, doc in enumerate(document_texts):
                doc_id_map[idx] = doc.get("id")
            
            # Create and save citations
            for citation_data in deduped_citations:
                try:
                    # Get the actual document ID from the index
                    doc_index = citation_data.get("document_index", 0)
                    document_id = doc_id_map.get(doc_index)
                    
                    if not document_id:
                        logger.warning(f"Could not find document ID for index {doc_index}, skipping citation")
                        continue
                    
                    # Log the citation data to verify it has been processed
                    logger.info(f"📊 Saving citation - cited_text: '{citation_data.get('cited_text', 'NO CITED TEXT')[:100]}...', was_processed: {citation_data.get('was_processed', False)}")
                    # Additional debug logging
                    if 'original_cited_text' in citation_data:
                        logger.info(f"📊 Citation has original_cited_text: '{citation_data['original_cited_text'][:50]}...'")
                    logger.info(f"📊 Full citation_data keys: {list(citation_data.keys())}")
                    
                    # Create citation through document repository
                    # Use the processed cited_text if available, otherwise fall back to original
                    cited_text = citation_data.get("cited_text", "")
                    was_processed = citation_data.get("was_processed", False)
                    
                    # If citation was processed, it should have the extracted specific value
                    if was_processed:
                        logger.info(f"✅ Using processed citation text: '{cited_text[:100]}...'")
                    else:
                        # Fallback to original if not processed
                        original_text = citation_data.get("original_cited_text", cited_text)
                        logger.warning(f"⚠️ Citation not processed, using original text: '{original_text[:100]}...'")
                    
                    citation_obj = {
                        "document_id": document_id,
                        "text": cited_text,  # Use the processed cited_text
                        "cited_text": cited_text,  # Use the processed cited_text
                        "display_text": citation_data.get("display_text"),  # Processed text for display
                        "searchable_text": citation_data.get("searchable_text"),  # Text for PDF rect finding
                        "document_title": citation_data.get("document_title", ""),
                        "type": citation_data.get("type", "page_location"),
                        "start_page_number": citation_data.get("start_page_number"),
                        "end_page_number": citation_data.get("end_page_number"),
                        "start_char_index": citation_data.get("start_char_index"),
                        "end_char_index": citation_data.get("end_char_index"),
                        "start_block_index": citation_data.get("start_block_index"),
                        "end_block_index": citation_data.get("end_block_index"),
                        # Persist marker index in section so downstream rect selection can
                        # resolve marker-specific answer context (for [1], [2], ...).
                        "section": (
                            str(citation_data.get("citation_index"))
                            if citation_data.get("citation_index") is not None
                            else None
                        ),
                        "highlight_id": str(uuid.uuid4()),
                        "rects": json.dumps([]),  # Empty array as JSON string
                        "message_id": assistant_message.id,
                        "analysis_id": None
                    }
                    
                    # Debug logging for searchable_text
                    if citation_obj.get("searchable_text"):
                        logger.info(f"✅ Citation has searchable_text: '{citation_obj['searchable_text']}'")
                    else:
                        logger.warning(f"⚠️ Citation missing searchable_text - will use full cited_text for rect finding")
                    
                    # Create citation through document repository
                    created_citation = await self.document_repository.create_citation_with_message(
                        document_id=document_id,
                        citation_data=citation_obj
                    )
                    logger.info(f"Created citation {created_citation.id} for document {document_id}")
                    
                except Exception as e:
                    logger.error(f"Error creating citation: {str(e)}", exc_info=True)
            
            logger.info(f"✅ Citations processing completed for message {assistant_message.id}")
        
        # Debug logging for metrics
        logger.info(f"DEBUG: result.get('metrics'): {result.get('metrics', []) if 'result' in locals() else 'result not available'}")
        logger.info(f"DEBUG: accumulated_metrics: {accumulated_metrics}")
        
        # Process and store visualizations (same logic as non-streaming)
        logger.info(f"Processing visualizations for conversation {conversation_id}: charts={len(visualizations.get('charts', []))}, tables={len(visualizations.get('tables', []))}, metrics={len(accumulated_metrics)}")
        
        if visualizations.get("charts") or visualizations.get("tables") or accumulated_metrics:
            # Create a NEW message for tools/visualizations
            tools_message = await self.conversation_repository.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content="",  # Tools message has no text content, only analysis blocks
                referenced_documents=[],
                referenced_analyses=[]
            )
            logger.info(f"✅ Created new message for tools/visualizations: {tools_message.id}")
            
            # Emit new_message_start for the tools message
            if emit_callback:
                await emit_callback({
                    "type": "new_message_start",
                    "message_id": str(tools_message.id),
                    "role": "assistant",
                    "is_tools_message": True
                })
            
            items_for_analysis_blocks = []
            
            # Process charts
            for chart_item in visualizations.get("charts", []):
                logger.info(f"Processing chart: {chart_item.get('config', {}).get('title', 'Unnamed Chart')}")
                processed_chart_item = {
                    "title": chart_item.get("config", {}).get("title", "Chart"),
                    "visualization_type": "chart",
                    "data": chart_item or {}
                }
                items_for_analysis_blocks.append(processed_chart_item)
            
            # Process tables
            for table_item in visualizations.get("tables", []):
                logger.info(f"Processing table: {table_item.get('config', {}).get('title', 'Unnamed Table')}")
                processed_table_item = {
                    "title": table_item.get("config", {}).get("title", "Table"),
                    "visualization_type": "table",
                    "data": table_item or {}
                }
                items_for_analysis_blocks.append(processed_table_item)
            
            # Process metrics
            for metric_item in accumulated_metrics:
                logger.info(f"Processing metric: {metric_item.get('name', metric_item.get('title', 'Unnamed Metric'))}")
                processed_metric_item = {
                    "title": metric_item.get("name", metric_item.get("title", "Metric")),
                    "visualization_type": "metric",
                    "data": metric_item or {}
                }
                items_for_analysis_blocks.append(processed_metric_item)
            
            # Store analysis blocks atomically with final content verification
            if items_for_analysis_blocks and tools_message:
                logger.info(f"Storing {len(items_for_analysis_blocks)} analysis blocks for tools message {tools_message.id}")
                await self._store_analysis_blocks_atomically(
                    message=tools_message,
                    visualizations=items_for_analysis_blocks
                )
                
                # NOW send message_complete for the initial answer after analysis blocks
                # are stored atomically unless we already sent it earlier. The tools
                # carrier message is completed separately below.
                if initial_message_completed:
                    logger.info(
                        "Skipping duplicate message_complete for initial message; it was already sent at first tool_start"
                    )
                else:
                    logger.info(
                        f"Sending message_complete event for conversation {conversation_id} after analysis blocks stored"
                    )

                # Serialize analysis blocks for immediate frontend rendering
                serialized_blocks = []
                try:
                    # Refresh tools_message to get the analysis blocks
                    await self.conversation_repository.db.refresh(tools_message, attribute_names=['analysis_blocks'])
                    for block in (tools_message.analysis_blocks or []):
                        serialized_blocks.append({
                            "id": block.id,
                            "block_type": block.block_type,
                            "title": block.title,
                            "content": block.content,
                            # ISO format ensures JSON serializable datetime
                            "created_at": block.created_at.isoformat() if block.created_at else None
                        })
                except Exception as ser_err:
                    logger.warning(f"Failed to serialize analysis blocks for message_complete event: {ser_err}")

                if emit_callback:
                    if not initial_message_completed:
                        await emit_callback({
                            "type": "message_complete",
                            "message_id": str(assistant_message.id),
                            "timestamp": datetime.utcnow().isoformat() + 'Z',
                            "citations": accumulated_citations,
                            "is_post_tools": False,
                            "is_post_visualization": False
                        })
                        initial_message_completed = True

                    # Send message_complete for the tools message
                    await emit_callback({
                        "type": "message_complete",
                        "message_id": str(tools_message.id),
                        "timestamp": datetime.utcnow().isoformat() + 'Z',
                        "analysis_blocks": serialized_blocks,  # provide blocks directly
                        "is_tools_message": True
                    })
                    logger.info(
                        f"message_complete event sent for tools message {tools_message.id} – blocks: {len(serialized_blocks)}"
                    )
                else:
                    logger.warning(
                        f"No emit_callback available to send message_complete for conversation {conversation_id}"
                    )
        else:
            # For conversations without visualizations, still send message_complete
            logger.info(f"Sending message_complete event for conversation {conversation_id} (no visualizations)")
            if emit_callback:
                await emit_callback({
                    "type": "message_complete",
                    "message_id": str(assistant_message.id),
                    "timestamp": datetime.utcnow().isoformat() + 'Z',
                    "citations": accumulated_citations  # Include citations for frontend
                })
                logger.info(f"message_complete event sent for conversation {conversation_id} (no visualizations)")
        
        return {
            "success": True,
            "message": assistant_message
        }
    
    def _build_system_prompt(self, document_texts: List[Dict[str, Any]], citations: List[Dict[str, Any]]) -> str:
        """
        Build a system prompt for Claude based on the conversation context.
        
        Args:
            document_texts: List of document texts
            citations: List of citations
            
        Returns:
            System prompt string
        """
        # Import citation instructions
        from services.citation_instructions import FINANCIAL_AGENT_INSTRUCTIONS
        
        prompt = """You are a financial document analysis assistant specialized in analyzing financial statements and reports.
Your role is to help users understand financial documents, extract insights, and provide financial analysis.

Here are some important guidelines:
1. Always provide accurate financial analysis and calculations.
2. Cite sources when referencing specific data from documents.
3. Use clear, professional language suitable for financial discussions.
4. When unsure, acknowledge limitations and avoid making up information.
5. When generating visualizations, follow the provided format exactly.
6. When analyzing financial documents, focus on key metrics, trends, and insights.
7. Provide context and explanations for financial terms and concepts.

""" + FINANCIAL_AGENT_INSTRUCTIONS
        
        # Add document context if available
        if document_texts and len(document_texts) > 0:
            prompt += "\nHere are the financial documents available for reference:\n\n"
            for i, doc in enumerate(document_texts):
                # Handle string or dictionary format
                if isinstance(doc, str):
                    # If document_texts contains raw strings instead of dictionaries
                    doc_id = f'doc_{i}'
                    doc_title = f'Document {i+1}'
                    doc_type = 'text/plain'
                    doc_text = doc  # The string itself is the text
                elif isinstance(doc, dict):
                    # If document_texts contains dictionaries (preferred format)
                    doc_id = doc.get('id', f'doc_{i}')
                    doc_title = doc.get('title', doc.get('filename', 'Untitled Document'))
                    doc_type = doc.get('content_type', doc.get('document_type', 'unknown'))
                    
                    # Get text from various possible fields
                    doc_text = ""
                    if 'raw_text' in doc:
                        doc_text = doc['raw_text']
                    elif 'text' in doc:
                        doc_text = doc['text']
                    elif 'content' in doc and isinstance(doc['content'], str):
                        doc_text = doc['content']
                else:
                    # Skip invalid document formats
                    logger.warning(f"Skipping invalid document format in system prompt: {type(doc)}")
                    continue
                
                # Add document metadata
                prompt += f"DOCUMENT {i+1} (ID: {doc_id}):\nTitle: {doc_title}\nType: {doc_type}\n"
                
                # Add a snippet of the document text if available
                if doc_text:
                    # Ensure preview_source is a string before slicing to satisfy type checker
                    preview_source: str
                    if isinstance(doc_text, str):
                        preview_source = doc_text
                    else:
                        preview_source = _to_str(doc_text)

                    preview_source_str: str = str(preview_source)
                    text_preview = preview_source_str[:1000] + "..." if len(preview_source_str) > 1000 else preview_source_str
                    prompt += f"\nContent preview:\n{text_preview}\n"
                else:
                    prompt += "\nNo text content available for this document.\n"
                
                prompt += "\n"
        
        # Add citation context if available
        if citations and len(citations) > 0:
            prompt += "\nThe user has referenced the following citations:\n\n"
            for i, citation in enumerate(citations):
                cit_id = citation.get('id', f'citation_{i}')
                doc_id = citation.get('document_id', 'unknown')
                content = citation.get('content', 'No content available')
                metadata = citation.get('metadata', {})
                
                prompt += f"CITATION {i+1} (ID: {cit_id}):\n"
                prompt += f"From document: {doc_id}\n"
                prompt += f"Content: {content}\n"
                if metadata:
                    prompt += f"Metadata: {metadata}\n"
                prompt += "\n"
        
        # Add visualization instructions for tool-based chat output (charts, tables, metric cards)
        prompt += """
When the user asks for analysis, trends, comparisons, or visualizations during chat, use the generate_graph_data, generate_table_data, and generate_financial_metric tools (not inline JSON blocks). Apply the banking metric formatting and table-first sourcing rules above to every chart series, table cell, and metric card you emit.
"""
        
        return prompt
    
    def _parse_claude_response(self, response: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Parse Claude's response to extract visualizations and clean the text.
        
        Args:
            response: Response string from Claude
            
        Returns:
            Tuple of (cleaned response text, list of visualization objects)
        """
        import re
        
        # Find all JSON blocks enclosed in triple backticks
        json_pattern = r"```json\s*([\s\S]*?)\s*```"
        json_blocks = re.findall(json_pattern, response)
        
        visualizations = []
        for json_block in json_blocks:
            try:
                visualization = json.loads(json_block)
                visualizations.append(visualization)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON block: {json_block}")
        
        # Remove the JSON blocks from the response
        cleaned_response = re.sub(json_pattern, "[Visualization]", response)
        
        return cleaned_response, visualizations
    
    async def _process_visualizations(
        self,
        message_id: str,
        visualizations: List[Dict[str, Any]]
    ):
        """
        Process and store visualizations as analysis blocks.
        
        Args:
            message_id: ID of the message to associate with the visualizations
            visualizations: List of visualization data
        """
        for i, viz in enumerate(visualizations):
            title = viz.get("title", f"Visualization {i+1}")
            block_type = viz.get("visualization_type", "chart")
            
            # Ensure block_type is one of the known types, or a new one like "metric"
            # Existing types: "bar", "line", "pie", "area", "scatter", "table"
            # New type: "metric"
            # The `visualization_type` from the item (e.g., "chart", "table", "metric") is used directly.
            # `add_analysis_block` in repository should handle `block_type=viz.get("visualization_type")`
            # and `content=viz.get("data")`
            
            # The content of the analysis block should be the 'data' part of the viz item
            data_content: Dict[str, Any] = viz.get("data") or {}
            if not isinstance(data_content, dict):
                data_content = {"value": data_content}
            await self.conversation_repository.add_analysis_block(
                message_id=message_id,
                block_type=viz.get("visualization_type", "unknown"),
                title=title,
                content=data_content
            )
    
    async def add_document_to_conversation(
        self,
        conversation_id: str,
        document_id: str
    ) -> bool:
        """
        Add a document to a conversation.
        
        Args:
            conversation_id: ID of the conversation
            document_id: ID of the document to add
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Starting document addition process - conversation={conversation_id}, document={document_id}")
        
        # Verify that the conversation and document exist
        conversation = await self.conversation_repository.get_conversation(conversation_id)
        if not conversation:
            logger.error(f"Conversation {conversation_id} not found when adding document {document_id}")
            return False
        
        document = await self.document_repository.get_document(document_id)
        if not document:
            logger.error(f"Document {document_id} not found when adding to conversation {conversation_id}")
            return False
            
        # Log document details for debugging
        doc_status = getattr(document, "processing_status", "unknown")
        doc_type = getattr(document, "document_type", "unknown")
        doc_filename = getattr(document, "filename", "unknown")
        logger.info(f"Document details: ID={document_id}, Filename={doc_filename}, Type={doc_type}, Status={doc_status}")
        
        # Add document to conversation
        success = await self.conversation_repository.add_document_to_conversation(
            conversation_id=conversation_id,
            document_id=document_id
        )
        
        if success:
            # Add a system message about the added document
            await self.conversation_repository.add_message(
                conversation_id=conversation_id,
                content=f"Document '{document.filename}' has been added to the conversation.",
                role="system"
            )
        
        return success
    
    async def remove_document_from_conversation(
        self,
        conversation_id: str,
        document_id: str
    ) -> bool:
        """
        Remove a document from a conversation.
        
        Args:
            conversation_id: ID of the conversation
            document_id: ID of the document to remove
            
        Returns:
            True if successful, False otherwise
        """
        # Verify that the conversation exists
        conversation = await self.conversation_repository.get_conversation(conversation_id)
        if not conversation:
            return False
        
        # Remove document from conversation
        success = await self.conversation_repository.remove_document_from_conversation(
            conversation_id=conversation_id,
            document_id=document_id
        )
        
        if success:
            # Get the document to access its filename
            document = await self.document_repository.get_document(document_id)
            filename = document.filename if document else "Unknown document"
            
            # Add a system message about the removed document
            await self.conversation_repository.add_message(
                conversation_id=conversation_id,
                content=f"Document '{filename}' has been removed from the conversation.",
                role="system"
            )
        
        return success
    
    async def generate_follow_up_questions(
        self,
        conversation_id: str,
        limit: int = 3
    ) -> List[str]:
        """
        Generate contextually relevant follow-up questions based on conversation history.
        
        Args:
            conversation_id: ID of the conversation
            limit: Maximum number of follow-up questions to generate (default: 3)
            
        Returns:
            List of follow-up question strings
        """
        try:
            # Get conversation and recent messages
            conversation = await self.conversation_repository.get_conversation(conversation_id)
            if not conversation:
                logger.warning(f"Conversation {conversation_id} not found for follow-up generation")
                return self._get_default_follow_up_questions()
            
            # Get the last few messages for context (last 6 messages or all if fewer)
            messages = await self.conversation_repository.get_conversation_messages(conversation_id)
            if not messages or len(messages) == 0:
                logger.info(f"No messages found for conversation {conversation_id}, using default questions")
                return self._get_default_follow_up_questions()
            
            # Take the last 6 messages for context (3 user-assistant pairs typically)
            recent_messages = messages[-6:] if len(messages) > 6 else messages
            
            # Build conversation context for the prompt
            conversation_context = ""
            for msg in recent_messages:
                role_label = "User" if msg.role == "user" else "Assistant"
                conversation_context += f"{role_label}: {msg.content}\n"
            
            # Get document context if available
            documents = await self.conversation_repository.get_conversation_documents(conversation_id)
            document_context = ""
            if documents:
                doc_titles = [doc.filename for doc in documents[:3]]  # Limit to 3 documents
                document_context = f"\nDocuments being discussed: {', '.join(doc_titles)}"
            
            # Create prompt for follow-up question generation
            follow_up_prompt = f"""Based on the following conversation about financial documents, generate exactly {limit} relevant follow-up questions that would naturally continue the discussion. Focus on:
1. Deeper analysis of mentioned financial metrics
2. Related financial concepts or ratios
3. Comparative analysis or trends
4. Practical implications of the findings

NOTE: ONLY PROVIDE QUESTIONS THAT COULD BE ANSWERED BY THE FINANCIAL DOCUMENTS PROVIDED.

Conversation context:{document_context}

{conversation_context}

Generate exactly {limit} follow-up questions, each on a new line, without numbering or bullet points. Make them conversational and specific to the context discussed."""

            # Use the configured fast model for cost-effective follow-up generation.
            try:
                follow_up_response_raw = await self._await_with_timeout(
                    "claude follow-up question generation",
                    self.claude_service.generate_response(
                        system_prompt="You are a financial analysis assistant that generates relevant follow-up questions for financial document discussions. Always provide exactly the requested number of questions, each on a separate line.",
                        messages=[{"role": "user", "content": follow_up_prompt}],
                        model=settings.MODEL_HAIKU,
                        max_tokens=500,  # Limit tokens since we only need a few questions
                        temperature=0.7,  # Slightly creative for varied questions
                    ),
                    timeout_seconds=LLM_RESPONSE_TIMEOUT_SECONDS,
                )
                follow_up_response: str = cast(str, follow_up_response_raw)
                
                # Parse the response into individual questions
                if follow_up_response and follow_up_response.strip():
                    questions = [
                        q.strip() 
                        for q in follow_up_response.strip().split('\n') 
                        if q.strip() and not q.strip().startswith(('1.', '2.', '3.', '-', '*'))
                    ]
                    
                    # Filter out empty questions and ensure we have valid questions
                    valid_questions = [q for q in questions if len(q) > 10 and q.endswith('?')]
                    
                    if valid_questions:
                        # Return the requested number of questions, or all if fewer
                        return valid_questions[:limit]
                    else:
                        logger.warning(f"Generated follow-up questions were invalid for conversation {conversation_id}")
                        return self._get_default_follow_up_questions()
                else:
                    logger.warning(f"Empty response from Claude for follow-up generation in conversation {conversation_id}")
                    return self._get_default_follow_up_questions()
                    
            except Exception as claude_error:
                logger.error(f"Claude API error generating follow-ups for conversation {conversation_id}: {str(claude_error)}")
                return self._get_default_follow_up_questions()
                
        except Exception as e:
            logger.error(f"Error generating follow-up questions for conversation {conversation_id}: {str(e)}")
            return self._get_default_follow_up_questions()
    
    def _get_default_follow_up_questions(self) -> List[str]:
        """
        Get default follow-up questions as fallback.
        
        Returns:
            List of default follow-up question strings
        """
        return [
            "What trends do you see in the financial performance?",
            "How does this compare to industry benchmarks?", 
            "Breakdown the financial performance by category"
        ]
    
    async def _decide_processing_approach(
        self,
        conversation_id: str,
        message_content: str,
        document_texts: List[Dict[str, Any]],
        conversation_history: List[Dict[str, Any]]
    ) -> str:
        """
        Decide which processing approach to use based on the message and context.
        Starts with simple QA for basic questions, but can transition to more 
        complex processing for analytical questions.
        
        Args:
            conversation_id: ID of the conversation
            message_content: User's message
            document_texts: List of document texts
            conversation_history: Previous conversation history
            
        Returns:
            The most appropriate processing approach: "simple_qa", "citations", "full_graph", "visualization_analysis"
        """
        # If no documents, use simple response
        if not document_texts or len(document_texts) == 0:
            logger.info(f"No documents available for conversation {conversation_id}, using simple_qa approach")
            return "simple_qa"

        lower_message_content = message_content.lower()

        # Keywords for visualization_analysis (explicit visualization)
        visualization_keywords = ["visualize", "chart", "graph", "plot", "table", "display"] # "show me" is too ambiguous, removed.
        # Keywords for visualization_analysis (analytical queries that benefit from structured output)
        analytical_keywords = ["analyze", "analysis", "calculate", "ratio", "trend", "compare", "deposits", "loans", "revenue", "profit", "assets", "liabilities"]
        # Keywords for visualization_analysis (summary/structured information)
        summary_keywords = [
            "summarize performance", "key financial changes", "what are the main metrics",
            "financial health", "breakdown of", "details on" # "details on" will be checked with financial context later
        ]
        # Keywords for citations
        citation_keywords = ["cite", "citation", "reference", "page", "section", "paragraph"]

        # Check for visualization keywords
        if any(term in lower_message_content for term in visualization_keywords):
            logger.info(f"User message for conversation {conversation_id} requests visualization, using visualization_analysis approach")
            return "visualization_analysis"

        # Check for analytical and summary keywords that should lead to visualization_analysis
        # This includes previous "full_graph" keywords and new summary keywords.
        analytical_or_summary_triggered = False
        if any(term in lower_message_content for term in analytical_keywords):
            analytical_or_summary_triggered = True
        
        for term in summary_keywords:
            if term == "details on":
                # Check for "details on [financial concept]" - simplistic check for now
                if "details on" in lower_message_content and ("financial" in lower_message_content or "metric" in lower_message_content or "kpi" in lower_message_content):
                    analytical_or_summary_triggered = True
                    break
            elif term in lower_message_content:
                analytical_or_summary_triggered = True
                break

        if analytical_or_summary_triggered:
            logger.info(f"User message for conversation {conversation_id} requests analysis/summary, using visualization_analysis approach")
            return "visualization_analysis"

        # Check for citation keywords IF no analytical/visualization keywords were strongly triggered
        # This gives priority to analytical/visualization paths if there's an overlap.
        if any(term in lower_message_content for term in citation_keywords):
            logger.info(f"User message for conversation {conversation_id} mentions citations and no strong analytical/viz keywords, using citations approach")
            return "citations"
        
        # Default to simple QA for basic questions
        logger.info(f"Using default simple_qa approach for conversation {conversation_id} (no specific keywords matched)")
        return "simple_qa"
    
    async def _process_with_langgraph(
        self,
        conversation_id: str,
        content: str,
        document_texts: List[Dict[str, Any]],
        messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Process a user message using LangGraph for simple document QA.
        Handles citation data from Claude API responses to provide source references.
        
        Args:
            conversation_id: ID of the conversation
            content: The user's message content
            document_texts: List of document texts
            messages: Conversation history messages
            
        Returns:
            Dictionary with response details
        """
        try:
            # Validate document_texts to ensure it's a list of dictionaries
            if not isinstance(document_texts, list):
                logger.warning(f"document_texts is not a list: {type(document_texts)}")
                if isinstance(document_texts, str):
                    logger.warning("Converting string document_text to a list with one document")
                    # Convert to a proper document format
                    document_texts = [{
                        "id": "doc_1",
                        "title": "Document",
                        "raw_text": document_texts,
                        "content_type": "text/plain"
                    }]
                elif isinstance(document_texts, dict):
                    logger.warning("Converting dictionary document_text to a list with one document")
                    document_texts = [document_texts]
                else:
                    logger.error(f"Invalid document_texts format: {type(document_texts)}")
                    document_texts = []
            
            # Validate each document in the list
            valid_documents = []
            for i, doc in enumerate(document_texts):
                if not isinstance(doc, dict):
                    logger.warning(f"Document at index {i} is not a dictionary: {type(doc)}")
                    if isinstance(doc, str):
                        # Convert string to document dictionary
                        valid_documents.append({
                            "id": f"doc_{i+1}",
                            "title": f"Document {i+1}",
                            "raw_text": doc,
                            "content_type": "text/plain"
                        })
                        logger.info(f"Converted string to document dictionary at index {i}")
                    else:
                        logger.warning(f"Skipping invalid document at index {i}")
                        continue
                else:
                    valid_documents.append(doc)
            
            document_texts = valid_documents
            
            # Optimize document texts using Claude Files API file_id (no text extraction needed)
            optimized_document_texts = []
            for i, doc in enumerate(document_texts):
                doc_id = doc.get('id', f'doc_{i+1}')
                
                # Get file_id from document database for Files API
                if 'id' in doc:
                    try:
                        db_doc = await self.document_repository.get_document(doc['id'])
                        if db_doc and db_doc.claude_file_id:
                            # Create optimized document object with file_id for native PDF support
                            optimized_doc = doc.copy()
                            optimized_doc['claude_file_id'] = db_doc.claude_file_id
                            optimized_doc['filename'] = db_doc.filename
                            # Remove raw_text since we'll use native PDF support via file_id
                            optimized_doc.pop('raw_text', None)
                            optimized_document_texts.append(optimized_doc)
                            logger.info(f"Using Files API file_id {db_doc.claude_file_id} for document {doc['id']} (native PDF support)")
                        else:
                            logger.warning(f"No claude_file_id found for document {doc['id']}, falling back to text")
                            optimized_document_texts.append(doc)
                    except Exception as e:
                        logger.warning(f"Failed to get file_id for document {doc['id']}: {e}")
                        optimized_document_texts.append(doc)
                else:
                    optimized_document_texts.append(doc)
            
            document_texts = optimized_document_texts
            
            # Log document information before sending
            logger.info(f"Processing {len(document_texts)} documents with native PDF support via Files API")
            for i, doc in enumerate(document_texts):
                doc_id = doc.get('id', f'doc_{i+1}')
                has_file_id = 'claude_file_id' in doc and bool(doc.get('claude_file_id'))
                has_raw_text = 'raw_text' in doc and bool(doc.get('raw_text'))
                filename = doc.get('filename', 'unknown')
                
                if has_file_id:
                    logger.info(f"Document {i+1}: ID={doc_id}, filename={filename}, using Files API file_id={doc['claude_file_id']}")
                elif has_raw_text:
                    content_length = len(doc.get('raw_text', ''))
                    logger.info(f"Document {i+1}: ID={doc_id}, filename={filename}, using raw_text fallback ({content_length} chars)")
                else:
                    logger.warning(f"Document {i+1}: ID={doc_id}, filename={filename}, no file_id or raw_text available")
            
            # Generate response with LangGraph
            logger.info("Using LangGraph for basic response generation with documents")
            response_data = await self.claude_service.generate_response_with_langgraph(
                question=content,
                document_texts=document_texts,
                conversation_history=messages
            )
            
            # Extract content and citations from response
            response_content = response_data.get("content", "I'm sorry, I couldn't generate a response.")
            response_citations = response_data.get("citations", [])
            
            # Check if the response is an error message from Claude
            if "error" in response_content.lower() and ("api key" in response_content.lower() or "authentication" in response_content.lower()):
                logger.error(f"Claude API authentication error: {response_content}")
                
                # Add assistance message about the error
                assistant_message = await self.add_message(
                    conversation_id=conversation_id,
                    content=f"I apologize, but there was an error processing your request: {response_content}",
                    role="assistant"
                )
                
                return {
                    "success": False,
                    "error": "Authentication error with Claude API",
                    "message": assistant_message
                }
            
            # Create citation objects to store in database
            citation_links = []
            citation_objects = []
            
            if response_citations:
                logger.info(f"Processing {len(response_citations)} citations from LangGraph response")
                
                # Map of document indexes to document IDs
                document_map = {}
                for i, doc in enumerate(document_texts):
                    if "id" in doc:
                        document_map[i] = doc["id"]
                
                # Process each citation
                for citation in response_citations:
                    try:
                        # Create a citation object for database storage
                        citation_id = str(uuid.uuid4())
                        citation_type = citation.get("type", "unknown")
                        
                        # Get document ID from document_index if available
                        document_id = None
                        document_index = citation.get("document_index")
                        if document_index is not None and document_index in document_map:
                            document_id = document_map[document_index]
                        
                        # Create the base citation object
                        citation_obj = {
                            "id": citation_id,
                            "text": citation.get("cited_text", ""),
                            "document_id": document_id,
                            "document_title": citation.get("document_title", "")
                        }
                        
                        # Add type-specific location information
                        if citation_type == "char_location":
                            citation_obj["location_type"] = "text"
                            citation_obj["start_char"] = citation.get("start_char_index")
                            citation_obj["end_char"] = citation.get("end_char_index")
                        elif citation_type == "page_location":
                            citation_obj["location_type"] = "page"
                            citation_obj["start_page"] = citation.get("start_page_number")
                            citation_obj["end_page"] = citation.get("end_page_number")
                        elif citation_type == "content_block_location":
                            citation_obj["location_type"] = "block"
                            citation_obj["start_block"] = citation.get("start_block_index")
                            citation_obj["end_block"] = citation.get("end_block_index")
                        
                        # Store citation and track ID for message linking
                        citation_objects.append(citation_obj)
                        citation_links.append(citation_id)
                        
                        logger.debug(f"Processed citation: {citation_id} from {citation_type}")
                    except Exception as e:
                        logger.error(f"Error processing citation: {str(e)}")
            
            # Save citations to repository if possible
            citation_ids = []
            if citation_objects and hasattr(self, 'citation_repository') and self.citation_repository:
                try:
                    for citation_obj in citation_objects:
                        citation_id = await self.citation_repository.add_citation(citation_obj)
                        if citation_id:
                            citation_ids.append(citation_id)
                except Exception as e:
                    logger.error(f"Error saving citations to repository: {str(e)}")
            
            # Add assistant message with citation links
            assistant_message = await self.add_message(
                conversation_id=conversation_id,
                content=_to_str(response_content),
                role="assistant",
                citation_ids=citation_ids if citation_ids else citation_links
            )
            
            if not assistant_message:
                logger.error("Failed to add assistant message")
                return {
                    "success": False,
                    "error": "Failed to save assistant message"
                }
            
            return {
                "success": True,
                "message": assistant_message
            }
            
        except Exception as e:
            logger.error(f"Error in _process_with_langgraph: {str(e)}", exc_info=True)
            
            # Add fallback message on error
            try:
                error_message = await self.add_message(
                    conversation_id=conversation_id,
                    content="I apologize, but I encountered an error processing your request. Please try again or rephrase your question.",
                    role="assistant"
                )
                
                return {
                    "success": False,
                    "error": str(e),
                    "message": error_message
                }
            except Exception as add_error:
                logger.error(f"Failed to add error message: {str(add_error)}")
                return {
                    "success": False,
                    "error": f"Multiple errors: {str(e)} and {str(add_error)}"
                }

    async def _store_analysis_blocks_atomically(
        self,
        message: Any,
        visualizations: List[Dict[str, Any]]
    ):
        """
        Store analysis blocks atomically with content verification to prevent frontend from
        retrieving incomplete message states during the streaming process.
        
        Args:
            message: The message object to attach analysis blocks to
            visualizations: List of visualization data to store as analysis blocks
        """
        from sqlalchemy.orm import sessionmaker
        
        # FIXED: Check if transaction is already active to prevent "transaction already begun" error
        db_session = self.conversation_repository.db
        
        # Check if there's already an active transaction
        if db_session.in_transaction():
            logger.info(f"ATOMIC: Using existing transaction for message {message.id}")
            # Use existing transaction - just execute the operations directly
            await self._store_blocks_in_current_transaction(message, visualizations)
        else:
            logger.info(f"ATOMIC: Creating new transaction for message {message.id}")
            # Create new transaction
            async with db_session.begin() as transaction:
                await self._store_blocks_in_current_transaction(message, visualizations)
    
    async def _store_blocks_in_current_transaction(
        self,
        message: Any,
        visualizations: List[Dict[str, Any]]
    ):
        """
        Store analysis blocks in the current transaction (helper method)
        """
        try:
            # First, ensure the message content is properly persisted
            await self.conversation_repository.db.refresh(message)
            logger.info(f"ATOMIC: Refreshed message {message.id} content length: {len(message.content or '')} chars")
            
            # Store all analysis blocks within the current transaction
            for i, viz in enumerate(visualizations):
                title = viz.get("title", f"Visualization {i+1}")
                block_type = viz.get("visualization_type", "chart")
                
                # Create analysis block within the transaction
                block_content: Dict[str, Any] = viz.get("data") or {}
                if not isinstance(block_content, dict):
                    block_content = {"value": block_content}
                await self.conversation_repository.add_analysis_block(
                    message_id=str(message.id),
                    block_type=viz.get("visualization_type", "unknown"),
                    title=title,
                    content=block_content
                )
                logger.info(f"ATOMIC: Stored analysis block {i+1}/{len(visualizations)}: {title}")
            
            # Refresh message to load analysis blocks within the transaction
            await self.conversation_repository.db.refresh(message, attribute_names=['analysis_blocks'])
            logger.info(f"ATOMIC: Transaction complete - message {message.id} has {len(message.analysis_blocks or [])} analysis blocks")
            
        except Exception as e:
            logger.error(f"ATOMIC: Transaction failed for message {message.id}: {str(e)}")
            # Transaction will rollback automatically on exception
            raise
