"""
Secure session management using httpOnly cookies instead of localStorage.
This replaces the insecure localStorage JWT storage pattern.
"""

import secrets
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple
import redis.asyncio as redis
from fastapi import Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.security.utils import get_authorization_scheme_param
import logging

from app.core.config import settings
from .security import verify_token, create_access_token, create_refresh_token, blacklist_token
from .exceptions import (
    TokenExpiredError,
    TokenInvalidError,
    TokenBlacklistedError,
    SessionInvalidError
)

logger = logging.getLogger(__name__)

# Session configuration
SESSION_COOKIE_NAME = "voltex_session"
CSRF_COOKIE_NAME = "voltex_csrf_token"
SESSION_EXPIRE_HOURS = 24  # Session expires in 24 hours
CSRF_TOKEN_EXPIRE_HOURS = 12  # CSRF token expires in 12 hours

# Cookie security settings
COOKIE_SECURE = settings.ENVIRONMENT.lower() == "production"  # Only HTTPS in production
COOKIE_SAMESITE = "strict" if settings.ENVIRONMENT.lower() == "production" else "lax"
COOKIE_HTTPONLY = True  # Prevent XSS attacks
COOKIE_DOMAIN = None  # Let browser set domain automatically

# Redis client for session storage
_redis_client: Optional[redis.Redis] = None


async def get_redis_client() -> redis.Redis:
    """Get Redis client for session storage."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/1")  # Use DB 1 for sessions
    return _redis_client


def generate_session_id() -> str:
    """Generate a cryptographically secure session ID."""
    return secrets.token_urlsafe(32)


def generate_csrf_token() -> str:
    """Generate a cryptographically secure CSRF token."""
    return secrets.token_urlsafe(24)


class SessionData:
    """Container for session data."""
    
    def __init__(
        self,
        user_id: str,
        session_id: str,
        csrf_token: str,
        created_at: datetime,
        last_accessed: datetime,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        is_remember_me: bool = False
    ):
        self.user_id = user_id
        self.session_id = session_id
        self.csrf_token = csrf_token
        self.created_at = created_at
        self.last_accessed = last_accessed
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.is_remember_me = is_remember_me
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session data to dictionary for Redis storage."""
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "csrf_token": self.csrf_token,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "is_remember_me": self.is_remember_me
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionData":
        """Create SessionData from dictionary."""
        return cls(
            user_id=data["user_id"],
            session_id=data["session_id"],
            csrf_token=data["csrf_token"],
            created_at=datetime.fromisoformat(data["created_at"]),
            last_accessed=datetime.fromisoformat(data["last_accessed"]),
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
            is_remember_me=data.get("is_remember_me", False)
        )
    
    @property
    def is_expired(self) -> bool:
        """Check if session is expired."""
        expire_hours = 24 * 7 if self.is_remember_me else SESSION_EXPIRE_HOURS  # 7 days for remember me
        expire_time = self.last_accessed + timedelta(hours=expire_hours)
        return datetime.now(timezone.utc) > expire_time.replace(tzinfo=timezone.utc)


class SecureSessionManager:
    """Manages secure sessions using httpOnly cookies and Redis storage."""
    
    @staticmethod
    async def create_session(
        response: Response,
        user_id: str,
        request: Request,
        remember_me: bool = False
    ) -> SessionData:
        """
        Create a new secure session.
        
        Args:
            response: FastAPI Response object to set cookies
            user_id: ID of the user
            request: FastAPI Request object for IP/User-Agent
            remember_me: Whether this is a "remember me" session
            
        Returns:
            SessionData object
        """
        redis_client = await get_redis_client()
        
        # Generate session ID and CSRF token
        session_id = generate_session_id()
        csrf_token = generate_csrf_token()
        
        # Get client info
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("User-Agent")
        
        # Create session data
        now = datetime.now(timezone.utc)
        session_data = SessionData(
            user_id=user_id,
            session_id=session_id,
            csrf_token=csrf_token,
            created_at=now,
            last_accessed=now,
            ip_address=ip_address,
            user_agent=user_agent,
            is_remember_me=remember_me
        )
        
        # Store session in Redis
        expire_seconds = (24 * 7 * 3600) if remember_me else (SESSION_EXPIRE_HOURS * 3600)
        await redis_client.setex(
            f"session:{session_id}",
            expire_seconds,
            json.dumps(session_data.to_dict(), default=str)
        )
        
        # Set httpOnly session cookie
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=session_id,
            max_age=expire_seconds,
            httponly=COOKIE_HTTPONLY,
            secure=COOKIE_SECURE,
            samesite=COOKIE_SAMESITE,
            domain=COOKIE_DOMAIN,
            path="/"
        )
        
        # Set CSRF token cookie (not httpOnly so frontend can read it)
        response.set_cookie(
            key=CSRF_COOKIE_NAME,
            value=csrf_token,
            max_age=CSRF_TOKEN_EXPIRE_HOURS * 3600,
            httponly=False,  # Frontend needs to read this for CSRF protection
            secure=COOKIE_SECURE,
            samesite=COOKIE_SAMESITE,
            domain=COOKIE_DOMAIN,
            path="/"
        )
        
        logger.info(f"Created secure session for user {user_id}, session_id: {session_id}")
        return session_data
    
    @staticmethod
    async def get_session(request: Request) -> Optional[SessionData]:
        """
        Get session data from request.
        
        Args:
            request: FastAPI Request object
            
        Returns:
            SessionData if valid session exists, None otherwise
        """
        # Get session ID from cookie
        session_id = request.cookies.get(SESSION_COOKIE_NAME)
        if not session_id:
            return None
        
        redis_client = await get_redis_client()
        
        # Get session data from Redis
        session_json = await redis_client.get(f"session:{session_id}")
        if not session_json:
            return None
        
        try:
            session_dict = json.loads(session_json)
            session_data = SessionData.from_dict(session_dict)
            
            # Check if session is expired
            if session_data.is_expired:
                await SecureSessionManager.destroy_session(session_id)
                return None
            
            # Update last accessed time
            session_data.last_accessed = datetime.now(timezone.utc)
            expire_seconds = (24 * 7 * 3600) if session_data.is_remember_me else (SESSION_EXPIRE_HOURS * 3600)
            await redis_client.setex(
                f"session:{session_id}",
                expire_seconds,
                json.dumps(session_data.to_dict(), default=str)
            )
            
            return session_data
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Invalid session data for session_id {session_id}: {e}")
            await SecureSessionManager.destroy_session(session_id)
            return None
    
    @staticmethod
    async def destroy_session(session_id: str) -> None:
        """
        Destroy a session.
        
        Args:
            session_id: Session ID to destroy
        """
        redis_client = await get_redis_client()
        await redis_client.delete(f"session:{session_id}")
        logger.info(f"Destroyed session: {session_id}")
    
    @staticmethod
    async def destroy_user_sessions(user_id: str) -> int:
        """
        Destroy all sessions for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Number of sessions destroyed
        """
        redis_client = await get_redis_client()
        
        # Find all sessions for this user
        session_keys = []
        async for key in redis_client.scan_iter(match="session:*"):
            session_json = await redis_client.get(key)
            if session_json:
                try:
                    session_dict = json.loads(session_json)
                    if session_dict.get("user_id") == user_id:
                        session_keys.append(key)
                except (json.JSONDecodeError, KeyError):
                    continue
        
        # Delete all user sessions
        if session_keys:
            await redis_client.delete(*session_keys)
            logger.info(f"Destroyed {len(session_keys)} sessions for user {user_id}")
        
        return len(session_keys)
    
    @staticmethod
    async def clear_session_cookies(response: Response) -> None:
        """
        Clear session cookies from response.
        
        Args:
            response: FastAPI Response object
        """
        # Clear session cookie
        response.delete_cookie(
            key=SESSION_COOKIE_NAME,
            httponly=COOKIE_HTTPONLY,
            secure=COOKIE_SECURE,
            samesite=COOKIE_SAMESITE,
            domain=COOKIE_DOMAIN,
            path="/"
        )
        
        # Clear CSRF cookie
        response.delete_cookie(
            key=CSRF_COOKIE_NAME,
            httponly=False,
            secure=COOKIE_SECURE,
            samesite=COOKIE_SAMESITE,
            domain=COOKIE_DOMAIN,
            path="/"
        )
    
    @staticmethod
    def validate_csrf_token(request: Request, session_data: SessionData) -> bool:
        """
        Validate CSRF token from request against session.
        
        Args:
            request: FastAPI Request object
            session_data: Current session data
            
        Returns:
            True if CSRF token is valid
        """
        # Get CSRF token from header (preferred) or form data
        csrf_token = (
            request.headers.get("X-CSRF-Token") or
            request.headers.get("X-CSRFToken") or
            request.cookies.get(CSRF_COOKIE_NAME)
        )
        
        if not csrf_token:
            logger.warning("Missing CSRF token in request")
            return False
        
        if csrf_token != session_data.csrf_token:
            logger.warning(f"Invalid CSRF token for session {session_data.session_id}")
            return False
        
        return True


class SecureSessionBearer(HTTPBearer):
    """
    Custom HTTPBearer that supports both JWT tokens and secure sessions.
    This maintains backward compatibility while adding secure session support.
    """
    
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
    
    async def __call__(self, request: Request) -> Optional[HTTPAuthorizationCredentials]:
        """
        Extract and validate authentication from request.
        
        Supports both:
        1. Secure sessions (preferred)
        2. JWT Bearer tokens (for API compatibility)
        """
        # Try secure session first
        session_data = await SecureSessionManager.get_session(request)
        if session_data:
            # Create a fake HTTPAuthorizationCredentials for compatibility
            return HTTPAuthorizationCredentials(
                scheme="Session",
                credentials=f"session:{session_data.user_id}"
            )
        
        # Fallback to JWT Bearer token
        authorization = request.headers.get("Authorization")
        if authorization:
            scheme, credentials = get_authorization_scheme_param(authorization)
            if scheme.lower() == "bearer":
                return HTTPAuthorizationCredentials(scheme=scheme, credentials=credentials)
        
        if self.auto_error:
            raise SessionInvalidError("Invalid session or missing authentication")
        
        return None