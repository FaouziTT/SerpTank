"""Main authentication service."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import redis.asyncio as redis

from app.models.user import User
from app.core.config import settings
from app.auth.core.security import (
    hash_password,
    verify_password,
    validate_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    blacklist_token,
    blacklist_all_user_tokens,
    generate_session_token,
    get_redis_client
)
from app.auth.core.exceptions import (
    InvalidCredentialsError,
    UserNotFoundError,
    UserAlreadyExistsError,
    AccountLockedError,
    EmailNotVerifiedError,
    TokenExpiredError,
    TokenInvalidError,
    RateLimitExceededError
)
from app.auth.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    AuthResponse,
    UserProfile,
    ChangePasswordRequest
)

logger = logging.getLogger(__name__)

# Login attempt tracking
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 30


class AuthService:
    """Main authentication service."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def register_user(self, register_data: RegisterRequest) -> UserProfile:
        """Register a new user."""
        # Check if user already exists
        result = await self.db.execute(
            select(User).where(User.email == register_data.email)
        )
        if result.scalar_one_or_none():
            raise UserAlreadyExistsError()
        
        # Validate password
        validate_password(register_data.password)
        
        # Create new user
        hashed_password = hash_password(register_data.password)
        
        user = User(
            email=register_data.email,
            hashed_password=hashed_password,
            full_name=register_data.full_name,
            company_name=register_data.company_name,
            auth_provider="email",
            is_active=True,
            email_verified=False,  # TODO: Implement email verification
            created_via="registration"
        )
        
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        
        # Log registration event
        await self._log_auth_event(user.id, "registration", {})
        
        logger.info(f"New user registered: {user.email}")
        
        return self._user_to_profile(user)
    
    async def authenticate_user(self, login_data: LoginRequest, user_agent: str = None, ip_address: str = None) -> Tuple[UserProfile, str, str]:
        """
        Authenticate user and return user profile with tokens.
        
        Returns:
            Tuple of (user_profile, access_token, refresh_token)
        """
        # Check rate limiting
        await self._check_login_rate_limit(ip_address or "unknown")
        
        # Find user
        result = await self.db.execute(
            select(User).where(User.email == login_data.email)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            # Log failed login attempt
            await self._log_auth_event(None, "failed_login", {
                "email": login_data.email,
                "reason": "user_not_found",
                "ip_address": ip_address
            })
            raise InvalidCredentialsError()
        
        # Check if account is locked
        await self._check_account_lockout(user.id)
        
        # Verify password
        if not verify_password(login_data.password, user.hashed_password):
            # Record failed attempt
            await self._record_failed_login(user.id, ip_address)
            await self._log_auth_event(user.id, "failed_login", {
                "reason": "invalid_password",
                "ip_address": ip_address
            })
            raise InvalidCredentialsError()
        
        # Check if user is active
        if not user.is_active:
            raise InvalidCredentialsError()
        
        # TODO: Check email verification if required
        # if not user.email_verified:
        #     raise EmailNotVerifiedError()
        
        # Clear any failed login attempts
        await self._clear_failed_logins(user.id)
        
        # Update last login
        user.last_login = datetime.now(timezone.utc)
        await self.db.commit()
        
        # Create tokens - use settings instead of hardcoded values
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS if not login_data.remember_me else 30)
        
        access_token = create_access_token(str(user.id), access_token_expires)
        refresh_token = create_refresh_token(str(user.id), refresh_token_expires)
        
        # Create session record
        await self._create_session(user.id, user_agent, ip_address)
        
        # Log successful login
        await self._log_auth_event(user.id, "login", {
            "ip_address": ip_address,
            "user_agent": user_agent,
            "remember_me": login_data.remember_me
        })
        
        logger.info(f"User logged in: {user.email}")
        
        return self._user_to_profile(user), access_token, refresh_token
    
    async def refresh_access_token(self, refresh_token: str) -> Tuple[str, str]:
        """
        Refresh access token using refresh token.
        
        Returns:
            Tuple of (new_access_token, new_refresh_token)
        """
        # Verify refresh token
        payload = await verify_token(refresh_token, "refresh")
        user_id = payload["sub"]
        jti = payload["jti"]
        
        # Check if user exists and is active
        result = await self.db.execute(
            select(User).where(User.id == int(user_id))
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.is_active:
            raise TokenInvalidError()
        
        # Blacklist old refresh token
        await blacklist_token(jti)
        
        # Create new tokens (token rotation)
        new_access_token = create_access_token(user_id)
        new_refresh_token = create_refresh_token(user_id)
        
        logger.info(f"Tokens refreshed for user: {user.email}")
        
        return new_access_token, new_refresh_token
    
    async def logout_user(self, refresh_token: str) -> None:
        """Logout user by blacklisting refresh token."""
        try:
            payload = await verify_token(refresh_token, "refresh")
            jti = payload["jti"]
            user_id = payload["sub"]
            
            # Blacklist the refresh token
            await blacklist_token(jti)
            
            # Log logout event
            await self._log_auth_event(int(user_id), "logout", {})
            
            logger.info(f"User logged out: {user_id}")
            
        except (TokenExpiredError, TokenInvalidError):
            # Token already invalid, nothing to do
            pass
    
    async def logout_all_devices(self, user_id: int) -> None:
        """Logout user from all devices."""
        await blacklist_all_user_tokens(str(user_id))
        
        # Log logout all event
        await self._log_auth_event(user_id, "logout_all", {})
        
        logger.info(f"User logged out from all devices: {user_id}")
    
    async def change_password(self, user_id: int, change_data: ChangePasswordRequest) -> None:
        """Change user password."""
        # Get user
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise UserNotFoundError()
        
        # Verify current password
        if not verify_password(change_data.current_password, user.hashed_password):
            raise InvalidCredentialsError()
        
        # Validate new password
        validate_password(change_data.new_password)
        
        # Update password
        user.hashed_password = hash_password(change_data.new_password)
        user.password_last_changed = datetime.now(timezone.utc)
        
        await self.db.commit()
        
        # Logout from all devices for security
        await self.logout_all_devices(user_id)
        
        # Log password change
        await self._log_auth_event(user_id, "password_change", {})
        
        logger.info(f"Password changed for user: {user.email}")
    
    async def get_user_by_id(self, user_id: int) -> Optional[UserProfile]:
        """Get user by ID."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        return self._user_to_profile(user)
    
    async def complete_onboarding(self, user_id: int) -> UserProfile:
        """Mark user onboarding as complete."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise UserNotFoundError()
        
        if not user.is_active:
            raise InvalidCredentialsError()
        
        # Mark onboarding as complete
        user.onboarding_completed = True
        await self.db.commit()
        await self.db.refresh(user)
        
        # Log onboarding completion
        await self._log_auth_event(user_id, "onboarding_completed", {})
        
        logger.info(f"Onboarding completed for user: {user.email}")
        
        return self._user_to_profile(user)
    
    def _user_to_profile(self, user: User) -> UserProfile:
        """Convert User model to UserProfile schema."""
        return UserProfile(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            company_name=user.company_name,
            avatar_url=getattr(user, 'avatar_url', None),
            auth_provider=getattr(user, 'auth_provider', 'email'),
            email_verified=getattr(user, 'email_verified', False),
            onboarding_completed=getattr(user, 'onboarding_completed', False),
            created_at=user.created_at.isoformat() if hasattr(user, 'created_at') and user.created_at else "",
            last_login=user.last_login.isoformat() if user.last_login else None,
            google_scopes=getattr(user, 'google_scopes', None),
            google_token_expires_at=user.google_token_expires_at.isoformat() if hasattr(user, 'google_token_expires_at') and user.google_token_expires_at else None
        )
    
    async def _check_login_rate_limit(self, ip_address: str) -> None:
        """Check login rate limiting."""
        redis_client = await get_redis_client()
        key = f"login_attempts:{ip_address}"
        
        # More lenient limits in development
        from app.core.config import settings
        max_attempts = 100 if settings.ENVIRONMENT == "development" else 10
        window_seconds = 60 if settings.ENVIRONMENT == "development" else 3600
        
        current_attempts = await redis_client.get(key)
        if current_attempts and int(current_attempts) >= max_attempts:
            raise RateLimitExceededError(window_seconds)
        
        # Increment attempts
        pipe = redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, window_seconds)
        await pipe.execute()
    
    async def _check_account_lockout(self, user_id: int) -> None:
        """Check if account is locked due to failed login attempts."""
        redis_client = await get_redis_client()
        key = f"failed_logins:{user_id}"
        
        failed_attempts = await redis_client.get(key)
        if failed_attempts and int(failed_attempts) >= MAX_LOGIN_ATTEMPTS:
            # Check if lockout period has expired
            ttl = await redis_client.ttl(key)
            if ttl > 0:
                raise AccountLockedError(ttl // 60)  # Convert to minutes
    
    async def _record_failed_login(self, user_id: int, ip_address: str = None) -> None:
        """Record a failed login attempt."""
        redis_client = await get_redis_client()
        key = f"failed_logins:{user_id}"
        
        pipe = redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, LOCKOUT_DURATION_MINUTES * 60)  # Convert to seconds
        await pipe.execute()
    
    async def _clear_failed_logins(self, user_id: int) -> None:
        """Clear failed login attempts for user."""
        redis_client = await get_redis_client()
        await redis_client.delete(f"failed_logins:{user_id}")
    
    async def _create_session(self, user_id: int, user_agent: str = None, ip_address: str = None) -> None:
        """Create a session record."""
        # TODO: Implement session tracking in database
        # For now, we'll just log it
        pass
    
    async def _log_auth_event(self, user_id: Optional[int], event_type: str, details: dict) -> None:
        """Log authentication event."""
        # TODO: Implement auth event logging
        # For now, we'll just log to the logger
        logger.info(f"Auth event - User: {user_id}, Event: {event_type}, Details: {details}")