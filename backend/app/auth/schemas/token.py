"""Token schemas."""

from typing import Optional
from pydantic import BaseModel, Field


class TokenData(BaseModel):
    """Token data schema."""
    user_id: str
    token_type: str
    expires_at: str
    jti: Optional[str] = None
    sub: Optional[str] = None  # Subject (user ID)
    exp: Optional[int] = None  # Expiration time
    iat: Optional[int] = None  # Issued at


class TokenResponse(BaseModel):
    """Token response schema."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshTokenResponse(BaseModel):
    """Refresh token response schema."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshTokenRequest(BaseModel):
    """Request to refresh access token."""
    refresh_token: str = Field(..., description="Refresh token")


class TokenMigrationRequest(BaseModel):
    """Request to migrate tokens to httpOnly cookies."""
    refresh_token: str = Field(..., description="Refresh token to migrate")


class TokenMigrationResponse(BaseModel):
    """Response after successful token migration."""
    message: str = Field(..., description="Migration status message")
    expires_in: int = Field(..., description="Access token expiration time in seconds")


class TokenVerificationResponse(BaseModel):
    """Response for token verification."""
    valid: bool = Field(..., description="Whether the token is valid")
    expires_at: Optional[int] = Field(None, description="Token expiration timestamp")
    token_type: Optional[str] = Field(None, description="Type of token")
    user_id: Optional[int] = Field(None, description="User ID from token")