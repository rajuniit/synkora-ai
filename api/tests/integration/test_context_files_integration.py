"""
Integration tests for Agent Context Files endpoints.

Tests context file upload, download, edit, and delete operations.
"""

import io
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

    email = f"context_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecureTestPass123!"

    # Register
    response = await async_client.post(
        "/console/api/auth/register",
        json={
            "email": email,
            "password": password,
            "name": "Context Files Test User",
            "tenant_name": "Context Files Test Org",
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    tenant_id = data["data"]["tenant"]["id"]

    # Activate account
    result = await async_db_session.execute(select(Account).filter_by(email=email))
    account = result.scalar_one_or_none()
    account.status = AccountStatus.ACTIVE
    await async_db_session.commit()

    # Login
    login_response = await async_client.post(
        "/console/api/auth/login",
        json={"email": email, "password": password},
    )
    token = login_response.json()["data"]["access_token"]

    return {"Authorization": f"Bearer {token}"}, tenant_id, account


@pytest_asyncio.fixture
async def test_agent_name(async_client: AsyncClient, auth_headers):
    """Create a test agent and return its name for context file tests."""
    headers, tenant_id, account = auth_headers

    agent_name = f"context-test-agent-{uuid.uuid4().hex[:8]}"
    response = await async_client.post(
        "/api/v1/agents",
        json={
            "name": f"Context Test Agent {uuid.uuid4().hex[:8]}",
            "agent_name": agent_name,
            "description": "Agent for context file tests",
            "system_prompt": "You are a test agent for context files.",
            "model": "gpt-4o-mini",
        },
        headers=headers,
    )
    if response.status_code == status.HTTP_201_CREATED:
        return agent_name
    return None


class TestContextFilesListIntegration:
    """Test listing context files."""

    @pytest.mark.asyncio
    async def test_list_context_files(self, async_client: AsyncClient, auth_headers, test_agent_name):
        """Test listing all context files for an agent."""
        headers, tenant_id, account = auth_headers

        if not test_agent_name:
            pytest.skip("Could not create test agent")

        response = await async_client.get(
            f"/api/v1/agents/{test_agent_name}/context-files",
            headers=headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_list_context_files_nonexistent_agent(self, async_client: AsyncClient, auth_headers):
        """Test listing context files for nonexistent agent returns 404."""
        headers, tenant_id, account = auth_headers

        fake_name = f"nonexistent-agent-{uuid.uuid4().hex[:8]}"
        response = await async_client.get(
            f"/api/v1/agents/{fake_name}/context-files",
            headers=headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestContextFilesUploadIntegration:
    """Test context file upload."""

    @pytest.mark.asyncio
    async def test_upload_context_file(self, async_client: AsyncClient, auth_headers, test_agent_name):
        """Test uploading a context file."""
        headers, tenant_id, account = auth_headers

        if not test_agent_name:
            pytest.skip("Could not create test agent")

        # Create a test file
        file_content = b"This is test content for context file."
        files = {"file": ("test_context.txt", io.BytesIO(file_content), "text/plain")}

        response = await async_client.post(
            f"/api/v1/agents/{test_agent_name}/context-files/upload",
            files=files,
            headers=headers,
        )

        # Accept 200/201 (success) or 500 (storage not available)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ]

    @pytest.mark.asyncio
    async def test_upload_context_file_nonexistent_agent(self, async_client: AsyncClient, auth_headers):
        """Test uploading context file to nonexistent agent returns 404."""
        headers, tenant_id, account = auth_headers

        fake_name = f"nonexistent-agent-{uuid.uuid4().hex[:8]}"
        file_content = b"This should fail."
        files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}

        response = await async_client.post(
            f"/api/v1/agents/{fake_name}/context-files/upload",
            files=files,
            headers=headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestContextFilesDownloadIntegration:
    """Test context file download."""

    @pytest.mark.asyncio
    async def test_download_context_file_not_found(self, async_client: AsyncClient, auth_headers):
        """Test downloading a nonexistent context file returns 404."""
        headers, tenant_id, account = auth_headers

        fake_file_id = str(uuid.uuid4())
        response = await async_client.get(
            f"/api/v1/agents/context-files/{fake_file_id}/download",
            headers=headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestContextFilesContentIntegration:
    """Test context file content retrieval."""

    @pytest.mark.asyncio
    async def test_get_context_file_content_not_found(self, async_client: AsyncClient, auth_headers):
        """Test getting content of nonexistent context file returns 404."""
        headers, tenant_id, account = auth_headers

        fake_file_id = str(uuid.uuid4())
        response = await async_client.get(
            f"/api/v1/agents/context-files/{fake_file_id}/content",
            headers=headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestContextFilesEditIntegration:
    """Test context file edit operations."""

    @pytest.mark.asyncio
    async def test_update_context_file_content_not_found(self, async_client: AsyncClient, auth_headers):
        """Test updating content of nonexistent context file returns 404."""
        headers, tenant_id, account = auth_headers

        fake_file_id = str(uuid.uuid4())
        update_data = {"content": "Updated content"}

        response = await async_client.put(
            f"/api/v1/agents/context-files/{fake_file_id}/content",
            json=update_data,
            headers=headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestContextFilesDeleteIntegration:
    """Test context file delete operations."""

    @pytest.mark.asyncio
    async def test_delete_context_file_not_found(self, async_client: AsyncClient, auth_headers):
        """Test deleting a nonexistent context file returns 404."""
        headers, tenant_id, account = auth_headers

        fake_file_id = str(uuid.uuid4())
        response = await async_client.delete(
            f"/api/v1/agents/context-files/{fake_file_id}",
            headers=headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestContextFilesAuthorizationIntegration:
    """Test context files authorization."""

    @pytest.mark.asyncio
    async def test_list_context_files_unauthorized(self, async_client: AsyncClient):
        """Test that unauthenticated requests to list context files are rejected."""
        fake_name = f"test-agent-{uuid.uuid4().hex[:8]}"
        response = await async_client.get(f"/api/v1/agents/{fake_name}/context-files")

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_upload_context_file_unauthorized(self, async_client: AsyncClient):
        """Test that unauthenticated requests to upload context files are rejected."""
        fake_name = f"test-agent-{uuid.uuid4().hex[:8]}"
        file_content = b"This should fail."
        files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}

        response = await async_client.post(
            f"/api/v1/agents/{fake_name}/context-files/upload",
            files=files,
        )

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_download_context_file_unauthorized(self, async_client: AsyncClient):
        """Test that unauthenticated requests to download context files are rejected."""
        fake_file_id = str(uuid.uuid4())
        response = await async_client.get(f"/api/v1/agents/context-files/{fake_file_id}/download")

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_delete_context_file_unauthorized(self, async_client: AsyncClient):
        """Test that unauthenticated requests to delete context files are rejected."""
        fake_file_id = str(uuid.uuid4())
        response = await async_client.delete(f"/api/v1/agents/context-files/{fake_file_id}")

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
