from enum import Enum
from typing import List, Optional, Union, Literal
from pydantic import BaseModel, Field, ConfigDict

# Utility for camelCase aliasing
def to_camel(string: str) -> str:
    parts = string.split('_')
    return parts[0] + ''.join(word.capitalize() for word in parts[1:]) if len(parts) > 1 else string

class CitationType(str, Enum):
    CHAR_LOCATION = "char_location"
    PAGE_LOCATION = "page_location"
    CONTENT_BLOCK_LOCATION = "content_block_location"

class CitationBase(BaseModel):
    """Base class for all citation types."""
    type: CitationType
    cited_text: str = Field(..., alias="citedText")
    document_index: int = Field(..., alias="documentIndex")
    document_title: str = Field(..., alias="documentTitle")

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

class CharLocationCitation(CitationBase):
    """Citation for plain text documents."""
    type: Literal[CitationType.CHAR_LOCATION] = CitationType.CHAR_LOCATION
    start_char_index: int = Field(..., alias="startCharIndex")
    end_char_index: int = Field(..., alias="endCharIndex")

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

class PageLocationCitation(CitationBase):
    """Citation for PDF documents."""
    type: Literal[CitationType.PAGE_LOCATION] = CitationType.PAGE_LOCATION
    start_page_number: int = Field(..., alias="startPageNumber")
    end_page_number: int = Field(..., alias="endPageNumber")

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

class ContentBlockLocationCitation(CitationBase):
    """Citation for custom content documents."""
    type: Literal[CitationType.CONTENT_BLOCK_LOCATION] = CitationType.CONTENT_BLOCK_LOCATION
    start_block_index: int = Field(..., alias="startBlockIndex")
    end_block_index: int = Field(..., alias="endBlockIndex")

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

# Generic Citation type that could be any of the specific citation types
Citation = Union[CharLocationCitation, PageLocationCitation, ContentBlockLocationCitation]

class ContentBlock(BaseModel):
    """Model for a content block in Claude's response."""
    type: Literal["text"] = "text"
    text: str
    citations: Optional[List[Citation]] = None

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

class AnthropicMessage(BaseModel):
    """Model for a message in Claude's response."""
    content: List[ContentBlock]

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True) 