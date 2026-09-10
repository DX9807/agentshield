"""Structured logging configuration."""

import logging
import sys
from typing import Optional, Dict, Any
import structlog
from structlog.types import Processor
from structlog.processors import (
    TimeStamper,
    add_log_level,
    format_exc_info,
    JSONRenderer,
    KeyValueRenderer,
)
from .config import settings


def setup_logging() -> None:
    """Configure structured logging."""
    
    # Determine processors based on environment
    processors: list[Processor] = [
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.stdlib.ExtraAdder(),
        TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    if settings.LOG_JSON_FORMAT:
        # JSON format for production
        processors.append(JSONRenderer())
    else:
        # Human-readable format for development
        processors.append(
            structlog.dev.ConsoleRenderer(
                colors=settings.APP_ENV == "development"
            )
        )
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard logging
    log_level = getattr(logging, settings.LOG_LEVEL)
    logging.basicConfig(
        format=settings.LOG_FORMAT,
        level=log_level,
        stream=sys.stdout,
    )
    
    # Silence noisy loggers
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    
    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove default handlers if they exist
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add our handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    root_logger.addHandler(handler)


def get_logger(name: Optional[str] = None) -> structlog.stdlib.BoundLogger:
    """Get a structured logger."""
    if name:
        return structlog.get_logger(name)
    return structlog.get_logger()


# Create a default logger
logger = get_logger("agentshield")