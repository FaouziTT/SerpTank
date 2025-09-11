"""
CSRF Protection Middleware

Custom implementation of CSRF protection for state-changing operations.
Uses secure random tokens with session-based validation.
"""

import secrets
import logging
from typing import Optional, Set
from fastapi import Request, HTTPException, status
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

logger = logging.getLogger(__name__)

class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """
    CSRF Protection Middleware for FastAPI
    
    Protects against Cross-Site Request Forgery attacks by:
    1. Generating secure CSRF tokens for each session
    2. Validating tokens on state-changing operations (POST, PUT, DELETE, PATCH)
    3. Exempting safe methods (GET, HEAD, OPTIONS) and specified endpoints
    """
    
    def __init__(
        self, 
        app,
        secret_key: str,
        exempt_paths: Optional[Set[str]] = None,
        token_header: str = "X-CSRF-Token",
        cookie_name: str = "csrf_token",
        secure: bool = True
    ):
        super().__init__(app)
        self.secret_key = secret_key
        self.exempt_paths = exempt_paths or {
            "/docs", "/redoc", "/openapi.json", "/health",
            "/api/v1/auth/login", "/api/v1/auth/logout",
            "/api/v1/auth/refresh"  # These handle CSRF differently
        }
        self.token_header = token_header
        self.cookie_name = cookie_name
        self.secure = secure
        self.safe_methods = {"GET", "HEAD", "OPTIONS", "TRACE"}
        
    def generate_csrf_token(self) -> str:
        """Generate a cryptographically secure CSRF token."""
        return secrets.token_urlsafe(32)
    
    def is_exempt_path(self, path: str) -> bool:
        """Check if the request path is exempt from CSRF protection."""
        return any(path.startswith(exempt) for exempt in self.exempt_paths)
    
    def get_token_from_request(self, request: Request) -> Optional[str]:
        """Extract CSRF token from request headers or form data."""
        # Try header first
        token = request.headers.get(self.token_header)
        if token:
            return token
            
        # Try form data for non-JSON requests
        if hasattr(request, '_form') and request._form:
            return request._form.get('csrf_token')
            
        return None
    
    def validate_csrf_token(self, request: Request, token: str) -> bool:
        """
        Validate CSRF token against the session token.
        
        Uses constant-time comparison to prevent timing attacks.
        """
        session_token = request.cookies.get(self.cookie_name)
        if not session_token:
            logger.warning("CSRF validation failed: No session token found")
            return False
            
        # Constant-time comparison to prevent timing attacks
        return secrets.compare_digest(token, session_token)
    
    async def dispatch(self, request: Request, call_next) -> StarletteResponse:
        """Process request with CSRF protection."""
        
        # Skip CSRF for safe methods
        if request.method in self.safe_methods:
            response = await call_next(request)
            # Add CSRF token to safe requests for subsequent state-changing operations
            if not request.cookies.get(self.cookie_name):
                csrf_token = self.generate_csrf_token()
                response.set_cookie(
                    key=self.cookie_name,
                    value=csrf_token,
                    httponly=True,
                    secure=self.secure,
                    samesite="strict",
                    max_age=3600,  # 1 hour
                    path="/"
                )
            return response
        
        # Skip CSRF for exempt paths
        if self.is_exempt_path(request.url.path):
            return await call_next(request)
        
        # Validate CSRF token for state-changing operations
        csrf_token = self.get_token_from_request(request)
        if not csrf_token:
            logger.warning(
                f"CSRF validation failed: No token provided for {request.method} {request.url.path}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token missing. Include X-CSRF-Token header or csrf_token form field."
            )
        
        if not self.validate_csrf_token(request, csrf_token):
            logger.warning(
                f"CSRF validation failed: Invalid token for {request.method} {request.url.path}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token invalid or expired."
            )
        
        # Token is valid, proceed with request
        response = await call_next(request)
        
        # Don't refresh CSRF token after successful requests to avoid sync issues
        # Token will only be refreshed when explicitly requested via /api/v1/csrf/token
        # This prevents race conditions where frontend uses old token while backend expects new one
        
        return response


class CSRFProtection:
    """
    Helper class for CSRF token generation and validation.
    
    Used by endpoints that need to handle CSRF tokens manually.
    """
    
    @staticmethod
    def generate_token() -> str:
        """Generate a new CSRF token."""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def validate_token(session_token: str, provided_token: str) -> bool:
        """Validate a CSRF token using constant-time comparison."""
        if not session_token or not provided_token:
            return False
        return secrets.compare_digest(session_token, provided_token)
    
    @staticmethod
    def get_token_from_request(request: Request) -> Optional[str]:
        """Extract CSRF token from request."""
        # Try header first
        token = request.headers.get("X-CSRF-Token")
        if token:
            return token
            
        # Try cookies as fallback (for same-origin requests)
        return request.cookies.get("csrf_token")


def get_csrf_token(request: Request) -> str:
    """
    Dependency to get the current CSRF token from the request.
    
    Usage:
        @app.get("/csrf-token")
        async def get_csrf(token: str = Depends(get_csrf_token)):
            return {"csrf_token": token}
    """
    token = request.cookies.get("csrf_token")
    if not token:
        # Generate new token if none exists
        token = CSRFProtection.generate_token()
    return token