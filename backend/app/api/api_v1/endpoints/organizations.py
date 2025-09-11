"""
Organization Management API

This module provides endpoints for managing organizations, members,
invitations, and organization-related operations in the multi-tenant system.
"""
import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.organization_service import organization_service

from app.auth.core.dependencies import get_current_active_user
from app.auth.schemas.auth import UserProfile
from app.db.session import get_db
from app.models.user import User
from app.models.organization import Organization, OrganizationMember, MemberRole, MemberStatus, OrganizationStatus
from app.services.multi_tenancy_service import MultiTenancyService, TenantContext
from app.core.tenant_dependencies import (
    validate_organization_access_dependency,
    validate_organization_modify_access_dependency,
    get_current_tenant_context_dependency,
    get_tenant_service
)
from app.core.rate_limit_dependencies import (
    rate_limit_general_api,
    rate_limit_data_intensive
)
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationResponse,
    OrganizationMemberResponse,
    OrganizationInvitationCreate,
    OrganizationInvitationResponse,
    OrganizationDomainCreate,
    OrganizationDomainResponse,
    OrganizationAuditLogResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/test")
async def test_organizations_endpoint():
    """Test endpoint to verify router is working."""
    return {"message": "Organizations router is working"}


@router.post("/", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    org_data: OrganizationCreate,
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_general_api)  # 60 requests per minute
):
    """Create a new organization."""
    try:
 # --- THIS IS THE ONLY LOGIC THAT SHOULD BE IN THE 'TRY' BLOCK ---
        # 1. Call our new, clean service to handle the database work
        organization = await organization_service.create_organization_with_owner(
        db=db, obj_in=org_data, owner_id=current_user.id
        )

        # 2. Return the successful response
        return OrganizationResponse(
            id=organization.id,
            name=organization.name,
            slug=organization.slug,
            description=organization.description,
            owner_id=None,
            is_active=organization.status == OrganizationStatus.ACTIVE,
            created_at=organization.created_at,
            updated_at=organization.updated_at,
            settings=organization.settings or {},
            member_count=1,
            project_count=0
        )
        # --- END OF CORRECTED LOGIC ---

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating organization: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create organization due to a server error."
        )


@router.get("/", response_model=List[OrganizationResponse])
async def get_user_organizations(
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    tenant_service: MultiTenancyService = Depends(get_tenant_service),
    _: None = Depends(rate_limit_general_api)  # 60 requests per minute
):
    """Get all organizations the current user belongs to."""
    try:
        logger.info(f"Getting organizations for user {current_user.id}")
        user_orgs = await tenant_service.get_user_organizations(current_user.id)
        logger.info(f"Found {len(user_orgs)} organizations for user {current_user.id}")
        
        # Transform the service response to match OrganizationResponse schema
        organizations = []
        for org_data in user_orgs:
            org_response = OrganizationResponse(
                id=org_data["id"],
                name=org_data["name"],
                slug=org_data["slug"],
                description=None,  # Not included in service response
                owner_id=None,  # Organization model doesn't have owner_id
                settings={},
                is_active=org_data["status"] == "active",
                created_at=datetime.now(),  # Use current datetime as fallback
                updated_at=datetime.now(),  # Use current datetime as fallback
                member_count=1,  # Service doesn't return count - could be enhanced
                project_count=0  # Service doesn't return count - could be enhanced
            )
            organizations.append(org_response)
        
        return organizations
    except Exception as e:
        logger.error(f"Error getting user organizations: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get organizations: {str(e)}"
        )


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: str,
    tenant_context: TenantContext = Depends(validate_organization_access_dependency),
    db: AsyncSession = Depends(get_db)
):
    """Get organization details."""
    try:
        # Access is already validated by the dependency
        from sqlalchemy import select, func
        from app.models.project import Project
        
        # Get organization details
        org_result = await db.execute(
            select(Organization).where(Organization.id == org_id)
        )
        organization = org_result.scalar_one_or_none()
        
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        # Get counts for statistics
        project_count_result = await db.execute(
            select(func.count(Project.id)).where(Project.organization_id == org_id)
        )
        project_count = project_count_result.scalar() or 0
        
        member_count_result = await db.execute(
            select(func.count(OrganizationMember.id)).where(OrganizationMember.organization_id == org_id)
        )
        member_count = member_count_result.scalar() or 0
        
        return OrganizationResponse(
            id=organization.id,
            name=organization.name,
            slug=organization.slug,
            description=organization.description,
            owner_id=None,
            settings=organization.settings or {},
            is_active=organization.status == OrganizationStatus.ACTIVE,
            created_at=organization.created_at,
            updated_at=organization.updated_at,
            member_count=member_count,
            project_count=project_count
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting organization: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get organization"
        )


@router.put("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: str,
    org_data: OrganizationUpdate,
    tenant_context: TenantContext = Depends(validate_organization_modify_access_dependency),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_general_api)  # 60 requests per minute
):
    """Update organization details. Requires admin role."""
    try:
        # Access is already validated by the dependency
        from sqlalchemy import select, func
        from app.models.project import Project
        
        # Get and update organization
        org_result = await db.execute(
            select(Organization).where(Organization.id == org_id)
        )
        organization = org_result.scalar_one_or_none()
        
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        # Update fields
        if org_data.name is not None:
            organization.name = org_data.name
        if org_data.description is not None:
            organization.description = org_data.description
        if org_data.settings is not None:
            organization.settings = org_data.settings
        
        await db.commit()
        await db.refresh(organization)
        
        # Get counts for response
        project_count_result = await db.execute(
            select(func.count(Project.id)).where(Project.organization_id == org_id)
        )
        project_count = project_count_result.scalar() or 0
        
        member_count_result = await db.execute(
            select(func.count(OrganizationMember.id)).where(OrganizationMember.organization_id == org_id)
        )
        member_count = member_count_result.scalar() or 0
        
        return OrganizationResponse(
            id=organization.id,
            name=organization.name,
            slug=organization.slug,
            description=organization.description,
            owner_id=None,
            settings=organization.settings or {},
            is_active=organization.status == OrganizationStatus.ACTIVE,
            created_at=organization.created_at,
            updated_at=organization.updated_at,
            member_count=member_count,
            project_count=project_count
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating organization: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update organization"
        )


@router.delete("/{org_id}")
async def delete_organization(
    org_id: str,
    tenant_context: TenantContext = Depends(validate_organization_modify_access_dependency),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_general_api)  # 60 requests per minute
):
    """Delete organization. Requires owner role."""
    try:
        # Access is already validated by the dependency
        # Additional owner check since delete requires ownership
        if not tenant_context.can_modify_organization(org_id) or tenant_context.role != MemberRole.OWNER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Owner access required to delete organization"
            )
        
        # Get and delete organization
        from sqlalchemy import select
        org_result = await db.execute(
            select(Organization).where(Organization.id == org_id)
        )
        organization = org_result.scalar_one_or_none()
        
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        await db.delete(organization)
        await db.commit()
        
        return {"message": "Organization deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting organization: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete organization"
        )


@router.get("/{org_id}/members", response_model=List[OrganizationMemberResponse])
async def get_organization_members(
    org_id: str,
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_general_api)  # 60 requests per minute
):
    """Get organization members."""
    try:
        from sqlalchemy import select, and_
        
        # First check if the user has access to this organization
        user_membership_check = await db.execute(
            select(OrganizationMember)
            .where(
                and_(
                    OrganizationMember.user_id == current_user.id,
                    OrganizationMember.organization_id == org_id,
                    OrganizationMember.status == MemberStatus.ACTIVE
                )
            )
        )
        
        user_membership = user_membership_check.scalar_one_or_none()
        if not user_membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to organization"
            )
        
        # Get members with user details
        members_result = await db.execute(
            select(OrganizationMember, User)
            .join(User, OrganizationMember.user_id == User.id)
            .where(OrganizationMember.organization_id == org_id)
        )
        
        members = []
        for member, user in members_result.all():
            member_dict = {
                "id": str(member.id),
                "organization_id": str(member.organization_id),
                "user_id": str(member.user_id),
                "role": member.role,
                "joined_at": member.joined_at,
                "added_by": str(member.invited_by_user_id) if member.invited_by_user_id else None,
                "user_email": user.email,
                "user_full_name": user.full_name
            }
            members.append(OrganizationMemberResponse(**member_dict))
        
        return members
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting organization members: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get organization members"
        )


@router.post("/{org_id}/members/{user_id}")
async def add_organization_member(
    org_id: UUID,
    user_id: UUID,
    role: MemberRole,
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Add a member to the organization. Requires admin role."""
    try:
        service = MultiTenancyService(db)
        
        # Check if user has admin access to this organization
        if not await service.user_has_organization_role(
            current_user.id, org_id, MemberRole.ADMIN
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        success = await service.add_member(
            org_id=org_id,
            user_id=user_id,
            role=role,
            added_by=current_user.id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to add member (user may already be a member)"
            )
        
        return {"message": "Member added successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding organization member: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add member"
        )


@router.put("/{org_id}/members/{user_id}")
async def update_member_role(
    org_id: UUID,
    user_id: UUID,
    new_role: MemberRole,
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a member's role. Requires admin role."""
    try:
        service = MultiTenancyService(db)
        
        # Check if user has admin access to this organization
        if not await service.user_has_organization_role(
            current_user.id, org_id, MemberRole.ADMIN
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        success = await service.update_member_role(
            org_id=org_id,
            user_id=user_id,
            new_role=new_role,
            updated_by_user_id=current_user.id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found"
            )
        
        return {"message": "Member role updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating member role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update member role"
        )


@router.delete("/{org_id}/members/{user_id}")
async def remove_organization_member(
    org_id: UUID,
    user_id: UUID,
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove a member from the organization. Requires admin role or self-removal."""
    try:
        service = MultiTenancyService(db)
        
        # Allow self-removal or require admin access
        if user_id != current_user.id:
            if not await service.user_has_organization_role(
                current_user.id, org_id, MemberRole.ADMIN
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin access required to remove other members"
                )
        
        success = await service.remove_member(
            org_id=org_id,
            user_id=user_id,
            removed_by=current_user.id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found"
            )
        
        return {"message": "Member removed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing organization member: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove member"
        )


@router.post("/{org_id}/invitations", response_model=OrganizationInvitationResponse)
async def create_invitation(
    org_id: UUID,
    invitation_data: OrganizationInvitationCreate,
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create an organization invitation. Requires admin role."""
    try:
        service = MultiTenancyService(db)
        
        # Check if user has admin access to this organization
        if not await service.user_has_organization_role(
            current_user.id, org_id, MemberRole.ADMIN
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        invitation = await service.create_invitation(
            org_id=org_id,
            email=invitation_data.email,
            role=invitation_data.role,
            invited_by=current_user.id,
            expires_at=invitation_data.expires_at
        )
        
        return invitation
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating invitation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create invitation"
        )


@router.get("/{org_id}/invitations", response_model=List[OrganizationInvitationResponse])
async def get_organization_invitations(
    org_id: str,
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get pending organization invitations. Requires admin role."""
    try:
        from sqlalchemy import select, and_
        
        # First check if the user has access to this organization
        user_membership_check = await db.execute(
            select(OrganizationMember)
            .where(
                and_(
                    OrganizationMember.user_id == current_user.id,
                    OrganizationMember.organization_id == org_id,
                    OrganizationMember.status == MemberStatus.ACTIVE
                )
            )
        )
        
        user_membership = user_membership_check.scalar_one_or_none()
        if not user_membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to organization"
            )
        
        # For now, return empty list since invitation system needs to be properly implemented
        return []
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting invitations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get invitations"
        )


@router.post("/invitations/{invitation_id}/accept")
async def accept_invitation(
    invitation_id: UUID,
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Accept an organization invitation."""
    try:
        service = MultiTenancyService(db)
        
        success = await service.accept_invitation(
            invitation_id=invitation_id,
            user_id=current_user.id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired invitation"
            )
        
        return {"message": "Invitation accepted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error accepting invitation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to accept invitation"
        )


@router.delete("/invitations/{invitation_id}")
async def revoke_invitation(
    invitation_id: UUID,
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Revoke an organization invitation. Requires admin role."""
    try:
        service = MultiTenancyService(db)
        
        # Get invitation to check organization access
        invitation = await service.get_invitation(invitation_id)
        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitation not found"
            )
        
        # Check if user has admin access to this organization
        if not await service.user_has_organization_role(
            current_user.id, invitation.organization_id, MemberRole.ADMIN
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        success = await service.revoke_invitation(invitation_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitation not found"
            )
        
        return {"message": "Invitation revoked successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking invitation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke invitation"
        )


@router.get("/{org_id}/audit-logs", response_model=List[OrganizationAuditLogResponse])
async def get_audit_logs(
    org_id: UUID,
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get organization audit logs. Requires admin role."""
    try:
        service = MultiTenancyService(db)
        
        # Check if user has admin access to this organization
        if not await service.user_has_organization_role(
            current_user.id, org_id, MemberRole.ADMIN
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        logs = await service.get_audit_logs(org_id, limit=limit, offset=offset)
        return logs
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting audit logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get audit logs"
        )
