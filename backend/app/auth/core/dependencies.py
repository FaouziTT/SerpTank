"""FastAPI dependencies for authentication with secure session support."""

from typing import Optional
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.auth.core.security import verify_token, is_user_logged_out
from app.auth.core.session_security import SecureSessionBearer, SecureSessionManager, SessionData
from app.auth.core.exceptions import (
    AuthenticationError,
    TokenExpiredError,
    TokenInvalidError,
    TokenBlacklistedError,
    SessionInvalidError
)
from app.auth.services.auth_service import AuthService
from app.auth.schemas.auth import UserProfile

# Secure session bearer (supports both sessions and JWT tokens)
security = SecureSessionBearer(auto_error=False)


async def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    """Get authentication service instance."""
    return AuthService(db)


async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> Optional[UserProfile]:
    """
    Get current user from session or token (optional).
    Returns None if no valid authentication is provided.
    """
    if not credentials:
        return None
    
    try:
        # Check if using secure session
        if credentials.scheme == "Session":
            user_id_str = credentials.credentials.replace("session:", "")
            user_profile = await auth_service.get_user_by_id(int(user_id_str))
            return user_profile
        
        # Fallback to JWT token validation
        payload = await verify_token(credentials.credentials, "access")
        user_id = payload["sub"]
        
        # Check if user was logged out after token was issued
        token_issued_at = payload.get("iat", 0)
        if await is_user_logged_out(user_id, token_issued_at):
            return None
        
        # Get user profile
        user_profile = await auth_service.get_user_by_id(int(user_id))
        return user_profile
        
    except (TokenExpiredError, TokenInvalidError, TokenBlacklistedError, SessionInvalidError):
        return None


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> UserProfile:
    """
    Get current user from session or token (required).
    Raises authentication error if no valid authentication.
    """
    if not credentials:
        raise AuthenticationError("Missing authentication")
    
    try:
        # Check if using secure session
        if credentials.scheme == "Session":
            user_id_str = credentials.credentials.replace("session:", "")
            user_profile = await auth_service.get_user_by_id(int(user_id_str))
            if not user_profile:
                raise AuthenticationError("User not found")
            return user_profile
        
        # Fallback to JWT token validation
        payload = await verify_token(credentials.credentials, "access")
        user_id = payload["sub"]
        
        # Check if user was logged out after token was issued
        token_issued_at = payload.get("iat", 0)
        if await is_user_logged_out(user_id, token_issued_at):
            raise AuthenticationError("Token has been revoked")
        
        # Get user profile
        user_profile = await auth_service.get_user_by_id(int(user_id))
        if not user_profile:
            raise AuthenticationError("User not found")
        
        return user_profile
        
    except (TokenExpiredError, TokenInvalidError, TokenBlacklistedError, SessionInvalidError) as e:
        raise AuthenticationError(str(e))


async def get_current_active_user(
    current_user: UserProfile = Depends(get_current_user)
) -> UserProfile:
    """
    Get current active user.
    Alias for get_current_user since we already check if user is active.
    """
    return current_user


async def get_current_superuser(
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> UserProfile:
    """Get current superuser (admin access required)."""
    # Get full user data to check superuser status
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    
    if not user or not getattr(user, 'is_superuser', False):
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions"
        )
    
    return current_user


def require_auth(
    current_user: UserProfile = Depends(get_current_user)
) -> UserProfile:
    """Dependency to require authentication."""
    return current_user


def optional_auth(
    current_user: Optional[UserProfile] = Depends(get_current_user_optional)
) -> Optional[UserProfile]:
    """Dependency for optional authentication."""
    return current_user


class AuthRequired:
    """Class-based dependency for requiring specific auth conditions."""
    
    def __init__(self, require_superuser: bool = False, require_verified_email: bool = False):
        self.require_superuser = require_superuser
        self.require_verified_email = require_verified_email
    
    async def __call__(
        self,
        request: Request,
        current_user: UserProfile = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ) -> UserProfile:
        """Check authentication requirements."""
        
        if self.require_verified_email and not current_user.email_verified:
            raise HTTPException(
                status_code=403,
                detail="Email verification required"
            )
        
        if self.require_superuser:
            # Check superuser status
            from sqlalchemy import select
            result = await db.execute(select(User).where(User.id == current_user.id))
            user = result.scalar_one_or_none()
            
            if not user or not getattr(user, 'is_superuser', False):
                raise HTTPException(
                    status_code=403,
                    detail="Superuser access required"
                )
        
        return current_user


# Common dependency instances
require_superuser = AuthRequired(require_superuser=True)
require_verified_email = AuthRequired(require_verified_email=True)
require_superuser_and_verified = AuthRequired(require_superuser=True, require_verified_email=True)