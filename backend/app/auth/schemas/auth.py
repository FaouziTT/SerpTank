"""Authentication request/response schemas."""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field, validator
import re


class LoginRequest(BaseModel):
    """Login request schema."""
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)
    remember_me: bool = False


class RegisterRequest(BaseModel):
    """Registration request schema."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=255)
    company_name: Optional[str] = Field(None, max_length=255)
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password meets security requirements."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character")
        
        return v


class ForgotPasswordRequest(BaseModel):
    """Forgot password request schema."""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Reset password request schema."""
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)
    
    @validator('new_password')
    def validate_password(cls, v):
        """Validate password meets security requirements."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character")
        
        return v


class ChangePasswordRequest(BaseModel):
    """Change password request schema."""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)
    
    @validator('new_password')
    def validate_password(cls, v):
        """Validate password meets security requirements."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character")
        
        return v


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema."""
    refresh_token: str


class GoogleAuthRequest(BaseModel):
    """Google authentication request schema."""
    code: str
    state: Optional[str] = None


class LinkGoogleAccountRequest(BaseModel):
    """Link Google account request schema."""
    google_code: str
    password: str  # Current account password for verification


class UserProfile(BaseModel):
    """User profile schema."""
    id: int
    email: str
    full_name: str
    company_name: Optional[str] = None
    avatar_url: Optional[str] = None
    auth_provider: str
    email_verified: bool
    onboarding_completed: bool = False
    created_at: str
    last_login: Optional[str] = None
    google_scopes: Optional[str] = None
    google_token_expires_at: Optional[str] = None
    two_factor_enabled: bool = False
    password_last_changed: Optional[str] = None
    
    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    """Authentication response schema."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: UserProfile


class MessageResponse(BaseModel):
    """Simple message response schema."""
    message: str


class SessionInfo(BaseModel):
    """Session information schema."""
    id: int
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: str
    last_seen: str
    is_current: bool
    
    class Config:
        from_attributes = True


class UserSessionsResponse(BaseModel):
    """User sessions response schema."""
    sessions: list[SessionInfo]