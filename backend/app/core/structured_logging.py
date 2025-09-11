"""
Enhanced structured logging configuration for the application.

This module provides a centralized logging configuration with structured
JSON output, context injection, and performance tracking.
"""
import logging
import json
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union
from contextvars import ContextVar
from functools import wraps
import traceback
import asyncio

from pythonjsonlogger import jsonlogger
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint

from app.core.config import settings

# Context variables for request tracking
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id_var: ContextVar[Optional[int]] = ContextVar('user_id', default=None)
organization_id_var: ContextVar[Optional[int]] = ContextVar('organization_id', default=None)
project_id_var: ContextVar[Optional[int]] = ContextVar('project_id', default=None)


class StructuredFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter that includes additional context."""
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        super(StructuredFormatter, self).add_fields(log_record, record, message_dict)
        
        # Add timestamp
        log_record['timestamp'] = datetime.now(timezone.utc).isoformat()
        
        # Add log level
        log_record['level'] = record.levelname
        
        # Add module and function info
        log_record['module'] = record.module
        log_record['function'] = record.funcName
        log_record['line'] = record.lineno
        
        # Add environment
        log_record['environment'] = settings.ENVIRONMENT
        
        # Add context variables if available
        if request_id := request_id_var.get():
            log_record['request_id'] = request_id
        
        if user_id := user_id_var.get():
            log_record['user_id'] = user_id
            
        if org_id := organization_id_var.get():
            log_record['organization_id'] = org_id
            
        if project_id := project_id_var.get():
            log_record['project_id'] = project_id
        
        # Add exception info if present
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)
            log_record['exception_type'] = record.exc_info[0].__name__
        
        # Add custom fields from extra
        if hasattr(record, 'extra_fields'):
            log_record.update(record.extra_fields)


class ContextFilter(logging.Filter):
    """Filter that adds context variables to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get() or 'no-request'
        record.user_id = user_id_var.get() or 'anonymous'
        record.organization_id = organization_id_var.get() or 'no-org'
        record.project_id = project_id_var.get() or 'no-project'
        return True


class PerformanceLogger:
    """Logger for tracking performance metrics."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def log_duration(self, operation: str, duration: float, **kwargs):
        """Log operation duration."""
        self.logger.info(
            f"Performance: {operation}",
            extra={
                'extra_fields': {
                    'performance': {
                        'operation': operation,
                        'duration_ms': round(duration * 1000, 2),
                        **kwargs
                    }
                }
            }
        )
    
    def log_db_query(self, query: str, duration: float, rows_affected: int = 0):
        """Log database query performance."""
        self.logger.info(
            "Database query executed",
            extra={
                'extra_fields': {
                    'database': {
                        'query': query[:200],  # Truncate long queries
                        'duration_ms': round(duration * 1000, 2),
                        'rows_affected': rows_affected
                    }
                }
            }
        )
    
    def log_cache_hit(self, key: str, hit: bool):
        """Log cache hit/miss."""
        self.logger.info(
            f"Cache {'hit' if hit else 'miss'}",
            extra={
                'extra_fields': {
                    'cache': {
                        'key': key,
                        'hit': hit
                    }
                }
            }
        )


def log_execution_time(logger: Optional[logging.Logger] = None):
    """Decorator to log function execution time."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            log = logger or logging.getLogger(func.__module__)
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                log.info(
                    f"Function {func.__name__} executed successfully",
                    extra={
                        'extra_fields': {
                            'execution': {
                                'function': func.__name__,
                                'duration_ms': round(duration * 1000, 2),
                                'success': True
                            }
                        }
                    }
                )
                return result
            except Exception as e:
                duration = time.time() - start_time
                
                log.error(
                    f"Function {func.__name__} failed",
                    extra={
                        'extra_fields': {
                            'execution': {
                                'function': func.__name__,
                                'duration_ms': round(duration * 1000, 2),
                                'success': False,
                                'error': str(e)
                            }
                        }
                    },
                    exc_info=True
                )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            log = logger or logging.getLogger(func.__module__)
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                log.info(
                    f"Function {func.__name__} executed successfully",
                    extra={
                        'extra_fields': {
                            'execution': {
                                'function': func.__name__,
                                'duration_ms': round(duration * 1000, 2),
                                'success': True
                            }
                        }
                    }
                )
                return result
            except Exception as e:
                duration = time.time() - start_time
                
                log.error(
                    f"Function {func.__name__} failed",
                    extra={
                        'extra_fields': {
                            'execution': {
                                'function': func.__name__,
                                'duration_ms': round(duration * 1000, 2),
                                'success': False,
                                'error': str(e)
                            }
                        }
                    },
                    exc_info=True
                )
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance with performance logger attached
    """
    logger = logging.getLogger(name)
    
    # Add performance logger if not already present
    if not hasattr(logger, 'performance'):
        logger.performance = PerformanceLogger(logger.getChild("performance"))
    
    return logger


# Utility functions for structured logging
def log_error(logger: logging.Logger, message: str, error: Exception, **kwargs):
    """Log an error with structured context."""
    logger.error(
        message,
        extra={
            'extra_fields': {
                'error': {
                    'type': type(error).__name__,
                    'message': str(error),
                    'traceback': traceback.format_exc(),
                    **kwargs
                }
            }
        },
        exc_info=True
    )


def log_api_call(
    logger: logging.Logger,
    service: str,
    endpoint: str,
    method: str,
    duration: float,
    status_code: int,
    **kwargs
):
    """Log external API call details."""
    level = logging.INFO if 200 <= status_code < 400 else logging.WARNING
    
    logger.log(
        level,
        f"API call to {service}",
        extra={
            'extra_fields': {
                'api_call': {
                    'service': service,
                    'endpoint': endpoint,
                    'method': method,
                    'duration_ms': round(duration * 1000, 2),
                    'status_code': status_code,
                    **kwargs
                }
            }
        }
    )


def log_business_event(
    logger: logging.Logger,
    event_type: str,
    description: str,
    **kwargs
):
    """Log business events for analytics."""
    logger.info(
        f"Business event: {event_type}",
        extra={
            'extra_fields': {
                'business_event': {
                    'type': event_type,
                    'description': description,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    **kwargs
                }
            }
        }
    )


def log_security_event(
    logger: logging.Logger,
    event_type: str,
    description: str,
    severity: str = "medium",
    **kwargs
):
    """Log security-related events."""
    level = {
        "low": logging.INFO,
        "medium": logging.WARNING,
        "high": logging.ERROR,
        "critical": logging.CRITICAL
    }.get(severity, logging.WARNING)
    
    logger.log(
        level,
        f"Security event: {event_type}",
        extra={
            'extra_fields': {
                'security_event': {
                    'type': event_type,
                    'description': description,
                    'severity': severity,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    **kwargs
                }
            }
        }
    )