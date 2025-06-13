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
from typing import List, Dict, Any, Optional, Tuple

from repositories.conversation_repository import ConversationRepository
from repositories.document_repository import DocumentRepository
from repositories.analysis_repository import AnalysisRepository
from pdf_processing.api_service import ClaudeService
from models.database_models import Message, Conversation

logger = logging.getLogger(__name__)

class ConversationService:
    """Service for managing conversations and messages."""
    
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
        
        self.claude_service = ClaudeService(api_key=api_key)
    
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
        referenced_analyses: Optional[List[str]] = None
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
        
        return await self.conversation_repository.add_message(
            conversation_id=conversation_id,
            content=content,
            role=role,
            citation_ids=citation_ids,
            referenced_documents=referenced_documents or [],
            referenced_analyses=referenced_analyses or []
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
                }
                
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
        
        # Extract document texts for system prompt
        document_texts = []
        if context.get("documents"):
            # Process each document
            for doc_info in context["documents"]:
                try:
                    # Get document content for citation processing
                    content_obj = await self.document_repository.get_document_content(doc_info["id"])
                    content_data = None
                    raw_text = None
                    extracted_data = None
                    
                    # Extract content and raw text from the dictionary returned by repository
                    if content_obj and isinstance(content_obj, dict):
                        content_data = content_obj.get("content")
                        raw_text = content_obj.get("raw_text")
                        extracted_data = content_obj.get("extracted_data")
                        
                        # Get the document model to check for claude_file_id
                        document = await self.document_repository.get_document(doc_info["id"])
                        
                        # Create proper document dictionary
                        doc_dict = {
                            "id": doc_info["id"],
                            "title": doc_info.get("filename", "Document"),
                            "type": "document"
                        }
                        
                        # Priority 1: Use claude_file_id for native PDF support (recommended approach)
                        if document and document.claude_file_id:
                            doc_dict["claude_file_id"] = document.claude_file_id
                            doc_dict["filename"] = document.filename
                            document_texts.append(doc_dict)
                            logger.info(f"Added document {doc_info['id']} with Files API file_id: {document.claude_file_id}")
                        
                        # Priority 2: Fallback to raw_text for non-PDF documents only
                        elif raw_text and not (document and document.mime_type == "application/pdf"):
                            doc_dict["raw_text"] = raw_text
                            document_texts.append(doc_dict)
                            logger.info(f"Added non-PDF document {doc_info['id']} with raw_text ({len(raw_text)} chars)")
                        
                        # Priority 3: Binary content for non-PDF documents
                        elif content_data and isinstance(content_data, bytes) and not (document and document.mime_type == "application/pdf"):
                            doc_dict["content"] = content_data
                            document_texts.append(doc_dict)
                            logger.info(f"Added non-PDF document {doc_info['id']} with binary content")
                        
                        # For PDFs without file_id, log a warning (should not happen in new uploads)
                        elif document and document.mime_type == "application/pdf":
                            logger.warning(f"PDF document {doc_info['id']} missing claude_file_id - cannot process with native PDF support")
                        
                        else:
                            logger.warning(f"No usable content available for document {doc_info['id']}")
                except Exception as e:
                    logger.error(f"Error processing document content for LLM: {str(e)}")
                    logger.exception(e)
                    continue
        
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
                    response = await self._process_with_langgraph(
                        conversation_id=conversation_id,
                        content=content,
                        document_texts=document_texts,
                        messages=message_history
                    )
                    return response
                except Exception as e:
                    logger.error(f"Error using LangGraph for simple QA: {str(e)}")
                    logger.info("Falling back to direct Claude API")
                    # Fall through to direct API approach
            
            # Use direct Claude API if LangGraph is not available or failed
            system_prompt = self._build_system_prompt(document_texts, [])
            
            # Generate response
            response_content = await self.claude_service.generate_response(
                system_prompt=system_prompt,
                messages=message_history + [{"role": "user", "content": content}]
            )
            
            # Add assistant message to conversation
            assistant_message = await self.add_message(
                conversation_id=conversation_id,
                content=response_content,
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
            result = await self.claude_service.analyze_with_visualization_tools(
                document_text=combined_doc_text,
                user_query=content,
                file_id=file_id
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
                content=analysis_text,
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
                    "data": chart_item  # Store the entire chart item as data (includes chartType)
                }
                items_for_analysis_blocks.append(processed_chart_item)
            
            # Process tables
            for table_item in tables_data:
                processed_table_item = {
                    "title": table_item.get("config", {}).get("title", "Table"),
                    "visualization_type": "table", # Matches frontend expectations
                    "data": table_item  # Store the entire table item as data
                }
                items_for_analysis_blocks.append(processed_table_item)

            # New: Process metrics
            for metric_item in metrics_data:
                processed_metric_item = {
                    "title": metric_item.get("name", metric_item.get("title", "Metric")), # Use 'name' or 'title'
                    "visualization_type": "metric", # Or "key_figure" - using "metric"
                    "data": metric_item  # Store the entire metric item as data
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
            return await self._process_with_langgraph(
                conversation_id=conversation_id,
                content=content,
                document_texts=document_texts,
                messages=message_history
            )
        
        elif approach == "full_graph":
            # Implement full conversation graph approach here (future)
            logger.info(f"Full graph approach not yet implemented, falling back to citation approach for conversation {conversation_id}")
            return await self._process_with_langgraph(
                conversation_id=conversation_id,
                content=content,
                document_texts=document_texts,
                messages=message_history
            )
        
        else:
            # Unknown approach, fall back to simple QA
            logger.warning(f"Unknown processing approach '{approach}', falling back to simple QA for conversation {conversation_id}")
            system_prompt = self._build_system_prompt(document_texts, [])
            
            # Generate response
            response_content = await self.claude_service.generate_response(
                system_prompt=system_prompt,
                messages=message_history + [{"role": "user", "content": content}]
            )
            
            # Add assistant message to conversation
            assistant_message = await self.add_message(
                conversation_id=conversation_id,
                content=response_content,
                role="assistant"
            )
            
            if not assistant_message:
                raise ValueError("Failed to add assistant message to conversation")
            
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

"""
        
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
                    # Limit to 1000 characters to avoid making the prompt too large
                    text_preview = doc_text[:1000] + "..." if len(doc_text) > 1000 else doc_text
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
        
        # Add visualization instructions
        prompt += """
When you need to create a financial visualization, use the following JSON format and enclose it within triple backticks:
```json
{
  "visualization_type": "chart_type",  // One of: bar, line, pie, area, scatter
  "title": "Chart Title",
  "data": [
    { "name": "Category1", "value": 100 },
    { "name": "Category2", "value": 200 }
  ],
  "x_axis": "X Axis Label",  // For bar, line, area, scatter charts
  "y_axis": "Y Axis Label",  // For bar, line, area, scatter charts
  "insight": "Brief explanation of what this visualization shows"
}
```

When analyzing financial documents, focus on:
1. Key financial metrics (revenue, profit, assets, liabilities, etc.)
2. Year-over-year or quarter-over-quarter trends
3. Financial ratios (profitability, liquidity, solvency, efficiency)
4. Anomalies or significant changes
5. Industry context and benchmarking when possible
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
            await self.conversation_repository.add_analysis_block(
                message_id=message_id,
                block_type=viz.get("visualization_type", "unknown"), # Use the type from the item directly
                title=title,
                content=viz.get("data") # Store the 'data' part of the item
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

Conversation context:{document_context}

{conversation_context}

Generate exactly {limit} follow-up questions, each on a new line, without numbering or bullet points. Make them conversational and specific to the context discussed."""

            # Use Haiku 3.5 for fast, cost-effective follow-up generation
            try:
                follow_up_response = await self.claude_service.generate_response(
                    system_prompt="You are a financial analysis assistant that generates relevant follow-up questions for financial document discussions. Always provide exactly the requested number of questions, each on a separate line.",
                    messages=[{"role": "user", "content": follow_up_prompt}],
                    model="claude-3-5-haiku-20241022",  # Use Haiku 3.5 as specified
                    max_tokens=500,  # Limit tokens since we only need a few questions
                    temperature=0.7  # Slightly creative for varied questions
                )
                
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
            "What are the key risk factors to consider?"
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
                content=response_content,
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