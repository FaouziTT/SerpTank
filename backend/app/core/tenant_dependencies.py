"""
FastAPI dependencies for tenant enforcement.

This module provides FastAPI dependencies that automatically enforce
tenant-scoped database access, preventing cross-tenant data leakage.
"""

from typing import Optional
from fastapi import Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.auth.core.dependencies import get_current_user
from app.auth.schemas.auth import UserProfile
from app.services.multi_tenancy_service import (
    MultiTenancyService,
    TenantContext,
    TenantAccessDeniedError,
    get_current_tenant_context,
    validate_tenant_resource_access
)


async def get_tenant_service(db: AsyncSession = Depends(get_db)) -> MultiTenancyService:
    """Get multi-tenancy service instance."""
    return MultiTenancyService(db)


async def get_current_tenant_context_dependency(
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> TenantContext:
    """
    FastAPI dependency to get current tenant context.
    
    Returns:
        TenantContext for the current user
        
    Raises:
        TenantAccessDeniedError: If user has no valid organization membership
    """
    return await get_current_tenant_context(db, current_user.id)


async def validate_organization_access_dependency(
    organization_id: str = Path(..., description="Organization ID"),
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> TenantContext:
    """
    FastAPI dependency to validate organization access from path parameter.
    
    Args:
        organization_id: Organization ID from URL path
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        TenantContext if access is allowed
        
    Raises:
        TenantAccessDeniedError: If user cannot access the organization
    """
    return await validate_tenant_resource_access(
        db, current_user.id, organization_id, require_modify=False
    )


async def validate_organization_modify_access_dependency(
    organization_id: str = Path(..., description="Organization ID"),
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> TenantContext:
    """
    FastAPI dependency to validate organization modify access from path parameter.
    
    Args:
        organization_id: Organization ID from URL path
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        TenantContext if modify access is allowed
        
    Raises:
        TenantAccessDeniedError: If user cannot modify the organization
    """
    return await validate_tenant_resource_access(
        db, current_user.id, organization_id, require_modify=True
    )


async def validate_project_access_dependency(
    project_id: int = Path(..., description="Project ID"),
    tenant_context: TenantContext = Depends(get_current_tenant_context_dependency),
    tenant_service: MultiTenancyService = Depends(get_tenant_service)
):
    """
    FastAPI dependency to validate project access from path parameter.
    
    Args:
        project_id: Project ID from URL path
        tenant_context: Current tenant context
        tenant_service: Multi-tenancy service
        
    Returns:
        Tuple of (TenantContext, Project) if access is allowed
        
    Raises:
        TenantAccessDeniedError: If user cannot access the project
    """
    project = await tenant_service.validate_project_access(tenant_context, project_id)
    return tenant_context, project


class TenantScopedQuery:
    """Helper class for tenant-scoped query dependencies."""
    
    def __init__(self, require_organization: bool = True, require_project: bool = False):
        self.require_organization = require_organization
        self.require_project = require_project
    
    async def __call__(
        self,
        tenant_context: TenantContext = Depends(get_current_tenant_context_dependency),
        organization_id: Optional[str] = Query(None, description="Filter by organization ID"),
        project_id: Optional[int] = Query(None, description="Filter by project ID"),
        tenant_service: MultiTenancyService = Depends(get_tenant_service)
    ):
        """
        Create a tenant-scoped query dependency.
        
        Args:
            tenant_context: Current tenant context
            organization_id: Optional organization ID filter
            project_id: Optional project ID filter
            tenant_service: Multi-tenancy service
            
        Returns:
            Dictionary with tenant context and validated filters
        """
        # Validate organization access if specified
        if organization_id:
            if not tenant_context.can_access_organization(organization_id):
                raise TenantAccessDeniedError("organization", organization_id)
        elif self.require_organization and not tenant_context.organization_id:
            raise TenantAccessDeniedError("any organization")
        
        # Validate project access if specified
        validated_project = None
        if project_id:
            validated_project = await tenant_service.validate_project_access(
                tenant_context, project_id
            )
        elif self.require_project:
            raise HTTPException(
                status_code=400,
                detail="Project ID is required"
            )
        
        return {
            "tenant_context": tenant_context,
            "organization_id": organization_id or tenant_context.organization_id,
            "project_id": project_id,
            "project": validated_project
        }


# Pre-configured dependency instances
tenant_scoped_organization = TenantScopedQuery(require_organization=True)
tenant_scoped_project = TenantScopedQuery(require_organization=True, require_project=True)
tenant_scoped_optional = TenantScopedQuery(require_organization=False)


class TenantResourceAccess:
    """Class-based dependency for specific resource access patterns."""
    
    def __init__(
        self, 
        resource_type: str = "resource",
        require_modify: bool = False,
        organization_field: str = "organization_id",
        project_field: str = "project_id"
    ):
        self.resource_type = resource_type
        self.require_modify = require_modify
        self.organization_field = organization_field
        self.project_field = project_field
    
    async def __call__(
        self,
        tenant_context: TenantContext = Depends(get_current_tenant_context_dependency),
        organization_id: Optional[str] = None,
        project_id: Optional[int] = None,
        tenant_service: MultiTenancyService = Depends(get_tenant_service)
    ):
        """
        Validate access to a specific resource type.
        
        Args:
            tenant_context: Current tenant context
            organization_id: Organization ID (from path or body)
            project_id: Project ID (from path or body)
            tenant_service: Multi-tenancy service
            
        Returns:
            Dictionary with validated access information
        """
        # Default to user's organization if not specified
        target_org_id = organization_id or tenant_context.organization_id
        
        if target_org_id:
            await tenant_service.validate_organization_access(
                tenant_context, target_org_id, self.require_modify
            )
        
        # Validate project access if specified
        validated_project = None
        if project_id:
            validated_project = await tenant_service.validate_project_access(
                tenant_context, project_id
            )
        
        return {
            "tenant_context": tenant_context,
            "organization_id": target_org_id,
            "project_id": project_id,
            "project": validated_project,
            "can_modify": tenant_context.can_modify_organization(target_org_id) if target_org_id else False
        }


# Common resource access patterns
require_organization_read = TenantResourceAccess("organization", require_modify=False)
require_organization_write = TenantResourceAccess("organization", require_modify=True)
require_project_access = TenantResourceAccess("project", require_modify=False)


async def enforce_superuser_or_organization_owner(
    tenant_context: TenantContext = Depends(get_current_tenant_context_dependency),
    organization_id: Optional[str] = None
) -> TenantContext:
    """
    Dependency that requires superuser OR organization owner access.
    
    Args:
        tenant_context: Current tenant context
        organization_id: Target organization ID
        
    Returns:
        TenantContext if access is allowed
        
    Raises:
        HTTPException: If user is not superuser or organization owner
    """
    target_org_id = organization_id or tenant_context.organization_id
    
    if not tenant_context.is_superuser:
        if not target_org_id or not tenant_context.can_modify_organization(target_org_id):
            raise HTTPException(
                status_code=403,
                detail="Requires superuser or organization owner access"
            )
    
    return tenant_context


# Utility function to create tenant-aware endpoint decorators
def create_tenant_dependency(
    require_organization: bool = True,
    require_project: bool = False,
    require_modify: bool = False,
    allow_superuser_bypass: bool = True
):
    """
    Create a custom tenant dependency with specific requirements.
    
    Args:
        require_organization: Whether organization access is required
        require_project: Whether project access is required
        require_modify: Whether modify permissions are required
        allow_superuser_bypass: Whether superusers bypass tenant checks
        
    Returns:
        FastAPI dependency function
    """
    async def tenant_dependency(
        current_user: UserProfile = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        organization_id: Optional[str] = Query(None),
        project_id: Optional[int] = Query(None)
    ):
        tenant_service = MultiTenancyService(db)
        context = await tenant_service.get_user_tenant_context(current_user.id)
        
        if not context and not allow_superuser_bypass:
            raise TenantAccessDeniedError("any organization")
        
        # Superuser bypass if enabled
        if allow_superuser_bypass and getattr(current_user, 'is_superuser', False):
            return TenantContext(
                user_id=current_user.id,
                organization_id=organization_id,
                is_superuser=True
            )
        
        if not context:
            raise TenantAccessDeniedError("any organization")
        
        # Validate organization access
        if require_organization or organization_id:
            target_org = organization_id or context.organization_id
            if target_org:
                await tenant_service.validate_organization_access(
                    context, target_org, require_modify
                )
        
        # Validate project access
        if require_project or project_id:
            if not project_id:
                raise HTTPException(status_code=400, detail="Project ID required")
            await tenant_service.validate_project_access(context, project_id)
        
        return context
    
    return tenant_dependency