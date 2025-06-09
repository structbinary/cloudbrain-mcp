import sys
import json
from typing import Any, Dict, Optional
from loguru import logger

# Remove default logger
logger.remove()

def serialize_record(record: Dict[str, Any]) -> str:
    """Serialize log record to JSON string."""
    try:
        # Extract basic fields
        log_data = {
            "timestamp": record["time"].isoformat(),
            "level": record["level"].name,
            "message": record["message"],
            "module": record["name"],
            "function": record["function"],
            "line": record["line"]
        }
        
        # Add extra fields if present
        if "extra" in record:
            log_data.update(record["extra"])
            
        return json.dumps(log_data)
    except Exception as e:
        return json.dumps({
            "error": f"Failed to serialize log record: {str(e)}",
            "message": str(record.get("message", ""))
        })

# Configure logger with JSON format
logger.add(
    sys.stdout,
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    level="INFO",
    serialize=False
)

def log_tool_execution(message: str, **kwargs) -> None:
    """
    Log a tool execution event.
    
    Args:
        message: The message to log
        **kwargs: Additional context to include in the log
    """
    logger.bind(event="tool_execution", **kwargs).info(message)

def log_success(message: str, **kwargs) -> None:
    """
    Log a success event.
    
    Args:
        message: The message to log
        **kwargs: Additional context to include in the log
    """
    logger.bind(event="success", status="success", **kwargs).success(message)

def log_api_request(message: str, **kwargs) -> None:
    """
    Log an API request event.
    
    Args:
        message: The message to log
        **kwargs: Additional context to include in the log
    """
    logger.bind(event="api_request", **kwargs).info(message)

def log_command_run(message: str, **kwargs) -> None:
    """
    Log a command run event.
    
    Args:
        message: The message to log
        **kwargs: Additional context to include in the log
    """
    logger.bind(event="command_run", **kwargs).info(message)

def log_browsing(message: str, **kwargs) -> None:
    """
    Log a browsing event.
    
    Args:
        message: The message to log
        **kwargs: Additional context to include in the log
    """
    logger.bind(event="browsing", **kwargs).info(message)

def log_info(
    message: str,
    tool: Optional[str] = None,
    resource: Optional[str] = None,
    status: str = "info",
    event: str = "info",
    **kwargs
) -> None:
    """
    Log an info message with additional context.
    
    Args:
        message: The message to log
        tool: The tool being used
        resource: The resource being operated on
        status: The status of the operation
        event: The type of event
        **kwargs: Additional context to include in the log
    """
    extra = {
        "tool": tool,
        "resource": resource,
        "status": status,
        "event": event,
        **kwargs
    }
    logger.bind(**extra).info(message)

def log_error(
    message: str,
    tool: Optional[str] = None,
    resource: Optional[str] = None,
    error: Optional[str] = None,
    status: str = "error",
    event: str = "error",
    **kwargs
) -> None:
    """
    Log an error message with additional context.
    
    Args:
        message: The message to log
        tool: The tool being used
        resource: The resource being operated on
        error: The error message or exception
        status: The status of the operation
        event: The type of event
        **kwargs: Additional context to include in the log
    """
    extra = {
        "tool": tool,
        "resource": resource,
        "error": error,
        "status": status,
        "event": event,
        **kwargs
    }
    logger.bind(**extra).error(message)

def log_warning(
    message: str,
    tool: Optional[str] = None,
    resource: Optional[str] = None,
    status: str = "warning",
    event: str = "warning",
    **kwargs
) -> None:
    """
    Log a warning message with additional context.
    
    Args:
        message: The message to log
        tool: The tool being used
        resource: The resource being operated on
        status: The status of the operation
        event: The type of event
        **kwargs: Additional context to include in the log
    """
    extra = {
        "tool": tool,
        "resource": resource,
        "status": status,
        "event": event,
        **kwargs
    }
    logger.bind(**extra).warning(message)

def log_debug(
    message: str,
    tool: Optional[str] = None,
    resource: Optional[str] = None,
    status: str = "debug",
    event: str = "debug",
    **kwargs
) -> None:
    """
    Log a debug message with additional context.
    
    Args:
        message: The message to log
        tool: The tool being used
        resource: The resource being operated on
        status: The status of the operation
        event: The type of event
        **kwargs: Additional context to include in the log
    """
    extra = {
        "tool": tool,
        "resource": resource,
        "status": status,
        "event": event,
        **kwargs
    }
    logger.bind(**extra).debug(message)
