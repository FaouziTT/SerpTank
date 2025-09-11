"""Token migration endpoints for transitioning to httpOnly cookies."""

import logging
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.auth.core.dependencies import get_auth_service
from app.auth.services.auth_service import AuthService
from app.auth.schemas.auth import MessageResponse
from app.auth.schemas.token import TokenMigrationRequest, TokenMigrationResponse
from app.auth.core.exceptions import TokenInvalidError
from app.auth.core.security import SecurityUtils

router = APIRouter(prefix="/auth", tags=["auth-migration"])
logger = logging.getLogger(__name__)

# Bearer token security for migration endpoint
security = HTTPBearer()


@router.post("/migrate-tokens", response_model=TokenMigrationResponse)
async def migrate_tokens(
    response: Response,
    migration_data: TokenMigrationRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Migrate JWT tokens from localStorage to httpOnly cookies.
    
    This endpoint helps transition existing users from localStorage-based
    authentication to more secure httpOnly cookie-based authentication.
    """
    try:
        # Verify the access token from Authorization header
        access_token = credentials.credentials
        token_data = await auth_service.decode_access_token(access_token)
        
        # Verify the refresh token from request body
        refresh_token_data = await auth_service.decode_refresh_token(
            migration_data.refresh_token
        )
        
        # Ensure tokens belong to the same user
        if token_data.sub != refresh_token_data.sub:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token mismatch"
            )
        
        # Get user
        user = await auth_service.get_user_by_id(int(token_data.sub))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Generate new tokens
        new_access_token = await auth_service.create_access_token(user)
        new_refresh_token = await auth_service.create_refresh_token(user)
        
        # Set httpOnly cookies
        access_max_age = int(timedelta(minutes=15).total_seconds())
        refresh_max_age = int(timedelta(days=7).total_seconds())
        
        # Determine if we're in a secure context
        secure = auth_service.settings.environment == "production"
        
        # Set access token cookie
        response.set_cookie(
            key="access_token",
            value=new_access_token,
            max_age=access_max_age,
            httponly=True,
            secure=secure,
            samesite="lax",
            path="/"
        )
        
        # Set refresh token cookie
        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            max_age=refresh_max_age,
            httponly=True,
            secure=secure,
            samesite="lax",
            path="/api/v1/auth"  # Restrict to auth endpoints
        )
        
        logger.info(f"Successfully migrated tokens for user {user.id}")
        
        return TokenMigrationResponse(
            message="Tokens successfully migrated to secure cookies",
            expires_in=access_max_age
        )
        
    except TokenInvalidError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid tokens"
        )
    except Exception as e:
        logger.error(f"Token migration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Migration failed"
        )


@router.post("/verify", response_model=MessageResponse)
async def verify_cookie_auth(
    auth_service: AuthService = Depends(get_auth_service),
    access_token: Optional[str] = Depends(SecurityUtils.get_token_from_cookie)
):
    """
    Verify authentication using httpOnly cookies.
    
    This endpoint checks if the user has valid authentication cookies.
    """
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No authentication cookie found"
        )
    
    try:
        token_data = await auth_service.decode_access_token(access_token)
        
        return MessageResponse(
            message="Authentication valid",
            details={
                "expires_at": token_data.exp,
                "token_type": "bearer"
            }
        )
    except TokenInvalidError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication cookie"
        )


@router.post("/clear-cookies", response_model=MessageResponse)
async def clear_auth_cookies(response: Response):
    """
    Clear authentication cookies.
    
    This endpoint removes all authentication cookies, effectively logging out the user.
    """
    # Clear access token cookie
    response.delete_cookie(
        key="access_token",
        path="/"
    )
    
    # Clear refresh token cookie
    response.delete_cookie(
        key="refresh_token",
        path="/api/v1/auth"
    )
    
    return MessageResponse(
        message="Authentication cookies cleared"
    )