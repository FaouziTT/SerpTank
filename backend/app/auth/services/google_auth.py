"""Google OAuth authentication service."""

import logging
import secrets
from typing import Optional, Tuple, Dict, Any
from urllib.parse import urlencode
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.core.config import settings
from app.auth.core.security import generate_session_token
from app.auth.core.exceptions import GoogleAuthError, UserAlreadyExistsError
from app.auth.schemas.auth import UserProfile

logger = logging.getLogger(__name__)

# Google OAuth configuration
GOOGLE_OAUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

# OAuth scopes - including Search Console and Analytics for mandatory integration
GOOGLE_SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/webmasters.readonly",  # Search Console
    "https://www.googleapis.com/auth/analytics.readonly"    # Analytics
]


class GoogleAuthService:
    """Google OAuth authentication service."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.client_id = getattr(settings, 'GOOGLE_CLIENT_ID', None)
        self.client_secret = getattr(settings, 'GOOGLE_CLIENT_SECRET', None)
        self.redirect_uri = getattr(settings, 'GOOGLE_REDIRECT_URI', 'http://localhost:3000/auth/google/callback')
    
    def is_configured(self) -> bool:
        """Check if Google OAuth is properly configured."""
        return all([self.client_id, self.client_secret, self.redirect_uri])
    
    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """
        Generate Google OAuth authorization URL with security best practices.
        
        Args:
            state: Optional state parameter for CSRF protection
            
        Returns:
            Authorization URL for redirecting user to Google
        """
        if not self.is_configured():
            raise GoogleAuthError("Google OAuth not configured")
        
        # Always generate a secure state token for CSRF protection
        if not state:
            state = secrets.token_urlsafe(32)
        
        # Log state for debugging (remove in production)
        logger.info(f"Generated OAuth state: {state[:10]}...")
        
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(GOOGLE_SCOPES),
            "response_type": "code",
            "state": state,
            "access_type": "offline",  # Get refresh token
            "prompt": "consent",  # Force consent screen to get refresh token
            "include_granted_scopes": "true"  # Include previously granted scopes
        }
        
        auth_url = f"{GOOGLE_OAUTH_URL}?{urlencode(params)}"
        logger.info(f"Generated OAuth URL with scopes: {', '.join(GOOGLE_SCOPES)}")
        
        return auth_url
    
    async def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access and refresh tokens with enhanced security.
        
        Args:
            code: Authorization code from Google OAuth callback
            
        Returns:
            Token response containing access_token, refresh_token, etc.
        """
        if not self.is_configured():
            raise GoogleAuthError("Google OAuth not configured")
        
        if not code or len(code) < 10:
            raise GoogleAuthError("Invalid authorization code")
        
        token_data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri
        }
        
        # Set timeout and security headers
        timeout = httpx.Timeout(10.0, connect=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                logger.info("Exchanging authorization code for tokens...")
                response = await client.post(
                    GOOGLE_TOKEN_URL, 
                    data=token_data,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "application/json",
                        "User-Agent": "VoltexSEO/1.0"
                    }
                )
                response.raise_for_status()
                
                tokens = response.json()
                
                if "error" in tokens:
                    error_desc = tokens.get('error_description', 'Unknown error')
                    logger.error(f"Token exchange error: {error_desc}")
                    raise GoogleAuthError(f"Token exchange failed: {error_desc}")
                
                # Validate required fields
                required_fields = ['access_token', 'token_type']
                for field in required_fields:
                    if field not in tokens:
                        raise GoogleAuthError(f"Missing required field: {field}")
                
                # Log successful exchange (without sensitive data)
                logger.info("Successfully exchanged authorization code for tokens")
                
                return tokens
                
            except httpx.TimeoutException:
                logger.error("Token exchange timeout")
                raise GoogleAuthError("Token exchange timed out")
            except httpx.HTTPError as e:
                logger.error(f"Google token exchange failed: {e}")
                raise GoogleAuthError("Failed to exchange authorization code")
            except Exception as e:
                logger.error(f"Unexpected error during token exchange: {e}")
                raise GoogleAuthError("Unexpected error during token exchange")
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Get user information from Google using access token.
        
        Args:
            access_token: Google access token
            
        Returns:
            User information from Google
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(GOOGLE_USERINFO_URL, headers=headers)
                response.raise_for_status()
                
                user_info = response.json()
                
                if "error" in user_info:
                    raise GoogleAuthError(f"Failed to get user info: {user_info.get('error_description', 'Unknown error')}")
                
                return user_info
                
            except httpx.HTTPError as e:
                logger.error(f"Google user info request failed: {e}")
                raise GoogleAuthError("Failed to get user information from Google")
    
    async def authenticate_with_google(self, code: str) -> Tuple[UserProfile, bool]:
        """
        Authenticate user with Google OAuth code.
        
        Args:
            code: Authorization code from Google OAuth callback
            
        Returns:
            Tuple of (user_profile, is_new_user)
        """
        # Exchange code for tokens
        tokens = await self.exchange_code_for_tokens(code)
        access_token = tokens["access_token"]
        
        # Get user info from Google
        google_user = await self.get_user_info(access_token)
        
        google_id = google_user["id"]
        email = google_user["email"]
        name = google_user.get("name", "")
        avatar_url = google_user.get("picture")
        
        # Check if user exists by Google ID
        result = await self.db.execute(
            select(User).where(User.google_id == google_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            # Existing Google user - update their info
            user.avatar_url = avatar_url
            user.last_login = self._get_current_timestamp()
            
            # Update Google tokens if available
            if "refresh_token" in tokens:
                user.google_refresh_token = tokens["refresh_token"]
            
            await self.db.commit()
            await self.db.refresh(user)
            
            logger.info(f"Existing Google user logged in: {user.email}")
            return self._user_to_profile(user), False
        
        # Check if user exists by email (different auth provider)
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            # User exists with email auth - we could link accounts
            # For now, we'll raise an error and suggest account linking
            raise GoogleAuthError(
                f"An account with email {email} already exists. "
                "Please log in with your password and link your Google account in settings."
            )
        
        # Create new user with Google auth
        new_user = User(
            email=email,
            full_name=name,
            auth_provider="google",
            google_id=google_id,
            avatar_url=avatar_url,
            email_verified=True,  # Google emails are pre-verified
            is_active=True,
            created_via="google_oauth",
            hashed_password="",  # No password for Google users
            google_refresh_token=tokens.get("refresh_token")
        )
        
        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)
        
        logger.info(f"New Google user created: {new_user.email}")
        return self._user_to_profile(new_user), True
    
    async def link_google_account(self, user_id: int, code: str) -> UserProfile:
        """
        Link Google account to existing user.
        
        Args:
            user_id: ID of existing user
            code: Google OAuth authorization code
            
        Returns:
            Updated user profile
        """
        # Get existing user
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise GoogleAuthError("User not found")
        
        if user.google_id:
            raise GoogleAuthError("Google account already linked")
        
        # Exchange code for tokens
        tokens = await self.exchange_code_for_tokens(code)
        access_token = tokens["access_token"]
        
        # Get user info from Google
        google_user = await self.get_user_info(access_token)
        
        google_id = google_user["id"]
        google_email = google_user["email"]
        
        # Verify email matches
        if google_email.lower() != user.email.lower():
            raise GoogleAuthError(
                f"Google account email ({google_email}) doesn't match your account email ({user.email})"
            )
        
        # Check if Google ID is already used
        result = await self.db.execute(
            select(User).where(User.google_id == google_id)
        )
        existing_google_user = result.scalar_one_or_none()
        
        if existing_google_user:
            raise GoogleAuthError("This Google account is already linked to another user")
        
        # Link the accounts
        user.google_id = google_id
        user.avatar_url = google_user.get("picture", user.avatar_url)
        user.email_verified = True  # Google emails are verified
        
        if "refresh_token" in tokens:
            user.google_refresh_token = tokens["refresh_token"]
        
        await self.db.commit()
        await self.db.refresh(user)
        
        logger.info(f"Linked Google account for user: {user.email}")
        return self._user_to_profile(user)
    
    async def unlink_google_account(self, user_id: int) -> UserProfile:
        """
        Unlink Google account from user.
        
        Args:
            user_id: ID of user to unlink
            
        Returns:
            Updated user profile
        """
        # Get user
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise GoogleAuthError("User not found")
        
        if not user.google_id:
            raise GoogleAuthError("No Google account linked")
        
        if user.auth_provider == "google" and not user.hashed_password:
            raise GoogleAuthError(
                "Cannot unlink Google account. Please set a password first to avoid losing access to your account."
            )
        
        # Unlink the account
        user.google_id = None
        user.google_refresh_token = None
        # Keep avatar_url - user might want to keep it
        
        await self.db.commit()
        await self.db.refresh(user)
        
        logger.info(f"Unlinked Google account for user: {user.email}")
        return self._user_to_profile(user)
    
    def _user_to_profile(self, user: User) -> UserProfile:
        """Convert User model to UserProfile schema."""
        return UserProfile(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            company_name=user.company_name,
            avatar_url=user.avatar_url,
            auth_provider=user.auth_provider,
            email_verified=user.email_verified,
            created_at=user.created_at.isoformat() if hasattr(user, 'created_at') and user.created_at else "",
            last_login=user.last_login.isoformat() if user.last_login else None
        )
    
    def _get_current_timestamp(self):
        """Get current timestamp."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc)