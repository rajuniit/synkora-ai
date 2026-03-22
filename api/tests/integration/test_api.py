"""
Integration tests for API endpoints.

Tests the FastAPI application and API routes.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class TestHealthEndpoint:
    """Test health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check(self, async_client: AsyncClient) -> None:
        """Test health check endpoint returns 200."""
        response = await async_client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestBlueprintEndpoints:
    """Test router index endpoints."""

    @pytest.mark.asyncio
    async def test_console_index(self, async_client: AsyncClient) -> None:
        """Test console API index."""
        response = await async_client.get("/console/api/")
        assert response.status_code == 200

        data = response.json()
        assert data["message"] == "Console API"
        assert "endpoints" in data

    @pytest.mark.asyncio
    async def test_service_api_index(self, async_client: AsyncClient) -> None:
        """Test service API index."""
        response = await async_client.get("/v1/")
        assert response.status_code == 200

        data = response.json()
        assert data["message"] == "Service API"

    @pytest.mark.asyncio
    async def test_web_api_index(self, async_client: AsyncClient) -> None:
        """Test web API index."""
        response = await async_client.get("/api/")
        assert response.status_code == 200

        data = response.json()
        assert data["message"] == "Synkora Web API"


class TestAuthEndpoints:
    """Test authentication endpoints."""

    @pytest.mark.asyncio
    async def test_register_success(self, async_client: AsyncClient) -> None:
        """Test successful user registration."""
        email = f"newuser_{uuid.uuid4().hex[:8]}@example.com"
        response = await async_client.post(
            "/console/api/auth/register",
            json={
                "email": email,
                "password": "SecureTestPass123!",
                "name": "New User",
                "tenant_name": "Test Company",
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert data["success"] is True
        # Registration returns INACTIVE account without tokens (requires email verification)
        assert data["data"]["account"]["email"] == email
        assert data["data"]["account"]["status"] == "INACTIVE"
        assert data["data"]["tenant"]["name"] == "Test Company"
        # Tokens are not returned until email is verified
        assert "access_token" not in data["data"]

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, async_client: AsyncClient) -> None:
        """Test registration with duplicate email fails."""
        dup_email = f"duplicate_{uuid.uuid4().hex[:8]}@example.com"
        # Register first user
        await async_client.post(
            "/console/api/auth/register",
            json={
                "email": dup_email,
                "password": "SecureTestPass123!",
                "name": "User One",
            },
        )

        # Try to register with same email
        response = await async_client.post(
            "/console/api/auth/register",
            json={
                "email": dup_email,
                "password": "SecureTestPass456!",
                "name": "User Two",
            },
        )

        assert response.status_code == 400
        data = response.json()
        assert "error" in data or "detail" in data

    @pytest.mark.asyncio
    async def test_login_success(self, async_client: AsyncClient, async_db_session: AsyncSession) -> None:
        """Test successful login."""
        from src.models import Account, AccountStatus

        email = f"logintest_{uuid.uuid4().hex[:8]}@example.com"
        password = "SecureTestPass123!"

        # Register user first
        await async_client.post(
            "/console/api/auth/register",
            json={
                "email": email,
                "password": password,
                "name": "Login Test",
            },
        )

        # Manually activate account for testing (simulating email verification)
        result = await async_db_session.execute(select(Account).filter_by(email=email))
        account = result.scalar_one()
        account.status = AccountStatus.ACTIVE
        await async_db_session.commit()

        # Login
        response = await async_client.post(
            "/console/api/auth/login",
            json={"email": email, "password": password},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]
        assert data["data"]["account"]["email"] == email

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, async_client: AsyncClient) -> None:
        """Test login with wrong password fails."""
        email = f"wrongpass_{uuid.uuid4().hex[:8]}@example.com"
        # Register user first
        await async_client.post(
            "/console/api/auth/register",
            json={
                "email": email,
                "password": "correctpassword",
                "name": "Wrong Pass Test",
            },
        )

        # Try to login with wrong password
        response = await async_client.post(
            "/console/api/auth/login",
            json={"email": email, "password": "WrongTestPass123!"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user(self, async_client: AsyncClient, async_db_session: AsyncSession) -> None:
        """Test getting current user info."""
        from src.models import Account, AccountStatus

        email = f"currentuser_{uuid.uuid4().hex[:8]}@example.com"
        password = "SecureTestPass123!"

        # Register user
        register_response = await async_client.post(
            "/console/api/auth/register",
            json={
                "email": email,
                "password": password,
                "name": "Current User",
            },
        )
        assert register_response.status_code == 201, f"Registration failed: {register_response.text}"

        # Manually activate account for testing (simulating email verification)
        result = await async_db_session.execute(select(Account).filter_by(email=email))
        account = result.scalar_one()
        account.status = AccountStatus.ACTIVE
        await async_db_session.commit()

        # Login to get token
        login_response = await async_client.post(
            "/console/api/auth/login",
            json={"email": email, "password": password},
        )
        assert login_response.status_code == 200
        token = login_response.json()["data"]["access_token"]

        # Get current user
        response = await async_client.get(
            "/console/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["data"]["account"]["email"] == email
        assert "tenants" in data["data"]

    @pytest.mark.asyncio
    async def test_get_current_user_without_auth(self, async_client: AsyncClient) -> None:
        """Test getting current user without authentication fails."""
        response = await async_client.get("/console/api/auth/me")

        assert response.status_code == 401


class TestErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_404_error(self, async_client: AsyncClient) -> None:
        """Test 404 error handling."""
        response = await async_client.get("/nonexistent")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_json(self, async_client: AsyncClient) -> None:
        """Test invalid JSON handling."""
        response = await async_client.post(
            "/console/api/auth/login",
            content="invalid json",  # Use content instead of data for string
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code in [400, 422, 500]

    @pytest.mark.asyncio
    async def test_missing_required_fields(self, async_client: AsyncClient) -> None:
        """Test missing required fields."""
        response = await async_client.post(
            "/console/api/auth/register",
            json={"email": "test@example.com"},  # Missing password and name
        )
        assert response.status_code in [400, 422]
