"""
User schemas for authentication and user management.

This module defines Pydantic models for user data.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Base user schema."""
    
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = True
    is_superuser: bool = False
    company: Optional[str] = None
    company_name: Optional[str] = None  # For auth service compatibility
    position: Optional[str] = None
    organization_name: Optional[str] = None
    website_url: Optional[str] = None
    industry: Optional[str] = None
    timezone: Optional[str] = None
    subscription_plan: Optional[str] = "free"
    subscription_status: Optional[str] = "active"


class UserCreate(UserBase):
    """User creation schema."""
    
    email: EmailStr
    password: str
    full_name: str
    company_name: Optional[str] = None


class UserUpdate(UserBase):
    """User update schema."""
    
    password: Optional[str] = None


class UserInDBBase(UserBase):
    """Base user schema for DB representation."""
    
    id: int
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    two_factor_enabled: bool = False
    password_last_changed: Optional[datetime] = None
    subscription_start_date: Optional[datetime] = None
    subscription_end_date: Optional[datetime] = None
    
    class Config:
        """Pydantic config."""
        
        from_attributes = True


class User(UserInDBBase):
    """User schema for API responses."""
    
    pass


class UserInDB(UserInDBBase):
    """User schema for DB operations."""
    
    hashed_password: str


class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    organization_name: Optional[str] = None
    website_url: Optional[str] = None
    industry: Optional[str] = None
    timezone: Optional[str] = None


class UserProfileSchema(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str] = None
    organization_name: Optional[str] = None
    website_url: Optional[str] = None
    industry: Optional[str] = None
    timezone: Optional[str] = None
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True