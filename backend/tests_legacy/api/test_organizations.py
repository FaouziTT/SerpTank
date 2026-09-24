"""
Tests for organizations API endpoints.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.organization import Organization, OrganizationMember, MemberRole


@pytest.mark.api
class TestOrganizationsAPI:
    """Test cases for organizations API endpoints."""
    
    async def test_create_organization_success(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict,
        test_user: User
    ):
        """Test successful organization creation."""
        org_data = {
            "name": "Test Organization",
            "description": "A test organization"
        }
        
        response = await async_client.post(
            "/api/v1/organizations/",
            json=org_data,
            headers=authenticated_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == org_data["name"]
        assert data["description"] == org_data["description"]
        assert "id" in data
        assert "slug" in data
        assert data["is_active"] is True
    
    async def test_create_organization_unauthenticated(
        self,
        async_client: AsyncClient
    ):
        """Test organization creation without authentication."""
        org_data = {
            "name": "Test Organization",
            "description": "A test organization"
        }
        
        response = await async_client.post(
            "/api/v1/organizations/",
            json=org_data
        )
        
        assert response.status_code == 401
    
    async def test_get_user_organizations(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict,
        test_organization_with_member: tuple[Organization, OrganizationMember]
    ):
        """Test getting user's organizations."""
        organization, member = test_organization_with_member
        
        response = await async_client.get(
            "/api/v1/organizations/",
            headers=authenticated_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        org_found = False
        for org in data:
            if org["id"] == organization.id:
                org_found = True
                assert org["name"] == organization.name
                break
        
        assert org_found, "Organization should be found in user's organizations"
    
    async def test_get_organization_details(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict,
        test_organization_with_member: tuple[Organization, OrganizationMember]
    ):
        """Test getting organization details."""
        organization, member = test_organization_with_member
        
        response = await async_client.get(
            f"/api/v1/organizations/{organization.id}",
            headers=authenticated_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == organization.id
        assert data["name"] == organization.name
        assert data["description"] == organization.description
    
    async def test_get_organization_details_unauthorized(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict,
        test_organization: Organization
    ):
        """Test getting organization details without membership."""
        response = await async_client.get(
            f"/api/v1/organizations/{test_organization.id}",
            headers=authenticated_headers
        )
        
        assert response.status_code == 403
    
    async def test_update_organization_success(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict,
        test_organization_with_member: tuple[Organization, OrganizationMember]
    ):
        """Test successful organization update."""
        organization, member = test_organization_with_member
        
        update_data = {
            "name": "Updated Organization Name",
            "description": "Updated description"
        }
        
        response = await async_client.put(
            f"/api/v1/organizations/{organization.id}",
            json=update_data,
            headers=authenticated_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["description"] == update_data["description"]
    
    async def test_update_organization_unauthorized(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict,
        test_organization: Organization
    ):
        """Test organization update without proper permissions."""
        update_data = {
            "name": "Unauthorized Update",
            "description": "Should not work"
        }
        
        response = await async_client.put(
            f"/api/v1/organizations/{test_organization.id}",
            json=update_data,
            headers=authenticated_headers
        )
        
        assert response.status_code == 403
    
    async def test_delete_organization_success(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict,
        test_organization_with_member: tuple[Organization, OrganizationMember]
    ):
        """Test successful organization deletion."""
        organization, member = test_organization_with_member
        
        response = await async_client.delete(
            f"/api/v1/organizations/{organization.id}",
            headers=authenticated_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "deleted successfully" in data["message"]
    
    async def test_get_organization_members(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict,
        test_organization_with_member: tuple[Organization, OrganizationMember]
    ):
        """Test getting organization members."""
        organization, member = test_organization_with_member
        
        response = await async_client.get(
            f"/api/v1/organizations/{organization.id}/members",
            headers=authenticated_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        member_found = False
        for org_member in data:
            if org_member["user_id"] == str(member.user_id):
                member_found = True
                assert org_member["role"] == member.role
                break
        
        assert member_found, "Member should be found in organization members"
    
    async def test_rate_limiting_on_organization_creation(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict
    ):
        """Test rate limiting on organization creation."""
        org_data = {
            "name": "Rate Limited Org",
            "description": "Testing rate limits"
        }
        
        # Make multiple rapid requests to trigger rate limiting
        responses = []
        for i in range(70):  # Exceed the 60 requests per minute limit
            response = await async_client.post(
                "/api/v1/organizations/",
                json={**org_data, "name": f"Org {i}"},
                headers=authenticated_headers
            )
            responses.append(response)
        
        # Should have at least one rate-limited response
        rate_limited = any(r.status_code == 429 for r in responses)
        assert rate_limited, "Should have rate-limited responses"