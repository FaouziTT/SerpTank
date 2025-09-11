"""
OAuth Service for Google APIs (Search Console, Analytics 4, etc.)

This service handles OAuth 2.0 flows for accessing user-owned Google data.
It supports both web server and desktop application flows.
"""
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlencode

import httpx
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)

# Google OAuth 2.0 scopes for various services
GOOGLE_SCOPES = {
    'search_console': 'https://www.googleapis.com/auth/webmasters.readonly',
    'analytics': 'https://www.googleapis.com/auth/analytics.readonly',
    'analytics_edit': 'https://www.googleapis.com/auth/analytics.edit',
    'drive': 'https://www.googleapis.com/auth/drive.readonly',
    'gmail': 'https://www.googleapis.com/auth/gmail.readonly'
}

# Common scope combinations
SCOPE_COMBINATIONS = {
    'basic': [GOOGLE_SCOPES['search_console'], GOOGLE_SCOPES['analytics']],
    'full': [
        GOOGLE_SCOPES['search_console'], 
        GOOGLE_SCOPES['analytics'], 
        GOOGLE_SCOPES['analytics_edit']
    ]
}


class GoogleOAuthService:
    """Handle Google OAuth 2.0 flows for accessing user data."""
    
    def __init__(self):
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = settings.GOOGLE_REDIRECT_URI
        
    def is_configured(self) -> bool:
        """Check if OAuth is properly configured."""
        return bool(self.client_id and self.client_secret and self.redirect_uri)
        
    def get_authorization_url(self, scopes: List[str], user_id: str, state_data: Optional[Dict] = None) -> str:
        """
        Generate Google OAuth authorization URL.
        
        Args:
            scopes: List of OAuth scopes to request
            user_id: User ID to include in state parameter
            state_data: Additional data to include in state parameter
            
        Returns:
            Authorization URL for the user to visit
        """
        if not self.client_id or not self.client_secret:
            raise ValueError("Google OAuth credentials not configured")
        
        # Prepare state parameter with user info
        state_info = {
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat(),
            **(state_data or {})
        }
        state = json.dumps(state_info)
        
        # Build authorization URL
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'scope': ' '.join(scopes),
            'redirect_uri': self.redirect_uri,
            'state': state,
            'access_type': 'offline',  # Request refresh token
            'prompt': 'consent'        # Force consent screen to get refresh token
        }
        
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
        logger.info(f"Generated OAuth URL for user {user_id} with scopes: {', '.join(scopes)}")
        
        return auth_url
    
    async def exchange_code_for_tokens(self, 
                                     authorization_code: str, 
                                     state: str) -> Tuple[Dict, Dict]:
        """
        Exchange authorization code for access and refresh tokens.
        
        Args:
            authorization_code: Authorization code from Google
            state: State parameter from the authorization URL
            
        Returns:
            Tuple of (token_data, state_data)
        """
        if not self.client_id or not self.client_secret:
            raise ValueError("Google OAuth credentials not configured")
        
        # Parse state parameter
        try:
            state_data = json.loads(state)
        except json.JSONDecodeError:
            raise ValueError("Invalid state parameter")
        
        # Exchange code for tokens
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': authorization_code,
            'grant_type': 'authorization_code',
            'redirect_uri': self.redirect_uri,
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=token_data)
            response.raise_for_status()
            
            tokens = response.json()
            
            # Calculate token expiry
            if 'expires_in' in tokens:
                expires_at = datetime.utcnow() + timedelta(seconds=tokens['expires_in'])
                tokens['expires_at'] = expires_at.isoformat()
            
            logger.info(f"Successfully exchanged OAuth code for user {state_data.get('user_id')}")
            return tokens, state_data
    
    async def refresh_access_token(self, refresh_token: str) -> Dict:
        """
        Refresh an access token using a refresh token.
        
        Args:
            refresh_token: Google OAuth refresh token
            
        Returns:
            New token data
        """
        if not self.client_id or not self.client_secret:
            raise ValueError("Google OAuth credentials not configured")
        
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token',
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=token_data)
            response.raise_for_status()
            
            tokens = response.json()
            
            # Calculate token expiry
            if 'expires_in' in tokens:
                expires_at = datetime.utcnow() + timedelta(seconds=tokens['expires_in'])
                tokens['expires_at'] = expires_at.isoformat()
            
            logger.info("Successfully refreshed OAuth access token")
            return tokens
    
    async def store_user_tokens(self, 
                              db: AsyncSession, 
                              user_id: int, 
                              tokens: Dict,
                              scopes: List[str]) -> None:
        """
        Store OAuth tokens for a user in the database.
        
        Args:
            db: Database session
            user_id: User ID
            tokens: Token data from Google
            scopes: OAuth scopes granted
        """
        # Get user
        user = await db.get(User, user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Store tokens
        user.google_access_token = tokens.get('access_token')
        user.google_refresh_token = tokens.get('refresh_token')
        user.google_scopes = json.dumps(scopes)
        
        if 'expires_at' in tokens:
            user.google_token_expires_at = datetime.fromisoformat(tokens['expires_at'])
        
        await db.commit()
        logger.info(f"Stored OAuth tokens for user {user_id}")
    
    async def get_valid_access_token(self, db: AsyncSession, user_id: int) -> Optional[str]:
        """
        Get a valid access token for a user, refreshing if necessary.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Valid access token or None if not available
        """
        user = await db.get(User, user_id)
        if not user or not user.google_access_token:
            return None
        
        # Check if token is expired
        now = datetime.utcnow()
        if user.google_token_expires_at and user.google_token_expires_at <= now:
            # Token is expired, try to refresh
            if user.google_refresh_token:
                try:
                    new_tokens = await self.refresh_access_token(user.google_refresh_token)
                    
                    # Update stored tokens
                    user.google_access_token = new_tokens.get('access_token')
                    if 'expires_at' in new_tokens:
                        user.google_token_expires_at = datetime.fromisoformat(new_tokens['expires_at'])
                    
                    # Keep refresh token if not provided in response
                    if 'refresh_token' in new_tokens:
                        user.google_refresh_token = new_tokens['refresh_token']
                    
                    await db.commit()
                    logger.info(f"Refreshed access token for user {user_id}")
                    
                    return user.google_access_token
                except Exception as e:
                    logger.error(f"Failed to refresh token for user {user_id}: {e}")
                    return None
            else:
                logger.warning(f"Access token expired for user {user_id} and no refresh token available")
                return None
        
        return user.google_access_token
    
    async def revoke_user_tokens(self, db: AsyncSession, user_id: int) -> bool:
        """
        Revoke OAuth tokens for a user.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            True if tokens were revoked successfully
        """
        user = await db.get(User, user_id)
        if not user or not user.google_access_token:
            return True  # Nothing to revoke
        
        # Revoke token at Google
        revoke_url = "https://oauth2.googleapis.com/revoke"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    revoke_url,
                    data={'token': user.google_access_token}
                )
                response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to revoke token at Google for user {user_id}: {e}")
        
        # Clear tokens from database
        user.google_access_token = None
        user.google_refresh_token = None
        user.google_token_expires_at = None
        user.google_scopes = None
        
        await db.commit()
        logger.info(f"Revoked OAuth tokens for user {user_id}")
        
        return True
    
    def get_user_scopes(self, user: User) -> List[str]:
        """
        Get the OAuth scopes granted by a user.
        
        Args:
            user: User model instance
            
        Returns:
            List of granted scopes
        """
        if not user.google_scopes:
            return []
        
        # If it's a space-separated string, split it
        if isinstance(user.google_scopes, str):
            # Try JSON first, then fall back to space-separated
            try:
                return json.loads(user.google_scopes)
            except json.JSONDecodeError:
                return user.google_scopes.split(' ') if user.google_scopes else []
        
        return []
    
    def has_scope(self, user: User, scope: str) -> bool:
        """
        Check if a user has granted a specific OAuth scope.
        
        Args:
            user: User model instance
            scope: OAuth scope to check
            
        Returns:
            True if user has granted the scope
        """
        user_scopes = self.get_user_scopes(user)
        return scope in user_scopes
    
    async def store_user_tokens(self, db: AsyncSession, user_id: int, tokens: Dict, scopes: List[str]) -> None:
        """
        Store OAuth tokens for a user.
        
        Args:
            db: Database session
            user_id: User ID
            tokens: Token data from Google
            scopes: List of granted scopes
        """
        from sqlalchemy import select
        
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Store tokens
        user.google_access_token = tokens.get('access_token')
        user.google_refresh_token = tokens.get('refresh_token')
        user.google_scopes = ' '.join(scopes) if scopes else ''
        
        # Set token expiry with timezone awareness
        if 'expires_in' in tokens:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=tokens['expires_in'])
            user.google_token_expires_at = expires_at
        elif 'expires_at' in tokens:
            # Handle both timezone-aware and naive datetime strings
            expires_at_str = tokens['expires_at']
            if expires_at_str.endswith('Z') or '+' in expires_at_str or expires_at_str.endswith('+00:00'):
                user.google_token_expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
            else:
                # Assume UTC if no timezone info
                user.google_token_expires_at = datetime.fromisoformat(expires_at_str).replace(tzinfo=timezone.utc)
        
        await db.commit()
        logger.info(f"Stored OAuth tokens for user {user_id} with scopes: {', '.join(scopes)}")
    
    async def get_valid_access_token(self, db: AsyncSession, user_id: int) -> Optional[str]:
        """
        Get a valid access token for a user, refreshing if necessary.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Valid access token or None
        """
        from sqlalchemy import select
        
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user or not user.google_access_token:
            return None
        
        # Check if token is expired
        if user.google_token_expires_at and user.google_token_expires_at <= datetime.now(timezone.utc):
            if user.google_refresh_token:
                # Try to refresh the token
                try:
                    new_tokens = await self.refresh_access_token(user.google_refresh_token)
                    
                    # Update user with new tokens
                    user.google_access_token = new_tokens.get('access_token')
                    if 'refresh_token' in new_tokens:
                        user.google_refresh_token = new_tokens['refresh_token']
                    
                    if 'expires_in' in new_tokens:
                        expires_at = datetime.now(timezone.utc) + timedelta(seconds=new_tokens['expires_in'])
                        user.google_token_expires_at = expires_at
                    
                    await db.commit()
                    logger.info(f"Refreshed OAuth token for user {user_id}")
                    return user.google_access_token
                    
                except Exception as e:
                    logger.error(f"Failed to refresh token for user {user_id}: {e}")
                    return None
            else:
                return None
        
        return user.google_access_token
    
    async def revoke_user_tokens(self, db: AsyncSession, user_id: int) -> bool:
        """
        Revoke OAuth tokens for a user.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            True if successful
        """
        from sqlalchemy import select
        
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            return False
        
        # Revoke tokens with Google
        if user.google_access_token:
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        f"https://oauth2.googleapis.com/revoke?token={user.google_access_token}"
                    )
            except Exception as e:
                logger.warning(f"Failed to revoke token with Google: {e}")
        
        # Clear stored tokens
        user.google_access_token = None
        user.google_refresh_token = None
        user.google_scopes = None
        user.google_token_expires_at = None
        
        await db.commit()
        logger.info(f"Revoked OAuth tokens for user {user_id}")
        return True


# Global OAuth service instance
oauth_service = GoogleOAuthService()
