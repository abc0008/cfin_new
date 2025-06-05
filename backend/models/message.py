from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
from pydantic import BaseModel, Field, UUID4, field_serializer, AliasChoices
import logging

from models.citation import Citation, ContentBlock

logger = logging.getLogger(__name__)


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(BaseModel):
    id: UUID4 = Field(default_factory=uuid.uuid4)
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.now, alias="created_at")
    role: MessageRole
    content: str
    referenced_documents: List[str] = Field(default_factory=list)
    referenced_analyses: List[str] = Field(default_factory=list)
    citation_links: List[str] = Field(default_factory=list)
    citations: Optional[List[Citation]] = Field(default_factory=list)
    content_blocks: Optional[List[ContentBlock]] = None
    analysis_blocks: Optional[List[Dict[str, Any]]] = None

    class Config:
        allow_population_by_field_name = True


class ConversationState(BaseModel):
    session_id: str
    active_documents: List[str] = Field(default_factory=list)
    active_analyses: List[str] = Field(default_factory=list)
    current_focus: Optional[str] = None
    user_preferences: Dict[str, Any] = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=datetime.now)
    message_history: List[Dict[str, Any]] = Field(default_factory=list)


class MessageRequest(BaseModel):
    session_id: str
    content: str
    user_id: str = "default-user"
    referenced_documents: List[str] = Field(default_factory=list)
    referenced_analyses: List[str] = Field(default_factory=list)
    citation_links: List[str] = Field(default_factory=list)
    citation_ids: Optional[List[str]] = Field(default_factory=list)


class ConversationCreateRequest(BaseModel):
    title: str
    user_id: str = "default-user"
    document_ids: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class MessageResponse(BaseModel):
    id: str
    session_id: str = Field(validation_alias=AliasChoices('session_id', 'conversation_id'))
    timestamp: datetime = Field(validation_alias=AliasChoices('timestamp', 'created_at'))
    role: MessageRole
    content: str
    referenced_documents: List[str] = Field(default_factory=list)
    referenced_analyses: List[str] = Field(default_factory=list)
    citation_links: List[str] = Field(default_factory=list)
    citations_data: List[Any] = Field(default_factory=list, alias="citations")
    content_blocks: Optional[List[ContentBlock]] = None
    analysis_blocks: Optional[List[Dict[str, Any]]] = None

    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }

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


class ConversationHistoryResponse(BaseModel):
    session_id: str
    messages: List[MessageResponse]
    has_more: bool = False
    next_cursor: Optional[str] = None