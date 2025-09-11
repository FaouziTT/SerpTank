"""Google OAuth authentication routes."""

import logging
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse

from app.auth.services.auth_service import AuthService
from app.auth.services.google_auth import GoogleAuthService
from app.auth.core.dependencies import get_auth_service, get_current_user
from app.auth.core.security import create_access_token, create_refresh_token
from app.auth.core.exceptions import GoogleAuthError
from app.auth.schemas.auth import (
    AuthResponse,
    MessageResponse,
    UserProfile,
    GoogleAuthRequest,
    LinkGoogleAccountRequest
)

router = APIRouter(tags=["google-oauth"])
logger = logging.getLogger(__name__)


async def get_google_auth_service(
    auth_service: AuthService = Depends(get_auth_service)
) -> GoogleAuthService:
    """Get Google auth service instance."""
    return GoogleAuthService(auth_service.db)


@router.get("/google/login")
async def google_login(
    state: str = Query(None, description="CSRF state parameter"),
    google_auth: GoogleAuthService = Depends(get_google_auth_service)
):
    """
    Initiate Google OAuth login.
    Redirects user to Google OAuth consent screen.
    """
    try:
        if not google_auth.is_configured():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Google OAuth is not configured"
            )
        
        authorization_url = google_auth.get_authorization_url(state)
        return RedirectResponse(url=authorization_url)
        
    except GoogleAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Google login initiation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate Google login"
        )


@router.get("/google/callback")
async def google_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(None, description="CSRF state parameter"),
    error: str = Query(None, description="Error from Google OAuth"),
    request: Request = None,
    google_auth: GoogleAuthService = Depends(get_google_auth_service)
):
    """
    Handle Google OAuth callback.
    Processes the authorization code and creates user session.
    """
    try:
        # Check for OAuth errors
        if error:
            logger.warning(f"Google OAuth error: {error}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Google OAuth error: {error}"
            )
        
        if not code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing authorization code"
            )
        
        # Authenticate with Google
        user_profile, is_new_user = await google_auth.authenticate_with_google(code)
        
        # Create JWT tokens
        access_token_expires = timedelta(minutes=15)
        refresh_token_expires = timedelta(days=7)
        
        access_token = create_access_token(str(user_profile.id), access_token_expires)
        refresh_token = create_refresh_token(str(user_profile.id), refresh_token_expires)
        
        # Log the authentication
        auth_type = "registration" if is_new_user else "login"
        logger.info(f"Google {auth_type} successful: {user_profile.email}")
        
        # For API usage, return JSON response
        # For web usage, this would typically redirect to frontend with tokens
        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=900,  # 15 minutes
            user=user_profile
        )
        
    except GoogleAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Google OAuth callback failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google authentication failed"
        )


@router.post("/google/authenticate", response_model=AuthResponse)
async def google_authenticate(
    auth_data: GoogleAuthRequest,
    request: Request,
    google_auth: GoogleAuthService = Depends(get_google_auth_service)
):
    """
    Authenticate with Google using authorization code.
    Alternative to callback endpoint for API usage.
    """
    try:
        # Get client info
        ip_address = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "unknown")
        
        # Authenticate with Google
        user_profile, is_new_user = await google_auth.authenticate_with_google(auth_data.code)
        
        # Create JWT tokens
        access_token_expires = timedelta(minutes=15)
        refresh_token_expires = timedelta(days=7)
        
        access_token = create_access_token(str(user_profile.id), access_token_expires)
        refresh_token = create_refresh_token(str(user_profile.id), refresh_token_expires)
        
        # Log the authentication
        auth_type = "registration" if is_new_user else "login"
        logger.info(f"Google {auth_type} via API: {user_profile.email} from {ip_address}")
        
        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=900,  # 15 minutes
            user=user_profile
        )
        
    except GoogleAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Google authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google authentication failed"
        )


@router.post("/google/link", response_model=UserProfile)
async def link_google_account(
    link_data: LinkGoogleAccountRequest,
    current_user: UserProfile = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
    google_auth: GoogleAuthService = Depends(get_google_auth_service)
):
    """
    Link Google account to existing user account.
    Requires current password for security.
    """
    try:
        # Verify current password first
        from app.auth.schemas.auth import LoginRequest
        login_verify = LoginRequest(
            email=current_user.email,
            password=link_data.password,
            remember_me=False
        )
        
        # This will raise an exception if password is wrong
        await auth_service.authenticate_user(login_verify)
        
        # Link the Google account
        updated_user = await google_auth.link_google_account(
            current_user.id, 
            link_data.google_code
        )
        
        return updated_user
        
    except GoogleAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Google account linking failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to link Google account"
        )


@router.post("/google/unlink", response_model=MessageResponse)
async def unlink_google_account(
    current_user: UserProfile = Depends(get_current_user),
    google_auth: GoogleAuthService = Depends(get_google_auth_service)
):
    """
    Unlink Google account from current user.
    """
    try:
        await google_auth.unlink_google_account(current_user.id)
        
        return MessageResponse(message="Google account unlinked successfully")
        
    except GoogleAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Google account unlinking failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unlink Google account"
        )


@router.get("/google/config")
async def get_google_config(
    google_auth: GoogleAuthService = Depends(get_google_auth_service)
):
    """
    Get Google OAuth configuration status.
    Useful for frontend to check if Google login is available.
    """
    return {
        "google_oauth_enabled": google_auth.is_configured(),
        "client_id": google_auth.client_id if google_auth.is_configured() else None,
        "redirect_uri": google_auth.redirect_uri if google_auth.is_configured() else None
    }