"""
Console apps endpoints.

Handles CRUD operations for applications.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_async_db
from src.middleware import get_current_account, get_current_tenant_id
from src.models import Account
from src.services import AppService

router = APIRouter()


class CreateAppRequest(BaseModel):
    """Create app request schema."""

    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    mode: str = Field(default="chat")
    icon: str | None = Field(default="🤖", max_length=10)
    icon_background: str | None = Field(default="#6366F1", max_length=20)


class UpdateAppRequest(BaseModel):
    """Update app request schema."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    icon: str | None = Field(default=None, max_length=10)
    icon_background: str | None = Field(default=None, max_length=20)


class AppResponse(BaseModel):
    """App response schema."""

    id: str
    name: str
    description: str | None
    mode: str
    icon: str | None
    icon_background: str | None
    status: str
    created_at: str | None
    updated_at: str | None


@router.get("")
async def list_apps(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    mode: str | None = None,
    name: str | None = None,
    tenant_id: UUID = Depends(get_current_tenant_id),
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_async_db),
):
    """
    List all apps for the current tenant.

    Args:
        page: Page number
        limit: Items per page
        mode: Filter by mode
        name: Filter by name
        tenant_id: Current tenant ID
        current_account: Current authenticated account
        db: Database session

    Returns:
        Paginated list of apps
    """
    # Get apps using service
    app_service = AppService(db)
    args = {
        "page": page,
        "limit": limit,
        "mode": mode,
        "name": name,
    }
    apps = await app_service.get_paginate_apps(tenant_id, args)

    # Format apps data
    apps_data = [
        {
            "id": str(app.id),
            "name": app.name,
            "description": app.description,
            "mode": app.mode,
            "icon": app.icon,
            "icon_background": app.icon_background,
            "status": app.status,
            "created_at": app.created_at.isoformat() if app.created_at else None,
            "updated_at": app.updated_at.isoformat() if app.updated_at else None,
        }
        for app in apps
    ]

    # Return Synkora-style pagination response
    return {
        "page": page,
        "limit": limit,
        "total": len(apps_data),
        "has_more": False,  # Simple implementation for now
        "data": apps_data,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_app(
    data: CreateAppRequest,
    tenant_id: UUID = Depends(get_current_tenant_id),
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Create a new app.

    Args:
        data: App creation data
        tenant_id: Current tenant ID
        current_account: Current authenticated account
        db: Database session

    Returns:
        Created app data
    """
    app_service = AppService(db)
    app = await app_service.create_app(
        tenant_id=tenant_id,
        name=data.name,
        mode=data.mode,
        description=data.description,
        icon=data.icon,
        icon_background=data.icon_background,
    )

    # Return app data directly (Synkora pattern)
    return {
        "id": str(app.id),
        "name": app.name,
        "description": app.description,
        "mode": app.mode,
        "icon": app.icon,
        "icon_background": app.icon_background,
        "status": app.status,
        "created_at": app.created_at.isoformat() if app.created_at else None,
        "updated_at": app.updated_at.isoformat() if app.updated_at else None,
    }


@router.get("/{app_id}")
async def get_app(
    app_id: str,
    tenant_id: UUID = Depends(get_current_tenant_id),
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get app details.

    Args:
        app_id: App ID
        tenant_id: Current tenant ID
        current_account: Current authenticated account
        db: Database session

    Returns:
        App data
    """
    app_service = AppService(db)
    app = await app_service.get_app(app_id, tenant_id)

    # Return app data directly (Synkora pattern)
    return {
        "id": str(app.id),
        "name": app.name,
        "description": app.description,
        "mode": app.mode,
        "icon": app.icon,
        "icon_background": app.icon_background,
        "status": app.status,
        "created_at": app.created_at.isoformat() if app.created_at else None,
        "updated_at": app.updated_at.isoformat() if app.updated_at else None,
    }


@router.put("/{app_id}")
async def update_app(
    app_id: str,
    data: UpdateAppRequest,
    tenant_id: UUID = Depends(get_current_tenant_id),
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Update app.

    Args:
        app_id: App ID
        data: App update data
        tenant_id: Current tenant ID
        current_account: Current authenticated account
        db: Database session

    Returns:
        Updated app data
    """
    app_service = AppService(db)
    app = await app_service.get_app(app_id, tenant_id)

    # Update app
    update_args = {}
    if data.name is not None:
        update_args["name"] = data.name
    if data.description is not None:
        update_args["description"] = data.description
    if data.icon is not None:
        update_args["icon"] = data.icon
    if data.icon_background is not None:
        update_args["icon_background"] = data.icon_background

    app = await app_service.update_app(app, update_args)

    # Return app data directly (Synkora pattern)
    return {
        "id": str(app.id),
        "name": app.name,
        "description": app.description,
        "mode": app.mode,
        "icon": app.icon,
        "icon_background": app.icon_background,
        "status": app.status,
        "created_at": app.created_at.isoformat() if app.created_at else None,
        "updated_at": app.updated_at.isoformat() if app.updated_at else None,
    }


@router.delete("/{app_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_app(
    app_id: str,
    tenant_id: UUID = Depends(get_current_tenant_id),
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Delete app.

    Args:
        app_id: App ID
        tenant_id: Current tenant ID
        current_account: Current authenticated account
        db: Database session

    Returns:
        No content
    """
    app_service = AppService(db)
    app = await app_service.get_app(app_id, tenant_id)
    await app_service.delete_app(app)

    # Return nothing for 204
    return None
