"""Security utilities for cookie-based authentication."""

from typing import Optional
from fastapi import Request, Response, HTTPException, status
from datetime import timedelta

from app.auth.core.config import get_settings


class SecurityUtils:
    """Utilities for secure cookie handling."""
    
    @staticmethod
    def get_token_from_cookie(request: Request) -> Optional[str]:
        """Extract access token from httpOnly cookie."""
        return request.cookies.get("access_token")
    
    @staticmethod
    def get_refresh_token_from_cookie(request: Request) -> Optional[str]:
        """Extract refresh token from httpOnly cookie."""
        return request.cookies.get("refresh_token")
    
    @staticmethod
    def set_auth_cookies(
        response: Response,
        access_token: str,
        refresh_token: str,
        remember_me: bool = False
    ) -> None:
        """Set httpOnly cookies for authentication."""
        settings = get_settings()
        
        # Determine if we're in a secure context
        secure = settings.environment == "production"
        
        # Access token cookie (15 minutes)
        access_max_age = int(timedelta(minutes=15).total_seconds())
        
        response.set_cookie(
            key="access_token",
            value=access_token,
            max_age=access_max_age,
            httponly=True,
            secure=secure,
            samesite="lax",
            path="/",
            domain=None  # Let browser handle domain
        )
        
        # Refresh token cookie (7 days or 30 days if remember me)
        refresh_max_age = int(timedelta(days=30 if remember_me else 7).total_seconds())
        
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            max_age=refresh_max_age,
            httponly=True,
            secure=secure,
            samesite="lax",
            path="/api/v1/auth",  # Restrict to auth endpoints
            domain=None
        )
        
        # Set CSRF token in a readable cookie (not httpOnly)
        # This allows the frontend to read it and include in headers
        response.set_cookie(
            key="csrf_token",
            value=access_token[:32],  # Use part of access token as CSRF
            max_age=access_max_age,
            httponly=False,  # Frontend needs to read this
            secure=secure,
            samesite="strict",
            path="/",
            domain=None
        )
    
    @staticmethod
    def clear_auth_cookies(response: Response) -> None:
        """Clear all authentication cookies."""
        cookies_to_clear = ["access_token", "refresh_token", "csrf_token"]
        
        for cookie in cookies_to_clear:
            response.delete_cookie(
                key=cookie,
                path="/" if cookie != "refresh_token" else "/api/v1/auth"
            )
    
    @staticmethod
    def validate_csrf_token(request: Request) -> bool:
        """Validate CSRF token from header against cookie."""
        # Get CSRF token from cookie
        cookie_csrf = request.cookies.get("csrf_token")
        if not cookie_csrf:
            return False
        
        # Get CSRF token from header
        header_csrf = request.headers.get("X-CSRF-Token")
        if not header_csrf:
            return False
        
        # Compare tokens
        return cookie_csrf == header_csrf
    
    @staticmethod
    def require_csrf_token(request: Request) -> None:
        """Require valid CSRF token for state-changing operations."""
        if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
            if not SecurityUtils.validate_csrf_token(request):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid CSRF token"
                )