"""
Standard error response models for API endpoints.
"""
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, ConfigDict

# Utility for camelCase aliasing
def to_camel(string: str) -> str:
    parts = string.split('_')
    return parts[0] + ''.join(word.capitalize() for word in parts[1:]) if len(parts) > 1 else string

class ValidationErrorDetail(BaseModel):
    """Detailed validation error for a specific field."""
    loc: List[Union[str, int]] = Field(
        ..., 
        description="Location of the error (field path)"
    )
    msg: str = Field(..., description="Error message")
    type: str = Field(..., description="Error type")

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

class ErrorResponse(BaseModel):
    """Standard error response model for all API endpoints."""
    status_code: int = Field(..., alias="statusCode", description="HTTP status code")
    detail: Union[str, List[ValidationErrorDetail], Dict[str, Any]] = Field(
        ...,
        description="Error details - can be a string message, validation errors array, or structured data"
    )
    error_type: Optional[str] = Field(
        None, 
        alias="errorType",
        description="Optional error type for categorization (not_found, validation_error, etc.)"
    )
    
    model_config = ConfigDict(
        alias_generator=to_camel, 
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "statusCode": 404,
                "detail": "Resource not found",
                "errorType": "not_found"
            }
        }
    )


def create_error_response(
    status_code: int, 
    detail: Union[str, List[ValidationErrorDetail], Dict[str, Any]],
    error_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a standardized error response dictionary.
    
    Args:
        status_code: HTTP status code
        detail: Error details (string, validation errors, or structured data)
        error_type: Optional error type for categorization
        
    Returns:
        Dictionary with standardized error format
    """
    return ErrorResponse(
        status_code=status_code,
        detail=detail,
        error_type=error_type
    ).model_dump(by_alias=True)
