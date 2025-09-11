"""User management routes for Authentication System 2.0."""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

from app.auth.core.dependencies import (
    get_current_user, 
    get_current_active_user, 
    get_current_superuser,
    get_db
)
from app.auth.core.security import get_password_hash
from app.auth.schemas.auth import UserProfile, MessageResponse
from app.models.user import User
from app.auth.services.auth_service import AuthService

router = APIRouter(tags=["user-management"])
logger = logging.getLogger(__name__)


# Pydantic schemas for user management
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class UserUpdateRequest(BaseModel):
    """User profile update request."""
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None

class UserCreateRequest(BaseModel):
    """Admin user creation request."""
    full_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    is_superuser: bool = False
    is_active: bool = True

class UserListResponse(BaseModel):
    """User list response."""
    users: List[UserProfile]
    total: int
    page: int
    page_size: int

class PasswordChangeRequest(BaseModel):
    """Password change request."""
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)


async def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    """Get auth service instance."""
    return AuthService(db)


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    current_user: UserProfile = Depends(get_current_active_user)
):
    """
    Get current user profile.
    
    Returns the authenticated user's profile information.
    """
    return current_user


@router.put("/me", response_model=UserProfile)
async def update_current_user_profile(
    update_data: UserUpdateRequest,
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current user's profile.
    
    Allows users to update their own profile information.
    Email changes may require verification in future versions.
    """
    try:
        # Get the full user model
        result = await db.execute(select(User).where(User.id == current_user.id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update fields
        update_dict = update_data.dict(exclude_unset=True)
        
        # Non-superusers cannot change their active status
        if not current_user.is_superuser and 'is_active' in update_dict:
            del update_dict['is_active']
        
        for field, value in update_dict.items():
            if hasattr(user, field):
                setattr(user, field, value)
        
        await db.commit()
        await db.refresh(user)
        
        # Return updated profile
        return UserProfile(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            created_at=user.created_at,
            auth_provider=getattr(user, 'auth_provider', 'email'),
            email_verified=getattr(user, 'email_verified', True)
        )
        
    except IntegrityError as e:
        await db.rollback()
        if "email" in str(e.orig):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid data provided"
        )
    except Exception as e:
        logger.error(f"Profile update error: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profile update failed"
        )


@router.post("/me/change-password", response_model=MessageResponse)
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: UserProfile = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Change current user's password.
    
    Requires current password verification for security.
    """
    try:
        # Verify current password first
        from app.auth.schemas.auth import LoginRequest
        login_verify = LoginRequest(
            email=current_user.email,
            password=password_data.current_password,
            remember_me=False
        )
        
        # This will raise an exception if password is wrong
        await auth_service.authenticate_user(login_verify)
        
        # Get the full user model and update password
        result = await auth_service.db.execute(select(User).where(User.id == current_user.id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update password
        user.hashed_password = get_password_hash(password_data.new_password)
        user.password_changed_at = func.now()
        
        await auth_service.db.commit()
        
        logger.info(f"Password changed for user {current_user.email}")
        
        return MessageResponse(message="Password changed successfully")
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions (like wrong current password)
    except Exception as e:
        logger.error(f"Password change error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )


# Admin-only endpoints
@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by email or name"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: UserProfile = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """
    List users (admin only).
    
    Provides paginated user listing with search and filtering capabilities.
    """
    try:
        # Build query
        query = select(User)
        
        # Apply filters
        if search:
            search_term = f"%{search}%"
            query = query.where(
                (User.email.ilike(search_term)) | 
                (User.full_name.ilike(search_term))
            )
        
        if is_active is not None:
            query = query.where(User.is_active == is_active)
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await db.execute(count_query)
        total = count_result.scalar()
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size).order_by(User.created_at.desc())
        
        # Execute query
        result = await db.execute(query)
        users = result.scalars().all()
        
        # Convert to UserProfile schemas
        user_profiles = [
            UserProfile(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                is_active=user.is_active,
                is_superuser=user.is_superuser,
                created_at=user.created_at,
                auth_provider=getattr(user, 'auth_provider', 'email'),
                email_verified=getattr(user, 'email_verified', True)
            )
            for user in users
        ]
        
        return UserListResponse(
            users=user_profiles,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"User listing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users"
        )


@router.post("", response_model=UserProfile, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreateRequest,
    current_user: UserProfile = Depends(get_current_superuser),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Create new user (admin only).
    
    Creates a new user account with the specified details.
    """
    try:
        # Use the auth service to create user
        from app.auth.schemas.auth import RegisterRequest
        
        register_data = RegisterRequest(
            full_name=user_data.full_name,
            email=user_data.email,
            password=user_data.password,
            confirmPassword=user_data.password
        )
        
        # Create user through auth service
        user_profile = await auth_service.register_user(register_data)
        
        # Update additional fields if needed
        if not user_data.is_active or user_data.is_superuser:
            result = await auth_service.db.execute(select(User).where(User.id == user_profile.id))
            user = result.scalar_one_or_none()
            
            if user:
                user.is_active = user_data.is_active
                user.is_superuser = user_data.is_superuser
                await auth_service.db.commit()
                
                # Update profile with new values
                user_profile.is_active = user_data.is_active
                user_profile.is_superuser = user_data.is_superuser
        
        logger.info(f"User {user_profile.email} created by admin {current_user.email}")
        
        return user_profile
        
    except Exception as e:
        logger.error(f"User creation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User creation failed"
        )


@router.get("/{user_id}", response_model=UserProfile)
async def get_user(
    user_id: int,
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user by ID.
    
    Users can only access their own profile unless they're superusers.
    """
    try:
        # Permission check
        if user_id != current_user.id and not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        # Get user
        user = await db.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return UserProfile(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            created_at=user.created_at,
            auth_provider=getattr(user, 'auth_provider', 'email'),
            email_verified=getattr(user, 'email_verified', True)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user"
        )


@router.put("/{user_id}", response_model=UserProfile)
async def update_user(
    user_id: int,
    update_data: UserUpdateRequest,
    current_user: UserProfile = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """
    Update user (admin only).
    
    Allows superusers to update any user's profile.
    """
    try:
        # Get user
        user = await db.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update fields
        update_dict = update_data.dict(exclude_unset=True)
        for field, value in update_dict.items():
            if hasattr(user, field):
                setattr(user, field, value)
        
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"User {user.email} updated by admin {current_user.email}")
        
        return UserProfile(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            created_at=user.created_at,
            auth_provider=getattr(user, 'auth_provider', 'email'),
            email_verified=getattr(user, 'email_verified', True)
        )
        
    except IntegrityError as e:
        await db.rollback()
        if "email" in str(e.orig):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid data provided"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User update error: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User update failed"
        )


@router.delete("/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: int,
    current_user: UserProfile = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete user (admin only).
    
    Soft delete by marking user as inactive.
    Prevents deletion of superuser accounts for security.
    """
    try:
        # Get user
        user = await db.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Prevent deletion of superusers
        if user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete superuser accounts"
            )
        
        # Prevent self-deletion
        if user.id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own account"
            )
        
        # Soft delete (mark as inactive)
        user.is_active = False
        await db.commit()
        
        logger.info(f"User {user.email} deactivated by admin {current_user.email}")
        
        return MessageResponse(message="User successfully deactivated")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User deletion error: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User deletion failed"
        )