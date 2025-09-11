"""
Password reset API endpoints.

This module provides API endpoints for password reset functionality.
"""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from app.db.session import get_db
from app.services.password_reset_service import PasswordResetService
from app.core.rate_limit_dependencies import (
    rate_limit_auth_endpoints,
    create_rate_limit_dependency
)

# Create a very strict rate limit for password reset
rate_limit_password_reset = create_rate_limit_dependency(limit=3, window=300)  # 3 requests per 5 minutes

router = APIRouter()


class PasswordResetRequest(BaseModel):
    """Schema for password reset request."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation."""
    token: str
    new_password: str


class PasswordResetTokenValidate(BaseModel):
    """Schema for token validation request."""
    token: str


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str


class TokenValidationResponse(BaseModel):
    """Token validation response."""
    valid: bool


@router.post("/forgot-password", response_model=MessageResponse)
async def request_password_reset(
    request: PasswordResetRequest,
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit_password_reset)  # 3 requests per 5 minutes
) -> Any:
    """
    Request a password reset.
    
    Sends a password reset email to the user if the email exists.
    Always returns success to prevent email enumeration.
    """
    service = PasswordResetService(db)
    await service.create_reset_token(request.email)
    
    # Always return success to prevent email enumeration
    return {
        "message": "If an account exists with this email, you will receive a password reset link."
    }


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    request: PasswordResetConfirm,
    db: Session = Depends(get_db)
) -> Any:
    """
    Reset password using a valid token.
    
    Validates the token and updates the user's password.
    """
    service = PasswordResetService(db)
    success = await service.reset_password(request.token, request.new_password)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    return {
        "message": "Password has been reset successfully"
    }


@router.post("/validate-reset-token", response_model=TokenValidationResponse)
async def validate_reset_token(
    request: PasswordResetTokenValidate,
    db: Session = Depends(get_db)
) -> Any:
    """
    Validate a password reset token.
    
    Checks if the token is valid and not expired.
    """
    service = PasswordResetService(db)
    is_valid = await service.validate_token(request.token)
    
    return {
        "valid": is_valid
    }