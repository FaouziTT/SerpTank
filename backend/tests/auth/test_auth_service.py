"""
Tests for authentication service.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.auth.services.auth_service import AuthService
from app.auth.schemas.auth import RegisterRequest, LoginRequest, ChangePasswordRequest
from app.auth.core.exceptions import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    AccountLockedError
)
from app.models.user import User


@pytest.mark.auth
class TestAuthService:
    """Test cases for AuthService."""
    
    async def test_register_user_success(
        self,
        async_session: AsyncSession,
        auth_service: AuthService
    ):
        """Test successful user registration."""
        register_data = RegisterRequest(
            email="newuser@example.com",
            password="securepassword123",
            full_name="New User"
        )
        
        user_profile = await auth_service.register_user(register_data)
        
        assert user_profile.email == register_data.email
        assert user_profile.full_name == register_data.full_name
        assert user_profile.is_active is True
        assert user_profile.is_superuser is False
        
        # Verify user exists in database
        from sqlalchemy import select
        result = await async_session.execute(
            select(User).where(User.email == register_data.email)
        )
        db_user = result.scalar_one_or_none()
        assert db_user is not None
        assert db_user.email == register_data.email
    
    async def test_register_user_duplicate_email(
        self,
        async_session: AsyncSession,
        auth_service: AuthService,
        test_user: User
    ):
        """Test registration with existing email."""
        register_data = RegisterRequest(
            email=test_user.email,
            password="securepassword123",
            full_name="Duplicate User"
        )
        
        with pytest.raises(UserAlreadyExistsError):
            await auth_service.register_user(register_data)
    
    async def test_authenticate_user_success(
        self,
        async_session: AsyncSession,
        auth_service: AuthService,
        test_user: User
    ):
        """Test successful user authentication."""
        login_data = LoginRequest(
            email=test_user.email,
            password="testpassword123",
            remember_me=False
        )
        
        user_profile, access_token, refresh_token = await auth_service.authenticate_user(
            login_data, "test-agent", "127.0.0.1"
        )
        
        assert user_profile.email == test_user.email
        assert user_profile.id == test_user.id
        assert access_token is not None
        assert refresh_token is not None
    
    async def test_authenticate_user_invalid_email(
        self,
        async_session: AsyncSession,
        auth_service: AuthService
    ):
        """Test authentication with invalid email."""
        login_data = LoginRequest(
            email="nonexistent@example.com",
            password="password123",
            remember_me=False
        )
        
        with pytest.raises(InvalidCredentialsError):
            await auth_service.authenticate_user(
                login_data, "test-agent", "127.0.0.1"
            )
    
    async def test_authenticate_user_invalid_password(
        self,
        async_session: AsyncSession,
        auth_service: AuthService,
        test_user: User
    ):
        """Test authentication with invalid password."""
        login_data = LoginRequest(
            email=test_user.email,
            password="wrongpassword",
            remember_me=False
        )
        
        with pytest.raises(InvalidCredentialsError):
            await auth_service.authenticate_user(
                login_data, "test-agent", "127.0.0.1"
            )
    
    async def test_authenticate_inactive_user(
        self,
        async_session: AsyncSession,
        auth_service: AuthService,
        user_factory
    ):
        """Test authentication with inactive user."""
        inactive_user = await user_factory.create_user(
            async_session,
            email="inactive@example.com",
            is_active=False
        )
        
        login_data = LoginRequest(
            email=inactive_user.email,
            password="password123",
            remember_me=False
        )
        
        with pytest.raises(InvalidCredentialsError):
            await auth_service.authenticate_user(
                login_data, "test-agent", "127.0.0.1"
            )
    
    async def test_refresh_access_token_success(
        self,
        async_session: AsyncSession,
        auth_service: AuthService,
        test_user: User
    ):
        """Test successful token refresh."""
        # First authenticate to get refresh token
        login_data = LoginRequest(
            email=test_user.email,
            password="testpassword123",
            remember_me=False
        )
        
        user_profile, access_token, refresh_token = await auth_service.authenticate_user(
            login_data, "test-agent", "127.0.0.1"
        )
        
        # Now refresh the token
        new_access_token, new_refresh_token = await auth_service.refresh_access_token(
            refresh_token
        )
        
        assert new_access_token is not None
        assert new_refresh_token is not None
        assert new_access_token != access_token
        assert new_refresh_token != refresh_token
    
    async def test_change_password_success(
        self,
        async_session: AsyncSession,
        auth_service: AuthService,
        test_user: User
    ):
        """Test successful password change."""
        change_data = ChangePasswordRequest(
            current_password="testpassword123",
            new_password="newsecurepassword456"
        )
        
        await auth_service.change_password(test_user.id, change_data)
        
        # Verify user can login with new password
        login_data = LoginRequest(
            email=test_user.email,
            password="newsecurepassword456",
            remember_me=False
        )
        
        user_profile, _, _ = await auth_service.authenticate_user(
            login_data, "test-agent", "127.0.0.1"
        )
        
        assert user_profile.email == test_user.email
    
    async def test_change_password_invalid_current(
        self,
        async_session: AsyncSession,
        auth_service: AuthService,
        test_user: User
    ):
        """Test password change with invalid current password."""
        change_data = ChangePasswordRequest(
            current_password="wrongcurrentpassword",
            new_password="newsecurepassword456"
        )
        
        with pytest.raises(InvalidCredentialsError):
            await auth_service.change_password(test_user.id, change_data)
    
    async def test_logout_user_success(
        self,
        async_session: AsyncSession,
        auth_service: AuthService,
        test_user: User
    ):
        """Test successful user logout."""
        # First authenticate to get refresh token
        login_data = LoginRequest(
            email=test_user.email,
            password="testpassword123",
            remember_me=False
        )
        
        user_profile, access_token, refresh_token = await auth_service.authenticate_user(
            login_data, "test-agent", "127.0.0.1"
        )
        
        # Logout (blacklist refresh token)
        await auth_service.logout_user(refresh_token)
        
        # Verify refresh token is now invalid
        from app.auth.core.exceptions import TokenInvalidError
        with pytest.raises(TokenInvalidError):
            await auth_service.refresh_access_token(refresh_token)
    
    async def test_logout_all_devices(
        self,
        async_session: AsyncSession,
        auth_service: AuthService,
        test_user: User
    ):
        """Test logout from all devices."""
        # Create multiple sessions
        login_data = LoginRequest(
            email=test_user.email,
            password="testpassword123",
            remember_me=False
        )
        
        # Session 1
        _, _, refresh_token_1 = await auth_service.authenticate_user(
            login_data, "agent1", "127.0.0.1"
        )
        
        # Session 2
        _, _, refresh_token_2 = await auth_service.authenticate_user(
            login_data, "agent2", "127.0.0.2"
        )
        
        # Logout all devices
        await auth_service.logout_all_devices(test_user.id)
        
        # Verify both tokens are invalid
        from app.auth.core.exceptions import TokenInvalidError
        with pytest.raises(TokenInvalidError):
            await auth_service.refresh_access_token(refresh_token_1)
        
        with pytest.raises(TokenInvalidError):
            await auth_service.refresh_access_token(refresh_token_2)