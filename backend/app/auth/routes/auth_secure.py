"""
Secure authentication routes using httpOnly cookies and sessions.
This replaces the insecure localStorage JWT pattern.
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, Request, Response, HTTPException, status
from fastapi.responses import JSONResponse

from app.auth.services.auth_service import AuthService
from app.auth.core.dependencies import get_auth_service, get_current_user
from app.auth.core.session_security import SecureSessionManager
from app.auth.core.exceptions import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    AccountLockedError,
    RateLimitExceededError,
    SessionInvalidError
)
from app.core.rate_limit_dependencies import (
    rate_limit_auth_endpoints, rate_limit_registration
)
from app.core.enhanced_rate_limiting import (
    rate_limit_login_attempts,
    rate_limit_password_operations,
    track_suspicious_activity
)
from app.auth.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    MessageResponse,
    UserProfile,
    ChangePasswordRequest,
    SessionInfo
)

router = APIRouter(tags=["secure-authentication"], prefix="/auth/secure")
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


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def secure_register(
    register_data: RegisterRequest,
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
    _: None = Depends(rate_limit_registration)  # 3 requests per 5 minutes
):
    """Register a new user with secure session."""
    try:
        # Register user
        user_profile = await auth_service.register_user(register_data)
        
        # Create secure session
        session_data = await SecureSessionManager.create_session(
            response=response,
            user_id=str(user_profile.id),
            request=request,
            remember_me=False
        )
        
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "message": "Registration successful",
                "user": user_profile.dict(),
                "csrf_token": session_data.csrf_token
            }
        )
        
    except UserAlreadyExistsError:
        # Don't reveal that the user exists - return generic error
        logger.info(f"Registration attempt for existing email: {register_data.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed. Please try again with different information."
        )
    except Exception as e:
        logger.error(f"Secure registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed. Please try again."
        )


@router.post("/login")
async def secure_login(
    login_data: LoginRequest,
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
    _: None = Depends(rate_limit_auth_endpoints)  # 5 requests per minute
):
    """Authenticate user with secure session."""
    try:
        ip_address, user_agent = get_client_info(request)
        
        # Note: We'll need to create a new method in auth_service that doesn't return JWT tokens
        # For now, using existing method but ignoring tokens
        user_profile, _, _ = await auth_service.authenticate_user(
            login_data, user_agent, ip_address
        )
        
        # Create secure session
        session_data = await SecureSessionManager.create_session(
            response=response,
            user_id=str(user_profile.id),
            request=request,
            remember_me=login_data.remember_me
        )
        
        return JSONResponse(
            content={
                "message": "Login successful",
                "user": user_profile.dict(),
                "csrf_token": session_data.csrf_token
            }
        )
        
    except (InvalidCredentialsError, AccountLockedError, RateLimitExceededError) as e:
        raise e
    except Exception as e:
        logger.error(f"Secure login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/logout", response_model=MessageResponse)
async def secure_logout(
    request: Request,
    response: Response
):
    """Logout user by destroying session."""
    try:
        # Get current session
        session_data = await SecureSessionManager.get_session(request)
        
        if session_data:
            # Destroy session
            await SecureSessionManager.destroy_session(session_data.session_id)
        
        # Clear session cookies
        await SecureSessionManager.clear_session_cookies(response)
        
        return MessageResponse(message="Successfully logged out")
        
    except Exception as e:
        logger.error(f"Secure logout error: {e}")
        # Don't fail logout even if there's an error - clear cookies anyway
        await SecureSessionManager.clear_session_cookies(response)
        return MessageResponse(message="Logged out")


@router.post("/logout-all", response_model=MessageResponse)
async def secure_logout_all_devices(
    request: Request,
    response: Response,
    current_user: UserProfile = Depends(get_current_user)
):
    """Logout user from all devices by destroying all sessions."""
    try:
        # Destroy all user sessions
        destroyed_count = await SecureSessionManager.destroy_user_sessions(str(current_user.id))
        
        # Clear session cookies from current response
        await SecureSessionManager.clear_session_cookies(response)
        
        logger.info(f"Destroyed {destroyed_count} sessions for user {current_user.id}")
        return MessageResponse(message="Successfully logged out from all devices")
        
    except Exception as e:
        logger.error(f"Secure logout all error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.get("/me", response_model=UserProfile)
async def get_current_user_secure(
    current_user: UserProfile = Depends(get_current_user)
):
    """Get current user profile from secure session."""
    return current_user


@router.get("/session-info")
async def get_session_info(
    request: Request,
    current_user: UserProfile = Depends(get_current_user)
) -> SessionInfo:
    """Get information about the current session."""
    try:
        session_data = await SecureSessionManager.get_session(request)
        
        if not session_data:
            raise SessionInvalidError()
        
        return SessionInfo(
            session_id=session_data.session_id,
            user_id=session_data.user_id,
            created_at=session_data.created_at,
            last_accessed=session_data.last_accessed,
            ip_address=session_data.ip_address,
            user_agent=session_data.user_agent,
            is_remember_me=session_data.is_remember_me
        )
        
    except Exception as e:
        logger.error(f"Get session info error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get session info"
        )


@router.get("/csrf-token")
async def get_csrf_token(request: Request):
    """Get CSRF token for the current session."""
    try:
        session_data = await SecureSessionManager.get_session(request)
        
        if not session_data:
            raise SessionInvalidError()
        
        return {"csrf_token": session_data.csrf_token}
        
    except SessionInvalidError:
        raise
    except Exception as e:
        logger.error(f"Get CSRF token error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get CSRF token"
        )