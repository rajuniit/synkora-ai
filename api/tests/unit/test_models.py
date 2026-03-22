"""
Unit tests for database models.

Tests model creation, validation, relationships, and utility methods.
"""

import uuid
from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Account, AccountRole, AccountStatus, Tenant, TenantAccountJoin, TenantPlan, TenantStatus


class TestTenantModel:
    """Test cases for Tenant model."""

    @pytest.mark.asyncio
    async def test_create_tenant(self, async_db_session: AsyncSession) -> None:
        """Test creating a tenant with valid data."""
        tenant = Tenant(
            name="Test Company",
            plan=TenantPlan.FREE,
            status=TenantStatus.ACTIVE,
        )
        async_db_session.add(tenant)
        await async_db_session.flush()

        assert tenant.id is not None
        assert isinstance(tenant.id, uuid.UUID)
        assert tenant.name == "Test Company"
        assert tenant.plan == TenantPlan.FREE
        assert tenant.status == TenantStatus.ACTIVE
        assert isinstance(tenant.created_at, datetime)
        assert isinstance(tenant.updated_at, datetime)

    @pytest.mark.asyncio
    async def test_tenant_default_values(self, async_db_session: AsyncSession) -> None:
        """Test tenant default values."""
        tenant = Tenant(name="Test Company")
        async_db_session.add(tenant)
        await async_db_session.flush()

        assert tenant.plan == TenantPlan.FREE
        # The model default is likely TenantStatus.ACTIVE or "active" depending on implementation
        # Let's assume model default handles it, but if it defaults to enum, it should be enum
        # If default is string "EXTERNAL", we check that
        # Checking tenant.py: default=TenantPlan.FREE and default=TenantType.EXTERNAL
        # StatusMixin usually adds status default.
        # StatusMixin in src/models/base.py ?
        # Let's assume it sets a default status.
        # If StatusMixin sets default="ACTIVE" (string) or Enum, we will see.
        # Based on failures, it seems it might default to lowercase 'active' in some places if defined as string in Mixin?
        # But TenantStatus is Enum.
        # Let's check assertions in failures: assert 'ACTIVE' == 'active'
        # This implies the DB returned 'ACTIVE' (because it's Enum in DB) but test expected 'active'.
        # Or model has 'ACTIVE' and test expects 'active'.
        # Wait, the error was:
        # E   AssertionError: assert 'ACTIVE' == 'active'
        # E     - active
        # E     + ACTIVE
        # So test expected 'active', but got 'ACTIVE'.
        # So we should assert against TenantStatus.ACTIVE (which is 'ACTIVE')
        assert tenant.status == TenantStatus.ACTIVE

    def test_tenant_to_dict(self, tenant: Tenant) -> None:
        """Test converting tenant to dictionary."""
        data = tenant.to_dict()

        assert isinstance(data, dict)
        assert data["name"] == "Test Organization"
        assert data["plan"] == "FREE"
        assert data["status"] == "ACTIVE"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    @pytest.mark.asyncio
    async def test_tenant_update_from_dict(self, async_db_session: AsyncSession, tenant: Tenant) -> None:
        """Test updating tenant from dictionary."""
        tenant.update_from_dict({"name": "Updated Company", "plan": TenantPlan.PRO})
        await async_db_session.flush()

        assert tenant.name == "Updated Company"
        assert tenant.plan == TenantPlan.PRO

    def test_tenant_is_active(self, tenant: Tenant) -> None:
        """Test is_active property."""
        assert tenant.is_active is True

        tenant.status = TenantStatus.SUSPENDED
        assert tenant.is_active is False

    def test_tenant_repr(self, tenant: Tenant) -> None:
        """Test string representation."""
        repr_str = repr(tenant)
        assert "Tenant" in repr_str
        assert str(tenant.id) in repr_str
        assert tenant.name in repr_str


class TestAccountModel:
    """Test cases for Account model."""

    @pytest.mark.asyncio
    async def test_create_account(self, async_db_session: AsyncSession) -> None:
        """Test creating an account with valid data."""
        unique_email = f"john_{uuid.uuid4().hex[:8]}@example.com"
        account = Account(
            name="John Doe",
            email=unique_email,
            password_hash="hashed_password_123",
            interface_language="en-US",
            timezone="UTC",
        )
        async_db_session.add(account)
        await async_db_session.flush()

        assert account.id is not None
        assert account.name == "John Doe"
        assert account.email == unique_email
        assert account.password_hash == "hashed_password_123"
        assert account.interface_language == "en-US"
        assert account.timezone == "UTC"

    @pytest.mark.asyncio
    async def test_account_unique_email(self, async_db_session: AsyncSession, account: Account) -> None:
        """Test that email must be unique."""
        duplicate_account = Account(
            name="Another User",
            email=account.email,  # Same email
            password_hash="different_hash",
        )
        async_db_session.add(duplicate_account)

        with pytest.raises(IntegrityError):
            await async_db_session.flush()

    @pytest.mark.asyncio
    async def test_account_default_values(self, async_db_session: AsyncSession) -> None:
        """Test account default values."""
        account = Account(
            name="Test User",
            email=f"test_defaults_{uuid.uuid4().hex[:8]}@example.com",
        )
        async_db_session.add(account)
        await async_db_session.flush()

        assert account.interface_language == "en-US"
        assert account.timezone == "UTC"
        assert account.status == AccountStatus.ACTIVE

    def test_account_to_dict_excludes_password(self, account: Account) -> None:
        """Test that to_dict excludes password_hash."""
        data = account.to_dict()

        assert "password_hash" not in data
        assert "email" in data
        assert "name" in data

    def test_account_repr(self, account: Account) -> None:
        """Test string representation."""
        repr_str = repr(account)
        assert "Account" in repr_str
        assert account.email in repr_str


class TestTenantAccountJoin:
    """Test cases for TenantAccountJoin model."""

    @pytest.mark.asyncio
    async def test_create_membership(self, async_db_session: AsyncSession, tenant: Tenant, account: Account) -> None:
        """Test creating a tenant-account relationship."""
        membership = TenantAccountJoin(
            tenant_id=tenant.id,
            account_id=account.id,
            role=AccountRole.ADMIN,
        )
        async_db_session.add(membership)
        await async_db_session.flush()

        assert membership.id is not None
        assert membership.tenant_id == tenant.id
        assert membership.account_id == account.id
        assert membership.role == AccountRole.ADMIN

    @pytest.mark.asyncio
    async def test_membership_default_role(
        self, async_db_session: AsyncSession, tenant: Tenant, account: Account
    ) -> None:
        """Test default role is NORMAL."""
        membership = TenantAccountJoin(
            tenant_id=tenant.id,
            account_id=account.id,
        )
        async_db_session.add(membership)
        await async_db_session.flush()

        assert membership.role == AccountRole.NORMAL

    @pytest.mark.asyncio
    async def test_membership_unique_constraint(
        self, async_db_session: AsyncSession, tenant: Tenant, account: Account
    ) -> None:
        """Test that tenant-account combination must be unique."""
        membership1 = TenantAccountJoin(
            tenant_id=tenant.id,
            account_id=account.id,
            role=AccountRole.OWNER,
        )
        async_db_session.add(membership1)
        await async_db_session.flush()

        # Try to create duplicate
        membership2 = TenantAccountJoin(
            tenant_id=tenant.id,
            account_id=account.id,
            role=AccountRole.ADMIN,
        )
        async_db_session.add(membership2)

        with pytest.raises(IntegrityError):
            await async_db_session.flush()

    def test_membership_relationships(self, tenant_member: TenantAccountJoin) -> None:
        """Test relationships are properly loaded."""
        assert tenant_member.tenant is not None
        assert tenant_member.account is not None
        assert tenant_member.tenant.name == "Test Organization"
        assert tenant_member.account.email is not None
        assert "@example.com" in tenant_member.account.email

    def test_is_owner_property(self, tenant_member: TenantAccountJoin) -> None:
        """Test is_owner property."""
        assert tenant_member.is_owner is True

        tenant_member.role = AccountRole.ADMIN
        assert tenant_member.is_owner is False

    def test_is_admin_property(self, tenant_member: TenantAccountJoin) -> None:
        """Test is_admin property."""
        tenant_member.role = AccountRole.OWNER
        assert tenant_member.is_admin is True

        tenant_member.role = AccountRole.ADMIN
        assert tenant_member.is_admin is True

        tenant_member.role = AccountRole.EDITOR
        assert tenant_member.is_admin is False

    def test_can_edit_property(self, tenant_member: TenantAccountJoin) -> None:
        """Test can_edit property."""
        tenant_member.role = AccountRole.OWNER
        assert tenant_member.can_edit is True

        tenant_member.role = AccountRole.ADMIN
        assert tenant_member.can_edit is True

        tenant_member.role = AccountRole.EDITOR
        assert tenant_member.can_edit is True

        tenant_member.role = AccountRole.NORMAL
        assert tenant_member.can_edit is False

    @pytest.mark.asyncio
    async def test_cascade_delete_tenant(
        self, async_db_session: AsyncSession, tenant: Tenant, tenant_member: TenantAccountJoin
    ) -> None:
        """Test that deleting tenant cascades to memberships."""
        membership_id = tenant_member.id

        # Re-attach to async session since fixtures use sync db_session
        merged_tenant = await async_db_session.merge(tenant)
        await async_db_session.delete(merged_tenant)
        await async_db_session.flush()

        # Membership should be deleted
        deleted_membership = await async_db_session.get(TenantAccountJoin, membership_id)
        assert deleted_membership is None

    @pytest.mark.asyncio
    async def test_cascade_delete_account(
        self, async_db_session: AsyncSession, account: Account, tenant_member: TenantAccountJoin
    ) -> None:
        """Test that deleting account cascades to memberships."""
        membership_id = tenant_member.id

        # Re-attach to async session since fixtures use sync db_session
        merged_account = await async_db_session.merge(account)
        await async_db_session.delete(merged_account)
        await async_db_session.flush()

        # Membership should be deleted
        deleted_membership = await async_db_session.get(TenantAccountJoin, membership_id)
        assert deleted_membership is None


class TestBaseModelMixins:
    """Test cases for base model mixins."""

    @pytest.mark.asyncio
    async def test_soft_delete_mixin(self, async_db_session: AsyncSession) -> None:
        """Test soft delete functionality."""
        # Note: We'll need a model with SoftDeleteMixin for this test
        # For now, this is a placeholder
        pass

    def test_timestamp_mixin(self, tenant: Tenant) -> None:
        """Test timestamp fields are set correctly."""
        assert tenant.created_at is not None
        assert tenant.updated_at is not None
        assert isinstance(tenant.created_at, datetime)
        assert isinstance(tenant.updated_at, datetime)

    def test_uuid_mixin(self, tenant: Tenant) -> None:
        """Test UUID primary key is generated."""
        assert tenant.id is not None
        assert isinstance(tenant.id, uuid.UUID)
