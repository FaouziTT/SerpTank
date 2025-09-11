"""Core security functions for authentication."""

import secrets
import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import redis.asyncio as redis
from passlib.context import CryptContext
from jose import jwt, JWTError
import logging

from app.core.config import settings
from .exceptions import (
    TokenExpiredError,
    TokenInvalidError,
    TokenBlacklistedError,
    PasswordValidationError
)

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT configuration - use settings instead of hardcoded values
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

# Redis client for token blacklisting
_redis_client: Optional[redis.Redis] = None


async def get_redis_client() -> redis.Redis:
    """Get Redis client for token blacklisting."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}")
    return _redis_client


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def get_password_hash(password: str) -> str:
    """Alias for hash_password for compatibility."""
    return hash_password(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def validate_password(password: str) -> bool:
    """
    Validate password meets security requirements.
    
    Requirements:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter  
    - At least one digit
    - At least one special character
    """
    if len(password) < 8:
        raise PasswordValidationError("Password must be at least 8 characters long")
    
    if len(password) > 128:
        raise PasswordValidationError("Password must be less than 128 characters")
    
    if not re.search(r"[A-Z]", password):
        raise PasswordValidationError("Password must contain at least one uppercase letter")
    
    if not re.search(r"[a-z]", password):
        raise PasswordValidationError("Password must contain at least one lowercase letter")
    
    if not re.search(r"\d", password):
        raise PasswordValidationError("Password must contain at least one digit")
    
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        raise PasswordValidationError("Password must contain at least one special character")
    
    return True


def generate_session_token() -> str:
    """Generate a secure session token."""
    return secrets.token_urlsafe(32)


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "access",
        "iat": datetime.now(timezone.utc)
    }
    
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT refresh token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "refresh",
        "iat": datetime.now(timezone.utc),
        "jti": secrets.token_urlsafe(16)  # Unique ID for blacklisting
    }
    
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


async def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token to verify
        token_type: Expected token type ("access" or "refresh")
        
    Returns:
        Token payload
        
    Raises:
        TokenInvalidError: If token is invalid
        TokenExpiredError: If token is expired
        TokenBlacklistedError: If token is blacklisted
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        
        # Check token type
        if payload.get("type") != token_type:
            raise TokenInvalidError()
        
        # Check if refresh token is blacklisted
        if token_type == "refresh":
            jti = payload.get("jti")
            if jti and await is_token_blacklisted(jti):
                raise TokenBlacklistedError()
        
        return payload
        
    except jwt.ExpiredSignatureError:
        raise TokenExpiredError()
    except JWTError:
        raise TokenInvalidError()


async def blacklist_token(jti: str, expires_in: int = None) -> None:
    """Add a token JTI to the blacklist."""
    redis_client = await get_redis_client()
    if expires_in is None:
        expires_in = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60  # Convert days to seconds
    
    await redis_client.setex(f"blacklist:{jti}", expires_in, "1")


async def is_token_blacklisted(jti: str) -> bool:
    """Check if a token JTI is blacklisted."""
    redis_client = await get_redis_client()
    result = await redis_client.get(f"blacklist:{jti}")
    return result is not None


async def blacklist_all_user_tokens(user_id: str) -> None:
    """Blacklist all tokens for a user (useful for logout all devices)."""
    redis_client = await get_redis_client()
    await redis_client.setex(
        f"user_logout:{user_id}", 
        REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,  # Expire after max token lifetime
        str(datetime.now(timezone.utc).timestamp())
    )


async def is_user_logged_out(user_id: str, token_issued_at: float) -> bool:
    """Check if user was logged out after token was issued."""
    redis_client = await get_redis_client()
    logout_time = await redis_client.get(f"user_logout:{user_id}")
    
    if logout_time is None:
        return False
    
    return float(logout_time) > token_issued_at


def extract_token_from_header(authorization: str) -> str:
    """Extract token from Authorization header."""
    if not authorization:
        raise TokenInvalidError()
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise TokenInvalidError()
        return token
    except ValueError:
        raise TokenInvalidError()


class TokenData:
    """Token data container."""
    
    def __init__(self, user_id: str, token_type: str, expires_at: datetime, jti: Optional[str] = None):
        self.user_id = user_id
        self.token_type = token_type
        self.expires_at = expires_at
        self.jti = jti
    
    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return datetime.now(timezone.utc) > self.expires_at