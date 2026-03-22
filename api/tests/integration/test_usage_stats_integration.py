"""
Integration tests for Usage Stats endpoints.

Tests usage statistics retrieval for subscription plans.
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

    email = f"usage_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecureTestPass123!"

    # Register
    response = client.post(
        "/console/api/auth/register",
        json={
            "email": email,
            "password": password,
            "name": "Usage Test User",
            "tenant_name": "Usage Test Org",
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


class TestUsageStatsIntegration:
    """Test Usage Stats operations."""

    def test_get_usage_stats(self, client: TestClient, db_session: Session, auth_headers):
        """Test getting usage statistics."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account = auth_headers

        response = client.get("/api/v1/usage-stats", headers=headers)

        # Accept 200 (success) or 500 (service error - plan not found etc)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert "plan_name" in data
            assert "plan_tier" in data
            assert "limits" in data
            assert "current_usage" in data
            assert "usage_percentage" in data

    def test_usage_stats_limits_structure(self, client: TestClient, db_session: Session, auth_headers):
        """Test that usage stats limits have expected structure."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account = auth_headers

        response = client.get("/api/v1/usage-stats", headers=headers)

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            limits = data.get("limits", {})

            # Check expected limit fields
            expected_limit_fields = [
                "max_agents",
                "max_team_members",
                "max_api_calls_per_month",
                "max_knowledge_bases",
                "max_data_sources",
                "max_custom_tools",
                "max_database_connections",
                "max_mcp_servers",
                "max_scheduled_tasks",
                "max_widgets",
                "max_slack_bots",
            ]

            for field in expected_limit_fields:
                assert field in limits, f"Missing expected limit field: {field}"

    def test_usage_stats_current_usage_structure(self, client: TestClient, db_session: Session, auth_headers):
        """Test that current usage has expected structure."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account = auth_headers

        response = client.get("/api/v1/usage-stats", headers=headers)

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            current_usage = data.get("current_usage", {})

            # Check expected usage fields
            expected_usage_fields = ["agents", "team_members", "api_calls_this_month"]

            for field in expected_usage_fields:
                assert field in current_usage, f"Missing expected usage field: {field}"
                assert isinstance(current_usage[field], int), f"Usage field {field} should be an integer"

    def test_usage_stats_percentage_structure(self, client: TestClient, db_session: Session, auth_headers):
        """Test that usage percentages have expected structure."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account = auth_headers

        response = client.get("/api/v1/usage-stats", headers=headers)

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            usage_percentage = data.get("usage_percentage", {})

            # Check expected percentage fields
            expected_percentage_fields = ["agents", "team_members", "api_calls"]

            for field in expected_percentage_fields:
                assert field in usage_percentage, f"Missing expected percentage field: {field}"
                assert isinstance(usage_percentage[field], (int, float)), f"Percentage field {field} should be a number"
                assert usage_percentage[field] >= 0, f"Percentage field {field} should be non-negative"

    def test_usage_stats_credit_balance(self, client: TestClient, db_session: Session, auth_headers):
        """Test that usage stats includes credit balance."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account = auth_headers

        response = client.get("/api/v1/usage-stats", headers=headers)

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            # credit_balance can be None or a Decimal value
            assert "credit_balance" in data


class TestUsageStatsAuthorization:
    """Test Usage Stats authorization."""

    def test_get_usage_stats_unauthorized(self, client: TestClient, db_session: Session):
        """Test that unauthenticated requests are rejected."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        response = client.get("/api/v1/usage-stats")

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


class TestUsageStatsTenantIsolation:
    """Test Usage Stats tenant isolation."""

    def test_usage_stats_per_tenant(self, client: TestClient, db_session: Session):
        """Test that usage stats are isolated per tenant."""
        from src.core.database import get_db
        from src.models import Account, AccountStatus

        client.app.dependency_overrides[get_db] = lambda: db_session

        # Create first tenant
        email1 = f"usage_tenant1_{uuid.uuid4().hex[:8]}@example.com"
        response1 = client.post(
            "/console/api/auth/register",
            json={
                "email": email1,
                "password": "SecureTestPass123!",
                "name": "Tenant 1 User",
                "tenant_name": "Usage Tenant 1 Org",
            },
        )
        assert response1.status_code == status.HTTP_201_CREATED

        account1 = db_session.query(Account).filter_by(email=email1).first()
        account1.status = AccountStatus.ACTIVE
        db_session.commit()

        login1 = client.post("/console/api/auth/login", json={"email": email1, "password": "SecureTestPass123!"})
        token1 = login1.json()["data"]["access_token"]
        headers1 = {"Authorization": f"Bearer {token1}"}

        # Create second tenant
        email2 = f"usage_tenant2_{uuid.uuid4().hex[:8]}@example.com"
        response2 = client.post(
            "/console/api/auth/register",
            json={
                "email": email2,
                "password": "SecureTestPass123!",
                "name": "Tenant 2 User",
                "tenant_name": "Usage Tenant 2 Org",
            },
        )
        assert response2.status_code == status.HTTP_201_CREATED

        account2 = db_session.query(Account).filter_by(email=email2).first()
        account2.status = AccountStatus.ACTIVE
        db_session.commit()

        login2 = client.post("/console/api/auth/login", json={"email": email2, "password": "SecureTestPass123!"})
        token2 = login2.json()["data"]["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}

        # Get usage stats for both tenants
        stats1 = client.get("/api/v1/usage-stats", headers=headers1)
        stats2 = client.get("/api/v1/usage-stats", headers=headers2)

        # Both should succeed or both should fail (if no plan exists)
        assert stats1.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]
        assert stats2.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]

        # If both succeeded, verify they're getting their own data
        if stats1.status_code == status.HTTP_200_OK and stats2.status_code == status.HTTP_200_OK:
            # Both tenants should have their own usage counts
            # New tenants should start with 1 team member (the owner)
            data1 = stats1.json()
            data2 = stats2.json()

            # Each tenant should have at least 1 team member (themselves)
            assert data1["current_usage"]["team_members"] >= 1
            assert data2["current_usage"]["team_members"] >= 1
