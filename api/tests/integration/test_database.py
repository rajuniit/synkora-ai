"""
Integration tests for database operations.

Tests database connectivity, transactions, and complex queries.
"""

import uuid

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models import Account, AccountRole, Tenant, TenantAccountJoin


class TestDatabaseConnectivity:
    """Test database connection and basic operations."""

    @pytest.mark.asyncio
    async def test_database_connection(self, async_db_session: AsyncSession) -> None:
        """Test that database connection is established."""
        assert async_db_session is not None
        assert async_db_session.is_active

    @pytest.mark.asyncio
    async def test_transaction_commit(self, async_db_session: AsyncSession) -> None:
        """Test that transactions can be committed."""
        tenant = Tenant(name="Transaction Test")
        async_db_session.add(tenant)
        await async_db_session.flush()

        # Verify it was saved
        result = await async_db_session.execute(select(Tenant).filter_by(name="Transaction Test"))
        saved_tenant = result.scalar_one_or_none()
        assert saved_tenant is not None
        assert saved_tenant.name == "Transaction Test"

    @pytest.mark.asyncio
    async def test_transaction_rollback(self, async_db_session: AsyncSession) -> None:
        """Test that transactions can be rolled back."""
        tenant = Tenant(name="Rollback Test")
        async_db_session.add(tenant)
        await async_db_session.flush()

        # Rollback before commit
        await async_db_session.rollback()

        # Verify it was not saved
        result = await async_db_session.execute(select(Tenant).filter_by(name="Rollback Test"))
        saved_tenant = result.scalar_one_or_none()
        assert saved_tenant is None


class TestTenantQueries:
    """Test complex queries for Tenant model."""

    @pytest.mark.asyncio
    async def test_query_all_tenants(self, async_db_session: AsyncSession) -> None:
        """Test querying all tenants."""
        # Create multiple tenants
        for i in range(3):
            tenant = Tenant(name=f"Company {i}")
            async_db_session.add(tenant)
        await async_db_session.flush()

        # Query all
        result = await async_db_session.execute(select(Tenant))
        tenants = result.scalars().all()
        assert len(tenants) >= 3

    @pytest.mark.asyncio
    async def test_query_tenant_by_status(self, async_db_session: AsyncSession) -> None:
        """Test filtering tenants by status."""
        active_tenant = Tenant(name="Active Company", status="active")
        suspended_tenant = Tenant(name="Suspended Company", status="suspended")
        async_db_session.add_all([active_tenant, suspended_tenant])
        await async_db_session.flush()

        # Query active tenants
        result = await async_db_session.execute(select(Tenant).filter_by(status="active"))
        active_tenants = result.scalars().all()
        assert len(active_tenants) >= 1
        assert all(t.status == "active" for t in active_tenants)

    @pytest.mark.asyncio
    async def test_query_tenant_with_members(
        self, async_db_session: AsyncSession, async_tenant: Tenant, async_account: Account, async_tenant_member: TenantAccountJoin
    ) -> None:
        """Test querying tenant with its members."""
        # Query tenant and load members
        result = await async_db_session.execute(select(Tenant).filter_by(id=async_tenant.id))
        queried_tenant = result.scalar_one_or_none()

        assert queried_tenant is not None
        # Use explicit query to avoid MissingGreenlet error with lazy-loaded relationships
        members_result = await async_db_session.execute(
            select(TenantAccountJoin)
            .options(selectinload(TenantAccountJoin.account))
            .filter_by(tenant_id=async_tenant.id)
        )
        members = members_result.scalars().all()
        assert len(members) >= 1
        assert members[0].account.email == async_account.email


class TestAccountQueries:
    """Test complex queries for Account model."""

    @pytest.mark.asyncio
    async def test_query_account_by_email(self, async_db_session: AsyncSession, async_account: Account) -> None:
        """Test querying account by email."""
        result = await async_db_session.execute(select(Account).filter_by(email=async_account.email))
        queried_account = result.scalar_one_or_none()

        assert queried_account is not None
        assert queried_account.id == async_account.id
        assert queried_account.email == async_account.email

    @pytest.mark.asyncio
    async def test_query_account_with_tenants(
        self, async_db_session: AsyncSession, async_account: Account, async_tenant: Tenant, async_tenant_member: TenantAccountJoin
    ) -> None:
        """Test querying account with its tenant memberships."""
        result = await async_db_session.execute(select(Account).filter_by(id=async_account.id))
        queried_account = result.scalar_one_or_none()

        assert queried_account is not None
        # Use explicit query to avoid MissingGreenlet error with lazy-loaded relationships
        memberships_result = await async_db_session.execute(
            select(TenantAccountJoin)
            .options(selectinload(TenantAccountJoin.tenant))
            .filter_by(account_id=async_account.id)
        )
        memberships = memberships_result.scalars().all()
        assert len(memberships) >= 1
        assert memberships[0].tenant.name == async_tenant.name


class TestTenantAccountRelationships:
    """Test tenant-account relationship operations."""

    @pytest.mark.asyncio
    async def test_add_multiple_members_to_tenant(self, async_db_session: AsyncSession, async_tenant: Tenant) -> None:
        """Test adding multiple members to a tenant."""
        # Create multiple accounts with unique emails
        accounts = []
        for i in range(3):
            account = Account(
                name=f"User {i}",
                email=f"user{i}_{uuid.uuid4().hex[:8]}@example.com",
            )
            async_db_session.add(account)
            accounts.append(account)
        await async_db_session.flush()

        # Add all as members
        for i, account in enumerate(accounts):
            role = AccountRole.OWNER if i == 0 else AccountRole.NORMAL
            membership = TenantAccountJoin(
                tenant_id=async_tenant.id,
                account_id=account.id,
                role=role,
            )
            async_db_session.add(membership)
        await async_db_session.flush()

        # Verify using explicit query to avoid MissingGreenlet error
        members_result = await async_db_session.execute(
            select(TenantAccountJoin).filter_by(tenant_id=async_tenant.id)
        )
        members = members_result.scalars().all()
        assert len(members) >= 3

    @pytest.mark.asyncio
    async def test_add_account_to_multiple_tenants(self, async_db_session: AsyncSession, async_account: Account) -> None:
        """Test adding an account to multiple tenants."""
        # Create multiple tenants
        tenants = []
        for i in range(3):
            tenant = Tenant(name=f"Company {i}")
            async_db_session.add(tenant)
            tenants.append(tenant)
        await async_db_session.flush()

        # Add account to all tenants
        for tenant in tenants:
            membership = TenantAccountJoin(
                tenant_id=tenant.id,
                account_id=async_account.id,
                role=AccountRole.NORMAL,
            )
            async_db_session.add(membership)
        await async_db_session.flush()

        # Verify using explicit query to avoid MissingGreenlet error
        memberships_result = await async_db_session.execute(
            select(TenantAccountJoin).filter_by(account_id=async_account.id)
        )
        memberships = memberships_result.scalars().all()
        assert len(memberships) >= 3

    @pytest.mark.asyncio
    async def test_query_members_by_role(self, async_db_session: AsyncSession, async_tenant: Tenant) -> None:
        """Test querying tenant members by role."""
        # Create accounts with different roles and unique emails
        owner = Account(name="Owner", email=f"owner_{uuid.uuid4().hex[:8]}@example.com")
        admin = Account(name="Admin", email=f"admin_{uuid.uuid4().hex[:8]}@example.com")
        editor = Account(name="Editor", email=f"editor_{uuid.uuid4().hex[:8]}@example.com")
        async_db_session.add_all([owner, admin, editor])
        await async_db_session.flush()

        # Add memberships
        async_db_session.add(TenantAccountJoin(tenant_id=async_tenant.id, account_id=owner.id, role=AccountRole.OWNER))
        async_db_session.add(TenantAccountJoin(tenant_id=async_tenant.id, account_id=admin.id, role=AccountRole.ADMIN))
        async_db_session.add(TenantAccountJoin(tenant_id=async_tenant.id, account_id=editor.id, role=AccountRole.EDITOR))
        await async_db_session.flush()

        # Query owners
        result = await async_db_session.execute(
            select(TenantAccountJoin).filter_by(tenant_id=async_tenant.id, role=AccountRole.OWNER)
        )
        owners = result.scalars().all()
        assert len(owners) >= 1


class TestDatabaseConstraints:
    """Test database constraints and validations."""

    @pytest.mark.asyncio
    async def test_not_null_constraint(self, async_db_session: AsyncSession) -> None:
        """Test that NOT NULL constraints are enforced."""
        # Try to create tenant without required name
        with pytest.raises(Exception):  # Will raise IntegrityError or similar
            tenant = Tenant()
            async_db_session.add(tenant)
            await async_db_session.flush()

    @pytest.mark.asyncio
    async def test_foreign_key_constraint(self, async_db_session: AsyncSession) -> None:
        """Test that foreign key constraints are enforced."""
        # Try to create membership with non-existent tenant
        with pytest.raises(Exception):  # Will raise IntegrityError
            membership = TenantAccountJoin(
                tenant_id=uuid.uuid4(),  # Non-existent
                account_id=uuid.uuid4(),  # Non-existent
                role=AccountRole.NORMAL,
            )
            async_db_session.add(membership)
            await async_db_session.flush()


class TestDatabasePerformance:
    """Test database performance and optimization."""

    @pytest.mark.asyncio
    async def test_bulk_insert(self, async_db_session: AsyncSession) -> None:
        """Test bulk insert performance."""
        # Create 100 tenants
        tenants = [Tenant(name=f"Bulk Company {i}") for i in range(100)]
        async_db_session.add_all(tenants)
        await async_db_session.flush()

        # Verify count
        result = await async_db_session.execute(
            select(func.count()).select_from(Tenant).filter(Tenant.name.like("Bulk Company%"))
        )
        count = result.scalar()
        assert count == 100

    @pytest.mark.asyncio
    async def test_query_with_limit(self, async_db_session: AsyncSession) -> None:
        """Test querying with limit."""
        # Create multiple tenants
        for i in range(20):
            tenant = Tenant(name=f"Limited Company {i}")
            async_db_session.add(tenant)
        await async_db_session.flush()

        # Query with limit
        result = await async_db_session.execute(select(Tenant).limit(10))
        tenants = result.scalars().all()
        assert len(tenants) == 10
