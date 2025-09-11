"""
OAuth API endpoints for Google integrations.

This module provides endpoints for handling OAuth 2.0 flows with Google APIs
to access user-owned data like Search Console and Analytics.
"""
import json
import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.core.dependencies import get_current_active_user
from app.auth.schemas.auth import UserProfile
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.services.oauth_service import oauth_service, SCOPE_COMBINATIONS

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/status")
async def get_oauth_status(
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict:
    """
    Get current OAuth connection status for the user.
    
    This endpoint provides detailed information about the user's Google OAuth
    connections, including what permissions they have and what's required
    for project creation.
    
    Returns:
        Detailed OAuth status including required connections for project creation
    """
    try:
        from app.services.oauth_validation_service import get_oauth_validation_service
        oauth_validator = get_oauth_validation_service(db)
        
        # Get detailed OAuth status
        oauth_status = await oauth_validator.get_user_oauth_status(current_user.id)
        
        # Check project creation requirements
        project_requirements = await oauth_validator.validate_all_required_connections(current_user.id)
        
        return {
            "user_id": current_user.id,
            "oauth_status": oauth_status,
            "project_creation_requirements": {
                "can_create_projects": project_requirements["all_valid"],
                "missing_connections": [] if project_requirements["all_valid"] else [
                    service for service in ["search_console", "analytics"] 
                    if not project_requirements[service]["valid"]
                ],
                "search_console": project_requirements["search_console"],
                "analytics": project_requirements["analytics"]
            },
            "help": {
                "message": "Projects require both Google Search Console and Google Analytics connections",
                "next_steps": [
                    "Connect your Google account with Search Console permissions",
                    "Connect your Google account with Analytics permissions", 
                    "Verify your website is added to both Search Console and Analytics",
                    "Create your first project"
                ] if not project_requirements["all_valid"] else [
                    "You're all set! You can now create projects."
                ]
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting OAuth status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get OAuth status: {str(e)}"
        )


@router.get("/google/authorize")
async def get_google_oauth_url(
    scopes: str = Query("basic", description="Scope combination: basic, full, or custom comma-separated scopes"),
    current_user: UserProfile = Depends(get_current_active_user),
) -> Dict:
    """
    Get Google OAuth authorization URL for user to grant permissions.
    
    Args:
        scopes: OAuth scope combination or custom scopes
        current_user: Current authenticated user
        
    Returns:
        Authorization URL and state information
    """
    try:
        # Check if OAuth is configured
        if not oauth_service.is_configured():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": "Google OAuth not configured",
                    "message": "Google OAuth credentials are not set up. Please configure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in your environment variables.",
                    "setup_instructions": "See GOOGLE_OAUTH_SETUP.md for detailed setup instructions",
                    "required_env_vars": [
                        "GOOGLE_CLIENT_ID",
                        "GOOGLE_CLIENT_SECRET", 
                        "GOOGLE_REDIRECT_URI"
                    ]
                }
            )
        
        # Parse scopes
        if scopes in SCOPE_COMBINATIONS:
            requested_scopes = SCOPE_COMBINATIONS[scopes]
        elif scopes.startswith('https://'):
            # Single Google API scope URL provided
            requested_scopes = [scopes.strip()]
        else:
            # Custom scopes provided as comma-separated values
            requested_scopes = [scope.strip() for scope in scopes.split(',')]
        
        # Generate authorization URL
        auth_url = oauth_service.get_authorization_url(
            scopes=requested_scopes,
            user_id=str(current_user.id),
            state_data={'scope_type': scopes}
        )
        
        return {
            'authorization_url': auth_url,
            'scopes': requested_scopes,
            'message': 'Visit the authorization URL to grant permissions'
        }
        
    except Exception as e:
        logger.error(f"Failed to generate OAuth URL for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate authorization URL: {str(e)}"
        )


@router.get("/google/callback")
async def handle_google_oauth_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(..., description="State parameter from authorization URL"),
    error: Optional[str] = Query(None, description="Error parameter if authorization failed"),
    db: AsyncSession = Depends(get_db),
) -> Dict:
    """
    Handle OAuth callback from Google and store tokens.
    
    Args:
        code: Authorization code from Google
        state: State parameter from the authorization request
        error: Error parameter if authorization was denied
        db: Database session
        
    Returns:
        Success message and granted scopes
    """
    if error:
        logger.warning(f"OAuth authorization failed: {error}")
        frontend_url = settings.FRONTEND_URL or "http://localhost:3000"
        redirect_url = f"{frontend_url}/oauth/callback?success=false&error={error}"
        return RedirectResponse(url=redirect_url, status_code=302)
    
    try:
        # Exchange code for tokens
        tokens, state_data = await oauth_service.exchange_code_for_tokens(code, state)
        
        # Extract user ID from state
        user_id = int(state_data.get('user_id'))
        if not user_id:
            raise ValueError("User ID not found in state parameter")
        
        # Determine scopes based on what was requested
        scope_type = state_data.get('scope_type', 'basic')
        if scope_type in SCOPE_COMBINATIONS:
            granted_scopes = SCOPE_COMBINATIONS[scope_type]
        else:
            # Extract scopes from token response if available
            granted_scopes = tokens.get('scope', '').split(' ') if 'scope' in tokens else []
        
        # Store tokens in database
        await oauth_service.store_user_tokens(
            db=db,
            user_id=user_id,
            tokens=tokens,
            scopes=granted_scopes
        )
        
        # Redirect to frontend onboarding wizard with success indicator
        frontend_url = settings.FRONTEND_URL or "http://localhost:3000"
        redirect_url = f"{frontend_url}/onboarding?oauth_success=true"
        
        return RedirectResponse(url=redirect_url, status_code=302)
        
    except Exception as e:
        logger.error(f"Failed to handle OAuth callback: {e}")
        frontend_url = settings.FRONTEND_URL or "http://localhost:3000"
        redirect_url = f"{frontend_url}/oauth/callback?success=false&error=processing_failed"
        return RedirectResponse(url=redirect_url, status_code=302)


@router.get("/google/status")
async def get_google_oauth_status(
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict:
    """
    Get current Google OAuth status for the user.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        OAuth status and granted scopes
    """
    try:
        # Check if user has valid tokens
        access_token = await oauth_service.get_valid_access_token(db, current_user.id)
        is_connected = access_token is not None
        
        # Get granted scopes
        granted_scopes = oauth_service.get_user_scopes(current_user)
        
        return {
            'connected': is_connected,
            'scopes': granted_scopes,
            'has_search_console': oauth_service.has_scope(current_user, 'https://www.googleapis.com/auth/webmasters.readonly'),
            'has_analytics': oauth_service.has_scope(current_user, 'https://www.googleapis.com/auth/analytics.readonly'),
            'token_expires_at': current_user.google_token_expires_at.isoformat() if current_user.google_token_expires_at else None
        }
        
    except Exception as e:
        logger.error(f"Failed to get OAuth status for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get OAuth status: {str(e)}"
        )


@router.post("/google/revoke")
async def revoke_google_oauth(
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict:
    """
    Revoke Google OAuth tokens for the user.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Success message
    """
    try:
        success = await oauth_service.revoke_user_tokens(db, current_user.id)
        
        if success:
            return {'message': 'OAuth tokens revoked successfully'}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to revoke OAuth tokens"
            )
            
    except Exception as e:
        logger.error(f"Failed to revoke OAuth tokens for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke OAuth tokens: {str(e)}"
        )


@router.post("/google/refresh")
async def refresh_google_oauth_token(
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict:
    """
    Manually refresh Google OAuth access token.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        New token information
    """
    try:
        # Get valid access token (this will refresh if needed)
        access_token = await oauth_service.get_valid_access_token(db, current_user.id)
        
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid refresh token available. Please re-authorize."
            )
        
        # Refresh user data to get updated token info
        await db.refresh(current_user)
        
        return {
            'message': 'Token refreshed successfully',
            'expires_at': current_user.google_token_expires_at.isoformat() if current_user.google_token_expires_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to refresh OAuth token for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh OAuth token: {str(e)}"
        )


@router.get("/google/test-connection")
async def test_google_connection(
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict:
    """
    Test Google API connection using stored OAuth tokens.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Connection test results
    """
    try:
        # Get valid access token
        access_token = await oauth_service.get_valid_access_token(db, current_user.id)
        
        if not access_token:
            return {
                'connected': False,
                'error': 'No valid access token available'
            }
        
        # Test Search Console API access
        search_console_ok = False
        if oauth_service.has_scope(current_user, 'https://www.googleapis.com/auth/webmasters.readonly'):
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        'https://searchconsole.googleapis.com/webmasters/v3/sites',
                        headers={'Authorization': f'Bearer {access_token}'}
                    )
                    search_console_ok = response.status_code == 200
            except Exception as e:
                logger.warning(f"Search Console API test failed: {e}")
        
        # Test Analytics API access
        analytics_ok = False
        if oauth_service.has_scope(current_user, 'https://www.googleapis.com/auth/analytics.readonly'):
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        'https://analyticsdata.googleapis.com/v1beta/properties',
                        headers={'Authorization': f'Bearer {access_token}'}
                    )
                    analytics_ok = response.status_code in [200, 404]  # 404 is ok, means no properties but API works
            except Exception as e:
                logger.warning(f"Analytics API test failed: {e}")
        
        return {
            'connected': True,
            'search_console_access': search_console_ok,
            'analytics_access': analytics_ok,
            'scopes': oauth_service.get_user_scopes(current_user)
        }
        
    except Exception as e:
        logger.error(f"Failed to test Google connection for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test connection: {str(e)}"
        )
