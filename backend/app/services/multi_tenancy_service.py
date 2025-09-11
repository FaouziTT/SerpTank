"""
Multi-tenancy service for enforcing tenant-scoped database operations.

This module provides utilities to ensure all database queries are properly
scoped to the correct organization/tenant, preventing cross-tenant data leakage.
"""

import logging
from typing import Optional, List, Dict, Any, Union, TypeVar, Generic
from sqlalchemy import select, Select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql.expression import BinaryExpression
from fastapi import HTTPException, status

from app.models.organization import Organization, OrganizationMember, MemberRole, MemberStatus
from app.models.user import User
from app.models.project import Project

logger = logging.getLogger(__name__)

# Generic type for SQLAlchemy models
ModelType = TypeVar('ModelType', bound=DeclarativeBase)


class TenantAccessDeniedError(HTTPException):
    """Raised when user tries to access data outside their tenant scope."""
    
    def __init__(self, resource: str = "resource", tenant_id: Optional[str] = None):
        detail = f"Access denied to {resource}"
        if tenant_id:
            detail += f" in organization {tenant_id}"
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


class TenantContext:
    """Context object containing current user and tenant information."""
    
    def __init__(
        self, 
        user_id: int, 
        organization_id: Optional[str] = None,
        project_id: Optional[int] = None,
        role: Optional[MemberRole] = None,
        is_superuser: bool = False
    ):
        self.user_id = user_id
        self.organization_id = organization_id
        self.project_id = project_id
        self.role = role
        self.is_superuser = is_superuser
        
    def can_access_organization(self, target_org_id: str) -> bool:
        """Check if current user can access the target organization."""
        if self.is_superuser:
            return True
        return self.organization_id == target_org_id
    
    def can_modify_organization(self, target_org_id: str) -> bool:
        """Check if current user can modify the target organization."""
        if self.is_superuser:
            return True
        return (
            self.organization_id == target_org_id and 
            self.role in [MemberRole.OWNER, MemberRole.ADMIN]
        )
    
    def can_access_project(self, target_project_org_id: Optional[str]) -> bool:
        """Check if current user can access a project."""
        if self.is_superuser:
            return True
        if not target_project_org_id:
            return False
        return self.organization_id == target_project_org_id
    
    def __repr__(self) -> str:
        return f"TenantContext(user={self.user_id}, org={self.organization_id}, role={self.role})"


class MultiTenancyService:
    """Service for managing multi-tenant database operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_user_tenant_context(self, user_id: int) -> Optional[TenantContext]:
        """
        Get tenant context for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            TenantContext if user has valid organization membership
        """
        # Get user with organization memberships
        query = (
            select(User, OrganizationMember, Organization)
            .join(OrganizationMember, User.id == OrganizationMember.user_id)
            .join(Organization, OrganizationMember.organization_id == Organization.id)
            .where(
                and_(
                    User.id == user_id,
                    OrganizationMember.status == MemberStatus.ACTIVE,
                    Organization.status.in_(["active", "ACTIVE"])  # Support both enum and string values
                )
            )
        )
        
        result = await self.db.execute(query)
        row = result.first()
        
        if not row:
            # User has no active organization membership
            return None
        
        user, membership, organization = row
        
        return TenantContext(
            user_id=user.id,
            organization_id=organization.id,
            role=membership.role,
            is_superuser=getattr(user, 'is_superuser', False)
        )
    
    async def validate_organization_access(
        self, 
        context: TenantContext, 
        target_organization_id: str,
        require_modify: bool = False
    ) -> None:
        """
        Validate that user can access the target organization.
        
        Args:
            context: Current tenant context
            target_organization_id: Organization to access
            require_modify: Whether modify permissions are required
            
        Raises:
            TenantAccessDeniedError: If access is denied
        """
        if require_modify:
            if not context.can_modify_organization(target_organization_id):
                raise TenantAccessDeniedError("organization (modify)", target_organization_id)
        else:
            if not context.can_access_organization(target_organization_id):
                raise TenantAccessDeniedError("organization", target_organization_id)
    
    async def validate_project_access(
        self,
        context: TenantContext,
        project_id: int
    ) -> Project:
        """
        Validate project access and return the project.
        
        Args:
            context: Current tenant context
            project_id: Project ID to access
            
        Returns:
            Project object if access is allowed
            
        Raises:
            TenantAccessDeniedError: If access is denied
        """
        # Get project with organization info
        query = select(Project).where(Project.id == project_id)
        result = await self.db.execute(query)
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        if not context.can_access_project(project.organization_id):
            raise TenantAccessDeniedError("project", project.organization_id)
        
        return project
    
    def add_organization_filter(
        self, 
        query: Select, 
        model_class: type, 
        context: TenantContext,
        organization_field: str = "organization_id"
    ) -> Select:
        """
        Add organization filter to a query.
        
        Args:
            query: SQLAlchemy select query
            model_class: Model class being queried
            context: Current tenant context
            organization_field: Field name for organization ID
            
        Returns:
            Modified query with organization filter
        """
        if context.is_superuser:
            return query
        
        org_field = getattr(model_class, organization_field)
        return query.where(org_field == context.organization_id)
    
    def add_user_or_organization_filter(
        self,
        query: Select,
        model_class: type,
        context: TenantContext,
        user_field: str = "user_id",
        organization_field: str = "organization_id"
    ) -> Select:
        """
        Add filter for user's own data OR organization data.
        
        Args:
            query: SQLAlchemy select query
            model_class: Model class being queried
            context: Current tenant context
            user_field: Field name for user ID
            organization_field: Field name for organization ID
            
        Returns:
            Modified query with user/organization filter
        """
        if context.is_superuser:
            return query
        
        user_field_attr = getattr(model_class, user_field)
        org_field_attr = getattr(model_class, organization_field, None)
        
        if org_field_attr is not None:
            # Model has both user and organization fields
            return query.where(
                or_(
                    user_field_attr == context.user_id,
                    org_field_attr == context.organization_id
                )
            )
        else:
            # Model only has user field
            return query.where(user_field_attr == context.user_id)
    
    async def get_user_organizations(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get all organizations the user is a member of.
        
        Args:
            user_id: User ID
            
        Returns:
            List of organization dictionaries with membership info
        """
        query = (
            select(Organization, OrganizationMember)
            .join(OrganizationMember, Organization.id == OrganizationMember.organization_id)
            .where(
                and_(
                    OrganizationMember.user_id == user_id,
                    OrganizationMember.status == MemberStatus.ACTIVE
                )
            )
            .order_by(Organization.name)
        )
        
        result = await self.db.execute(query)
        organizations = []
        
        for org, membership in result.all():
            organizations.append({
                "id": org.id,
                "name": org.name,
                "slug": org.slug,
                "status": org.status,
                "role": membership.role,
                "joined_at": membership.joined_at,
                "is_owner": membership.role == MemberRole.OWNER,
                "can_modify": membership.role in [MemberRole.OWNER, MemberRole.ADMIN]
            })
        
        return organizations
    
    async def get_organization_projects(
        self, 
        context: TenantContext,
        organization_id: Optional[str] = None
    ) -> List[Project]:
        """
        Get projects for an organization.
        
        Args:
            context: Current tenant context
            organization_id: Specific organization ID (defaults to user's org)
            
        Returns:
            List of projects
        """
        target_org_id = organization_id or context.organization_id
        
        if not target_org_id:
            return []
        
        await self.validate_organization_access(context, target_org_id)
        
        query = select(Project).where(Project.organization_id == target_org_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    def create_tenant_scoped_query(
        self,
        model_class: type,
        context: TenantContext,
        additional_filters: Optional[List[BinaryExpression]] = None
    ) -> Select:
        """
        Create a tenant-scoped query for a model.
        
        Args:
            model_class: SQLAlchemy model class
            context: Current tenant context
            additional_filters: Additional WHERE conditions
            
        Returns:
            Tenant-scoped select query
        """
        query = select(model_class)
        
        # Apply tenant filtering based on model type
        if hasattr(model_class, 'organization_id'):
            query = self.add_organization_filter(query, model_class, context)
        elif hasattr(model_class, 'user_id') and not context.is_superuser:
            # For user-scoped data when no organization field exists
            query = query.where(model_class.user_id == context.user_id)
        
        # Apply additional filters
        if additional_filters:
            for filter_condition in additional_filters:
                query = query.where(filter_condition)
        
        return query


# Utility functions for common tenant operations
async def get_current_tenant_context(db: AsyncSession, user_id: int) -> TenantContext:
    """
    Get current tenant context for a user.
    
    Args:
        db: Database session
        user_id: User ID
        
    Returns:
        TenantContext
        
    Raises:
        TenantAccessDeniedError: If user has no valid tenant access
    """
    service = MultiTenancyService(db)
    context = await service.get_user_tenant_context(user_id)
    
    if not context:
        raise TenantAccessDeniedError("any organization")
    
    return context


async def validate_tenant_resource_access(
    db: AsyncSession,
    user_id: int,
    organization_id: str,
    require_modify: bool = False
) -> TenantContext:
    """
    Validate tenant resource access.
    
    Args:
        db: Database session
        user_id: User ID
        organization_id: Organization ID to access
        require_modify: Whether modify permissions are required
        
    Returns:
        TenantContext if access is allowed
        
    Raises:
        TenantAccessDeniedError: If access is denied
    """
    context = await get_current_tenant_context(db, user_id)
    service = MultiTenancyService(db)
    
    await service.validate_organization_access(context, organization_id, require_modify)
    
    return context


def create_organization_scoped_query(
    model_class: type,
    organization_id: str,
    is_superuser: bool = False
) -> Select:
    """
    Create an organization-scoped query.
    
    Args:
        model_class: SQLAlchemy model class
        organization_id: Organization ID to scope to
        is_superuser: Whether user is superuser (bypasses scoping)
        
    Returns:
        Scoped select query
    """
    query = select(model_class)
    
    if not is_superuser and hasattr(model_class, 'organization_id'):
        query = query.where(model_class.organization_id == organization_id)
    
    return query


# Decorator for tenant-aware endpoints
def tenant_required(require_modify: bool = False):
    """
    Decorator to require tenant context for endpoint functions.
    
    Args:
        require_modify: Whether modify permissions are required
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # This would be implemented as a dependency in FastAPI endpoints
            # For now, it's a placeholder for the pattern
            pass
        return wrapper
    return decorator