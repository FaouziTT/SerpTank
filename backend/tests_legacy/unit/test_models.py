"""
Unit tests for database models.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.models.organization import Organization, OrganizationMember, MemberRole, MemberStatus
from app.models.project import Project


@pytest.mark.unit
class TestUserModel:
    """Test cases for User model."""
    
    async def test_user_creation(self, async_session: AsyncSession):
        """Test creating a user."""
        user = User(
            email="test@example.com",
            full_name="Test User",
            hashed_password="hashed_password_123",
            is_active=True,
            is_superuser=False
        )
        
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)
        
        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.is_active is True
        assert user.is_superuser is False
        assert user.created_at is not None
        assert user.updated_at is not None
    
    async def test_user_email_uniqueness(self, async_session: AsyncSession):
        """Test that user emails must be unique."""
        # Create first user
        user1 = User(
            email="unique@example.com",
            full_name="User One",
            hashed_password="hash1",
            is_active=True
        )
        async_session.add(user1)
        await async_session.commit()
        
        # Try to create second user with same email
        user2 = User(
            email="unique@example.com",
            full_name="User Two", 
            hashed_password="hash2",
            is_active=True
        )
        async_session.add(user2)
        
        with pytest.raises(Exception):  # Should raise IntegrityError
            await async_session.commit()
    
    async def test_user_string_representation(self, async_session: AsyncSession):
        """Test user string representation."""
        user = User(
            email="repr@example.com",
            full_name="Repr User",
            hashed_password="hash",
            is_active=True
        )
        
        assert str(user) == "repr@example.com"


@pytest.mark.unit
class TestOrganizationModel:
    """Test cases for Organization model."""
    
    async def test_organization_creation(self, async_session: AsyncSession):
        """Test creating an organization."""
        org = Organization(
            name="Test Organization",
            slug="test-organization",
            description="A test organization",
            is_active=True
        )
        
        async_session.add(org)
        await async_session.commit()
        await async_session.refresh(org)
        
        assert org.id is not None
        assert org.name == "Test Organization"
        assert org.slug == "test-organization"
        assert org.description == "A test organization"
        assert org.is_active is True
        assert org.created_at is not None
        assert org.updated_at is not None
    
    async def test_organization_slug_uniqueness(self, async_session: AsyncSession):
        """Test that organization slugs must be unique."""
        # Create first organization
        org1 = Organization(
            name="Org One",
            slug="unique-slug",
            description="First org",
            is_active=True
        )
        async_session.add(org1)
        await async_session.commit()
        
        # Try to create second organization with same slug
        org2 = Organization(
            name="Org Two",
            slug="unique-slug",
            description="Second org",
            is_active=True
        )
        async_session.add(org2)
        
        with pytest.raises(Exception):  # Should raise IntegrityError
            await async_session.commit()
    
    async def test_organization_string_representation(self, async_session: AsyncSession):
        """Test organization string representation."""
        org = Organization(
            name="Repr Organization",
            slug="repr-org",
            description="For testing repr",
            is_active=True
        )
        
        assert str(org) == "Repr Organization"


@pytest.mark.unit
class TestOrganizationMemberModel:
    """Test cases for OrganizationMember model."""
    
    async def test_organization_member_creation(
        self,
        async_session: AsyncSession,
        test_user: User,
        test_organization: Organization
    ):
        """Test creating an organization member."""
        member = OrganizationMember(
            user_id=test_user.id,
            organization_id=test_organization.id,
            role=MemberRole.ADMIN,
            status=MemberStatus.ACTIVE,
            invited_by_user_id=test_user.id
        )
        
        async_session.add(member)
        await async_session.commit()
        await async_session.refresh(member)
        
        assert member.user_id == test_user.id
        assert member.organization_id == test_organization.id
        assert member.role == MemberRole.ADMIN
        assert member.status == MemberStatus.ACTIVE
        assert member.invited_by_user_id == test_user.id
        assert member.created_at is not None
        assert member.updated_at is not None
    
    async def test_member_role_enum(self):
        """Test MemberRole enum values."""
        assert MemberRole.OWNER == "owner"
        assert MemberRole.ADMIN == "admin"
        assert MemberRole.MANAGER == "manager"
        assert MemberRole.ANALYST == "analyst"
        assert MemberRole.VIEWER == "viewer"
    
    async def test_member_status_enum(self):
        """Test MemberStatus enum values."""
        assert MemberStatus.PENDING == "pending"
        assert MemberStatus.ACTIVE == "active"
        assert MemberStatus.SUSPENDED == "suspended"
    
    async def test_unique_user_organization_constraint(
        self,
        async_session: AsyncSession,
        test_user: User,
        test_organization: Organization
    ):
        """Test that user can only have one membership per organization."""
        # Create first membership
        member1 = OrganizationMember(
            user_id=test_user.id,
            organization_id=test_organization.id,
            role=MemberRole.ADMIN,
            status=MemberStatus.ACTIVE,
            invited_by_user_id=test_user.id
        )
        async_session.add(member1)
        await async_session.commit()
        
        # Try to create second membership for same user/org
        member2 = OrganizationMember(
            user_id=test_user.id,
            organization_id=test_organization.id,
            role=MemberRole.VIEWER,
            status=MemberStatus.ACTIVE,
            invited_by_user_id=test_user.id
        )
        async_session.add(member2)
        
        with pytest.raises(Exception):  # Should raise IntegrityError
            await async_session.commit()


@pytest.mark.unit
class TestProjectModel:
    """Test cases for Project model."""
    
    async def test_project_creation(
        self,
        async_session: AsyncSession,
        test_user: User,
        test_organization: Organization
    ):
        """Test creating a project."""
        project = Project(
            name="Test Project",
            description="A test project",
            domain="example.com",
            organization_id=test_organization.id,
            created_by_user_id=test_user.id,
            is_active=True
        )
        
        async_session.add(project)
        await async_session.commit()
        await async_session.refresh(project)
        
        assert project.id is not None
        assert project.name == "Test Project"
        assert project.description == "A test project"
        assert project.domain == "example.com"
        assert project.organization_id == test_organization.id
        assert project.created_by_user_id == test_user.id
        assert project.is_active is True
        assert project.created_at is not None
        assert project.updated_at is not None
    
    async def test_project_organization_relationship(
        self,
        async_session: AsyncSession,
        test_project: Project,
        test_organization: Organization
    ):
        """Test project-organization relationship."""
        # Load project with organization relationship
        result = await async_session.execute(
            select(Project)
            .where(Project.id == test_project.id)
        )
        project = result.scalar_one()
        
        assert project.organization_id == test_organization.id
    
    async def test_project_string_representation(self, async_session: AsyncSession):
        """Test project string representation."""
        from app.models.organization import Organization
        from app.models.user import User
        
        # Create test data
        user = User(
            email="project_test@example.com",
            full_name="Project Test User",
            hashed_password="hash",
            is_active=True
        )
        async_session.add(user)
        await async_session.flush()
        
        org = Organization(
            name="Project Test Org",
            slug="project-test-org",
            description="For project testing",
            is_active=True
        )
        async_session.add(org)
        await async_session.flush()
        
        project = Project(
            name="Repr Project",
            description="For testing repr",
            domain="repr.com",
            organization_id=org.id,
            created_by_user_id=user.id,
            is_active=True
        )
        
        assert str(project) == "Repr Project"
    
    async def test_project_domain_validation(
        self,
        async_session: AsyncSession,
        test_user: User,
        test_organization: Organization
    ):
        """Test project domain field."""
        project = Project(
            name="Domain Test Project",
            description="Testing domain field",
            domain="valid-domain.com",
            organization_id=test_organization.id,
            created_by_user_id=test_user.id,
            is_active=True
        )
        
        async_session.add(project)
        await async_session.commit()
        await async_session.refresh(project)
        
        assert project.domain == "valid-domain.com"


@pytest.mark.unit
class TestModelRelationships:
    """Test cases for model relationships."""
    
    async def test_organization_members_relationship(
        self,
        async_session: AsyncSession,
        test_organization_with_member: tuple[Organization, OrganizationMember]
    ):
        """Test organization members relationship."""
        organization, member = test_organization_with_member
        
        # Query organization and check members
        result = await async_session.execute(
            select(Organization)
            .where(Organization.id == organization.id)
        )
        org = result.scalar_one()
        
        # Note: In a real scenario, you'd need to configure relationships
        # For now, we just verify the foreign key relationship works
        assert member.organization_id == org.id
    
    async def test_organization_projects_relationship(
        self,
        async_session: AsyncSession,
        test_organization: Organization,
        test_project: Project
    ):
        """Test organization projects relationship."""
        # Verify project belongs to organization
        assert test_project.organization_id == test_organization.id
        
        # Query to verify relationship
        result = await async_session.execute(
            select(Project)
            .where(Project.organization_id == test_organization.id)
        )
        projects = result.scalars().all()
        
        project_ids = [p.id for p in projects]
        assert test_project.id in project_ids
    
    async def test_user_created_projects_relationship(
        self,
        async_session: AsyncSession,
        test_user: User,
        test_project: Project
    ):
        """Test user created projects relationship."""
        # Verify project was created by user
        assert test_project.created_by_user_id == test_user.id
        
        # Query projects created by user
        result = await async_session.execute(
            select(Project)
            .where(Project.created_by_user_id == test_user.id)
        )
        projects = result.scalars().all()
        
        project_ids = [p.id for p in projects]
        assert test_project.id in project_ids