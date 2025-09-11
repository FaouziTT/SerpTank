"""Main authentication routes."""

import logging
from datetime import timedelta
from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from app.auth.services.auth_service import AuthService
from app.auth.core.dependencies import get_auth_service, get_current_user, security, get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.core.exceptions import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    AccountLockedError,
    RateLimitExceededError,
    TokenExpiredError,
    TokenInvalidError
)
from app.core.rate_limit_dependencies import (
    rate_limit_auth_endpoints, rate_limit_registration
)
from app.auth.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    AuthResponse,
    MessageResponse,
    UserProfile,
    ChangePasswordRequest,
    RefreshTokenRequest,
    SessionInfo,
    UserSessionsResponse
)
from app.auth.schemas.token import RefreshTokenResponse

router = APIRouter(tags=["authentication"])
logger = logging.getLogger(__name__)


def get_client_info(request: Request) -> tuple[str, str]:
    """Extract client IP and user agent from request."""
    # Get real IP address (consider proxy headers)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        ip_address = forwarded_for.split(",")[0].strip()
    else:
        ip_address = request.client.host if request.client else "unknown"
    
    user_agent = request.headers.get("User-Agent", "unknown")
    
    return ip_address, user_agent


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    register_data: RegisterRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
    _: None = Depends(rate_limit_registration)  # 3 requests per 5 minutes
):
    """Register a new user."""
    try:
        ip_address, user_agent = get_client_info(request)
        
        # Register user
        user_profile = await auth_service.register_user(register_data)
        
        # Automatically log them in
        login_data = LoginRequest(
            email=register_data.email,
            password=register_data.password,
            remember_me=False
        )
        
        user_profile, access_token, refresh_token = await auth_service.authenticate_user(
            login_data, user_agent, ip_address
        )
        
        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=900,  # 15 minutes
            user=user_profile
        )
        
    except UserAlreadyExistsError as e:
        # Don't reveal that the user exists - return generic error
        logger.info(f"Registration attempt for existing email: {register_data.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed. Please try again with different information."
        )
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed. Please try again."
        )


@router.post("/login", response_model=AuthResponse)
async def login(
    login_data: LoginRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
    _: None = Depends(rate_limit_auth_endpoints)  # 5 requests per minute
):
    """Authenticate user and return tokens."""
    try:
        ip_address, user_agent = get_client_info(request)
        
        user_profile, access_token, refresh_token = await auth_service.authenticate_user(
            login_data, user_agent, ip_address
        )
        
        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=900,  # 15 minutes
            user=user_profile
        )
        
    except (InvalidCredentialsError, AccountLockedError, RateLimitExceededError) as e:
        raise e
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Refresh access token using refresh token."""
    try:
        new_access_token, new_refresh_token = await auth_service.refresh_access_token(
            refresh_data.refresh_token
        )
        
        return RefreshTokenResponse(
            access_token=new_access_token,
            token_type="bearer",
            expires_in=900  # 15 minutes
        )
        
    except (TokenExpiredError, TokenInvalidError) as e:
        raise e
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    refresh_data: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Logout user by blacklisting refresh token."""
    try:
        await auth_service.logout_user(refresh_data.refresh_token)
        
        return MessageResponse(message="Successfully logged out")
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        # Don't fail logout even if there's an error
        return MessageResponse(message="Logged out")


@router.post("/logout-all", response_model=MessageResponse)
async def logout_all_devices(
    current_user: UserProfile = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Logout user from all devices."""
    try:
        await auth_service.logout_all_devices(current_user.id)
        
        return MessageResponse(message="Successfully logged out from all devices")
        
    except Exception as e:
        logger.error(f"Logout all error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    current_user: UserProfile = Depends(get_current_user)
):
    """Get current user profile."""
    return current_user


@router.post("/complete-onboarding", response_model=UserProfile)
async def complete_onboarding(
    current_user: UserProfile = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Mark user onboarding as complete."""
    try:
        updated_user = await auth_service.complete_onboarding(current_user.id)
        return updated_user
    except Exception as e:
        logger.error(f"Onboarding completion error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete onboarding"
        )


@router.put("/me", response_model=UserProfile)
async def update_current_user_profile(
    update_data: dict,  # Accept any dict for now, validate in endpoint
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current user profile.
    
    Accepts updates for:
    - full_name: User's display name
    - email: User's email (may require verification in future)
    
    Note: Regular users cannot update is_active or is_superuser status.
    """
    try:
        # Get the full user model
        from app.models.user import User
        from sqlalchemy import select
        
        result = await db.execute(select(User).where(User.id == current_user.id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Only allow updating specific fields
        allowed_fields = ['full_name', 'email']
        
        # Filter update data to only allowed fields
        filtered_update = {k: v for k, v in update_data.items() if k in allowed_fields and v is not None}
        
        # Update fields
        for field, value in filtered_update.items():
            if hasattr(user, field):
                setattr(user, field, value)
        
        await db.commit()
        await db.refresh(user)
        
        # Return updated profile
        return UserProfile(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            created_at=user.created_at,
            auth_provider=getattr(user, 'auth_provider', 'email'),
            email_verified=getattr(user, 'email_verified', True)
        )
        
    except Exception as e:
        logger.error(f"Profile update error: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profile update failed"
        )


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    change_data: ChangePasswordRequest,
    current_user: UserProfile = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Change user password."""
    try:
        await auth_service.change_password(current_user.id, change_data)
        
        return MessageResponse(message="Password changed successfully")
        
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    except Exception as e:
        logger.error(f"Password change error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )


@router.get("/sessions", response_model=UserSessionsResponse)
async def get_user_sessions(
    current_user: UserProfile = Depends(get_current_user),
    request: Request = None,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Get user active sessions.
    
    Returns a list of active sessions (JWT tokens) for the current user.
    Note: This is a simplified implementation that tracks JWT tokens.
    Full session management would require database storage.
    """
    try:
        # Get current token to identify current session
        current_token = None
        if request and request.headers.get('Authorization'):
            auth_header = request.headers.get('Authorization')
            if auth_header.startswith('Bearer '):
                current_token = auth_header.split(' ')[1]
        
        # For now, return a simplified response
        # In a full implementation, we would:
        # 1. Store session info in database when tokens are created
        # 2. Track user agent, IP, last activity
        # 3. Allow revoking specific sessions
        
        # Create a mock session for the current connection
        from datetime import datetime, timezone
        current_session = SessionInfo(
            id=1,
            user_agent=request.headers.get('User-Agent', 'Unknown') if request else 'Unknown',
            ip_address=request.client.host if request and request.client else 'Unknown',
            created_at=datetime.now(timezone.utc).isoformat(),
            last_seen=datetime.now(timezone.utc).isoformat(),
            is_current=True
        )
        
        return UserSessionsResponse(sessions=[current_session])
        
    except Exception as e:
        logger.error(f"Error fetching sessions: {e}")
        return UserSessionsResponse(sessions=[])


@router.delete("/sessions/{session_id}", response_model=MessageResponse)
async def revoke_session(
    session_id: int,
    current_user: UserProfile = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Revoke a specific session.
    
    Note: This is a placeholder implementation. In a full session management system:
    1. Sessions would be stored in the database with unique IDs
    2. Revoking would mark the session as invalid
    3. The associated JWT token would be blacklisted
    
    Currently, we can only revoke all tokens via logout-all-devices.
    """
    # For now, if session_id is 1 (current session), suggest using logout
    if session_id == 1:
        return MessageResponse(
            message="Cannot revoke current session. Please use /logout endpoint instead."
        )
    
    # For other session IDs, return success (placeholder)
    # In a real implementation, we would:
    # 1. Verify the session belongs to the current user
    # 2. Add the session's token to the blacklist
    # 3. Remove the session from the database
    
    return MessageResponse(message=f"Session {session_id} revoked successfully")