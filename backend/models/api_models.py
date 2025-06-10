from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, Literal

# Utility for camelCase aliasing
def to_camel(string: str) -> str:
    parts = string.split('_')
    return parts[0] + ''.join(word.capitalize() for word in parts[1:]) if len(parts) > 1 else string

class RetryExtractionRequest(BaseModel):
    """
    Request model for retrying document extraction
    """
    extraction_type: Literal["structured_financial_data", "text_only", "tables_only"] = Field(
        "structured_financial_data", 
        alias="extractionType",
        description="Type of extraction to perform"
    )
    options: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional options for extraction"
    )

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True) 