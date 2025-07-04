from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
from pydantic import BaseModel, Field, UUID4, field_serializer, field_validator, AliasChoices, ConfigDict
import logging

from models.citation import Citation, ContentBlock

logger = logging.getLogger(__name__)

# Utility for camelCase aliasing
def to_camel(string: str) -> str:
    parts = string.split('_')
    return parts[0] + ''.join(word.capitalize() for word in parts[1:]) if len(parts) > 1 else string


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(BaseModel):
    id: UUID4 = Field(default_factory=uuid.uuid4)
    session_id: str = Field(alias="sessionId")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    role: MessageRole
    content: str
    referenced_documents: List[str] = Field(default_factory=list, alias="referencedDocuments")
    referenced_analyses: List[str] = Field(default_factory=list, alias="referencedAnalyses")
    citation_links: List[str] = Field(default_factory=list, alias="citationLinks")
    citations: Optional[List[Citation]] = Field(default_factory=list)
    content_blocks: Optional[List[ContentBlock]] = Field(default=None, alias="contentBlocks")
    analysis_blocks: Optional[List[Dict[str, Any]]] = Field(default=None, alias="analysisBlocks")
    follow_up_questions: Optional[List[str]] = Field(default=None, alias="followUpQuestions")

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    @field_serializer('timestamp', when_used='always')
    def serialize_timestamp(self, timestamp: datetime) -> str:
        """Ensure timestamp is serialized as UTC with Z suffix"""
        if timestamp.tzinfo is None:
            # Assume it's UTC if no timezone info
            timestamp = timestamp.replace(tzinfo=None)
        return timestamp.isoformat() + 'Z' if not timestamp.isoformat().endswith('Z') else timestamp.isoformat()


class ConversationState(BaseModel):
    session_id: str = Field(alias="sessionId")
    active_documents: List[str] = Field(default_factory=list, alias="activeDocuments")
    active_analyses: List[str] = Field(default_factory=list, alias="activeAnalyses")
    current_focus: Optional[str] = Field(default=None, alias="currentFocus")
    user_preferences: Dict[str, Any] = Field(default_factory=dict, alias="userPreferences")
    last_updated: datetime = Field(default_factory=datetime.utcnow, alias="lastUpdated")
    message_history: List[Dict[str, Any]] = Field(default_factory=list, alias="messageHistory")
    
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    @field_serializer('last_updated', when_used='always')
    def serialize_last_updated(self, timestamp: datetime) -> str:
        """Ensure timestamp is serialized as UTC with Z suffix"""
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=None)
        return timestamp.isoformat() + 'Z' if not timestamp.isoformat().endswith('Z') else timestamp.isoformat()


class MessageRequest(BaseModel):
    session_id: str = Field(alias="sessionId")
    content: str
    user_id: str = Field(default="default-user", alias="userId")
    referenced_documents: List[str] = Field(default_factory=list, alias="referencedDocuments")
    referenced_analyses: List[str] = Field(default_factory=list, alias="referencedAnalyses")
    citation_links: List[str] = Field(default_factory=list, alias="citationLinks")
    citation_ids: Optional[List[str]] = Field(default_factory=list, alias="citationIds")
    
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ConversationCreateRequest(BaseModel):
    title: str
    user_id: str = Field(default="default-user", alias="userId")
    document_ids: Optional[List[str]] = Field(default=None, alias="documentIds")
    metadata: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class MessageResponse(BaseModel):
    id: str
    session_id: str = Field(alias="sessionId", validation_alias=AliasChoices('session_id', 'conversation_id'))
    timestamp: datetime = Field(validation_alias=AliasChoices('timestamp', 'created_at'))
    role: MessageRole
    content: str
    referenced_documents: List[str] = Field(default_factory=list, alias="referencedDocuments")
    referenced_analyses: List[str] = Field(default_factory=list, alias="referencedAnalyses")
    citation_links: List[str] = Field(default_factory=list, alias="citationLinks")
    citations_data: List[Any] = Field(default_factory=list, alias="citations")
    content_blocks: Optional[List[ContentBlock]] = Field(default=None, alias="contentBlocks")
    analysis_blocks: Optional[List[Dict[str, Any]]] = Field(default=None, alias="analysisBlocks")
    follow_up_questions: Optional[List[str]] = Field(default=None, alias="followUpQuestions")

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True
    )

    @field_serializer('timestamp', when_used='always')
    def serialize_timestamp(self, timestamp: datetime) -> str:
        """Ensure timestamp is serialized as UTC with Z suffix"""
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=None)
        return timestamp.isoformat() + 'Z' if not timestamp.isoformat().endswith('Z') else timestamp.isoformat()

    @field_serializer('citations_data', when_used='always')
    def serialize_citations_data(self, v: Optional[List[Any]]) -> List[Citation]:
        if not v:
            return []
        processed_citations = []
        for message_citation_orm in v:
            if hasattr(message_citation_orm, 'citation') and message_citation_orm.citation:
                try:
                    citation_pydantic = Citation.model_validate(message_citation_orm.citation, from_attributes=True)
                    processed_citations.append(citation_pydantic)
                except Exception as e:
                    logger.warning(f"Error validating citation: {e} for {getattr(message_citation_orm.citation, 'id', 'unknown ID')}")
                    pass
        return processed_citations

    @field_validator('analysis_blocks', mode='before')
    @classmethod
    def validate_analysis_blocks(cls, v: Any) -> List[Dict[str, Any]]:
        """Convert ORM objects to dictionaries before validation."""
        if not v:
            return []
        
        processed_blocks = []
        for analysis_block_orm in v:
            try:
                # Convert ORM object to dictionary
                if hasattr(analysis_block_orm, '__dict__'):
                    # Handle datetime serialization more safely
                    created_at_str = None
                    if hasattr(analysis_block_orm, 'created_at') and analysis_block_orm.created_at:
                        try:
                            created_at_str = analysis_block_orm.created_at.isoformat()
                        except Exception:
                            created_at_str = str(analysis_block_orm.created_at)
                    
                    block_dict = {
                        'id': getattr(analysis_block_orm, 'id', ''),
                        'block_type': getattr(analysis_block_orm, 'block_type', ''),
                        'title': getattr(analysis_block_orm, 'title', ''),
                        'content': getattr(analysis_block_orm, 'content', {}),
                        'created_at': created_at_str
                    }
                    processed_blocks.append(block_dict)
                elif isinstance(analysis_block_orm, dict):
                    # If it's already a dictionary, use it as-is
                    processed_blocks.append(analysis_block_orm)
                else:
                    logger.warning(f"Unexpected analysis block type: {type(analysis_block_orm)}")
            except Exception as e:
                logger.warning(f"Error converting analysis block: {e} for {getattr(analysis_block_orm, 'id', 'unknown ID')}")
                # Don't fail completely, just skip this block
                continue
        return processed_blocks


class ConversationHistoryResponse(BaseModel):
    session_id: str = Field(alias="sessionId")
    messages: List[MessageResponse]
    has_more: bool = Field(default=False, alias="hasMore")
    next_cursor: Optional[str] = Field(default=None, alias="nextCursor")
    
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)