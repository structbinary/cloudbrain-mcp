from typing import Optional

class CloudbrainMCPError(Exception):
    """
    Base exception for all Cloudbrain MCP Server errors.
    Optionally accepts a details dictionary for extra context.

    Example:
        raise CloudbrainMCPError("A generic error occurred.", details={"info": "context"})
    """
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message)
        self.details = details

class AgentCardError(CloudbrainMCPError):
    """
    Exception raised for errors related to agent cards.
    Example:
        raise AgentCardError("Agent card not found.", details={"agent_id": "abc123"})
    """
    pass

class MCPServerError(CloudbrainMCPError):
    """
    Exception raised for errors related to MCP servers.
    Example:
        raise MCPServerError("MCP server connection failed.", details={"server_id": "srv001"})
    """
    pass

class ValidationError(CloudbrainMCPError):
    """
    Exception raised for data validation errors.
    Example:
        raise ValidationError("Invalid data format.", details={"field": "version"})
    """
    pass

class ResourceNotFoundError(CloudbrainMCPError):
    """
    Exception raised when a requested resource is not found.
    Example:
        raise ResourceNotFoundError("Resource not found.", details={"resource": "agent_card", "id": "abc123"})
    """
    pass

"""
Usage Example:
    try:
        # ... some operation ...
        raise AgentCardError("Agent card missing.", details={"agent_id": "abc123"})
    except CloudbrainMCPError as e:
        print(f"Error: {e}")
        if e.details:
            print(f"Details: {e.details}")
""" 