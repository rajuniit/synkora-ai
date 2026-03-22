"""
Seed data for default agent role templates.

This script creates the default system role templates (PM, QA, BA, etc.)
that are available to all tenants. These templates are read-only and
serve as a starting point for role-based agents.
"""

import asyncio
import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.models import AgentRole

logger = logging.getLogger(__name__)

# System tenant ID for system-wide templates
SYSTEM_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")


async def seed_role_templates(db: AsyncSession, tenant_id: uuid.UUID | None = None) -> list[AgentRole]:
    """
    Create default agent role templates if they don't exist.

    Args:
        db: Async database session
        tenant_id: Tenant ID to use for templates (defaults to system tenant)

    Returns:
        List of created or existing role templates
    """
    from src.services.roles.agent_role_service import AgentRoleService

    service = AgentRoleService(db)
    target_tenant_id = tenant_id or SYSTEM_TENANT_ID

    roles = await service.seed_system_roles(system_tenant_id=target_tenant_id)

    logger.info(f"Seeded {len(roles)} role templates:")
    for role in roles:
        logger.info(f"  - {role.role_name} ({role.role_type})")

    return roles


async def async_main():
    """Run the seed script asynchronously."""
    logging.basicConfig(level=logging.INFO)
    from src.core.database import get_async_session_factory

    AsyncSessionLocal = get_async_session_factory()
    async with AsyncSessionLocal() as db:
        try:
            await seed_role_templates(db)
            logger.info("Role templates seeded successfully!")
        except Exception as e:
            logger.error(f"Error seeding role templates: {e}")
            await db.rollback()
            raise


def main():
    """Run the seed script."""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
