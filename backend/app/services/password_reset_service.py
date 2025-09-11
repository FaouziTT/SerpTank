"""
Password reset service.

This module handles password reset functionality including token generation,
email sending, and password updates.
"""
from datetime import datetime, timezone
from typing import Optional
import logging

from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select

from app.models import User, PasswordResetToken
from app.auth.core.security import get_password_hash
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class PasswordResetService:
    """Service for handling password reset operations."""
    
    def __init__(self, db: Session):
        self.db = db
        self.notification_service = NotificationService(db)
    
    async def create_reset_token(self, email: str) -> Optional[PasswordResetToken]:
        """
        Create a password reset token for a user.
        
        Args:
            email: The email address of the user
            
        Returns:
            The created PasswordResetToken or None if user not found
        """
        # Find user by email
        stmt = select(User).where(User.email == email)
        user = self.db.execute(stmt).scalar_one_or_none()
        
        if not user:
            # Don't reveal whether the email exists
            logger.info(f"Password reset requested for non-existent email: {email}")
            return None
        
        # Invalidate any existing unused tokens for this user
        existing_tokens = self.db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.used == False
            )
        ).scalars().all()
        
        for token in existing_tokens:
            token.mark_as_used()
        
        # Create new token
        reset_token = PasswordResetToken.create_for_user(user.id)
        self.db.add(reset_token)
        self.db.commit()
        
        # Send reset email
        await self._send_reset_email(user, reset_token)
        
        logger.info(f"Password reset token created for user {user.id}")
        return reset_token
    
    async def _send_reset_email(self, user: User, token: PasswordResetToken) -> None:
        """Send password reset email to user."""
        # TODO: Replace with actual frontend URL from config
        reset_url = f"https://voltex.app/reset-password/{token.token}"
        
        subject = "Reset Your Voltex Password"
        body = f"""
        Hello {user.full_name},
        
        We received a request to reset your password for your Voltex account.
        
        Click the link below to reset your password:
        {reset_url}
        
        This link will expire in 1 hour.
        
        If you didn't request this password reset, please ignore this email.
        Your password will remain unchanged.
        
        Best regards,
        The Voltex Team
        """
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2563eb;">Reset Your Password</h2>
                
                <p>Hello {user.full_name},</p>
                
                <p>We received a request to reset your password for your Voltex account.</p>
                
                <p>Click the button below to reset your password:</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}" 
                       style="background-color: #2563eb; color: white; padding: 12px 24px; 
                              text-decoration: none; border-radius: 4px; display: inline-block;">
                        Reset Password
                    </a>
                </div>
                
                <p>Or copy and paste this link into your browser:</p>
                <p style="word-break: break-all; color: #2563eb;">{reset_url}</p>
                
                <p><strong>This link will expire in 1 hour.</strong></p>
                
                <p>If you didn't request this password reset, please ignore this email. 
                   Your password will remain unchanged.</p>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                
                <p style="color: #666; font-size: 14px;">
                    Best regards,<br>
                    The Voltex Team
                </p>
            </div>
        </body>
        </html>
        """
        
        # TODO: Implement actual email sending
        # For now, we'll create a notification
        await self.notification_service.create_notification(
            user_id=user.id,
            title="Password Reset Requested",
            message=f"Password reset link: {reset_url}",
            notification_type="system",
            priority="high"
        )
    
    async def reset_password(self, token_string: str, new_password: str) -> bool:
        """
        Reset a user's password using a valid token.
        
        Args:
            token_string: The reset token string
            new_password: The new password
            
        Returns:
            True if password was reset successfully, False otherwise
        """
        # Find the token
        stmt = select(PasswordResetToken).where(
            PasswordResetToken.token == token_string
        ).options(
            # Eagerly load the user relationship
            selectinload(PasswordResetToken.user)
        )
        
        reset_token = self.db.execute(stmt).scalar_one_or_none()
        
        if not reset_token:
            logger.warning(f"Invalid password reset token attempted: {token_string[:8]}...")
            return False
        
        if not reset_token.is_valid():
            logger.warning(f"Expired or used password reset token attempted: {token_string[:8]}...")
            return False
        
        # Update user's password
        user = reset_token.user
        user.hashed_password = get_password_hash(new_password)
        user.password_last_changed = datetime.now(timezone.utc)
        
        # Mark token as used
        reset_token.mark_as_used()
        
        self.db.commit()
        
        # Send confirmation email
        await self._send_confirmation_email(user)
        
        logger.info(f"Password successfully reset for user {user.id}")
        return True
    
    async def _send_confirmation_email(self, user: User) -> None:
        """Send password reset confirmation email."""
        subject = "Your Voltex Password Has Been Reset"
        body = f"""
        Hello {user.full_name},
        
        Your password has been successfully reset.
        
        If you did not make this change, please contact our support team immediately.
        
        Best regards,
        The Voltex Team
        """
        
        # TODO: Implement actual email sending
        await self.notification_service.create_notification(
            user_id=user.id,
            title="Password Reset Successful",
            message="Your password has been successfully reset.",
            notification_type="system",
            priority="medium"
        )
    
    async def validate_token(self, token_string: str) -> bool:
        """
        Validate if a reset token is valid.
        
        Args:
            token_string: The reset token string
            
        Returns:
            True if token is valid, False otherwise
        """
        stmt = select(PasswordResetToken).where(
            PasswordResetToken.token == token_string
        )
        
        reset_token = self.db.execute(stmt).scalar_one_or_none()
        
        if not reset_token:
            return False
        
        return reset_token.is_valid()