"""
Permissions management controller
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_async_db
from src.middleware.auth_middleware import get_current_account, get_current_tenant_id
from src.models.tenant import AccountRole, TenantAccountJoin
from src.services.permissions.permission_service import PermissionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/permissions", tags=["permissions"])


async def get_user_role(db: AsyncSession, account_id: uuid.UUID, tenant_id: uuid.UUID) -> str:
    """
    Get user's role in a tenant.

    Args:
        db: Async database session
        account_id: User's account ID
        tenant_id: Tenant ID

    Returns:
        Role name as string (e.g., 'OWNER', 'ADMIN', 'EDITOR', 'NORMAL')
    """
    result = await db.execute(
        select(TenantAccountJoin).filter(
            TenantAccountJoin.account_id == account_id, TenantAccountJoin.tenant_id == tenant_id
        )
    )
    membership = result.scalar_one_or_none()

    return membership.role.value if membership else AccountRole.NORMAL.value


# Pydantic models for request/response
class PermissionResponse(BaseModel):
    id: str
    name: str
    resource: str
    action: str
    description: str | None
    is_system: bool
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class RolePermissionsResponse(BaseModel):
    role: str
    permissions: list[str]


class UserPermissionsResponse(BaseModel):
    account_id: str
    role: str
    role_permissions: list[str]
    custom_permissions: list[str]
    effective_permissions: list[str]


class CheckPermissionRequest(BaseModel):
    permission: str = Field(..., pattern=r"^[a-z_]+\.[a-z_]+$")


class CheckPermissionResponse(BaseModel):
    has_permission: bool
    reason: str | None = None


@router.get("", response_model=list[PermissionResponse])
async def list_permissions(
    resource: str | None = None,
    is_platform_wide: bool | None = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_account=Depends(get_current_account),
):
    """List all available permissions"""
    try:
        permission_service = PermissionService(db)
        permissions = await permission_service.get_all_permissions(is_platform_permission=is_platform_wide)

        # Apply filtering and pagination
        if resource:
            permissions = [p for p in permissions if p.name.startswith(f"{resource}.")]

        paginated = permissions[skip : skip + limit]

        return [
            PermissionResponse(
                id=str(p.id),
                name=p.name,
                resource=p.resource,
                action=p.action,
                description=p.description,
                is_system=p.is_system,
                created_at=p.created_at.isoformat() if hasattr(p.created_at, "isoformat") else (p.created_at or ""),
            )
            for p in paginated
        ]

    except Exception as e:
        logger.error(f"Error listing permissions: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list permissions")


@router.get("/roles/{role}", response_model=RolePermissionsResponse)
async def get_role_permissions(
    role: str,
    db: AsyncSession = Depends(get_async_db),
    current_account=Depends(get_current_account),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Get permissions for a specific role"""
    from src.models.role import Role

    try:
        # Validate role
        if role not in [r.value for r in AccountRole]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid role: {role}")

        # Look up the Role by name to get its UUID
        result = await db.execute(
            select(Role).filter(
                Role.name == role,
                (Role.tenant_id == tenant_id) | (Role.tenant_id.is_(None)),  # Check tenant-specific or system role
            )
        )
        role_obj = result.scalar_one_or_none()

        if role_obj:
            permission_service = PermissionService(db)
            permissions = await permission_service.get_role_permissions(tenant_id, role_obj.id)
        else:
            # Role not found in database, return empty permissions
            permissions = []

        return {"role": role, "permissions": permissions}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting role permissions: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get role permissions")


@router.get("/users/{account_id}", response_model=UserPermissionsResponse)
async def get_user_permissions(
    account_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_account=Depends(get_current_account),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Get all permissions for a specific user"""
    try:
        account_uuid = uuid.UUID(account_id)
        permission_service = PermissionService(db)
        permissions = await permission_service.get_user_permissions(account_uuid, tenant_id)
        user_role = await get_user_role(db, account_uuid, tenant_id)

        return {
            "account_id": account_id,
            "role": user_role,
            "role_permissions": permissions,
            "custom_permissions": [],
            "effective_permissions": permissions,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user permissions: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get user permissions")


@router.get("/me", response_model=UserPermissionsResponse)
async def get_my_permissions(
    db: AsyncSession = Depends(get_async_db),
    current_account=Depends(get_current_account),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Get permissions for the current user"""
    try:
        logger.info(f"[PERMISSIONS /me] Request received for account_id={current_account.id}, tenant_id={tenant_id}")

        # Get user role
        user_role = await get_user_role(db, current_account.id, tenant_id)
        logger.info(f"[PERMISSIONS /me] User role retrieved: {user_role}")

        # Get permissions
        permission_service = PermissionService(db)
        permissions = await permission_service.get_user_permissions(current_account.id, tenant_id)
        logger.info(f"[PERMISSIONS /me] Permissions retrieved: {permissions} (count: {len(permissions)})")

        response_data = {
            "account_id": str(current_account.id),
            "role": user_role,
            "role_permissions": permissions,
            "custom_permissions": [],
            "effective_permissions": permissions,
        }

        logger.info(f"[PERMISSIONS /me] Returning response with {len(permissions)} permissions for role {user_role}")
        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[PERMISSIONS /me] Error getting current user permissions: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get current user permissions"
        )


@router.post("/check", response_model=CheckPermissionResponse)
async def check_permission(
    request: CheckPermissionRequest,
    db: AsyncSession = Depends(get_async_db),
    current_account=Depends(get_current_account),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Check if the current user has a specific permission"""
    try:
        # Parse permission into resource and action
        parts = request.permission.split(".")
        if len(parts) != 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid permission format. Expected 'resource.action'"
            )

        resource, action = parts
        permission_service = PermissionService(db)
        has_permission = await permission_service.check_permission(current_account.id, tenant_id, resource, action)

        return {"has_permission": has_permission, "reason": None if has_permission else "Permission denied"}

    except Exception as e:
        logger.error(f"Error checking permission: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to check permission")


@router.post("/users/{account_id}/grant", response_model=UserPermissionsResponse)
async def grant_permission(
    account_id: str,
    request: CheckPermissionRequest,
    db: AsyncSession = Depends(get_async_db),
    current_account=Depends(get_current_account),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Grant a custom permission to a user"""
    try:
        permission_service = PermissionService(db)

        # Check if current user has permission to grant permissions
        has_permission = await permission_service.check_permission(
            current_account.id, tenant_id, "team", "manage_permissions"
        )

        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions to grant permissions"
            )

        success = await permission_service.grant_permission(uuid.UUID(account_id), tenant_id, request.permission)

        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found in tenant")

        # Get updated permissions
        account_uuid = uuid.UUID(account_id)
        permissions = await permission_service.get_user_permissions(account_uuid, tenant_id)
        user_role = await get_user_role(db, account_uuid, tenant_id)

        return {
            "account_id": account_id,
            "role": user_role,
            "role_permissions": permissions,
            "custom_permissions": [],
            "effective_permissions": permissions,
        }

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error granting permission: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to grant permission")


@router.post("/users/{account_id}/revoke", response_model=UserPermissionsResponse)
async def revoke_permission(
    account_id: str,
    request: CheckPermissionRequest,
    db: AsyncSession = Depends(get_async_db),
    current_account=Depends(get_current_account),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Revoke a custom permission from a user"""
    try:
        permission_service = PermissionService(db)

        # Check if current user has permission to revoke permissions
        has_permission = await permission_service.check_permission(
            current_account.id, tenant_id, "team", "manage_permissions"
        )

        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions to revoke permissions"
            )

        success = await permission_service.revoke_permission(uuid.UUID(account_id), tenant_id, request.permission)

        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found in tenant")

        # Get updated permissions
        account_uuid = uuid.UUID(account_id)
        permissions = await permission_service.get_user_permissions(account_uuid, tenant_id)
        user_role = await get_user_role(db, account_uuid, tenant_id)

        return {
            "account_id": account_id,
            "role": user_role,
            "role_permissions": permissions,
            "custom_permissions": [],
            "effective_permissions": permissions,
        }

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error revoking permission: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to revoke permission")
