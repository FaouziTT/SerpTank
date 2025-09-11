"""
CSRF Token Management Endpoints

Provides endpoints for CSRF token generation and validation.
"""

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from app.core.csrf import get_csrf_token, CSRFProtection
from app.core.config import settings

router = APIRouter()


@router.get("/token")
async def get_csrf_token_endpoint(request: Request):
    """
    Get a CSRF token for the current session.
    
    This endpoint provides a CSRF token that must be included in subsequent
    state-changing requests (POST, PUT, DELETE, PATCH).
    
    Returns:
        dict: Contains the CSRF token
    """
    # Generate or retrieve existing token
    existing_token = request.cookies.get("csrf_token")
    # Calculate expiration time (1 hour from now)
    # Use UTC timezone and ensure proper ISO format with 'Z' suffix
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    expires_at_str = expires_at.isoformat().replace('+00:00', 'Z')
    
    if existing_token:
        token = existing_token
        # Return existing token without setting cookie again
        return {
            "csrf_token": token,
            "expires_at": expires_at_str,
            "instructions": {
                "header": "Include as 'X-CSRF-Token' header in state-changing requests",
                "form": "Include as 'csrf_token' field in form submissions"
            }
        }
    else:
        # Generate new token and set cookie
        token = CSRFProtection.generate_token()
        
        response_data = {
            "csrf_token": token,
            "expires_at": expires_at_str,
            "instructions": {
                "header": "Include as 'X-CSRF-Token' header in state-changing requests",
                "form": "Include as 'csrf_token' field in form submissions"
            }
        }
        
        response = JSONResponse(content=response_data)
        response.set_cookie(
            key="csrf_token",
            value=token,
            httponly=True,
            secure=settings.SSL_ENABLED,
            samesite="strict",
            max_age=3600,  # 1 hour
            path="/"
        )
        
        return response


@router.post("/validate")
async def validate_csrf_token_endpoint(
    request: Request,
    token: str
):
    """
    Validate a CSRF token (for testing purposes).
    
    Args:
        token: The CSRF token to validate
    
    Returns:
        dict: Validation result
    """
    session_token = request.cookies.get("csrf_token")
    is_valid = CSRFProtection.validate_token(session_token, token)
    
    return {
        "valid": is_valid,
        "message": "Token is valid" if is_valid else "Token is invalid or expired"
    }