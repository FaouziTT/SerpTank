"""
Tests for multi-tenancy service.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.multi_tenancy_service import (
    MultiTenancyService, 
    TenantContext, 
    TenantAccessDeniedError
)
from app.models.user import User
from app.models.organization import Organization, OrganizationMember, MemberRole, MemberStatus
from app.models.project import Project


@pytest.mark.unit
class TestMultiTenancyService:
    """Test cases for MultiTenancyService."""
    
    @pytest.fixture
    async def tenancy_service(self, async_session: AsyncSession) -> MultiTenancyService:
        """Create multi-tenancy service for testing."""
        return MultiTenancyService(async_session)
    
    async def test_get_user_tenant_context_success(
        self,
        tenancy_service: MultiTenancyService,
        test_organization_with_member: tuple[Organization, OrganizationMember],
        test_user: User
    ):
        """Test getting user tenant context successfully."""
        organization, member = test_organization_with_member
        
        context = await tenancy_service.get_user_tenant_context(test_user.id)
        
        assert context is not None
        assert context.user_id == test_user.id
        assert context.organization_id == organization.id
        assert context.role == member.role
        assert context.is_superuser == test_user.is_superuser
    
    async def test_get_user_tenant_context_no_membership(
        self,
        tenancy_service: MultiTenancyService,
        test_user: User
    ):
        """Test getting tenant context for user with no organization membership."""
        context = await tenancy_service.get_user_tenant_context(test_user.id)
        
        assert context is None
    
    async def test_validate_organization_access_success(
        self,
        tenancy_service: MultiTenancyService,
        test_organization_with_member: tuple[Organization, OrganizationMember],
        test_user: User
    ):
        """Test successful organization access validation."""
        organization, member = test_organization_with_member
        context = TenantContext(
            user_id=test_user.id,
            organization_id=organization.id,
            role=member.role
        )
        
        # Should not raise exception
        await tenancy_service.validate_organization_access(
            context, organization.id
        )
    
    async def test_validate_organization_access_denied(
        self,
        tenancy_service: MultiTenancyService,
        test_user: User,
        organization_factory
    ):
        """Test organization access validation failure."""
        # Create organization the user is not a member of
        other_org = await organization_factory.create_organization(
            tenancy_service.db,
            name="Other Organization",
            slug="other-org"
        )
        
        context = TenantContext(
            user_id=test_user.id,
            organization_id="different-org-id",
            role=MemberRole.VIEWER
        )
        
        with pytest.raises(TenantAccessDeniedError):
            await tenancy_service.validate_organization_access(
                context, other_org.id
            )
    
    async def test_validate_organization_modify_access_success(
        self,
        tenancy_service: MultiTenancyService,
        test_organization_with_member: tuple[Organization, OrganizationMember],
        test_user: User
    ):
        """Test successful organization modify access validation."""
        organization, member = test_organization_with_member
        context = TenantContext(
            user_id=test_user.id,
            organization_id=organization.id,
            role=MemberRole.OWNER  # Owner can modify
        )
        
        # Should not raise exception
        await tenancy_service.validate_organization_access(
            context, organization.id, require_modify=True
        )
    
    async def test_validate_organization_modify_access_denied(
        self,
        tenancy_service: MultiTenancyService,
        test_organization_with_member: tuple[Organization, OrganizationMember],
        test_user: User
    ):
        """Test organization modify access validation failure."""
        organization, member = test_organization_with_member
        context = TenantContext(
            user_id=test_user.id,
            organization_id=organization.id,
            role=MemberRole.VIEWER  # Viewer cannot modify
        )
        
        with pytest.raises(TenantAccessDeniedError):
            await tenancy_service.validate_organization_access(
                context, organization.id, require_modify=True
            )
    
    async def test_validate_project_access_success(
        self,
        tenancy_service: MultiTenancyService,
        test_project: Project,
        test_organization_with_member: tuple[Organization, OrganizationMember],
        test_user: User
    ):
        """Test successful project access validation."""
        organization, member = test_organization_with_member
        context = TenantContext(
            user_id=test_user.id,
            organization_id=organization.id,
            role=member.role
        )
        
        project = await tenancy_service.validate_project_access(
            context, test_project.id
        )
        
        assert project.id == test_project.id
        assert project.organization_id == organization.id
    
    async def test_validate_project_access_denied(
        self,
        tenancy_service: MultiTenancyService,
        test_user: User,
        organization_factory,
        project_factory
    ):
        """Test project access validation failure."""
        # Create project in different organization
        other_org = await organization_factory.create_organization(
            tenancy_service.db,
            name="Other Organization", 
            slug="other-org"
        )
        other_user = await tenancy_service.db.execute(
            "INSERT INTO users (email, full_name, hashed_password, is_active) "
            "VALUES ('other@example.com', 'Other User', 'hash', true) "
            "RETURNING id"
        )
        other_user_id = other_user.scalar()
        
        other_project = await project_factory.create_project(
            tenancy_service.db,
            user_id=other_user_id,
            organization=other_org
        )
        
        context = TenantContext(
            user_id=test_user.id,
            organization_id="different-org-id",
            role=MemberRole.VIEWER
        )
        
        with pytest.raises(TenantAccessDeniedError):
            await tenancy_service.validate_project_access(
                context, other_project.id
            )
    
    async def test_add_organization_filter(
        self,
        tenancy_service: MultiTenancyService,
        test_organization_with_member: tuple[Organization, OrganizationMember],
        test_user: User
    ):
        """Test adding organization filter to query."""
        from sqlalchemy import select
        
        organization, member = test_organization_with_member
        context = TenantContext(
            user_id=test_user.id,
            organization_id=organization.id,
            role=member.role
        )
        
        # Create base query
        base_query = select(Project)
        
        # Apply organization filter
        filtered_query = tenancy_service.add_organization_filter(
            base_query, Project, context
        )
        
        # The filtered query should have a WHERE clause
        query_str = str(filtered_query)
        assert "WHERE" in query_str
        assert "organization_id" in query_str
    
    async def test_superuser_bypass_tenant_checks(
        self,
        tenancy_service: MultiTenancyService,
        superuser: User,
        test_organization: Organization
    ):
        """Test that superuser bypasses tenant access checks."""
        context = TenantContext(
            user_id=superuser.id,
            organization_id=None,  # Superuser may not have org membership
            role=None,
            is_superuser=True
        )
        
        # Should not raise exception even without org membership
        await tenancy_service.validate_organization_access(
            context, test_organization.id
        )
    
    async def test_get_user_organizations(
        self,
        tenancy_service: MultiTenancyService,
        test_organization_with_member: tuple[Organization, OrganizationMember],
        test_user: User
    ):
        """Test getting user organizations."""
        organization, member = test_organization_with_member
        
        organizations = await tenancy_service.get_user_organizations(test_user.id)
        
        assert len(organizations) >= 1
        
        found_org = None
        for org_data in organizations:
            if org_data["id"] == organization.id:
                found_org = org_data
                break
        
        assert found_org is not None
        assert found_org["name"] == organization.name
        assert found_org["role"] == member.role
        assert found_org["is_owner"] == (member.role == MemberRole.OWNER)
        assert found_org["can_modify"] == (member.role in [MemberRole.OWNER, MemberRole.ADMIN])
    
    async def test_get_organization_projects(
        self,
        tenancy_service: MultiTenancyService,
        test_project: Project,
        test_organization_with_member: tuple[Organization, OrganizationMember],
        test_user: User
    ):
        """Test getting organization projects."""
        organization, member = test_organization_with_member
        context = TenantContext(
            user_id=test_user.id,
            organization_id=organization.id,
            role=member.role
        )
        
        projects = await tenancy_service.get_organization_projects(
            context, organization.id
        )
        
        assert len(projects) >= 1
        
        found_project = None
        for project in projects:
            if project.id == test_project.id:
                found_project = project
                break
        
        assert found_project is not None
        assert found_project.organization_id == organization.id


@pytest.mark.unit
class TestTenantContext:
    """Test cases for TenantContext."""
    
    def test_can_access_organization_same_org(self):
        """Test organization access for same organization."""
        context = TenantContext(
            user_id=1,
            organization_id="org-123",
            role=MemberRole.VIEWER
        )
        
        assert context.can_access_organization("org-123") is True
    
    def test_can_access_organization_different_org(self):
        """Test organization access for different organization."""
        context = TenantContext(
            user_id=1,
            organization_id="org-123",
            role=MemberRole.VIEWER
        )
        
        assert context.can_access_organization("org-456") is False
    
    def test_can_access_organization_superuser(self):
        """Test organization access for superuser."""
        context = TenantContext(
            user_id=1,
            organization_id=None,
            role=None,
            is_superuser=True
        )
        
        assert context.can_access_organization("any-org") is True
    
    def test_can_modify_organization_owner(self):
        """Test organization modify access for owner."""
        context = TenantContext(
            user_id=1,
            organization_id="org-123",
            role=MemberRole.OWNER
        )
        
        assert context.can_modify_organization("org-123") is True
    
    def test_can_modify_organization_admin(self):
        """Test organization modify access for admin."""
        context = TenantContext(
            user_id=1,
            organization_id="org-123",
            role=MemberRole.ADMIN
        )
        
        assert context.can_modify_organization("org-123") is True
    
    def test_can_modify_organization_viewer(self):
        """Test organization modify access for viewer."""
        context = TenantContext(
            user_id=1,
            organization_id="org-123",
            role=MemberRole.VIEWER
        )
        
        assert context.can_modify_organization("org-123") is False
    
    def test_can_access_project_same_org(self):
        """Test project access for same organization."""
        context = TenantContext(
            user_id=1,
            organization_id="org-123",
            role=MemberRole.VIEWER
        )
        
        assert context.can_access_project("org-123") is True
    
    def test_can_access_project_different_org(self):
        """Test project access for different organization."""
        context = TenantContext(
            user_id=1,
            organization_id="org-123",
            role=MemberRole.VIEWER
        )
        
        assert context.can_access_project("org-456") is False