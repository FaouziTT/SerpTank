"""
Logging configuration for the Voltex DSE application.

This module sets up structured logging for the application, including
console and file handlers, formatters, and log levels.
"""
import logging
import logging.config
import sys
from pathlib import Path
from typing import Dict, Any

from app.core.config import settings
from app.core.structured_logging import StructuredFormatter, ContextFilter
from app.core.log_aggregation import setup_log_aggregation

# Create logs directory if it doesn't exist
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Log format for structured logging
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def setup_logging() -> None:
    """
    Set up logging configuration for the application.
    
    This function configures logging with console and file handlers,
    sets appropriate log levels, and formats log messages.
    """
    log_config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": LOG_FORMAT,
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "json": {
                "()": "app.core.structured_logging.StructuredFormatter",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "default",
                "level": settings.LOG_LEVEL,
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": LOG_DIR / "voltex.log",
                "maxBytes": 10485760,  # 10 MB
                "backupCount": 5,
                "formatter": "json",
                "level": settings.LOG_LEVEL,
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": LOG_DIR / "error.log",
                "maxBytes": 10485760,  # 10 MB
                "backupCount": 5,
                "formatter": "json",
                "level": "ERROR",
            },
        },
        "loggers": {
            "": {  # Root logger
                "handlers": ["console", "file", "error_file"],
                "level": settings.LOG_LEVEL,
                "propagate": True,
            },
            "uvicorn": {
                "handlers": ["console", "file"],
                "level": settings.LOG_LEVEL,
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["console", "file"],
                "level": settings.LOG_LEVEL,
                "propagate": False,
            },
            "sqlalchemy.engine": {
                "handlers": ["console", "file"],
                "level": "WARNING",
                "propagate": False,
            },
        },
    }
    
    # Apply logging configuration
    logging.config.dictConfig(log_config)
    
    # Add context filter to all handlers
    for handler in logging.getLogger().handlers:
        handler.addFilter(ContextFilter())
    
    # Set up log aggregation
    setup_log_aggregation()
    
    # Log startup message
    logging.getLogger("voltex").info("Logging configured with structured output")