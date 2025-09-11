"""
Custom Exception Classes and Error Handling

This module defines custom exceptions and error handlers for consistent
error responses across the application.
"""

from fastapi import HTTPException, status
from typing import Any, Dict, Optional, List


class BaseAPIException(HTTPException):
    """Base exception class for API errors"""
    def __init__(
        self, 
        status_code: int, 
        detail: str, 
        error_code: str,
        headers: Optional[Dict[str, Any]] = None
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.error_code = error_code


# Authentication Errors (400-403)
class InvalidCredentialsError(BaseAPIException):
    """Raised when login credentials are invalid"""
    def __init__(self, detail: str = "Invalid email or password"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_code="AUTH_INVALID_CREDENTIALS",
            headers={"WWW-Authenticate": "Bearer"}
        )


class TokenExpiredError(BaseAPIException):
    """Raised when JWT token has expired"""
    def __init__(self, detail: str = "Token has expired"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_code="AUTH_TOKEN_EXPIRED",
            headers={"WWW-Authenticate": "Bearer"}
        )


class InsufficientPermissionsError(BaseAPIException):
    """Raised when user lacks required permissions"""
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code="AUTH_INSUFFICIENT_PERMISSIONS"
        )


class AccountDisabledError(BaseAPIException):
    """Raised when user account is disabled"""
    def __init__(self, detail: str = "Account has been disabled"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code="AUTH_ACCOUNT_DISABLED"
        )


# Resource Errors (404, 409)
class ResourceNotFoundError(BaseAPIException):
    """Raised when requested resource doesn't exist"""
    def __init__(self, resource: str, detail: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail or f"{resource} not found",
            error_code=f"{resource.upper()}_NOT_FOUND"
        )


class ResourceAlreadyExistsError(BaseAPIException):
    """Raised when trying to create a resource that already exists"""
    def __init__(self, resource: str, detail: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail or f"{resource} already exists",
            error_code=f"{resource.upper()}_ALREADY_EXISTS"
        )


# Validation Errors (422)
class ValidationError(BaseAPIException):
    """Raised when request validation fails"""
    def __init__(self, detail: str, errors: Optional[List[Dict[str, Any]]] = None):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            error_code="VALIDATION_ERROR"
        )
        self.errors = errors or []


# Rate Limiting Errors (429)
class RateLimitExceededError(BaseAPIException):
    """Raised when rate limit is exceeded"""
    def __init__(self, detail: str = "Rate limit exceeded", retry_after: Optional[int] = None):
        headers = {}
        if retry_after:
            headers["Retry-After"] = str(retry_after)
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            error_code="RATE_LIMIT_EXCEEDED",
            headers=headers
        )


# External Service Errors (502, 503)
class ExternalServiceError(BaseAPIException):
    """Raised when external service fails"""
    def __init__(self, service: str, detail: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=detail or f"{service} service unavailable",
            error_code=f"{service.upper()}_SERVICE_ERROR"
        )


class ServiceUnavailableError(BaseAPIException):
    """Raised when service is temporarily unavailable"""
    def __init__(self, detail: str = "Service temporarily unavailable", retry_after: Optional[int] = None):
        headers = {}
        if retry_after:
            headers["Retry-After"] = str(retry_after)
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
            error_code="SERVICE_UNAVAILABLE",
            headers=headers
        )


# Business Logic Errors (400)
class InvalidOperationError(BaseAPIException):
    """Raised when an invalid operation is attempted"""
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code="INVALID_OPERATION"
        )


class QuotaExceededError(BaseAPIException):
    """Raised when user exceeds their quota"""
    def __init__(self, resource: str, detail: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=detail or f"{resource} quota exceeded",
            error_code=f"{resource.upper()}_QUOTA_EXCEEDED"
        )


# Database Errors (500)
class DatabaseError(BaseAPIException):
    """Raised when database operation fails"""
    def __init__(self, detail: str = "Database operation failed"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_code="DATABASE_ERROR"
        )


# Error Response Model
def create_error_response(
    error_code: str,
    message: str,
    status_code: int,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create a standardized error response"""
    response = {
        "error": {
            "code": error_code,
            "message": message,
            "status_code": status_code
        }
    }
    if details:
        response["error"]["details"] = details
    return response