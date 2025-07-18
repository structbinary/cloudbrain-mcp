from typing import TypeVar, Generic, Optional, List, Dict
from pydantic import BaseModel, Field
from pydantic.generics import GenericModel

T = TypeVar("T")

class Meta(BaseModel):
    """
    Optional metadata for API responses (e.g., pagination, request info).
    Extend as needed for future requirements.
    """
    page: Optional[int] = None
    per_page: Optional[int] = None
    total: Optional[int] = None
    request_id: Optional[str] = None

class ApiResponse(GenericModel, Generic[T]):
    """
    Generic API response wrapper for success and error cases.
    status: 'success' or 'error'
    data: payload of type T (optional)
    message: optional context message
    meta: optional metadata (pagination, request info, etc.)
    """
    status: str = Field(..., description="Status of the response, e.g., 'success' or 'error'")
    data: Optional[T] = Field(None, description="Payload data")
    message: Optional[str] = Field(None, description="Optional message for context")
    meta: Optional[Meta] = Field(None, description="Optional metadata (pagination, request info, etc.)")

class ErrorResponse(BaseModel):
    """
    Standardized error response model for all API endpoints.

    Fields:
        status: Always 'error'.
        error_code: Optional machine-readable error code (e.g., 'validation_error', 'not_found', 'unauthorized', 'internal_error').
        message: Human-readable error message for clients.
        details: Optional extra information (e.g., validation errors, stack traces in debug mode).
        meta: Optional metadata (e.g., request ID, timestamp).

    Usage:
        - Use for all error responses in API endpoints.
        - Map custom exceptions to this model for consistent error handling.

    Example:
        ErrorResponse(
            status='error',
            error_code='not_found',
            message='Agent card not found',
            details={'agent_id': 'abc123'}
        )
    """
    status: str = Field(default="error", description="Status of the response, always 'error'")
    error_code: Optional[str] = None
    message: str
    details: Optional[Dict] = None
    meta: Optional[Meta] = None

# Optional: Utility function for converting exceptions to ErrorResponse

def exception_to_error_response(exc: Exception, error_code: Optional[str] = None, meta: Optional[Meta] = None) -> ErrorResponse:
    """
    Convert an exception to a standardized ErrorResponse.
    Args:
        exc: The exception instance.
        error_code: Optional error code string.
        meta: Optional Meta object for additional metadata.
    Returns:
        ErrorResponse instance.
    """
    return ErrorResponse(
        error_code=error_code or exc.__class__.__name__,
        message=str(exc),
        details=getattr(exc, 'details', None),
        meta=meta
    )

class PaginatedResponse(GenericModel, Generic[T]):
    """
    API response model for paginated results.
    status: response status
    data: list of items of type T
    total: total number of items
    page: current page number
    size: number of items per page
    meta: optional metadata (pagination, request info, etc.)
    """
    status: str
    data: List[T]
    total: int
    page: int
    size: int
    meta: Optional[Meta] = None

# --- Specialized API Response Type Aliases ---
# Import domain models (assume these exist in the models directory)
from .agent_card import AgentCard
from .mcp_server import MCPServer

# Single object responses
AgentCardResponse = ApiResponse[AgentCard]
MCPServerResponse = ApiResponse[MCPServer]

# List responses
AgentCardListResponse = ApiResponse[List[AgentCard]]
MCPServerListResponse = ApiResponse[List[MCPServer]]

# Paginated responses
PaginatedAgentCardResponse = PaginatedResponse[AgentCard]
PaginatedMCPServerResponse = PaginatedResponse[MCPServer]

"""
Usage examples:
- Use AgentCardResponse for /agent_cards/{agent_id}
- Use AgentCardListResponse for /agent_cards
- Use PaginatedAgentCardResponse for paginated agent card endpoints
- Use ErrorResponse for error cases
""" 