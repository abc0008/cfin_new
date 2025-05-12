"""
Database Models Module
=====================

This module defines the SQLAlchemy ORM models for the CFIN financial analysis platform's database schema.
It provides the core data structures for users, documents, citations, conversations, messages, and analysis results.
These models are used throughout the backend for all database operations and are the foundation for repository and service layers.

Primary responsibilities:
- Define the database schema for all core entities (users, documents, citations, conversations, messages, analysis results)
- Provide relationships between entities (e.g., documents to users, citations to documents, messages to conversations)
- Enumerate document types and processing statuses for consistent use across the application

Key Components:
- User: Model for user authentication and ownership of documents/conversations
- Document: Model for uploaded financial documents and their metadata/content
- Citation: Model for document citations, including page, text, and bounding box
- Message: Model for conversation messages, including content and citations
- Conversation: Model for chat sessions between users and the AI assistant
- AnalysisResult: Model for storing results of financial analyses
- AnalysisBlock: Model for storing analysis blocks (charts, insights, etc.) attached to messages
- ConversationDocument, MessageCitation: Association tables for many-to-many relationships
- DocumentType, ProcessingStatusEnum: Enums for document classification and processing state

Interactions with other files:
-----------------------------
1. cfin/backend/repositories/document_repository.py:
   - Uses Document, Citation, User, DocumentType, ProcessingStatusEnum for all document and citation CRUD operations
   - Converts ORM models to Pydantic models for API responses

2. cfin/backend/repositories/conversation_repository.py:
   - Uses Conversation, Message, MessageCitation, ConversationDocument for managing conversations and messages

3. cfin/backend/repositories/analysis_repository.py:
   - Uses AnalysisResult and AnalysisBlock for storing and retrieving analysis data

4. cfin/backend/services/conversation_service.py:
   - Uses Message, Conversation, Document, Citation, AnalysisBlock, User for orchestrating conversation logic

5. cfin/backend/pdf_processing/claude_service.py:
   - Uses DocumentType, ProcessingStatusEnum for document processing and status tracking

6. cfin/backend/pdf_processing/document_service.py:
   - Uses Document, Citation, DocumentType, ProcessingStatusEnum for document upload and processing

7. cfin/backend/pdf_processing/langgraph_service.py:
   - Uses Document, Citation, Message, Conversation for managing conversational state and document Q&A

8. cfin/backend/create_db.py:
   - Imports all models to create and initialize the database schema

9. cfin/backend/utils/database.py:
   - Provides the Base class for all ORM models and manages the database engine/session

These models are the backbone of the backend application, ensuring consistent data structure and relationships across all services and repositories.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON, Boolean, Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
import enum
from typing import List, Dict, Any, Optional

from utils.database import Base


class DocumentType(enum.Enum):
    BALANCE_SHEET = "balance_sheet"
    INCOME_STATEMENT = "income_statement"
    CASH_FLOW = "cash_flow"
    NOTES = "notes"
    OTHER = "other"


class ProcessingStatusEnum(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


def generate_uuid():
    return str(uuid.uuid4())


class User(Base):
    """User model for authentication."""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    documents = relationship("Document", back_populates="user")
    conversations = relationship("Conversation", back_populates="user")


class Document(Base):
    """Document model for storing uploaded financial documents."""
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)  # Path or URL to the stored file
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String, nullable=False)
    upload_timestamp = Column(DateTime, default=datetime.utcnow)
    user_id = Column(String, ForeignKey("users.id"))
    
    # Document processing fields
    document_type = Column(SQLAlchemyEnum(DocumentType), default=DocumentType.OTHER)
    processing_status = Column(SQLAlchemyEnum(ProcessingStatusEnum), default=ProcessingStatusEnum.PENDING)
    processing_timestamp = Column(DateTime)
    extraction_timestamp = Column(DateTime)
    confidence_score = Column(Float, default=0.0)
    error_message = Column(Text)
    
    # Document content
    raw_text = Column(Text)
    periods = Column(JSON, default=lambda: [])
    extracted_data = Column(JSON, default=lambda: {})
    
    # Relationships
    user = relationship("User", back_populates="documents")
    citations = relationship("Citation", back_populates="document", cascade="all, delete-orphan")
    analysis_results = relationship("AnalysisResult", back_populates="document")
    conversations = relationship(
        "Conversation", 
        secondary="conversation_documents",
        back_populates="documents",
        primaryjoin="Document.id == ConversationDocument.document_id",
        secondaryjoin="ConversationDocument.conversation_id == Conversation.id"
    )


class Citation(Base):
    """Citation model for storing document citations."""
    __tablename__ = "citations"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    page = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    section = Column(String)
    bounding_box = Column(JSON)  # JSON object with coordinates
    
    # Relationships
    document = relationship("Document", back_populates="citations")
    messages = relationship("MessageCitation", back_populates="citation")


class MessageCitation(Base):
    """Many-to-many relationship between messages and citations."""
    __tablename__ = "message_citations"
    
    message_id = Column(String, ForeignKey("messages.id"), primary_key=True)
    citation_id = Column(String, ForeignKey("citations.id"), primary_key=True)
    
    # Relationships
    message = relationship("Message", back_populates="citations")
    citation = relationship("Citation", back_populates="messages")


class Conversation(Base):
    """Conversation model for storing chat interactions."""
    __tablename__ = "conversations"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String, nullable=False)
    user_id = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    documents = relationship(
        "Document", 
        secondary="conversation_documents",
        back_populates="conversations",
        primaryjoin="Conversation.id == ConversationDocument.conversation_id",
        secondaryjoin="ConversationDocument.document_id == Document.id"
    )


class ConversationDocument(Base):
    """Many-to-many relationship between conversations and documents."""
    __tablename__ = "conversation_documents"
    
    conversation_id = Column(String, ForeignKey("conversations.id"), primary_key=True)
    document_id = Column(String, ForeignKey("documents.id"), primary_key=True)


class Message(Base):
    """Message model for storing conversation messages."""
    __tablename__ = "messages"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    content = Column(Text, nullable=False)
    role = Column(String, nullable=False)  # "user" or "assistant"
    created_at = Column(DateTime, default=datetime.utcnow)
    content_blocks = Column(JSON)  # Store structured content blocks from Claude API
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    citations = relationship("MessageCitation", back_populates="message")
    analysis_blocks = relationship("AnalysisBlock", back_populates="message", cascade="all, delete-orphan")


class AnalysisResult(Base):
    """Analysis result model for storing document analysis results."""
    __tablename__ = "analysis_results"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    analysis_type = Column(String, nullable=False)  # e.g., "financial_ratios", "sentiment", etc.
    result_data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    document = relationship("Document", back_populates="analysis_results")


class AnalysisBlock(Base):
    """Analysis block model for storing message-related analysis blocks."""
    __tablename__ = "analysis_blocks"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    message_id = Column(String, ForeignKey("messages.id"), nullable=False)
    block_type = Column(String, nullable=False)  # e.g., "chart", "insight", etc.
    title = Column(String)
    content = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    message = relationship("Message", back_populates="analysis_blocks")