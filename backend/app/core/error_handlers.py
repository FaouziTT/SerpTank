"""
RFC 7807 Problem Details for HTTP APIs Implementation

This module provides RFC 7807 compliant error responses for better
API error standardization and frontend compatibility.
"""

from typing import Any, Dict, Optional, List, Union
from datetime import datetime
from pydantic import BaseModel, Field
from fastapi import Request
from fastapi.responses import JSONResponse


class ProblemDetail(BaseModel):
    """
    RFC 7807 Problem Details model.
    
    See: https://datatracker.ietf.org/doc/html/rfc7807
    """
    type: str = Field(
        ..., 
        description="A URI reference that identifies the problem type"
    )
    title: str = Field(
        ..., 
        description="A short, human-readable summary of the problem type"
    )
    status: int = Field(
        ..., 
        description="The HTTP status code"
    )
    detail: Optional[str] = Field(
        None, 
        description="A human-readable explanation specific to this occurrence"
    )
    instance: Optional[str] = Field(
        None, 
        description="A URI reference that identifies the specific occurrence"
    )
    
    # Additional fields for enhanced error information
    timestamp: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        description="When the error occurred"
    )
    errors: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error details (e.g., validation errors)"
    )
    correlation_id: Optional[str] = Field(
        None,
        description="Correlation ID for tracking"
    )
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# Standard problem types
class ProblemTypes:
    """Standard problem type URIs for common errors."""
    
    # Base URI for problem types
    BASE_URI = "https://api.voltex.ai/problems"
    
    # Authentication & Authorization
    INVALID_CREDENTIALS = f"{BASE_URI}/invalid-credentials"
    TOKEN_EXPIRED = f"{BASE_URI}/token-expired"
    TOKEN_INVALID = f"{BASE_URI}/token-invalid"
    INSUFFICIENT_PERMISSIONS = f"{BASE_URI}/insufficient-permissions"
    ACCOUNT_DISABLED = f"{BASE_URI}/account-disabled"
    ACCOUNT_LOCKED = f"{BASE_URI}/account-locked"
    
    # Validation
    VALIDATION_ERROR = f"{BASE_URI}/validation-error"
    INVALID_REQUEST = f"{BASE_URI}/invalid-request"
    
    # Resources
    RESOURCE_NOT_FOUND = f"{BASE_URI}/resource-not-found"
    RESOURCE_ALREADY_EXISTS = f"{BASE_URI}/resource-already-exists"
    RESOURCE_CONFLICT = f"{BASE_URI}/resource-conflict"
    
    # Rate Limiting & Quotas
    RATE_LIMIT_EXCEEDED = f"{BASE_URI}/rate-limit-exceeded"
    QUOTA_EXCEEDED = f"{BASE_URI}/quota-exceeded"
    
    # External Services
    EXTERNAL_SERVICE_ERROR = f"{BASE_URI}/external-service-error"
    SERVICE_UNAVAILABLE = f"{BASE_URI}/service-unavailable"
    
    # Business Logic
    INVALID_OPERATION = f"{BASE_URI}/invalid-operation"
    PAYMENT_REQUIRED = f"{BASE_URI}/payment-required"
    
    # System Errors
    INTERNAL_ERROR = f"{BASE_URI}/internal-error"
    DATABASE_ERROR = f"{BASE_URI}/database-error"


def create_problem_response(
    request: Request,
    problem_type: str,
    title: str,
    status: int,
    detail: Optional[str] = None,
    errors: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None
) -> JSONResponse:
    """
    Create an RFC 7807 compliant problem response.
    
    Args:
        request: The current request
        problem_type: URI identifying the problem type
        title: Short summary of the problem
        status: HTTP status code
        detail: Specific details about this occurrence
        errors: Additional error information
        headers: Additional response headers
        
    Returns:
        JSONResponse with problem details
    """
    problem = ProblemDetail(
        type=problem_type,
        title=title,
        status=status,
        detail=detail,
        instance=str(request.url),
        errors=errors,
        correlation_id=getattr(request.state, "correlation_id", None)
    )
    
    response_headers = headers or {}
    response_headers["Content-Type"] = "application/problem+json"
    
    return JSONResponse(
        status_code=status,
        content=problem.dict(exclude_none=True),
        headers=response_headers
    )


# Convenience functions for common errors

def validation_error_response(
    request: Request,
    errors: List[Dict[str, Any]]
) -> JSONResponse:
    """Create a validation error response."""
    error_dict = {}
    for error in errors:
        field = ".".join(str(x) for x in error["loc"][1:])  # Skip 'body' prefix
        if field not in error_dict:
            error_dict[field] = []
        error_dict[field].append({
            "message": error["msg"],
            "type": error["type"]
        })
    
    return create_problem_response(
        request=request,
        problem_type=ProblemTypes.VALIDATION_ERROR,
        title="Validation Error",
        status=422,
        detail="The request contains invalid data",
        errors=error_dict
    )


def not_found_response(
    request: Request,
    resource_type: str,
    resource_id: Optional[str] = None
) -> JSONResponse:
    """Create a resource not found response."""
    detail = f"{resource_type} not found"
    if resource_id:
        detail = f"{resource_type} with ID '{resource_id}' not found"
    
    return create_problem_response(
        request=request,
        problem_type=ProblemTypes.RESOURCE_NOT_FOUND,
        title=f"{resource_type} Not Found",
        status=404,
        detail=detail
    )


def unauthorized_response(
    request: Request,
    detail: str = "Authentication required"
) -> JSONResponse:
    """Create an unauthorized response."""
    return create_problem_response(
        request=request,
        problem_type=ProblemTypes.TOKEN_INVALID,
        title="Unauthorized",
        status=401,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"}
    )


def rate_limit_response(
    request: Request,
    retry_after: int,
    detail: Optional[str] = None
) -> JSONResponse:
    """Create a rate limit exceeded response."""
    return create_problem_response(
        request=request,
        problem_type=ProblemTypes.RATE_LIMIT_EXCEEDED,
        title="Rate Limit Exceeded",
        status=429,
        detail=detail or f"Please retry after {retry_after} seconds",
        headers={"Retry-After": str(retry_after)}
    )


def conflict_response(
    request: Request,
    resource_type: str,
    detail: Optional[str] = None
) -> JSONResponse:
    """Create a resource conflict response."""
    return create_problem_response(
        request=request,
        problem_type=ProblemTypes.RESOURCE_ALREADY_EXISTS,
        title="Resource Conflict",
        status=409,
        detail=detail or f"{resource_type} already exists"
    )


def internal_error_response(
    request: Request,
    detail: str = "An unexpected error occurred"
) -> JSONResponse:
    """Create an internal server error response."""
    return create_problem_response(
        request=request,
        problem_type=ProblemTypes.INTERNAL_ERROR,
        title="Internal Server Error",
        status=500,
        detail=detail
    )