"""Permission management service."""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models import Permission, RolePermission, TenantAccountJoin

logger = logging.getLogger(__name__)


class PermissionService:
    """Service for managing permissions and role-based access control."""

    def __init__(self, db: AsyncSession):
        """Initialize the permission service.

        Args:
            db: Async database session
        """
        self.db = db

    async def check_permission(self, account_id: UUID, tenant_id: UUID, resource: str, action: str) -> bool:
        """Check if a user has permission to perform an action on a resource.

        Args:
            account_id: User account ID
            tenant_id: Tenant ID
            resource: Resource name (e.g., "agents", "team")
            action: Action name (e.g., "create", "read", "update", "delete")

        Returns:
            True if user has permission, False otherwise
        """
        permission_name = f"{resource}.{action}"
        logger.info(
            f"[PermissionService.check_permission] Checking {permission_name} for account_id={account_id}, tenant_id={tenant_id}"
        )

        # Get user's tenant membership
        stmt = select(TenantAccountJoin).where(
            TenantAccountJoin.tenant_id == tenant_id, TenantAccountJoin.account_id == account_id
        )
        result = await self.db.execute(stmt)
        membership = result.scalar_one_or_none()

        if not membership:
            logger.warning("[PermissionService.check_permission] No membership found")
            return False

        logger.info(f"[PermissionService.check_permission] Membership found: role_id={membership.role_id}")

        # Check custom permissions first (user-specific overrides)
        if membership.custom_permissions:
            custom_perms = membership.custom_permissions
            if permission_name in custom_perms:
                logger.info(
                    f"[PermissionService.check_permission] Custom permission found: {custom_perms[permission_name]}"
                )
                return custom_perms[permission_name]

        # Check role-based permissions - FIXED: Include NULL tenant_id for system roles
        if membership.role_id:
            stmt = (
                select(Permission)
                .join(RolePermission)
                .where(RolePermission.role_id == membership.role_id, Permission.name == permission_name)
                .where((RolePermission.tenant_id == tenant_id) | (RolePermission.tenant_id.is_(None)))
            )
            result = await self.db.execute(stmt)
            permission = result.scalar_one_or_none()

            has_perm = permission is not None
            logger.info(f"[PermissionService.check_permission] Role-based permission check result: {has_perm}")
            return has_perm

        logger.warning("[PermissionService.check_permission] No role_id found, returning False")
        return False

    async def get_user_permissions(self, account_id: UUID, tenant_id: UUID) -> list[str]:
        """Get all permissions for a user in a tenant.

        Args:
            account_id: User account ID
            tenant_id: Tenant ID

        Returns:
            List of permission names (e.g., ["agents.create", "agents.read"])
        """
        logger.info(f"[PermissionService] Getting permissions for account_id={account_id}, tenant_id={tenant_id}")

        # Get user's tenant membership
        stmt = select(TenantAccountJoin).where(
            TenantAccountJoin.tenant_id == tenant_id, TenantAccountJoin.account_id == account_id
        )
        result = await self.db.execute(stmt)
        membership = result.scalar_one_or_none()

        if not membership:
            logger.warning(
                f"[PermissionService] No membership found for account_id={account_id}, tenant_id={tenant_id}"
            )
            return []

        logger.info(
            f"[PermissionService] Membership found: role_id={membership.role_id}, role={getattr(membership, 'role', None)}"
        )

        # Get role-based permissions
        permissions = []
        if membership.role_id:
            logger.info(f"[PermissionService] Querying permissions for role_id={membership.role_id}")
            # Query for both tenant-specific and system-wide (NULL tenant_id) permissions
            stmt = (
                select(Permission.name)
                .join(RolePermission)
                .where(RolePermission.role_id == membership.role_id)
                .where((RolePermission.tenant_id == tenant_id) | (RolePermission.tenant_id.is_(None)))
            )
            result = await self.db.execute(stmt)
            permissions = [row[0] for row in result.all()]
            logger.info(f"[PermissionService] Found {len(permissions)} permissions from role_permissions table")
        else:
            logger.warning("[PermissionService] membership.role_id is None - checking if role enum exists")
            # Check if old role enum exists
            if hasattr(membership, "role") and membership.role:
                logger.info(f"[PermissionService] Found old role enum: {membership.role}")

        # Apply custom permission overrides
        if membership.custom_permissions:
            custom_perms = membership.custom_permissions
            logger.info(f"[PermissionService] Applying custom permissions: {custom_perms}")
            # Add granted custom permissions
            for perm, granted in custom_perms.items():
                if granted and perm not in permissions:
                    permissions.append(perm)
                # Remove revoked permissions
                elif not granted and perm in permissions:
                    permissions.remove(perm)

        logger.info(f"[PermissionService] Returning {len(permissions)} total permissions: {permissions}")
        return permissions

    async def grant_permission(self, account_id: UUID, tenant_id: UUID, permission_name: str) -> bool:
        """Grant a custom permission to a user.

        Args:
            account_id: User account ID
            tenant_id: Tenant ID
            permission_name: Permission name (e.g., "agents.create")

        Returns:
            True if permission was granted, False otherwise
        """
        stmt = select(TenantAccountJoin).where(
            TenantAccountJoin.tenant_id == tenant_id, TenantAccountJoin.account_id == account_id
        )
        result = await self.db.execute(stmt)
        membership = result.scalar_one_or_none()

        if not membership:
            return False

        # Update custom permissions
        custom_perms = membership.custom_permissions or {}
        custom_perms[permission_name] = True
        membership.custom_permissions = custom_perms

        await self.db.commit()
        return True

    async def revoke_permission(self, account_id: UUID, tenant_id: UUID, permission_name: str) -> bool:
        """Revoke a custom permission from a user.

        Args:
            account_id: User account ID
            tenant_id: Tenant ID
            permission_name: Permission name (e.g., "agents.create")

        Returns:
            True if permission was revoked, False otherwise
        """
        stmt = select(TenantAccountJoin).where(
            TenantAccountJoin.tenant_id == tenant_id, TenantAccountJoin.account_id == account_id
        )
        result = await self.db.execute(stmt)
        membership = result.scalar_one_or_none()

        if not membership:
            return False

        # Update custom permissions
        custom_perms = membership.custom_permissions or {}
        custom_perms[permission_name] = False
        membership.custom_permissions = custom_perms

        await self.db.commit()
        return True

    async def get_role_permissions(self, tenant_id: UUID, role_id: UUID) -> list[str]:
        """Get all permissions for a role in a tenant.

        Args:
            tenant_id: Tenant ID
            role_id: Role ID

        Returns:
            List of permission names
        """
        stmt = (
            select(Permission.name)
            .join(RolePermission)
            .where(RolePermission.tenant_id == tenant_id, RolePermission.role_id == role_id)
        )
        result = await self.db.execute(stmt)
        return [row[0] for row in result.all()]

    async def create_permission(
        self, name: str, description: str | None = None, is_platform_permission: bool = False
    ) -> Permission:
        """Create a new permission.

        Args:
            name: Permission name (format: resource.action)
            description: Permission description
            is_platform_permission: Whether this is a platform-wide permission

        Returns:
            Created permission
        """
        permission = Permission(name=name, description=description, is_platform_permission=is_platform_permission)
        self.db.add(permission)
        await self.db.commit()
        await self.db.refresh(permission)
        return permission

    async def assign_permission_to_role(self, tenant_id: UUID, role_id: UUID, permission_id: UUID) -> RolePermission:
        """Assign a permission to a role in a tenant.

        Args:
            tenant_id: Tenant ID
            role_id: Role ID
            permission_id: Permission ID

        Returns:
            Created role permission mapping
        """
        role_permission = RolePermission(tenant_id=tenant_id, role_id=role_id, permission_id=permission_id)
        self.db.add(role_permission)
        await self.db.commit()
        await self.db.refresh(role_permission)
        return role_permission

    async def remove_permission_from_role(self, tenant_id: UUID, role_id: UUID, permission_id: UUID) -> bool:
        """Remove a permission from a role in a tenant.

        Args:
            tenant_id: Tenant ID
            role_id: Role ID
            permission_id: Permission ID

        Returns:
            True if permission was removed, False otherwise
        """
        stmt = select(RolePermission).where(
            RolePermission.tenant_id == tenant_id,
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_id,
        )
        result = await self.db.execute(stmt)
        role_permission = result.scalar_one_or_none()

        if not role_permission:
            return False

        await self.db.delete(role_permission)
        await self.db.commit()
        return True

    async def get_all_permissions(self, is_platform_permission: bool | None = None) -> list[Permission]:
        """Get all permissions.

        Args:
            is_platform_permission: Filter by system permission flag (is_system field)

        Returns:
            List of permissions
        """
        stmt = select(Permission)
        if is_platform_permission is not None:
            stmt = stmt.where(Permission.is_system == is_platform_permission)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())
