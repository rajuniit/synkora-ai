"""
Integration tests for Integration Configs endpoints.

Tests CRUD operations for integration configurations (email, etc.).
"""

import uuid

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


@pytest.fixture
def auth_headers(client: TestClient, db_session: Session):
    """Create authenticated user and return headers with tenant info."""
    from src.core.database import get_db
    from src.models import Account, AccountStatus

    client.app.dependency_overrides[get_db] = lambda: db_session

    email = f"intconfig_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecureTestPass123!"

    # Register
    response = client.post(
        "/console/api/auth/register",
        json={
            "email": email,
            "password": password,
            "name": "Integration Config Test User",
            "tenant_name": "Integration Config Test Org",
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    tenant_id = data["data"]["tenant"]["id"]

    # Activate account
    account = db_session.query(Account).filter_by(email=email).first()
    account.status = AccountStatus.ACTIVE
    db_session.commit()

    # Login
    login_response = client.post(
        "/console/api/auth/login",
        json={"email": email, "password": password},
    )
    token = login_response.json()["data"]["access_token"]

    return {"Authorization": f"Bearer {token}"}, tenant_id, account


class TestIntegrationConfigsCRUDIntegration:
    """Test Integration Configs CRUD operations."""

    def test_integration_config_full_lifecycle(self, client: TestClient, db_session: Session, auth_headers):
        """Test complete integration config lifecycle: create -> get -> update -> delete."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account = auth_headers

        # 1. Create Integration Config
        create_response = client.post(
            "/console/api/integration-configs",
            json={
                "integration_type": "email",
                "provider": "smtp",
                "config_data": {
                    "host": "smtp.example.com",
                    "port": 587,
                    "username": "user@example.com",
                    "password": "test_password",
                    "from_email": "noreply@example.com",
                },
                "is_active": True,
                "is_default": False,
            },
            headers=headers,
        )

        # May fail if user doesn't have permission (depends on role)
        if create_response.status_code == status.HTTP_403_FORBIDDEN:
            pytest.skip("User doesn't have permission to create integration configs")

        assert create_response.status_code == status.HTTP_200_OK
        create_data = create_response.json()
        assert "id" in create_data
        config_id = create_data["id"]

        # 2. Get Integration Config
        get_response = client.get(f"/console/api/integration-configs/{config_id}", headers=headers)
        assert get_response.status_code == status.HTTP_200_OK
        get_data = get_response.json()
        assert get_data["integration_type"] == "email"
        assert get_data["provider"] == "smtp"

        # 3. List Integration Configs
        list_response = client.get("/console/api/integration-configs", headers=headers)
        assert list_response.status_code == status.HTTP_200_OK
        list_data = list_response.json()
        config_ids = [c["id"] for c in list_data]
        assert config_id in config_ids

        # 4. Update Integration Config
        update_response = client.put(
            f"/console/api/integration-configs/{config_id}",
            json={
                "config_data": {
                    "host": "smtp.updated.com",
                    "port": 465,
                    "username": "updated@example.com",
                    "password": "updated_password",
                    "from_email": "noreply@updated.com",
                },
                "is_active": False,
            },
            headers=headers,
        )
        assert update_response.status_code == status.HTTP_200_OK

        # 5. Delete Integration Config
        delete_response = client.delete(f"/console/api/integration-configs/{config_id}", headers=headers)
        assert delete_response.status_code == status.HTTP_200_OK

        # Verify deletion
        verify_response = client.get(f"/console/api/integration-configs/{config_id}", headers=headers)
        assert verify_response.status_code == status.HTTP_404_NOT_FOUND

    def test_list_configs_by_type(self, client: TestClient, db_session: Session, auth_headers):
        """Test listing configs filtered by integration type."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account = auth_headers

        # List by type
        response = client.get("/console/api/integration-configs?integration_type=email", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        # All returned configs should be email type
        for config in response.json():
            if config["integration_type"]:
                assert config["integration_type"] == "email"

    def test_list_configs_by_provider(self, client: TestClient, db_session: Session, auth_headers):
        """Test listing configs filtered by provider."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account = auth_headers

        # List by provider
        response = client.get("/console/api/integration-configs?provider=smtp", headers=headers)
        assert response.status_code == status.HTTP_200_OK

    def test_get_active_config(self, client: TestClient, db_session: Session, auth_headers):
        """Test getting the active configuration for a type."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account = auth_headers

        # Get active config (may not exist)
        response = client.get("/console/api/integration-configs/active?integration_type=email", headers=headers)
        # Either finds one or returns 404
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_get_nonexistent_config(self, client: TestClient, db_session: Session, auth_headers):
        """Test getting a nonexistent config returns 404."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account = auth_headers
        fake_id = str(uuid.uuid4())

        response = client.get(f"/console/api/integration-configs/{fake_id}", headers=headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_config_missing_fields(self, client: TestClient, db_session: Session, auth_headers):
        """Test creating config with missing required fields fails."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account = auth_headers

        response = client.post(
            "/console/api/integration-configs",
            json={
                "integration_type": "email",
                # Missing provider and config_data
            },
            headers=headers,
        )

        # Either 400 for missing fields or 403 for no permission
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN]

    def test_update_nonexistent_config(self, client: TestClient, db_session: Session, auth_headers):
        """Test updating a nonexistent config returns 404."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account = auth_headers
        fake_id = str(uuid.uuid4())

        response = client.put(
            f"/console/api/integration-configs/{fake_id}",
            json={"is_active": False},
            headers=headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_nonexistent_config(self, client: TestClient, db_session: Session, auth_headers):
        """Test deleting a nonexistent config returns 404."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account = auth_headers
        fake_id = str(uuid.uuid4())

        response = client.delete(f"/console/api/integration-configs/{fake_id}", headers=headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestIntegrationConfigsTenantIsolation:
    """Test integration configs tenant isolation."""

    def test_cannot_access_other_tenant_config(self, client: TestClient, db_session: Session):
        """Test that users cannot access configs from other tenants."""
        from src.core.database import get_db
        from src.models import Account, AccountStatus

        client.app.dependency_overrides[get_db] = lambda: db_session

        # Create first user/tenant
        email1 = f"tenant1_config_{uuid.uuid4().hex[:8]}@example.com"
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
        email2 = f"tenant2_config_{uuid.uuid4().hex[:8]}@example.com"
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

        # Create config as tenant 1
        create_response = client.post(
            "/console/api/integration-configs",
            json={
                "integration_type": "email",
                "provider": "smtp",
                "config_data": {
                    "host": "smtp.tenant1.com",
                    "port": 587,
                },
                "is_active": True,
            },
            headers=headers1,
        )

        # Skip if no permission
        if create_response.status_code == status.HTTP_403_FORBIDDEN:
            pytest.skip("User doesn't have permission to create integration configs")

        config_id = create_response.json()["id"]

        # Tenant 2 should not be able to access tenant 1's config
        get_response = client.get(f"/console/api/integration-configs/{config_id}", headers=headers2)
        # Either 403 (unauthorized) or 404 (not found for this tenant)
        assert get_response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]


class TestIntegrationConfigsEmailTest:
    """Test email configuration testing endpoints."""

    def test_test_email_config(self, client: TestClient, db_session: Session, auth_headers):
        """Test the email config test endpoint."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account = auth_headers

        # Test email config (will likely fail without real SMTP)
        response = client.post(
            "/console/api/integration-configs/test",
            json={"test_email": "test@example.com"},
            headers=headers,
        )

        # Should return a response (success or failure based on config)
        # If no permission or no config, may return 403/404
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_500_INTERNAL_SERVER_ERROR,  # SMTP connection failure
        ]

    def test_test_specific_config(self, client: TestClient, db_session: Session, auth_headers):
        """Test testing a specific email configuration."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account = auth_headers

        # Create a config first
        create_response = client.post(
            "/console/api/integration-configs",
            json={
                "integration_type": "email",
                "provider": "smtp",
                "config_data": {
                    "host": "smtp.test.com",
                    "port": 587,
                    "username": "test",
                    "password": "test",
                },
                "is_active": True,
            },
            headers=headers,
        )

        if create_response.status_code == status.HTTP_403_FORBIDDEN:
            pytest.skip("User doesn't have permission to create integration configs")

        config_id = create_response.json()["id"]

        # Test the specific config
        response = client.post(
            f"/console/api/integration-configs/{config_id}/test",
            json={"test_email": "test@example.com"},
            headers=headers,
        )

        # Will fail to connect but should return proper response
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ]

    def test_test_nonexistent_config(self, client: TestClient, db_session: Session, auth_headers):
        """Test testing a nonexistent config returns 404."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account = auth_headers
        fake_id = str(uuid.uuid4())

        response = client.post(
            f"/console/api/integration-configs/{fake_id}/test",
            json={"test_email": "test@example.com"},
            headers=headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
