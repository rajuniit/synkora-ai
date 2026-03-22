"""
App service for managing AI applications.

This service handles CRUD operations and business logic for apps.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.errors import NotFoundError
from src.models.app import App, AppStatus


class AppService:
    """Service for managing apps."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        self.db = db

    async def get_paginate_apps(self, tenant_id: str, args: dict):
        """
        Get app list with pagination.

        Args:
            tenant_id: Tenant ID
            args: Request args with page, limit, etc.

        Returns:
            Paginated apps
        """
        filters = [App.tenant_id == tenant_id]

        if args.get("mode"):
            filters.append(App.mode == args["mode"])

        if args.get("name"):
            name = args["name"][:30]
            # SECURITY: Escape special LIKE pattern characters to prevent SQL injection
            escaped_name = name.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            filters.append(App.name.ilike(f"%{escaped_name}%", escape="\\"))

        query = select(App).where(*filters).order_by(App.created_at.desc())

        # Simple pagination
        page = args.get("page", 1)
        limit = args.get("limit", 20)
        offset = (page - 1) * limit

        query = query.limit(limit).offset(offset)

        result = await self.db.execute(query)
        apps = list(result.scalars().all())

        return apps

    async def create_app(
        self,
        tenant_id: str,
        name: str,
        mode: str = "chat",
        description: str | None = None,
        icon: str | None = None,
        icon_background: str | None = None,
    ) -> App:
        """
        Create a new app.

        Args:
            tenant_id: Tenant ID
            name: App name
            mode: App mode
            description: App description
            icon: App icon
            icon_background: Icon background color

        Returns:
            Created app
        """
        app = App(
            tenant_id=tenant_id,
            name=name,
            mode=mode,
            description=description or "",
            icon=icon or "🤖",
            icon_background=icon_background or "#6366F1",
            status=AppStatus.NORMAL,
        )

        self.db.add(app)
        await self.db.commit()
        await self.db.refresh(app)

        return app

    async def get_app(self, app_id: str, tenant_id: str) -> App:
        """
        Get app by ID.

        Args:
            app_id: App ID
            tenant_id: Tenant ID for access control

        Returns:
            App instance

        Raises:
            NotFoundError: If app not found
            PermissionDeniedError: If tenant doesn't have access
        """
        result = await self.db.execute(select(App).filter(App.id == app_id, App.tenant_id == tenant_id))
        app = result.scalar_one_or_none()

        if not app:
            raise NotFoundError("App not found")

        return app

    async def update_app(self, app: App, args: dict) -> App:
        """
        Update an app.

        Args:
            app: App instance
            args: Update arguments

        Returns:
            Updated app
        """
        if "name" in args:
            app.name = args["name"]
        if "description" in args:
            app.description = args["description"]
        if "icon" in args:
            app.icon = args["icon"]
        if "icon_background" in args:
            app.icon_background = args["icon_background"]

        await self.db.commit()
        await self.db.refresh(app)

        return app

    async def delete_app(self, app: App):
        """
        Delete an app (soft delete).

        Args:
            app: App instance
        """
        # Soft delete by setting status
        app.status = AppStatus.DELETED
        await self.db.commit()
