
"""
Application Middleware

This module contains middleware functions for request/response processing,
including timing headers and global exception handling.
"""

import time
import traceback
from logging import getLogger
from typing import Any, Dict
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.exceptions import BaseAPIException, create_error_response

logger = getLogger(__name__)


async def add_process_time_header(request: Request, call_next):
    """Add process time header to response."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    logger.info("Request processed in %s seconds", process_time)
    return response


class GlobalExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """
    Global exception handler middleware to ensure consistent error responses.
    
    This middleware catches all exceptions and transforms them into
    standardized error responses.
    """
    
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except BaseAPIException as exc:
            # Handle custom API exceptions
            return JSONResponse(
                status_code=exc.status_code,
                content=create_error_response(
                    error_code=exc.error_code,
                    message=exc.detail,
                    status_code=exc.status_code,
                    details=getattr(exc, 'errors', None)
                ),
                headers=exc.headers
            )
        except Exception as exc:
            # Log unexpected exceptions
            logger.error(
                f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
                exc_info=True,
                extra={
                    "request_path": request.url.path,
                    "request_method": request.method,
                    "traceback": traceback.format_exc()
                }
            )
            
            # Return generic error response
            return JSONResponse(
                status_code=500,
                content=create_error_response(
                    error_code="INTERNAL_SERVER_ERROR",
                    message="An unexpected error occurred",
                    status_code=500
                )
            )
