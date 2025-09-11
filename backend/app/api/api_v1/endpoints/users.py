"""
API endpoints for user management.

This module provides endpoints for user management, including creating, updating,
and retrieving user information.
"""
import logging
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth.core.dependencies import get_current_active_user, get_current_superuser
from app.auth.schemas.auth import UserProfile
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import User as UserSchema
from app.schemas.user import UserCreate, UserUpdate

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/me", response_model=UserSchema)
async def read_current_user(
    request: Request,
    current_user: UserProfile = Depends(get_current_active_user),
) -> Any:
    """
    Get current user.
    
    Args:
        current_user: The current authenticated user
        
    Returns:
        Current user information
    """
    return current_user


@router.put("/me", response_model=UserSchema)
async def update_current_user(
    request: Request,
    user_in: UserUpdate,
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Update current user.
    
    Args:
        user_in: User update data
        current_user: The current authenticated user
        db: Database session
        
    Returns:
        Updated user information
    """
    # This is a placeholder implementation
    # In a real implementation, you would update the user in the database
    
    # Update user fields
    update_data = user_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    # Save changes
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    
    logger.info(f"User {current_user.email} updated their profile")
    
    return current_user


@router.get("", response_model=List[UserSchema])
async def read_users(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    current_user: UserProfile = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Retrieve users.
    
    Args:
        skip: Number of users to skip
        limit: Maximum number of users to return
        current_user: The current authenticated superuser
        db: Database session
        
    Returns:
        List of users
    """
    # This is a placeholder implementation
    # In a real implementation, you would query the database
    
    result = await db.execute(select(User).offset(skip).limit(limit))
    users = result.scalars().all()
    
    return users


@router.post("", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: Request,
    user_in: UserCreate,
    current_user: UserProfile = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Create new user.
    
    Args:
        user_in: User creation data
        current_user: The current authenticated superuser
        db: Database session
        
    Returns:
        Created user information
    """
    # This is a placeholder implementation
    # In a real implementation, you would create a new user in the database
    
    # Check if user with this email already exists
    result = await db.execute(select(User).where(User.email == user_in.email))
    user = result.scalars().first()
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists",
        )
    
    # Create new user
    from app.auth.core.security import get_password_hash
    
    user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        is_superuser=user_in.is_superuser,
    )
    
    # Save user
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    logger.info(f"User {user.email} created by {current_user.email}")
    
    return user


@router.get("/{user_id}", response_model=UserSchema)
async def read_user(
    request: Request,
    user_id: int,
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get a specific user by id.
    
    Args:
        user_id: User ID
        current_user: The current authenticated user
        db: Database session
        
    Returns:
        User information
    """
    # This is a placeholder implementation
    # In a real implementation, you would query the database
    
    # Only superusers can access other users' data
    if user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    # Get user
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return user


@router.put("/{user_id}", response_model=UserSchema)
async def update_user(
    request: Request,
    user_id: int,
    user_in: UserUpdate,
    current_user: UserProfile = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Update a user.
    
    Args:
        user_id: User ID
        user_in: User update data
        current_user: The current authenticated superuser
        db: Database session
        
    Returns:
        Updated user information
    """
    # This is a placeholder implementation
    # In a real implementation, you would update the user in the database
    
    # Get user
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Update user fields
    update_data = user_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "password" and value:
            from app.auth.core.security import get_password_hash
            
            hashed_password = get_password_hash(value)
            setattr(user, "hashed_password", hashed_password)
        else:
            setattr(user, field, value)
    
    # Save changes
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    logger.info(f"User {user.email} updated by {current_user.email}")
    
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    request: Request,
    user_id: int,
    current_user: UserProfile = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a user.
    
    Args:
        user_id: User ID
        current_user: The current authenticated superuser
        db: Database session
        
    Returns:
        None
    """
    # This is a placeholder implementation
    # In a real implementation, you would delete the user from the database
    
    # Get user
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Delete user
    await db.delete(user)
    await db.commit()
    
    logger.info(f"User {user.email} deleted by {current_user.email}")