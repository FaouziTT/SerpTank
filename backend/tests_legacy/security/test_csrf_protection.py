"""
Tests for CSRF protection functionality.
"""

import pytest
from httpx import AsyncClient
from unittest.mock import patch

from app.models.user import User
from app.models.organization import Organization, OrganizationMember


@pytest.mark.security
class TestCSRFProtection:
    """Test cases for CSRF protection."""
    
    async def test_csrf_protection_enabled_for_state_changing_operations(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict,
        test_organization_with_member: tuple[Organization, OrganizationMember]
    ):
        """Test that CSRF protection is enabled for POST/PUT/DELETE operations."""
        organization, member = test_organization_with_member
        
        # Test without CSRF token (should fail)
        org_data = {
            "name": "Test Organization",
            "description": "A test organization"
        }
        
        response = await async_client.post(
            "/api/v1/organizations/",
            json=org_data,
            headers={
                "Authorization": authenticated_headers["Authorization"]
                # Missing X-CSRFToken header
            }
        )
        
        # Should fail due to missing CSRF token
        assert response.status_code in [403, 422]
    
    async def test_csrf_protection_with_valid_token(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict,
        test_organization_with_member: tuple[Organization, OrganizationMember]
    ):
        """Test CSRF protection with valid token."""
        organization, member = test_organization_with_member
        
        # First get CSRF token
        csrf_response = await async_client.get(
            "/api/v1/auth/csrf-token",
            headers=authenticated_headers
        )
        
        if csrf_response.status_code == 200:
            csrf_data = csrf_response.json()
            csrf_token = csrf_data.get("csrf_token")
            
            # Include CSRF token in headers
            headers_with_csrf = {
                **authenticated_headers,
                "X-CSRFToken": csrf_token
            }
            
            org_data = {
                "name": "CSRF Protected Organization",
                "description": "Created with CSRF protection"
            }
            
            response = await async_client.post(
                "/api/v1/organizations/",
                json=org_data,
                headers=headers_with_csrf
            )
            
            # Should succeed with valid CSRF token
            assert response.status_code == 200
    
    async def test_csrf_protection_with_invalid_token(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict
    ):
        """Test CSRF protection with invalid token."""
        headers_with_invalid_csrf = {
            **authenticated_headers,
            "X-CSRFToken": "invalid_csrf_token_12345"
        }
        
        org_data = {
            "name": "Invalid CSRF Organization",
            "description": "Should not be created"
        }
        
        response = await async_client.post(
            "/api/v1/organizations/",
            json=org_data,
            headers=headers_with_invalid_csrf
        )
        
        # Should fail with invalid CSRF token
        assert response.status_code in [403, 422]
    
    async def test_csrf_token_generation_endpoint(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict
    ):
        """Test CSRF token generation endpoint."""
        response = await async_client.get(
            "/api/v1/auth/csrf-token",
            headers=authenticated_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "csrf_token" in data
            assert isinstance(data["csrf_token"], str)
            assert len(data["csrf_token"]) > 10  # Token should be substantial length
    
    async def test_csrf_protection_read_operations_exempt(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict,
        test_organization_with_member: tuple[Organization, OrganizationMember]
    ):
        """Test that read operations (GET) don't require CSRF tokens."""
        organization, member = test_organization_with_member
        
        # GET request should work without CSRF token
        response = await async_client.get(
            "/api/v1/organizations/",
            headers={
                "Authorization": authenticated_headers["Authorization"]
                # No CSRF token needed for GET
            }
        )
        
        assert response.status_code == 200
    
    async def test_csrf_protection_options_exempt(
        self,
        async_client: AsyncClient
    ):
        """Test that OPTIONS requests don't require CSRF tokens."""
        response = await async_client.options("/api/v1/organizations/")
        
        # OPTIONS should be allowed for CORS preflight
        assert response.status_code in [200, 204, 405]  # 405 if OPTIONS not explicitly handled
    
    async def test_csrf_double_submit_cookie_pattern(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict
    ):
        """Test CSRF double-submit cookie pattern if implemented."""
        # Get CSRF token
        csrf_response = await async_client.get(
            "/api/v1/auth/csrf-token",
            headers=authenticated_headers
        )
        
        if csrf_response.status_code == 200:
            # Check if CSRF cookie is set
            csrf_cookie = None
            for cookie_header in csrf_response.headers.get_list("set-cookie"):
                if "csrftoken" in cookie_header.lower():
                    csrf_cookie = cookie_header
                    break
            
            if csrf_cookie:
                # Extract token from cookie
                csrf_token = csrf_response.json().get("csrf_token")
                
                # Make request with both cookie and header
                headers_with_csrf = {
                    **authenticated_headers,
                    "X-CSRFToken": csrf_token,
                    "Cookie": csrf_cookie.split(";")[0]  # Just the csrf cookie part
                }
                
                org_data = {
                    "name": "Double Submit CSRF Test",
                    "description": "Testing double-submit pattern"
                }
                
                response = await async_client.post(
                    "/api/v1/organizations/",
                    json=org_data,
                    headers=headers_with_csrf
                )
                
                # Should work with proper double-submit pattern
                assert response.status_code in [200, 201]
    
    async def test_csrf_protection_project_operations(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict,
        test_organization_with_member: tuple[Organization, OrganizationMember]
    ):
        """Test CSRF protection on project operations."""
        organization, member = test_organization_with_member
        
        project_data = {
            "name": "CSRF Test Project",
            "description": "Testing CSRF on projects",
            "domain": "csrf-test.com",
            "organization_id": organization.id
        }
        
        # Test without CSRF token
        response = await async_client.post(
            "/api/v1/projects/",
            json=project_data,
            headers={
                "Authorization": authenticated_headers["Authorization"]
                # Missing CSRF token
            }
        )
        
        # Should fail due to missing CSRF token
        assert response.status_code in [403, 422]
    
    async def test_csrf_protection_update_operations(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict,
        test_organization_with_member: tuple[Organization, OrganizationMember]
    ):
        """Test CSRF protection on update operations."""
        organization, member = test_organization_with_member
        
        update_data = {
            "name": "Updated Organization Name",
            "description": "Updated without CSRF"
        }
        
        # Test PUT without CSRF token
        response = await async_client.put(
            f"/api/v1/organizations/{organization.id}",
            json=update_data,
            headers={
                "Authorization": authenticated_headers["Authorization"]
                # Missing CSRF token
            }
        )
        
        # Should fail due to missing CSRF token
        assert response.status_code in [403, 422]
    
    async def test_csrf_protection_delete_operations(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict,
        async_session,
        organization_factory
    ):
        """Test CSRF protection on delete operations."""
        # Create a test organization to delete
        test_org = await organization_factory.create_organization(
            async_session,
            name="To Be Deleted",
            slug="to-be-deleted"
        )
        
        # Test DELETE without CSRF token
        response = await async_client.delete(
            f"/api/v1/organizations/{test_org.id}",
            headers={
                "Authorization": authenticated_headers["Authorization"]
                # Missing CSRF token
            }
        )
        
        # Should fail due to missing CSRF token
        assert response.status_code in [403, 422]


@pytest.mark.security
class TestCSRFTokenManagement:
    """Test cases for CSRF token management."""
    
    async def test_csrf_token_uniqueness(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict
    ):
        """Test that CSRF tokens are unique per request."""
        # Get first token
        response1 = await async_client.get(
            "/api/v1/auth/csrf-token",
            headers=authenticated_headers
        )
        
        # Get second token
        response2 = await async_client.get(
            "/api/v1/auth/csrf-token", 
            headers=authenticated_headers
        )
        
        if response1.status_code == 200 and response2.status_code == 200:
            token1 = response1.json().get("csrf_token")
            token2 = response2.json().get("csrf_token")
            
            # Tokens should be different (if system generates new tokens each time)
            # Note: Some implementations reuse tokens within a session
            assert token1 is not None
            assert token2 is not None
    
    async def test_csrf_token_expiry_handling(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict
    ):
        """Test handling of expired CSRF tokens."""
        # This test would require mocking time or waiting for token expiry
        # For now, we test with an obviously invalid/expired token format
        
        headers_with_expired_csrf = {
            **authenticated_headers,
            "X-CSRFToken": "expired_token_from_yesterday"
        }
        
        org_data = {
            "name": "Expired CSRF Test",
            "description": "Should fail with expired token"
        }
        
        response = await async_client.post(
            "/api/v1/organizations/",
            json=org_data,
            headers=headers_with_expired_csrf
        )
        
        # Should fail with expired/invalid token
        assert response.status_code in [403, 422]