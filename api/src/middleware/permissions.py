"""Permission middleware and decorators."""

from collections.abc import Callable
from functools import wraps
from uuid import UUID

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_async_db
from ..models import Account
from ..services.permissions.permission_service import PermissionService
from .auth_middleware import get_current_account, get_current_tenant_id


def require_permission(resource: str, action: str):
    """
    Decorator to require specific permission for an endpoint.

    Args:
        resource: Resource name (e.g., "integration_configs", "agents")
        action: Action name (e.g., "create", "read", "update", "delete")

    Usage:
        @router.post("/integration-configs")
        @require_permission("integration_configs", "create")
        async def create_config(...):
            ...
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract dependencies from kwargs
            current_account: Account = kwargs.get("current_account")
            tenant_id: str = kwargs.get("tenant_id")
            db: AsyncSession = kwargs.get("db")

            if not current_account or not tenant_id or not db:
                raise HTTPException(status_code=500, detail="Missing required dependencies for permission check")

            # Check permission
            permission_service = PermissionService(db)
            has_permission = await permission_service.check_permission(
                account_id=UUID(str(current_account.id)), tenant_id=UUID(tenant_id), resource=resource, action=action
            )

            if not has_permission:
                raise HTTPException(status_code=403, detail=f"Permission denied: {resource}.{action}")

            return await func(*args, **kwargs)

        return wrapper

    return decorator


async def check_permission_dependency(
    resource: str,
    action: str,
    current_account: Account = Depends(get_current_account),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Dependency function to check permissions.

    Usage:
        @router.post("/integration-configs")
        async def create_config(
            _: None = Depends(lambda: check_permission_dependency("integration_configs", "create"))
        ):
            ...
    """
    permission_service = PermissionService(db)
    has_permission = await permission_service.check_permission(
        account_id=UUID(str(current_account.id)), tenant_id=UUID(tenant_id), resource=resource, action=action
    )

    if not has_permission:
        raise HTTPException(status_code=403, detail=f"Permission denied: {resource}.{action}")

    return None
