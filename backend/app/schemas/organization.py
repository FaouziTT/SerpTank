"""
Organization Schemas

Pydantic models for organization-related API requests and responses.
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, validator

from app.models.organization import MemberRole


class OrganizationBase(BaseModel):
    """Base organization schema."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class OrganizationCreate(OrganizationBase):
    """Schema for creating an organization."""
    slug: Optional[str] = Field(None, min_length=1, max_length=50)  # Made optional since service auto-generates it
    settings: Optional[Dict[str, Any]] = None
    
    @validator('slug')
    def validate_slug(cls, v):
        """Validate organization slug format."""
        if v is None:
            return v  # Allow None values
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Slug must contain only alphanumeric characters, hyphens, and underscores')
        return v.lower()


class OrganizationUpdate(BaseModel):
    """Schema for updating an organization."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    settings: Optional[Dict[str, Any]] = None


class OrganizationResponse(OrganizationBase):
    """Schema for organization response."""
    id: str  # Changed from UUID to str to match the model
    slug: str
    owner_id: Optional[str] = None  # Made optional since it's not in the model
    is_active: bool = True  # Default value since model doesn't have this field
    created_at: datetime
    updated_at: datetime
    settings: Optional[Dict[str, Any]] = None
    
    # Statistics
    member_count: Optional[int] = None
    domain_count: Optional[int] = None
    project_count: Optional[int] = None
    
    class Config:
        from_attributes = True


class OrganizationMemberBase(BaseModel):
    """Base organization member schema."""
    role: MemberRole


class OrganizationMemberResponse(OrganizationMemberBase):
    """Schema for organization member response."""
    id: str  # Changed from UUID to str
    organization_id: str  # Changed from UUID to str
    user_id: int  # User IDs are integers
    role: MemberRole
    joined_at: datetime
    added_by: Optional[int] = None  # User IDs are integers
    
    # User information
    user_email: Optional[str] = None
    user_full_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class OrganizationInvitationBase(BaseModel):
    """Base organization invitation schema."""
    email: EmailStr
    role: MemberRole


class OrganizationInvitationCreate(OrganizationInvitationBase):
    """Schema for creating an organization invitation."""
    expires_at: Optional[datetime] = None


class OrganizationInvitationResponse(OrganizationInvitationBase):
    """Schema for organization invitation response."""
    id: UUID
    organization_id: UUID
    email: EmailStr
    role: MemberRole
    is_accepted: bool
    is_expired: bool
    invited_by: UUID
    invited_at: datetime
    expires_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    
    # Organization information
    organization_name: Optional[str] = None
    inviter_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class OrganizationDomainBase(BaseModel):
    """Base organization domain schema."""
    domain: str = Field(..., min_length=1, max_length=255)


class OrganizationDomainCreate(OrganizationDomainBase):
    """Schema for creating an organization domain."""
    pass


class OrganizationDomainResponse(OrganizationDomainBase):
    """Schema for organization domain response."""
    id: UUID
    organization_id: UUID
    domain: str
    is_verified: bool
    is_primary: bool
    added_at: datetime
    verified_at: Optional[datetime] = None
    added_by: UUID
    
    class Config:
        from_attributes = True


class OrganizationAuditLogResponse(BaseModel):
    """Schema for organization audit log response."""
    id: UUID
    organization_id: UUID
    user_id: Optional[UUID] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime
    
    # User information
    user_email: Optional[str] = None
    user_full_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class OrganizationStatsResponse(BaseModel):
    """Schema for organization statistics response."""
    total_members: int
    total_domains: int
    total_invitations: int
    recent_activity_count: int
    created_at: datetime


class OrganizationSwitchRequest(BaseModel):
    """Schema for switching current organization context."""
    organization_id: UUID


class UserOrganizationResponse(BaseModel):
    """Schema for user's organization membership response."""
    organization: OrganizationResponse
    role: MemberRole
    joined_at: datetime
    is_current: bool = False  # Whether this is the user's currently active organization
    
    class Config:
        from_attributes = True
