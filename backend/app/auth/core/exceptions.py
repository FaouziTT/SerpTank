"""Custom authentication exceptions."""

from fastapi import HTTPException, status


class AuthenticationError(HTTPException):
    """Base authentication error."""
    
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )


class InvalidCredentialsError(AuthenticationError):
    """Invalid email or password."""
    
    def __init__(self):
        super().__init__("Invalid email or password")


class AccountLockedError(AuthenticationError):
    """Account is locked due to too many failed attempts."""
    
    def __init__(self, retry_after: int):
        super().__init__(f"Account locked. Try again in {retry_after} minutes")


class EmailNotVerifiedError(AuthenticationError):
    """Email address not verified."""
    
    def __init__(self):
        super().__init__("Email address not verified")


class TokenExpiredError(AuthenticationError):
    """Token has expired."""
    
    def __init__(self):
        super().__init__("Token has expired")


class TokenInvalidError(AuthenticationError):
    """Token is invalid."""
    
    def __init__(self):
        super().__init__("Invalid token")


class TokenBlacklistedError(AuthenticationError):
    """Token has been blacklisted."""
    
    def __init__(self):
        super().__init__("Token has been revoked")


class UserNotFoundError(HTTPException):
    """User not found."""
    
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )


class UserAlreadyExistsError(HTTPException):
    """User already exists."""
    
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists"
        )


class PasswordValidationError(HTTPException):
    """Password doesn't meet requirements."""
    
    def __init__(self, detail: str = "Password doesn't meet requirements"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )


class RateLimitExceededError(HTTPException):
    """Rate limit exceeded."""
    
    def __init__(self, retry_after: int):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many requests. Try again in {retry_after} seconds",
            headers={"Retry-After": str(retry_after)}
        )


class SessionInvalidError(AuthenticationError):
    """Session is invalid or expired."""
    
    def __init__(self, detail: str = "Session is invalid or expired"):
        super().__init__(detail)


class GoogleAuthError(HTTPException):
    """Google authentication error."""
    
    def __init__(self, detail: str = "Google authentication failed"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )