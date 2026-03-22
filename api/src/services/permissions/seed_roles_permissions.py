"""
Seed script for default roles and permissions.
This script creates system roles and their associated permissions.
"""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.permission import Permission
from src.models.role import Role
from src.models.role_permission import RolePermission

logger = logging.getLogger(__name__)

# Define all resources in the system
RESOURCES = [
    "agents",
    "knowledge_bases",
    "data_sources",
    "mcp_servers",
    "custom_tools",
    "database_connections",
    "scheduled_tasks",
    "app_store_sources",
    "integration_configs",
    "billing",
    "teams",
    "profiles",
    "activity_logs",
    "oauth_apps",
    "widgets",
    "slack_bots",
    "charts",
    "conversations",
    "messages",
    "platform",  # Platform-level resource for platform owners
]

# Define all actions
ACTIONS = ["create", "read", "update", "delete", "manage"]

# Define role configurations
ROLE_CONFIGS = {
    "platform_owner": {
        "name": "Platform Owner",
        "description": "Platform administrator with full access to platform-wide configurations",
        "is_system": True,
        "is_default": False,
        "permissions": dict.fromkeys(RESOURCES, ACTIONS),
    },
    "owner": {
        "name": "Owner",
        "description": "Full access to tenant resources (cannot manage platform configs)",
        "is_system": True,
        "is_default": False,
        "permissions": {
            # Owner has all permissions on all resources EXCEPT platform
            resource: ACTIONS
            for resource in RESOURCES
            if resource != "platform"
        },
    },
    "admin": {
        "name": "Admin",
        "description": "Full access to all resources except tenant deletion",
        "is_system": True,
        "is_default": False,
        "permissions": {
            # Admin has all permissions except manage on teams and billing
            resource: ACTIONS if resource not in ["teams", "billing"] else ["create", "read", "update", "delete"]
            for resource in RESOURCES
        },
    },
    "editor": {
        "name": "Editor",
        "description": "Can create, read, and update most resources",
        "is_system": True,
        "is_default": True,  # Default role for new users
        "permissions": {
            # Editor can create, read, update but not delete or manage
            resource: ["create", "read", "update"]
            for resource in RESOURCES
            if resource not in ["teams", "billing", "integration_configs"]
        }
        | {
            # Read-only for sensitive resources
            "teams": ["read"],
            "billing": ["read"],
            "integration_configs": ["read"],
        },
    },
    "viewer": {
        "name": "Viewer",
        "description": "Read-only access to most resources",
        "is_system": True,
        "is_default": False,
        "permissions": {
            # Viewer has read-only access
            resource: ["read"]
            for resource in RESOURCES
            if resource not in ["billing", "integration_configs", "teams"]
        },
    },
}


async def create_permissions(db: AsyncSession) -> dict[str, Permission]:
    """Create all permissions for resources and actions."""
    permissions = {}

    for resource in RESOURCES:
        for action in ACTIONS:
            permission_key = f"{resource}:{action}"

            # Check if permission already exists
            result = await db.execute(
                select(Permission).filter(Permission.resource == resource, Permission.action == action)
            )
            existing = result.scalar_one_or_none()

            if existing:
                permissions[permission_key] = existing
                logger.debug(f"Permission already exists: {permission_key}")
            else:
                permission_name = f"{resource}.{action}"
                permission = Permission(
                    id=str(uuid.uuid4()),
                    name=permission_name,
                    resource=resource,
                    action=action,
                    description=f"{action.capitalize()} {resource.replace('_', ' ')}",
                )
                db.add(permission)
                permissions[permission_key] = permission
                logger.debug(f"Created permission: {permission_key}")

    await db.commit()
    return permissions


async def create_roles(db: AsyncSession, permissions: dict[str, Permission]) -> dict[str, Role]:
    """Create system roles and assign permissions."""
    roles = {}

    for role_key, config in ROLE_CONFIGS.items():
        # Check if role already exists
        result = await db.execute(select(Role).filter(Role.name == config["name"], Role.is_system))
        existing_role = result.scalar_one_or_none()

        if existing_role:
            role = existing_role
            logger.debug(f"Role already exists: {config['name']}")
        else:
            role = Role(
                id=str(uuid.uuid4()),
                tenant_id=None,  # System roles don't belong to a specific tenant
                name=config["name"],
                description=config["description"],
                is_system=config["is_system"],
                is_default=config["is_default"],
            )
            db.add(role)
            await db.flush()  # Flush to get the role ID
            logger.debug(f"Created role: {config['name']}")

        roles[role_key] = role

        # Assign permissions to role
        for resource, actions in config["permissions"].items():
            for action in actions:
                permission_key = f"{resource}:{action}"
                permission = permissions.get(permission_key)

                if permission:
                    # Check if role_permission already exists
                    result = await db.execute(
                        select(RolePermission).filter(
                            RolePermission.role_id == role.id, RolePermission.permission_id == permission.id
                        )
                    )
                    existing_rp = result.scalar_one_or_none()

                    if not existing_rp:
                        role_permission = RolePermission(
                            id=str(uuid.uuid4()), role_id=role.id, permission_id=permission.id
                        )
                        db.add(role_permission)
                        logger.debug(f"  Assigned permission: {permission_key} to {config['name']}")

    await db.commit()
    return roles


async def seed_roles_and_permissions(db: AsyncSession):
    """Main function to seed roles and permissions."""
    logger.info("Starting roles and permissions seeding...")

    try:
        # Create all permissions
        logger.info("1. Creating permissions...")
        permissions = await create_permissions(db)
        logger.info(f"Total permissions: {len(permissions)}")

        # Create roles and assign permissions
        logger.info("2. Creating roles and assigning permissions...")
        roles = await create_roles(db, permissions)
        logger.info(f"Total roles: {len(roles)}")

        logger.info("Roles and permissions seeded successfully!")

        # Log summary
        logger.info("=== Summary ===")
        for _role_key, role in roles.items():
            from sqlalchemy import func

            result = await db.execute(
                select(func.count()).select_from(RolePermission).filter(RolePermission.role_id == role.id)
            )
            permission_count = result.scalar()
            logger.info(f"{role.name}: {permission_count} permissions")

        return True

    except Exception as e:
        logger.error(f"Error seeding roles and permissions: {str(e)}")
        await db.rollback()
        raise


if __name__ == "__main__":
    # This allows running the script directly for testing
    import asyncio

    from src.core.database import get_async_db

    async def main():
        async for db in get_async_db():
            try:
                await seed_roles_and_permissions(db)
            finally:
                await db.close()

    asyncio.run(main())
