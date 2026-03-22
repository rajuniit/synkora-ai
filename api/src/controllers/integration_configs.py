"""
Integration configurations controller.

Handles API endpoints for managing integration configurations (email, etc.).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_async_db
from src.middleware.auth_middleware import get_current_account, get_current_tenant_id
from src.models import Account
from src.services.integrations.email_service import EmailService
from src.services.integrations.integration_config_service import IntegrationConfigService
from src.services.permissions.permission_service import PermissionService

router = APIRouter(prefix="/console/api/integration-configs", tags=["integration-configs"])


async def check_integration_permission(
    action: str, current_account: Account, tenant_id: UUID, db: AsyncSession, is_platform_config: bool = False
):
    """Check if user has permission for integration config actions."""
    permission_service = PermissionService(db)

    # For platform configs, check platform permission
    if is_platform_config:
        has_platform_permission = await permission_service.check_permission(
            account_id=UUID(str(current_account.id)), tenant_id=tenant_id, resource="platform", action=action
        )

        if not has_platform_permission:
            raise HTTPException(
                status_code=403, detail=f"Permission denied: Only Platform Owners can {action} platform configurations"
            )
    else:
        # For tenant configs, check integration_configs permission
        has_permission = await permission_service.check_permission(
            account_id=UUID(str(current_account.id)), tenant_id=tenant_id, resource="integration_configs", action=action
        )

        if not has_permission:
            raise HTTPException(status_code=403, detail=f"Permission denied: integration_configs.{action}")
    return None


@router.get("")
async def list_configs(
    integration_type: str | None = None,
    provider: str | None = None,
    current_account: Account = Depends(get_current_account),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """List integration configurations for the current tenant."""
    # Check permission
    await check_integration_permission("read", current_account, tenant_id, db)

    # Check if user is Platform Owner
    permission_service = PermissionService(db)
    is_platform_owner = await permission_service.check_permission(
        account_id=UUID(str(current_account.id)), tenant_id=tenant_id, resource="platform", action="read"
    )

    service = IntegrationConfigService(db)

    configs = await service.list_configs(tenant_id=tenant_id, integration_type=integration_type, provider=provider)

    # Filter out platform configs if user is not Platform Owner
    if not is_platform_owner:
        configs = [config for config in configs if not config.is_platform_config]

    return [
        {
            "id": str(config.id),
            "integration_type": config.integration_type,
            "provider": config.provider,
            "is_active": config.is_active,
            "is_default": config.is_default,
            "is_platform_config": config.is_platform_config,
            "created_at": config.created_at.isoformat() if config.created_at else None,
            "updated_at": config.updated_at.isoformat() if config.updated_at else None,
        }
        for config in configs
    ]


@router.get("/active")
async def get_active_config(
    integration_type: str = "email",
    provider: str | None = None,
    current_account: Account = Depends(get_current_account),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Get the active configuration for a specific integration type."""
    # Check permission
    await check_integration_permission("read", current_account, tenant_id, db)

    service = IntegrationConfigService(db)

    config = await service.get_active_config(tenant_id=tenant_id, integration_type=integration_type, provider=provider)

    if not config:
        raise HTTPException(status_code=404, detail="No active configuration found")

    # Get decrypted config data using public method
    config_data = await service.get_active_config_data(
        tenant_id=tenant_id, integration_type=integration_type, provider=provider
    )

    return {
        "id": str(config.id),
        "integration_type": config.integration_type,
        "provider": config.provider,
        "config_data": config_data,
        "is_active": config.is_active,
        "is_default": config.is_default,
        "is_platform_config": config.is_platform_config,
    }


@router.get("/{config_id}")
async def get_config(
    config_id: str,
    current_account: Account = Depends(get_current_account),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Get a specific integration configuration."""
    service = IntegrationConfigService(db)

    config = await service.get_config(config_id)

    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    # Check permission based on config type
    if config.is_platform_config:
        # Only Platform Owners can access platform configs
        await check_integration_permission("read", current_account, tenant_id, db, is_platform_config=True)
    else:
        # For tenant configs, check standard permission and ownership
        await check_integration_permission("read", current_account, tenant_id, db)
        if str(config.tenant_id) != str(tenant_id):
            raise HTTPException(status_code=403, detail="Unauthorized")

    # Get decrypted config data using public method
    config_data = await service.get_config_data(config_id)

    return {
        "id": str(config.id),
        "integration_type": config.integration_type,
        "provider": config.provider,
        "config_data": config_data,
        "is_active": config.is_active,
        "is_default": config.is_default,
        "is_platform_config": config.is_platform_config,
        "created_at": config.created_at.isoformat() if config.created_at else None,
        "updated_at": config.updated_at.isoformat() if config.updated_at else None,
    }


@router.post("")
async def create_config(
    data: dict,
    current_account: Account = Depends(get_current_account),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Create a new integration configuration."""
    # Validate required fields
    if not data.get("integration_type") or not data.get("provider") or not data.get("config_data"):
        raise HTTPException(status_code=400, detail="Missing required fields")

    # Determine if this should be a platform config
    is_platform_config = data.get("is_platform_config", False)

    # Check permission based on config type
    await check_integration_permission("create", current_account, tenant_id, db, is_platform_config)

    service = IntegrationConfigService(db)
    config_tenant_id = None if is_platform_config else tenant_id

    try:
        config = await service.create_config(
            tenant_id=config_tenant_id,
            integration_type=data["integration_type"],
            provider=data["provider"],
            config_data=data["config_data"],
            is_active=data.get("is_active", True),
            is_default=data.get("is_default", False),
            is_platform_config=is_platform_config,
            created_by=current_account.id,
        )

        return {"id": str(config.id), "message": "Configuration created successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{config_id}")
async def update_config(
    config_id: str,
    data: dict,
    current_account: Account = Depends(get_current_account),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Update an existing integration configuration."""
    service = IntegrationConfigService(db)

    # Get existing config
    config = await service.get_config(config_id)

    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    # Check permission based on config type
    await check_integration_permission("update", current_account, tenant_id, db, config.is_platform_config)

    # Check ownership for tenant configs
    if not config.is_platform_config and str(config.tenant_id) != str(tenant_id):
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Update config
    updated_config = await service.update_config(
        config_id=config_id,
        config_data=data.get("config_data"),
        is_active=data.get("is_active"),
        is_default=data.get("is_default"),
    )

    if not updated_config:
        raise HTTPException(status_code=500, detail="Failed to update configuration")

    return {"id": str(updated_config.id), "message": "Configuration updated successfully"}


@router.delete("/{config_id}")
async def delete_config(
    config_id: str,
    current_account: Account = Depends(get_current_account),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Delete an integration configuration."""
    service = IntegrationConfigService(db)

    # Get existing config
    config = await service.get_config(config_id)

    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    # Check permission based on config type
    await check_integration_permission("delete", current_account, tenant_id, db, config.is_platform_config)

    # Check ownership for tenant configs
    if not config.is_platform_config and str(config.tenant_id) != str(tenant_id):
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Delete config
    success = await service.delete_config(config_id)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete configuration")

    return {"message": "Configuration deleted successfully"}


@router.post("/{config_id}/test")
async def test_specific_config(
    config_id: str,
    data: dict,
    current_account: Account = Depends(get_current_account),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Test a specific integration configuration."""
    # Check permission
    await check_integration_permission("read", current_account, tenant_id, db)

    service = IntegrationConfigService(db)

    # Get the config
    config = await service.get_config(config_id)

    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    # Check permission
    if not config.is_platform_config and str(config.tenant_id) != str(tenant_id):
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Only support email testing for now
    if config.integration_type != "email":
        raise HTTPException(status_code=400, detail="Only email configurations can be tested")

    email_service = EmailService(db)

    # Get test email address
    test_email = data.get("test_email", current_account.email)

    # Test connection with specific config
    result = await email_service.test_connection(tenant_id=tenant_id, test_email=test_email, config_id=config_id)

    return result


@router.post("/test")
async def test_email_config(
    data: dict,
    current_account: Account = Depends(get_current_account),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Test email configuration by sending a test email (uses active config)."""
    # Check permission
    await check_integration_permission("read", current_account, tenant_id, db)

    email_service = EmailService(db)

    # Get test email address
    test_email = data.get("test_email", current_account.email)

    # Test connection
    result = await email_service.test_connection(tenant_id=tenant_id, test_email=test_email)

    return result
