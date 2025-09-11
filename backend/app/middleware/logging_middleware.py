"""
Request/Response logging middleware for FastAPI.

This middleware logs all incoming requests and outgoing responses
with structured context and performance metrics.
"""
import time
import uuid
import json
from typing import Callable, Optional
from datetime import datetime, timezone

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint

from app.core.structured_logging import (
    get_logger, 
    request_id_var, 
    user_id_var,
    organization_id_var,
    project_id_var
)

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses."""
    
    def __init__(self, app, exclude_paths: Optional[list] = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/health", "/metrics", "/docs", "/openapi.json"]
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip logging for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Generate request ID
        request_id = str(uuid.uuid4())
        request_id_var.set(request_id)
        
        # Extract user context from request if available
        user_id = None
        org_id = None
        project_id = None
        
        if hasattr(request.state, "user"):
            user_id = getattr(request.state.user, "id", None)
            org_id = getattr(request.state.user, "organization_id", None)
            user_id_var.set(user_id)
            organization_id_var.set(org_id)
        
        # Extract project_id from path parameters or query
        if "project_id" in request.path_params:
            project_id = request.path_params["project_id"]
            project_id_var.set(project_id)
        elif "project_id" in request.query_params:
            project_id = request.query_params["project_id"]
            project_id_var.set(project_id)
        
        # Log request
        start_time = time.time()
        request_body = None
        
        # Only log body for certain content types and methods
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                try:
                    body = await request.body()
                    request_body = json.loads(body) if body else None
                    # Don't log sensitive fields
                    if request_body and isinstance(request_body, dict):
                        sensitive_fields = ["password", "token", "secret", "api_key"]
                        request_body = {
                            k: "[REDACTED]" if k.lower() in sensitive_fields else v
                            for k, v in request_body.items()
                        }
                except Exception:
                    request_body = "[Failed to parse body]"
        
        logger.info(
            f"Request: {request.method} {request.url.path}",
            extra={
                'extra_fields': {
                    'request': {
                        'method': request.method,
                        'path': request.url.path,
                        'query_params': dict(request.query_params),
                        'headers': dict(request.headers),
                        'body': request_body,
                        'client_host': request.client.host if request.client else None,
                        'user_agent': request.headers.get("user-agent"),
                        'request_id': request_id,
                        'user_id': user_id,
                        'organization_id': org_id,
                        'project_id': project_id
                    }
                }
            }
        )
        
        # Call the actual endpoint
        response = None
        error_details = None
        
        try:
            response = await call_next(request)
            
            # Read response body
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk
            
            # Create new response with the same body
            response = Response(
                content=response_body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
        except Exception as e:
            error_details = {
                "type": type(e).__name__,
                "message": str(e)
            }
            logger.error(
                f"Request failed: {request.method} {request.url.path}",
                extra={
                    'extra_fields': {
                        'request_error': error_details
                    }
                },
                exc_info=True
            )
            raise
        finally:
            # Calculate request duration
            duration = time.time() - start_time
            
            # Log response
            if response:
                # Parse response body for logging (if JSON)
                response_data = None
                if response.media_type == "application/json" and response.status_code < 500:
                    try:
                        response_data = json.loads(response_body)
                        # Truncate large responses
                        if isinstance(response_data, dict) and "items" in response_data:
                            if isinstance(response_data["items"], list) and len(response_data["items"]) > 10:
                                response_data["items"] = response_data["items"][:10] + ["[truncated]"]
                    except Exception:
                        response_data = "[Failed to parse response]"
                
                log_level = logger.info if response.status_code < 400 else logger.warning
                
                log_level(
                    f"Response: {response.status_code} {request.method} {request.url.path}",
                    extra={
                        'extra_fields': {
                            'response': {
                                'status_code': response.status_code,
                                'headers': dict(response.headers),
                                'body': response_data,
                                'duration_ms': round(duration * 1000, 2),
                                'request_id': request_id
                            }
                        }
                    }
                )
                
                # Log performance metrics
                logger.performance.log_duration(
                    f"{request.method} {request.url.path}",
                    duration,
                    status_code=response.status_code,
                    user_id=user_id
                )
            
            # Clear context variables
            request_id_var.set(None)
            user_id_var.set(None)
            organization_id_var.set(None)
            project_id_var.set(None)
        
        return response


class APICallLoggingMiddleware:
    """Middleware for logging external API calls."""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = get_logger(f"api.{service_name}")
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Log outgoing API request
        self.logger.info(
            f"API Request to {self.service_name}",
            extra={
                'extra_fields': {
                    'api_request': {
                        'service': self.service_name,
                        'method': request.method,
                        'url': str(request.url),
                        'headers': dict(request.headers)
                    }
                }
            }
        )
        
        # Make the request
        response = await call_next(request)
        duration = time.time() - start_time
        
        # Log API response
        self.logger.info(
            f"API Response from {self.service_name}",
            extra={
                'extra_fields': {
                    'api_response': {
                        'service': self.service_name,
                        'status_code': response.status_code,
                        'duration_ms': round(duration * 1000, 2),
                        'headers': dict(response.headers)
                    }
                }
            }
        )
        
        return response