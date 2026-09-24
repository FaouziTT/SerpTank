"""
Integration tests for complete authentication flows.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.organization import Organization


@pytest.mark.integration
class TestAuthenticationFlow:
    """Integration tests for complete authentication workflows."""
    
    async def test_complete_registration_login_flow(
        self,
        async_client: AsyncClient,
        async_session: AsyncSession
    ):
        """Test complete user registration and login flow."""
        # Step 1: Register new user
        registration_data = {
            "email": "integration@example.com",
            "password": "securepassword123",
            "full_name": "Integration Test User"
        }
        
        register_response = await async_client.post(
            "/api/v1/auth/register",
            json=registration_data
        )
        
        assert register_response.status_code == 200
        register_data = register_response.json()
        assert register_data["email"] == registration_data["email"]
        assert "access_token" in register_data
        assert "refresh_token" in register_data
        
        # Step 2: Login with new user
        login_data = {
            "email": registration_data["email"],
            "password": registration_data["password"],
            "remember_me": False
        }
        
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json=login_data
        )
        
        assert login_response.status_code == 200
        login_result = login_response.json()
        assert "access_token" in login_result
        assert "refresh_token" in login_result
        assert login_result["user"]["email"] == registration_data["email"]
        
        # Step 3: Use access token to make authenticated request
        auth_headers = {
            "Authorization": f"Bearer {login_result['access_token']}"
        }
        
        profile_response = await async_client.get(
            "/api/v1/auth/me",
            headers=auth_headers
        )
        
        assert profile_response.status_code == 200
        profile_data = profile_response.json()
        assert profile_data["email"] == registration_data["email"]
    
    async def test_token_refresh_flow(
        self,
        async_client: AsyncClient,
        test_user: User
    ):
        """Test token refresh flow."""
        # Step 1: Login to get tokens
        login_data = {
            "email": test_user.email,
            "password": "testpassword123",
            "remember_me": False
        }
        
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json=login_data
        )
        
        assert login_response.status_code == 200
        login_result = login_response.json()
        original_access_token = login_result["access_token"]
        refresh_token = login_result["refresh_token"]
        
        # Step 2: Refresh tokens
        refresh_response = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert refresh_response.status_code == 200
        refresh_result = refresh_response.json()
        new_access_token = refresh_result["access_token"]
        new_refresh_token = refresh_result["refresh_token"]
        
        # Tokens should be different
        assert new_access_token != original_access_token
        assert new_refresh_token != refresh_token
        
        # Step 3: Use new access token
        auth_headers = {
            "Authorization": f"Bearer {new_access_token}"
        }
        
        profile_response = await async_client.get(
            "/api/v1/auth/me",
            headers=auth_headers
        )
        
        assert profile_response.status_code == 200
    
    async def test_logout_flow(
        self,
        async_client: AsyncClient,
        test_user: User
    ):
        """Test logout flow."""
        # Step 1: Login
        login_data = {
            "email": test_user.email,
            "password": "testpassword123",
            "remember_me": False
        }
        
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json=login_data
        )
        
        assert login_response.status_code == 200
        login_result = login_response.json()
        access_token = login_result["access_token"]
        refresh_token = login_result["refresh_token"]
        
        # Step 2: Make authenticated request (should work)
        auth_headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        profile_response = await async_client.get(
            "/api/v1/auth/me",
            headers=auth_headers
        )
        
        assert profile_response.status_code == 200
        
        # Step 3: Logout
        logout_response = await async_client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
            headers=auth_headers
        )
        
        assert logout_response.status_code == 200
        
        # Step 4: Try to refresh token (should fail)
        refresh_response = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert refresh_response.status_code in [401, 403]
    
    async def test_password_change_flow(
        self,
        async_client: AsyncClient,
        test_user: User
    ):
        """Test password change flow."""
        # Step 1: Login with current password
        login_data = {
            "email": test_user.email,
            "password": "testpassword123",
            "remember_me": False
        }
        
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json=login_data
        )
        
        assert login_response.status_code == 200
        login_result = login_response.json()
        auth_headers = {
            "Authorization": f"Bearer {login_result['access_token']}"
        }
        
        # Step 2: Change password
        change_password_data = {
            "current_password": "testpassword123",
            "new_password": "newpassword456"
        }
        
        change_response = await async_client.post(
            "/api/v1/auth/change-password",
            json=change_password_data,
            headers=auth_headers
        )
        
        assert change_response.status_code == 200
        
        # Step 3: Try login with old password (should fail)
        old_login_response = await async_client.post(
            "/api/v1/auth/login",
            json=login_data
        )
        
        assert old_login_response.status_code == 401
        
        # Step 4: Login with new password (should work)
        new_login_data = {
            "email": test_user.email,
            "password": "newpassword456",
            "remember_me": False
        }
        
        new_login_response = await async_client.post(
            "/api/v1/auth/login",
            json=new_login_data
        )
        
        assert new_login_response.status_code == 200
    
    async def test_organization_creation_after_registration(
        self,
        async_client: AsyncClient,
        async_session: AsyncSession
    ):
        """Test creating organization after user registration."""
        # Step 1: Register user
        registration_data = {
            "email": "orgcreator@example.com",
            "password": "securepassword123",
            "full_name": "Organization Creator"
        }
        
        register_response = await async_client.post(
            "/api/v1/auth/register",
            json=registration_data
        )
        
        assert register_response.status_code == 200
        register_result = register_response.json()
        
        # Step 2: Create organization with new user
        auth_headers = {
            "Authorization": f"Bearer {register_result['access_token']}"
        }
        
        org_data = {
            "name": "Integration Test Organization",
            "description": "Created during integration test"
        }
        
        # Get CSRF token if required
        csrf_response = await async_client.get(
            "/api/v1/auth/csrf-token",
            headers=auth_headers
        )
        
        if csrf_response.status_code == 200:
            csrf_token = csrf_response.json().get("csrf_token")
            if csrf_token:
                auth_headers["X-CSRFToken"] = csrf_token
        
        org_response = await async_client.post(
            "/api/v1/organizations/",
            json=org_data,
            headers=auth_headers
        )
        
        assert org_response.status_code == 200
        org_result = org_response.json()
        assert org_result["name"] == org_data["name"]
        
        # Step 3: Verify user can access their organization
        orgs_response = await async_client.get(
            "/api/v1/organizations/",
            headers=auth_headers
        )
        
        assert orgs_response.status_code == 200
        orgs_data = orgs_response.json()
        assert len(orgs_data) >= 1
        
        found_org = any(org["id"] == org_result["id"] for org in orgs_data)
        assert found_org, "Created organization should be accessible to user"
    
    async def test_multi_device_login_logout(
        self,
        async_client: AsyncClient,
        test_user: User
    ):
        """Test multi-device login and logout scenarios."""
        login_data = {
            "email": test_user.email,
            "password": "testpassword123",
            "remember_me": False
        }
        
        # Step 1: Login from first device
        login_response_1 = await async_client.post(
            "/api/v1/auth/login",
            json=login_data,
            headers={"User-Agent": "Device-1"}
        )
        
        assert login_response_1.status_code == 200
        device_1_tokens = login_response_1.json()
        
        # Step 2: Login from second device
        login_response_2 = await async_client.post(
            "/api/v1/auth/login",
            json=login_data,
            headers={"User-Agent": "Device-2"}
        )
        
        assert login_response_2.status_code == 200
        device_2_tokens = login_response_2.json()
        
        # Step 3: Both devices should work
        auth_headers_1 = {
            "Authorization": f"Bearer {device_1_tokens['access_token']}"
        }
        auth_headers_2 = {
            "Authorization": f"Bearer {device_2_tokens['access_token']}"
        }
        
        profile_response_1 = await async_client.get(
            "/api/v1/auth/me",
            headers=auth_headers_1
        )
        profile_response_2 = await async_client.get(
            "/api/v1/auth/me",
            headers=auth_headers_2
        )
        
        assert profile_response_1.status_code == 200
        assert profile_response_2.status_code == 200
        
        # Step 4: Logout all devices
        logout_all_response = await async_client.post(
            "/api/v1/auth/logout-all",
            headers=auth_headers_1
        )
        
        assert logout_all_response.status_code == 200
        
        # Step 5: Both refresh tokens should be invalid
        refresh_response_1 = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": device_1_tokens["refresh_token"]}
        )
        refresh_response_2 = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": device_2_tokens["refresh_token"]}
        )
        
        assert refresh_response_1.status_code in [401, 403]
        assert refresh_response_2.status_code in [401, 403]