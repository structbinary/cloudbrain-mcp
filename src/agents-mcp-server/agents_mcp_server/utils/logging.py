import logging
import sys
from typing import Optional
from logging.handlers import RotatingFileHandler

def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_to_file: Optional[str] = None,
    file_level: Optional[int] = None,
    fmt: str = "%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt: str = "%Y-%m-%dT%H:%M:%S%z"
) -> logging.Logger:
    """
    Configure and return a logger with the given name and level.
    Prevents duplicate handlers and supports console/file output.

    Args:
        name: Logger name (usually __name__ or project/module name).
        level: Log level for the logger and console handler (default: INFO).
        log_to_file: Optional file path for file logging (default: None).
        file_level: Optional log level for file handler (default: same as level).
        fmt: Log message format string.
        datefmt: Date/time format string.
    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.handlers:
        # Console handler
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(level)
        formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
        # Optional file handler
        if log_to_file:
            file_handler = RotatingFileHandler(
                log_to_file, maxBytes=10**6, backupCount=3
            )
            file_handler.setLevel(file_level or level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
    return logger

# Default project logger
logger = setup_logger('agents_mcp_server')

"""
Usage Example:
    from agents_mcp_server.utils.logging import setup_logger
    logger = setup_logger(__name__, level=logging.DEBUG)
    logger.info("Logger initialized!")
""" 