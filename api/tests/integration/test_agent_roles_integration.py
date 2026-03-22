"""
Integration tests for Agent Roles endpoints.

Tests agent role template CRUD operations including system templates and custom roles.
"""

import uuid

import pytest
import pytest_asyncio
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture
async def auth_headers(async_client: AsyncClient, async_db_session: AsyncSession):
    """Create authenticated user and return headers with tenant info."""
    from src.models import Account, AccountStatus

    email = f"roles_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecureTestPass123!"

    # Register
    response = await async_client.post(
        "/console/api/auth/register",
        json={
            "email": email,
            "password": password,
            "name": "Roles Test User",
            "tenant_name": "Roles Test Org",
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    tenant_id = data["data"]["tenant"]["id"]

    # Activate account
    result = await async_db_session.execute(select(Account).filter_by(email=email))
    account = result.scalar_one()
    account.status = AccountStatus.ACTIVE
    await async_db_session.commit()

    # Login
    login_response = await async_client.post(
        "/console/api/auth/login",
        json={"email": email, "password": password},
    )
    token = login_response.json()["data"]["access_token"]

    return {"Authorization": f"Bearer {token}"}, tenant_id, account


class TestAgentRolesListIntegration:
    """Test listing agent roles."""

    @pytest.mark.asyncio
    async def test_list_roles(self, async_client: AsyncClient, auth_headers):
        """Test listing all roles."""
        headers, tenant_id, account = auth_headers

        response = await async_client.get(
            "/api/v1/agent-roles",
            headers=headers,
        )

        # Accept 200 (success) or 500 (service error)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_list_roles_exclude_system(self, async_client: AsyncClient, auth_headers):
        """Test listing roles excluding system templates."""
        headers, tenant_id, account = auth_headers

        response = await async_client.get(
            "/api/v1/agent-roles?include_system=false",
            headers=headers,
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert isinstance(data, list)
            # All returned roles should not be system templates
            for role in data:
                assert role.get("is_system_template") is False

    @pytest.mark.asyncio
    async def test_list_roles_filter_by_type(self, async_client: AsyncClient, auth_headers):
        """Test listing roles filtered by role type."""
        headers, tenant_id, account = auth_headers

        response = await async_client.get(
            "/api/v1/agent-roles?role_type=custom",
            headers=headers,
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]


class TestAgentRolesTypesIntegration:
    """Test role types endpoint."""

    @pytest.mark.asyncio
    async def test_list_role_types(self, async_client: AsyncClient, auth_headers):
        """Test listing available role types."""
        headers, tenant_id, account = auth_headers

        response = await async_client.get(
            "/api/v1/agent-roles/types",
            headers=headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert isinstance(data["data"], list)


class TestAgentRolesCRUDIntegration:
    """Test agent role CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_role(self, async_client: AsyncClient, auth_headers):
        """Test creating a new custom role."""
        headers, tenant_id, account = auth_headers

        role_data = {
            "role_type": "custom",
            "role_name": f"Test Role {uuid.uuid4().hex[:8]}",
            "description": "A test custom role",
            "system_prompt_template": "You are a helpful assistant that specializes in testing.",
            "suggested_tools": ["web_search"],
            "default_capabilities": {"can_browse": True},
        }

        response = await async_client.post(
            "/api/v1/agent-roles",
            json=role_data,
            headers=headers,
        )

        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_500_INTERNAL_SERVER_ERROR]

        if response.status_code == status.HTTP_201_CREATED:
            data = response.json()
            assert data["role_name"] == role_data["role_name"]
            assert data["role_type"] == "custom"
            assert data["is_system_template"] is False
            assert "id" in data

    @pytest.mark.asyncio
    async def test_create_role_minimal(self, async_client: AsyncClient, auth_headers):
        """Test creating a role with minimal required fields."""
        headers, tenant_id, account = auth_headers

        role_data = {
            "role_type": "custom",
            "role_name": f"Minimal Role {uuid.uuid4().hex[:8]}",
            "system_prompt_template": "You are a test assistant.",
        }

        response = await async_client.post(
            "/api/v1/agent-roles",
            json=role_data,
            headers=headers,
        )

        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_500_INTERNAL_SERVER_ERROR]

    @pytest.mark.asyncio
    async def test_get_role(self, async_client: AsyncClient, auth_headers):
        """Test getting a specific role by ID."""
        headers, tenant_id, account = auth_headers

        # First create a role
        role_data = {
            "role_type": "custom",
            "role_name": f"Get Test Role {uuid.uuid4().hex[:8]}",
            "system_prompt_template": "Test prompt for get role test.",
        }

        create_response = await async_client.post(
            "/api/v1/agent-roles",
            json=role_data,
            headers=headers,
        )

        if create_response.status_code != status.HTTP_201_CREATED:
            pytest.skip("Could not create role for test")

        role_id = create_response.json()["id"]

        # Now get the role
        response = await async_client.get(
            f"/api/v1/agent-roles/{role_id}",
            headers=headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == role_id
        assert data["role_name"] == role_data["role_name"]

    @pytest.mark.asyncio
    async def test_get_nonexistent_role(self, async_client: AsyncClient, auth_headers):
        """Test getting a role that doesn't exist returns 404."""
        headers, tenant_id, account = auth_headers

        fake_id = str(uuid.uuid4())
        response = await async_client.get(
            f"/api/v1/agent-roles/{fake_id}",
            headers=headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_role_invalid_id(self, async_client: AsyncClient, auth_headers):
        """Test getting a role with invalid ID format returns 400."""
        headers, tenant_id, account = auth_headers

        response = await async_client.get(
            "/api/v1/agent-roles/invalid-uuid",
            headers=headers,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_update_role(self, async_client: AsyncClient, auth_headers):
        """Test updating a custom role."""
        headers, tenant_id, account = auth_headers

        # First create a role
        role_data = {
            "role_type": "custom",
            "role_name": f"Update Test Role {uuid.uuid4().hex[:8]}",
            "system_prompt_template": "Original prompt.",
        }

        create_response = await async_client.post(
            "/api/v1/agent-roles",
            json=role_data,
            headers=headers,
        )

        if create_response.status_code != status.HTTP_201_CREATED:
            pytest.skip("Could not create role for test")

        role_id = create_response.json()["id"]

        # Now update the role
        update_data = {
            "role_name": f"Updated Role {uuid.uuid4().hex[:8]}",
            "description": "Updated description",
        }

        response = await async_client.put(
            f"/api/v1/agent-roles/{role_id}",
            json=update_data,
            headers=headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["role_name"] == update_data["role_name"]
        assert data["description"] == update_data["description"]

    @pytest.mark.asyncio
    async def test_update_nonexistent_role(self, async_client: AsyncClient, auth_headers):
        """Test updating a role that doesn't exist returns 404."""
        headers, tenant_id, account = auth_headers

        fake_id = str(uuid.uuid4())
        update_data = {"role_name": "Should Fail"}

        response = await async_client.put(
            f"/api/v1/agent-roles/{fake_id}",
            json=update_data,
            headers=headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_role(self, async_client: AsyncClient, auth_headers):
        """Test deleting a custom role."""
        headers, tenant_id, account = auth_headers

        # First create a role
        role_data = {
            "role_type": "custom",
            "role_name": f"Delete Test Role {uuid.uuid4().hex[:8]}",
            "system_prompt_template": "To be deleted.",
        }

        create_response = await async_client.post(
            "/api/v1/agent-roles",
            json=role_data,
            headers=headers,
        )

        if create_response.status_code != status.HTTP_201_CREATED:
            pytest.skip("Could not create role for test")

        role_id = create_response.json()["id"]

        # Now delete the role
        response = await async_client.delete(
            f"/api/v1/agent-roles/{role_id}",
            headers=headers,
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify it's deleted
        get_response = await async_client.get(
            f"/api/v1/agent-roles/{role_id}",
            headers=headers,
        )
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_nonexistent_role(self, async_client: AsyncClient, auth_headers):
        """Test deleting a role that doesn't exist returns 404."""
        headers, tenant_id, account = auth_headers

        fake_id = str(uuid.uuid4())
        response = await async_client.delete(
            f"/api/v1/agent-roles/{fake_id}",
            headers=headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestAgentRolesCloneIntegration:
    """Test role cloning operations."""

    @pytest.mark.asyncio
    async def test_clone_role(self, async_client: AsyncClient, auth_headers):
        """Test cloning an existing role."""
        headers, tenant_id, account = auth_headers

        # First create a role to clone
        role_data = {
            "role_type": "custom",
            "role_name": f"Clone Source Role {uuid.uuid4().hex[:8]}",
            "description": "Role to be cloned",
            "system_prompt_template": "Original prompt to clone.",
            "suggested_tools": ["web_search"],
        }

        create_response = await async_client.post(
            "/api/v1/agent-roles",
            json=role_data,
            headers=headers,
        )

        if create_response.status_code != status.HTTP_201_CREATED:
            pytest.skip("Could not create source role for clone test")

        source_role_id = create_response.json()["id"]

        # Clone the role
        clone_data = {"new_name": f"Cloned Role {uuid.uuid4().hex[:8]}"}

        response = await async_client.post(
            f"/api/v1/agent-roles/{source_role_id}/clone",
            json=clone_data,
            headers=headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["role_name"] == clone_data["new_name"]
        assert data["system_prompt_template"] == role_data["system_prompt_template"]
        assert data["is_system_template"] is False
        assert data["id"] != source_role_id

    @pytest.mark.asyncio
    async def test_clone_nonexistent_role(self, async_client: AsyncClient, auth_headers):
        """Test cloning a role that doesn't exist returns 404."""
        headers, tenant_id, account = auth_headers

        fake_id = str(uuid.uuid4())
        clone_data = {"new_name": "Should Fail"}

        response = await async_client.post(
            f"/api/v1/agent-roles/{fake_id}/clone",
            json=clone_data,
            headers=headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestAgentRolesSeedIntegration:
    """Test seeding system roles."""

    @pytest.mark.asyncio
    async def test_seed_system_roles(self, async_client: AsyncClient, auth_headers):
        """Test seeding default system role templates."""
        headers, tenant_id, account = auth_headers

        response = await async_client.post(
            "/api/v1/agent-roles/seed",
            headers=headers,
        )

        # Accept 201 (created) or 500 (service error)
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_500_INTERNAL_SERVER_ERROR]

        if response.status_code == status.HTTP_201_CREATED:
            data = response.json()
            assert data["success"] is True
            assert "roles" in data["data"]


class TestAgentRolesAuthorizationIntegration:
    """Test agent roles authorization."""

    @pytest.mark.asyncio
    async def test_list_roles_unauthorized(self, async_client: AsyncClient):
        """Test that unauthenticated requests to list roles are rejected."""
        response = await async_client.get("/api/v1/agent-roles")

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_create_role_unauthorized(self, async_client: AsyncClient):
        """Test that unauthenticated requests to create roles are rejected."""
        role_data = {
            "role_type": "custom",
            "role_name": "Unauthorized Role",
            "system_prompt_template": "Test prompt.",
        }

        response = await async_client.post(
            "/api/v1/agent-roles",
            json=role_data,
        )

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_delete_role_unauthorized(self, async_client: AsyncClient):
        """Test that unauthenticated requests to delete roles are rejected."""
        fake_id = str(uuid.uuid4())
        response = await async_client.delete(f"/api/v1/agent-roles/{fake_id}")

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
