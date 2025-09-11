"""
Tests for projects API endpoints.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.organization import Organization, OrganizationMember, MemberRole
from app.models.project import Project


@pytest.mark.api
class TestProjectsAPI:
    """Test cases for projects API endpoints."""
    
    async def test_create_project_success(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict,
        test_organization_with_member: tuple[Organization, OrganizationMember]
    ):
        """Test successful project creation."""
        organization, member = test_organization_with_member
        
        project_data = {
            "name": "Test Project",
            "description": "A test project",
            "domain": "example.com",
            "organization_id": organization.id
        }
        
        response = await async_client.post(
            "/api/v1/projects/",
            json=project_data,
            headers=authenticated_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == project_data["name"]
        assert data["description"] == project_data["description"]
        assert data["domain"] == project_data["domain"]
        assert data["organization_id"] == organization.id
        assert "id" in data
        assert data["is_active"] is True
    
    async def test_create_project_unauthenticated(
        self,
        async_client: AsyncClient,
        test_organization: Organization
    ):
        """Test project creation without authentication."""
        project_data = {
            "name": "Test Project",
            "description": "A test project",
            "domain": "example.com",
            "organization_id": test_organization.id
        }
        
        response = await async_client.post(
            "/api/v1/projects/",
            json=project_data
        )
        
        assert response.status_code == 401
    
    async def test_create_project_unauthorized_organization(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict,
        test_organization: Organization
    ):
        """Test project creation in organization without membership."""
        project_data = {
            "name": "Test Project",
            "description": "A test project", 
            "domain": "example.com",
            "organization_id": test_organization.id
        }
        
        response = await async_client.post(
            "/api/v1/projects/",
            json=project_data,
            headers=authenticated_headers
        )
        
        assert response.status_code == 403
    
    async def test_get_organization_projects(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict,
        test_project: Project,
        test_organization_with_member: tuple[Organization, OrganizationMember]
    ):
        """Test getting organization projects."""
        organization, member = test_organization_with_member
        
        response = await async_client.get(
            f"/api/v1/projects/?organization_id={organization.id}",
            headers=authenticated_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        project_found = False
        for project in data:
            if project["id"] == test_project.id:
                project_found = True
                assert project["organization_id"] == organization.id
                break
        
        assert project_found, "Project should be found in organization projects"
    
    async def test_get_project_details(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict,
        test_project: Project
    ):
        """Test getting project details."""
        response = await async_client.get(
            f"/api/v1/projects/{test_project.id}",
            headers=authenticated_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_project.id
        assert data["name"] == test_project.name
        assert data["description"] == test_project.description
        assert data["domain"] == test_project.domain
    
    async def test_get_project_details_unauthorized(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict,
        async_session: AsyncSession,
        organization_factory,
        project_factory
    ):
        """Test getting project details without access."""
        # Create project in different organization
        other_org = await organization_factory.create_organization(
            async_session,
            name="Other Organization",
            slug="other-org"
        )
        
        # Create another user for the other organization
        from app.models.user import User
        from sqlalchemy import insert
        result = await async_session.execute(
            insert(User).values(
                email="other@example.com",
                full_name="Other User",
                hashed_password="hash",
                is_active=True
            ).returning(User.id)
        )
        other_user_id = result.scalar()
        await async_session.commit()
        
        other_project = await project_factory.create_project(
            async_session,
            user_id=other_user_id,
            organization=other_org
        )
        
        response = await async_client.get(
            f"/api/v1/projects/{other_project.id}",
            headers=authenticated_headers
        )
        
        assert response.status_code == 403
    
    async def test_update_project_success(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict,
        test_project: Project
    ):
        """Test successful project update."""
        update_data = {
            "name": "Updated Project Name",
            "description": "Updated description",
            "domain": "updated-example.com"
        }
        
        response = await async_client.put(
            f"/api/v1/projects/{test_project.id}",
            json=update_data,
            headers=authenticated_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["description"] == update_data["description"]
        assert data["domain"] == update_data["domain"]
    
    async def test_update_project_unauthorized(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict,
        async_session: AsyncSession,
        organization_factory,
        project_factory
    ):
        """Test project update without proper permissions."""
        # Create project in different organization
        other_org = await organization_factory.create_organization(
            async_session,
            name="Other Organization",
            slug="other-org"
        )
        
        from app.models.user import User
        from sqlalchemy import insert
        result = await async_session.execute(
            insert(User).values(
                email="other@example.com",
                full_name="Other User", 
                hashed_password="hash",
                is_active=True
            ).returning(User.id)
        )
        other_user_id = result.scalar()
        await async_session.commit()
        
        other_project = await project_factory.create_project(
            async_session,
            user_id=other_user_id,
            organization=other_org
        )
        
        update_data = {
            "name": "Unauthorized Update",
            "description": "Should not work"
        }
        
        response = await async_client.put(
            f"/api/v1/projects/{other_project.id}",
            json=update_data,
            headers=authenticated_headers
        )
        
        assert response.status_code == 403
    
    async def test_delete_project_success(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict,
        test_project: Project
    ):
        """Test successful project deletion."""
        response = await async_client.delete(
            f"/api/v1/projects/{test_project.id}",
            headers=authenticated_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "deleted successfully" in data["message"]
    
    async def test_rate_limiting_on_project_creation(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict,
        test_organization_with_member: tuple[Organization, OrganizationMember]
    ):
        """Test rate limiting on project creation (data-intensive operations)."""
        organization, member = test_organization_with_member
        
        project_data = {
            "name": "Rate Limited Project",
            "description": "Testing rate limits",
            "domain": "ratelimit.com",
            "organization_id": organization.id
        }
        
        # Make multiple rapid requests to trigger rate limiting
        # Project creation uses data-intensive rate limiting (10 requests/min)
        responses = []
        for i in range(15):  # Exceed the 10 requests per minute limit
            response = await async_client.post(
                "/api/v1/projects/",
                json={**project_data, "name": f"Project {i}", "domain": f"example{i}.com"},
                headers=authenticated_headers
            )
            responses.append(response)
        
        # Should have at least one rate-limited response
        rate_limited = any(r.status_code == 429 for r in responses)
        assert rate_limited, "Should have rate-limited responses for data-intensive operations"
    
    async def test_project_sites_endpoint(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict,
        test_project: Project
    ):
        """Test getting project sites."""
        response = await async_client.get(
            f"/api/v1/projects/{test_project.id}/sites",
            headers=authenticated_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Sites might be empty for a new project
    
    async def test_project_analytics_endpoint(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict,
        test_project: Project
    ):
        """Test getting project analytics."""
        response = await async_client.get(
            f"/api/v1/projects/{test_project.id}/analytics",
            headers=authenticated_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        # Analytics data structure should be validated
        assert "overview" in data or "message" in data  # May return empty state message