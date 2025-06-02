from enum import Enum
from loguru import logger
from mcp.server.fastmcp import Context
from typing import Any
import os
import json
from mcp.types import TextContent

class LogLevel(Enum):
    """Enum for log levels."""
    DEBUG = 'debug'
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'
    CRITICAL = 'critical'


def log_with_request_id(ctx: Context, level: LogLevel, message: str, **kwargs: Any) -> None:
    """
    Log a message with the request ID from the MCP context.

    Args:
        ctx: The MCP context containing the request ID
        level: The log level (from LogLevel enum)
        message: The message to log
        **kwargs: Additional fields to include in the log message
    """
    # Format the log message with request_id
    request_id = getattr(ctx, 'request_id', None)
    log_message = f"[request_id={request_id}] {message}" if request_id else message

    # Log at the appropriate level
    if level == LogLevel.DEBUG:
        logger.debug(log_message, **kwargs)
    elif level == LogLevel.INFO:
        logger.info(log_message, **kwargs)
    elif level == LogLevel.WARNING:
        logger.warning(log_message, **kwargs)
    elif level == LogLevel.ERROR:
        logger.error(log_message, **kwargs)
    elif level == LogLevel.CRITICAL:
        logger.critical(log_message, **kwargs)


def configure_logging_from_env():
    """
    Configure loguru logging level based on FASTMCP_LOG_LEVEL environment variable.
    Defaults to INFO if not set. Accepts: DEBUG, INFO, WARNING, ERROR, CRITICAL (case-insensitive).
    """
    log_level = os.environ.get('FASTMCP_LOG_LEVEL', 'INFO').upper()
    # Remove all existing handlers
    logger.remove()
    # Add a new handler with the desired level
    logger.add(lambda msg: print(msg, end=''), level=log_level)
    logger.info(f"Logging configured. FASTMCP_LOG_LEVEL={log_level}") 