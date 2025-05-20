from typing import Union, Optional

class ToolSchemaValidationError(ValueError):
    """Custom exception for tool input/output schema validation errors."""
    def __init__(self, message: str, original_exception: Union[Exception, None] = None):
        super().__init__(message)
        self.original_exception = original_exception 