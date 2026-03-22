"""
Account Linking Service.

Handles linking social auth providers to existing accounts and creating new accounts
from social login providers.
"""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models import (
    Account,
    AccountProvider,
    AccountRole,
    AccountStatus,
    Tenant,
    TenantAccountJoin,
    TenantPlan,
    TenantStatus,
)
from src.models.role import Role
from src.models.subscription_plan import PlanTier
from src.services.billing.subscription_service import SubscriptionService

logger = logging.getLogger(__name__)


class AccountLinkingService:
    """Service for linking social auth providers to accounts."""

    @staticmethod
    async def find_account_by_email(db: AsyncSession, email: str) -> Account | None:
        """
        Find an account by email address.

        Args:
            db: Database session
            email: Email address to search for

        Returns:
            Account if found, None otherwise
        """
        stmt = select(Account).filter_by(email=email)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def find_account_by_provider(
        db: AsyncSession,
        provider: str,
        provider_user_id: str,
    ) -> Account | None:
        """
        Find an account by social auth provider.

        Args:
            db: Database session
            provider: Provider name (google, microsoft, apple)
            provider_user_id: User ID from the provider

        Returns:
            Account if found, None otherwise
        """
        stmt = select(AccountProvider).filter_by(provider=provider, provider_user_id=provider_user_id)
        result = await db.execute(stmt)
        social_auth = result.scalar_one_or_none()

        if not social_auth:
            return None

        stmt = select(Account).filter_by(id=social_auth.account_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def link_provider_to_account(
        db: AsyncSession,
        account_id: uuid.UUID,
        provider: str,
        provider_user_id: str,
        provider_email: str,
        provider_data: dict,
    ) -> AccountProvider:
        """
        Link a social auth provider to an existing account.

        Args:
            db: Database session
            account_id: Account UUID to link to
            provider: Provider name (google, microsoft, apple)
            provider_user_id: User ID from the provider
            provider_email: Email from the provider
            provider_data: Additional data from the provider

        Returns:
            Created AccountProvider instance

        Raises:
            ValueError: If provider is already linked to another account
        """
        # Check if provider is already linked
        stmt = select(AccountProvider).filter_by(provider=provider, provider_user_id=provider_user_id)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            if existing.account_id != account_id:
                raise ValueError(f"{provider.capitalize()} account is already linked to another user")
            # Update existing link
            existing.provider_email = provider_email
            existing.provider_metadata = provider_data
            existing.last_used_at = datetime.now(UTC).isoformat()
            await db.commit()
            await db.refresh(existing)
            return existing

        # Create new link
        social_auth = AccountProvider(
            account_id=account_id,
            provider=provider,
            provider_user_id=provider_user_id,
            provider_email=provider_email,
            provider_metadata=provider_data,
            connected_at=datetime.now(UTC).isoformat(),
            last_used_at=datetime.now(UTC).isoformat(),
        )
        db.add(social_auth)
        await db.commit()
        await db.refresh(social_auth)

        return social_auth

    @staticmethod
    async def create_account_from_provider(
        db: AsyncSession,
        provider: str,
        provider_user_id: str,
        provider_email: str,
        provider_name: str,
        provider_data: dict,
        tenant_name: str | None = None,
    ) -> tuple[Account, Tenant, AccountProvider]:
        """
        Create a new account from social auth provider.

        Args:
            db: Database session
            provider: Provider name (google, microsoft, apple)
            provider_user_id: User ID from the provider
            provider_email: Email from the provider
            provider_name: Name from the provider
            provider_data: Additional data from the provider
            tenant_name: Optional tenant name

        Returns:
            Tuple of (Account, Tenant, AccountProvider)

        Raises:
            ValueError: If email already exists
        """
        # Check if email already exists
        stmt = select(Account).filter_by(email=provider_email)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            raise ValueError("Email already registered")

        # Create account (no password for social login)
        account = Account(
            name=provider_name,
            email=provider_email,
            password_hash=None,  # No password for social login
            status=AccountStatus.ACTIVE,
        )
        db.add(account)
        await db.flush()

        # Create tenant
        if not tenant_name:
            tenant_name = f"{provider_name}'s Workspace"

        tenant = Tenant(
            name=tenant_name,
            plan=TenantPlan.FREE,
            status=TenantStatus.ACTIVE,
        )
        db.add(tenant)
        await db.flush()

        # Add account as owner of tenant
        membership = TenantAccountJoin(
            tenant_id=tenant.id,
            account_id=account.id,
            role=AccountRole.OWNER,
        )
        db.add(membership)

        # Link social auth provider
        social_auth = AccountProvider(
            account_id=account.id,
            provider=provider,
            provider_user_id=provider_user_id,
            provider_email=provider_email,
            provider_metadata=provider_data,
            connected_at=datetime.now(UTC).isoformat(),
            last_used_at=datetime.now(UTC).isoformat(),
        )
        db.add(social_auth)

        await db.commit()
        await db.refresh(account)
        await db.refresh(tenant)
        await db.refresh(social_auth)

        # Create free subscription for the new tenant
        try:
            subscription_service = SubscriptionService(db)
            free_plan = await subscription_service.get_plan_by_tier(PlanTier.FREE)
            if free_plan:
                await subscription_service.create_subscription(tenant_id=tenant.id, plan_id=free_plan.id)
        except Exception as e:
            # Log error but don't fail registration if subscription creation fails
            logger.error(f"Failed to create free subscription for tenant {tenant.id}: {e}")

        # Auto-assign user to company tenant if domain matches
        email_domain = provider_email.split("@")[-1].lower() if "@" in provider_email else None
        if email_domain:
            try:
                # Find tenant with matching domain that has auto-assign enabled
                stmt = select(Tenant).filter(
                    Tenant.domain == email_domain,
                    Tenant.auto_assign_domain_users == "true",
                    Tenant.status == TenantStatus.ACTIVE,
                )
                result = await db.execute(stmt)
                company_tenant = result.scalar_one_or_none()

                if company_tenant and company_tenant.id != tenant.id:
                    logger.info(f"Found company tenant {company_tenant.name} for domain {email_domain}")

                    # Check if user is not already a member
                    stmt = select(TenantAccountJoin).filter_by(tenant_id=company_tenant.id, account_id=account.id)
                    result = await db.execute(stmt)
                    existing_membership = result.scalar_one_or_none()

                    if not existing_membership:
                        # Get member role for company tenant
                        stmt = select(Role).filter_by(name="Member", tenant_id=None, is_system=True)
                        result = await db.execute(stmt)
                        member_role = result.scalar_one_or_none()

                        if not member_role:
                            stmt = select(Role).filter_by(name="member", tenant_id=None, is_system=True)
                            result = await db.execute(stmt)
                            member_role = result.scalar_one_or_none()

                        # Add user as member of company tenant
                        company_membership = TenantAccountJoin(
                            tenant_id=company_tenant.id,
                            account_id=account.id,
                            role=AccountRole.NORMAL,
                            role_id=member_role.id if member_role else None,
                            joined_at=datetime.now(UTC).isoformat(),
                        )
                        db.add(company_membership)
                        await db.commit()
                        logger.info(f"Auto-assigned user {provider_email} to company tenant {company_tenant.name}")
            except Exception as e:
                logger.error(f"Error auto-assigning user to company tenant: {e}")
                # Don't fail registration if auto-assignment fails

        return account, tenant, social_auth

    @staticmethod
    async def update_last_login(
        db: AsyncSession,
        provider: str,
        provider_user_id: str,
    ) -> None:
        """
        Update the last login timestamp for a social auth provider.

        Args:
            db: Database session
            provider: Provider name
            provider_user_id: User ID from the provider
        """
        stmt = select(AccountProvider).filter_by(provider=provider, provider_user_id=provider_user_id)
        result = await db.execute(stmt)
        social_auth = result.scalar_one_or_none()

        if social_auth:
            social_auth.last_used_at = datetime.now(UTC).isoformat()
            await db.commit()

    @staticmethod
    async def unlink_provider(
        db: AsyncSession,
        account_id: uuid.UUID,
        provider: str,
    ) -> bool:
        """
        Unlink a social auth provider from an account.

        Args:
            db: Database session
            account_id: Account UUID
            provider: Provider name to unlink

        Returns:
            True if unlinked, False if not found

        Raises:
            ValueError: If this is the only auth method and account has no password
        """
        # Check if account has a password
        stmt = select(Account).filter_by(id=account_id)
        result = await db.execute(stmt)
        account = result.scalar_one_or_none()
        if not account:
            return False

        # Count linked providers
        stmt = select(func.count(AccountProvider.id)).filter_by(account_id=account_id)
        result = await db.execute(stmt)
        provider_count = result.scalar() or 0

        # Don't allow unlinking if it's the only auth method and no password
        if provider_count == 1 and not account.password_hash:
            raise ValueError("Cannot unlink the only authentication method. Please set a password first.")

        # Find and delete the provider link
        stmt = select(AccountProvider).filter_by(account_id=account_id, provider=provider)
        result = await db.execute(stmt)
        social_auth = result.scalar_one_or_none()

        if not social_auth:
            return False

        await db.delete(social_auth)
        await db.commit()

        return True

    @staticmethod
    async def get_linked_providers(
        db: AsyncSession,
        account_id: uuid.UUID,
    ) -> list[AccountProvider]:
        """
        Get all linked social auth providers for an account.

        Args:
            db: Database session
            account_id: Account UUID

        Returns:
            List of AccountProvider instances
        """
        stmt = select(AccountProvider).filter_by(account_id=account_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def link_or_create_account(
        db: AsyncSession,
        provider: str,
        provider_user_id: str,
        provider_email: str,
        provider_name: str,
        provider_data: dict,
    ) -> tuple[Account, Tenant, bool]:
        """
        Link provider to existing account or create new account.

        This is the main method for social login flow.

        SECURITY: This method now enforces strict email verification requirements:
        1. If provider is already linked, allow login
        2. If email exists but provider not linked, ONLY auto-link if:
           - The OAuth provider confirms the email is verified
           - The existing account was created via the same email (not password-based)
        3. For password-based accounts, require explicit linking via authenticated session

        Args:
            db: Database session
            provider: Provider name (google, microsoft, apple)
            provider_user_id: User ID from the provider
            provider_email: Email from the provider
            provider_name: Name from the provider
            provider_data: Additional data from the provider

        Returns:
            Tuple of (Account, Tenant, is_new_account)

        Raises:
            ValueError: If email exists but cannot be auto-linked (requires explicit linking)
        """
        # Check if provider is already linked
        account = await AccountLinkingService.find_account_by_provider(db, provider, provider_user_id)

        if account:
            # Update last login
            await AccountLinkingService.update_last_login(db, provider, provider_user_id)
            # Get primary tenant
            stmt = (
                select(TenantAccountJoin)
                .filter_by(account_id=account.id)
                .options(selectinload(TenantAccountJoin.tenant))
            )
            result = await db.execute(stmt)
            membership = result.scalar_one_or_none()
            tenant = membership.tenant if membership else None
            return account, tenant, False

        # Check if email exists
        existing_account = await AccountLinkingService.find_account_by_email(db, provider_email)

        if existing_account:
            # SECURITY: Check if we can safely auto-link this provider

            # Check if OAuth provider verified the email
            email_verified = provider_data.get("email_verified", False)
            if isinstance(email_verified, str):
                email_verified = email_verified.lower() == "true"

            # Check if existing account has a password (password-based account)
            has_password = existing_account.password_hash is not None

            # Check if existing account already has other OAuth providers linked
            stmt = select(AccountProvider).filter_by(account_id=existing_account.id)
            result = await db.execute(stmt)
            existing_providers = result.scalars().all()
            has_other_oauth = len(existing_providers) > 0

            # SECURITY: Only auto-link if ALL of these conditions are met:
            # 1. OAuth provider verified the email address
            # 2. Either:
            #    a) The account was created via OAuth (no password, has OAuth providers)
            #    b) The account has no password AND no other OAuth (was created via this flow before)
            can_auto_link = email_verified and (
                (not has_password and has_other_oauth)  # Pure OAuth account
                or (not has_password and not has_other_oauth)  # Orphan account (edge case)
            )

            if can_auto_link:
                logger.info(
                    f"Auto-linking {provider} to existing OAuth account {existing_account.id} "
                    f"(email_verified={email_verified}, has_password={has_password})"
                )
                # Link provider to existing OAuth-based account
                await AccountLinkingService.link_provider_to_account(
                    db,
                    existing_account.id,
                    provider,
                    provider_user_id,
                    provider_email,
                    provider_data,
                )
                # Get primary tenant
                stmt = (
                    select(TenantAccountJoin)
                    .filter_by(account_id=existing_account.id)
                    .options(selectinload(TenantAccountJoin.tenant))
                )
                result = await db.execute(stmt)
                membership = result.scalar_one_or_none()
                tenant = membership.tenant if membership else None
                return existing_account, tenant, False

            # SECURITY: For password-based accounts or unverified emails, reject auto-linking
            # User must sign in to their existing account and explicitly link the provider
            logger.warning(
                f"Rejecting auto-link of {provider} to account {existing_account.id}: "
                f"email_verified={email_verified}, has_password={has_password}"
            )
            raise ValueError(
                f"An account with email {provider_email} already exists. "
                f"Please sign in to your existing account first, then link your {provider.capitalize()} account "
                f"from the account settings."
            )

        # Create new account (email doesn't exist)
        account, tenant, _ = await AccountLinkingService.create_account_from_provider(
            db,
            provider,
            provider_user_id,
            provider_email,
            provider_name,
            provider_data,
        )

        return account, tenant, True
