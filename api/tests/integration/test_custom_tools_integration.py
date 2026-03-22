"""
Integration tests for Custom Tools CRUD operations.

Tests the complete lifecycle of custom tools: create, list, get, update, delete.
"""

import uuid

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# Sample OpenAPI schema for testing
SAMPLE_OPENAPI_SCHEMA = {
    "openapi": "3.0.0",
    "info": {
        "title": "Test API",
        "version": "1.0.0",
        "description": "A test API for integration testing",
    },
    "servers": [{"url": "https://api.example.com"}],
    "paths": {
        "/users": {
            "get": {
                "operationId": "listUsers",
                "summary": "List all users",
                "description": "Returns a list of users",
                "responses": {"200": {"description": "Success"}},
            },
            "post": {
                "operationId": "createUser",
                "summary": "Create a user",
                "description": "Creates a new user",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {"name": {"type": "string"}, "email": {"type": "string"}},
                            }
                        }
                    }
                },
                "responses": {"201": {"description": "Created"}},
            },
        },
        "/users/{userId}": {
            "get": {
                "operationId": "getUser",
                "summary": "Get a user",
                "parameters": [{"name": "userId", "in": "path", "required": True, "schema": {"type": "string"}}],
                "responses": {"200": {"description": "Success"}},
            }
        },
    },
}


@pytest.fixture
def auth_headers(client: TestClient, db_session: Session):
    """Create authenticated user and return headers with tenant info."""
    from src.models import Account, AccountStatus

    # Create user and get token
    email = f"test_custom_tools_{uuid.uuid4()}@example.com"
    password = "SecureTestPass123!"

    # Register
    response = client.post(
        "/console/api/auth/register",
        json={
            "email": email,
            "password": password,
            "name": "Custom Tools Test User",
            "tenant_name": "Custom Tools Test Org",
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    tenant_id = data["data"]["tenant"]["id"]
    account_id = data["data"]["account"]["id"]

    # Manually activate account for testing (simulating email verification)
    account = db_session.query(Account).filter_by(email=email).first()
    account.status = AccountStatus.ACTIVE
    db_session.commit()

    # Login to get token
    login_response = client.post(
        "/console/api/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == status.HTTP_200_OK
    token = login_response.json()["data"]["access_token"]

    return {"Authorization": f"Bearer {token}"}, tenant_id, account_id


class TestCustomToolsCRUDIntegration:
    """Test Custom Tools CRUD operations."""

    def test_custom_tool_full_lifecycle(self, client: TestClient, db_session: Session, auth_headers):
        """Test complete custom tool lifecycle: create -> get -> update -> delete."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account_id = auth_headers
        tool_name = f"TestTool_{uuid.uuid4().hex[:8]}"

        # 1. Create Custom Tool
        create_response = client.post(
            "/api/v1/custom-tools",
            json={
                "name": tool_name,
                "description": "Test custom tool for integration tests",
                "openapi_schema": SAMPLE_OPENAPI_SCHEMA,
                "auth_type": "none",
                "enabled": True,
                "tags": ["test", "integration"],
            },
            headers=headers,
        )

        assert create_response.status_code == status.HTTP_201_CREATED
        create_data = create_response.json()
        assert create_data["name"] == tool_name
        assert create_data["enabled"] is True
        assert create_data["operation_count"] == 3  # listUsers, createUser, getUser
        tool_id = create_data["id"]

        # 2. Get Custom Tool
        get_response = client.get(f"/api/v1/custom-tools/{tool_id}", headers=headers)
        assert get_response.status_code == status.HTTP_200_OK
        get_data = get_response.json()
        assert get_data["name"] == tool_name
        assert "openapi_schema" in get_data
        assert "operations" in get_data
        assert len(get_data["operations"]) == 3

        # 3. List Custom Tools
        list_response = client.get("/api/v1/custom-tools", headers=headers)
        assert list_response.status_code == status.HTTP_200_OK
        list_data = list_response.json()
        assert isinstance(list_data, list)
        tool_ids = [t["id"] for t in list_data]
        assert tool_id in tool_ids

        # 4. Update Custom Tool
        update_response = client.put(
            f"/api/v1/custom-tools/{tool_id}",
            json={
                "name": f"{tool_name}_updated",
                "description": "Updated description",
                "enabled": False,
            },
            headers=headers,
        )
        assert update_response.status_code == status.HTTP_200_OK
        update_data = update_response.json()
        assert update_data["name"] == f"{tool_name}_updated"
        assert update_data["enabled"] is False

        # 5. List Operations
        ops_response = client.get(f"/api/v1/custom-tools/{tool_id}/operations", headers=headers)
        assert ops_response.status_code == status.HTTP_200_OK
        ops_data = ops_response.json()
        assert len(ops_data) == 3
        operation_ids = [op["operation_id"] for op in ops_data]
        assert "listUsers" in operation_ids
        assert "createUser" in operation_ids
        assert "getUser" in operation_ids

        # 6. Delete Custom Tool
        delete_response = client.delete(f"/api/v1/custom-tools/{tool_id}", headers=headers)
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT

        # Verify deletion
        verify_response = client.get(f"/api/v1/custom-tools/{tool_id}", headers=headers)
        assert verify_response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_duplicate_tool_name(self, client: TestClient, db_session: Session, auth_headers):
        """Test that creating a tool with duplicate name fails."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account_id = auth_headers
        tool_name = f"DuplicateTool_{uuid.uuid4().hex[:8]}"

        # Create first tool
        first_response = client.post(
            "/api/v1/custom-tools",
            json={
                "name": tool_name,
                "description": "First tool",
                "openapi_schema": SAMPLE_OPENAPI_SCHEMA,
                "auth_type": "none",
            },
            headers=headers,
        )
        assert first_response.status_code == status.HTTP_201_CREATED

        # Try to create second tool with same name
        second_response = client.post(
            "/api/v1/custom-tools",
            json={
                "name": tool_name,
                "description": "Second tool",
                "openapi_schema": SAMPLE_OPENAPI_SCHEMA,
                "auth_type": "none",
            },
            headers=headers,
        )
        assert second_response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in second_response.json()["detail"]

    def test_create_tool_with_minimal_schema(self, client: TestClient, db_session: Session, auth_headers):
        """Test creating a tool with minimal schema (no paths/operations).

        The OpenAPI parser is lenient and accepts any dict, but tools with
        no valid paths will have 0 operations.
        """
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account_id = auth_headers
        tool_name = f"MinimalSchemaTool_{uuid.uuid4().hex[:8]}"

        # The API accepts minimal schemas but creates tools with 0 operations
        response = client.post(
            "/api/v1/custom-tools",
            json={
                "name": tool_name,
                "description": "Tool with minimal schema",
                "openapi_schema": {"openapi": "3.0.0", "info": {"title": "Empty API", "version": "1.0.0"}},
                "auth_type": "none",
            },
            headers=headers,
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        # Schema is accepted but has no operations since there are no paths
        assert data["operation_count"] == 0

    def test_get_nonexistent_tool(self, client: TestClient, db_session: Session, auth_headers):
        """Test that getting a nonexistent tool returns 404."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account_id = auth_headers
        fake_id = str(uuid.uuid4())

        response = client.get(f"/api/v1/custom-tools/{fake_id}", headers=headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_list_enabled_tools_only(self, client: TestClient, db_session: Session, auth_headers):
        """Test listing only enabled tools."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account_id = auth_headers

        # Create an enabled tool
        enabled_name = f"EnabledTool_{uuid.uuid4().hex[:8]}"
        client.post(
            "/api/v1/custom-tools",
            json={
                "name": enabled_name,
                "description": "Enabled tool",
                "openapi_schema": SAMPLE_OPENAPI_SCHEMA,
                "auth_type": "none",
                "enabled": True,
            },
            headers=headers,
        )

        # Create a disabled tool
        disabled_name = f"DisabledTool_{uuid.uuid4().hex[:8]}"
        client.post(
            "/api/v1/custom-tools",
            json={
                "name": disabled_name,
                "description": "Disabled tool",
                "openapi_schema": SAMPLE_OPENAPI_SCHEMA,
                "auth_type": "none",
                "enabled": False,
            },
            headers=headers,
        )

        # List enabled only
        response = client.get("/api/v1/custom-tools?enabled_only=true", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        tool_names = [t["name"] for t in data]
        assert enabled_name in tool_names
        assert disabled_name not in tool_names

    def test_create_tool_with_auth_config(self, client: TestClient, db_session: Session, auth_headers):
        """Test creating a tool with authentication config."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account_id = auth_headers
        tool_name = f"AuthTool_{uuid.uuid4().hex[:8]}"

        # Create tool with bearer auth
        response = client.post(
            "/api/v1/custom-tools",
            json={
                "name": tool_name,
                "description": "Tool with auth",
                "openapi_schema": SAMPLE_OPENAPI_SCHEMA,
                "auth_type": "bearer",
                "auth_config": {"token": "test-bearer-token-12345"},
                "enabled": True,
            },
            headers=headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["auth_type"] == "bearer"

    def test_update_tool_schema(self, client: TestClient, db_session: Session, auth_headers):
        """Test updating a tool's OpenAPI schema."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account_id = auth_headers
        tool_name = f"UpdateSchemaTool_{uuid.uuid4().hex[:8]}"

        # Create tool
        create_response = client.post(
            "/api/v1/custom-tools",
            json={
                "name": tool_name,
                "description": "Tool to update schema",
                "openapi_schema": SAMPLE_OPENAPI_SCHEMA,
                "auth_type": "none",
            },
            headers=headers,
        )
        tool_id = create_response.json()["id"]
        assert create_response.json()["operation_count"] == 3

        # Update with a simpler schema
        simple_schema = {
            "openapi": "3.0.0",
            "info": {"title": "Simple API", "version": "1.0.0"},
            "servers": [{"url": "https://api.example.com"}],
            "paths": {
                "/status": {
                    "get": {
                        "operationId": "getStatus",
                        "summary": "Get status",
                        "responses": {"200": {"description": "Success"}},
                    }
                }
            },
        }

        update_response = client.put(
            f"/api/v1/custom-tools/{tool_id}",
            json={"openapi_schema": simple_schema},
            headers=headers,
        )
        assert update_response.status_code == status.HTTP_200_OK
        assert update_response.json()["operation_count"] == 1


class TestCustomToolsTenantIsolation:
    """Test Custom Tools tenant isolation."""

    def test_cannot_access_other_tenant_tool(self, client: TestClient, db_session: Session):
        """Test that users cannot access tools from other tenants."""
        from src.core.database import get_db
        from src.models import Account, AccountStatus

        client.app.dependency_overrides[get_db] = lambda: db_session

        # Create first user/tenant
        email1 = f"tenant1_tool_{uuid.uuid4()}@example.com"
        client.post(
            "/console/api/auth/register",
            json={
                "email": email1,
                "password": "SecureTestPass123!",
                "name": "Tenant 1 User",
                "tenant_name": "Tenant 1 Org",
            },
        )
        account1 = db_session.query(Account).filter_by(email=email1).first()
        account1.status = AccountStatus.ACTIVE
        db_session.commit()

        login1 = client.post("/console/api/auth/login", json={"email": email1, "password": "SecureTestPass123!"})
        token1 = login1.json()["data"]["access_token"]
        headers1 = {"Authorization": f"Bearer {token1}"}

        # Create second user/tenant
        email2 = f"tenant2_tool_{uuid.uuid4()}@example.com"
        client.post(
            "/console/api/auth/register",
            json={
                "email": email2,
                "password": "SecureTestPass123!",
                "name": "Tenant 2 User",
                "tenant_name": "Tenant 2 Org",
            },
        )
        account2 = db_session.query(Account).filter_by(email=email2).first()
        account2.status = AccountStatus.ACTIVE
        db_session.commit()

        login2 = client.post("/console/api/auth/login", json={"email": email2, "password": "SecureTestPass123!"})
        token2 = login2.json()["data"]["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}

        # Create tool as tenant 1
        tool_name = f"IsolatedTool_{uuid.uuid4().hex[:8]}"
        create_response = client.post(
            "/api/v1/custom-tools",
            json={
                "name": tool_name,
                "description": "Tenant 1 tool",
                "openapi_schema": SAMPLE_OPENAPI_SCHEMA,
                "auth_type": "none",
            },
            headers=headers1,
        )
        tool_id = create_response.json()["id"]

        # Tenant 2 should not be able to access tenant 1's tool
        get_response = client.get(f"/api/v1/custom-tools/{tool_id}", headers=headers2)
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

        # Tenant 2 should not be able to update tenant 1's tool
        update_response = client.put(f"/api/v1/custom-tools/{tool_id}", json={"name": "Hacked Tool"}, headers=headers2)
        assert update_response.status_code == status.HTTP_404_NOT_FOUND

        # Tenant 2 should not be able to delete tenant 1's tool
        delete_response = client.delete(f"/api/v1/custom-tools/{tool_id}", headers=headers2)
        assert delete_response.status_code == status.HTTP_404_NOT_FOUND
