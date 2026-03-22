"""Service for managing OAuth apps with platform-level fallback support.

This service handles retrieval of OAuth apps with automatic fallback to platform apps
when a tenant doesn't have their own OAuth app for a provider.

Platform OAuth apps (is_platform_app=True, tenant_id=None) are Synkora-provided
integrations that any tenant can use without setting up their own OAuth credentials.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.oauth_app import OAuthApp
from ...models.tenant import Tenant


class OAuthAppService:
    """Service for OAuth app management with platform app fallback."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_oauth_app(
        self,
        tenant_id: UUID,
        provider: str,
        *,
        app_id: int | None = None,
        auth_method: str | None = None,
        include_platform_apps: bool = True,
    ) -> OAuthApp | None:
        """
        Get an OAuth app for a tenant with automatic fallback to platform apps.

        Priority order:
        1. Tenant's own app (if app_id specified, use that)
        2. Tenant's default app for the provider
        3. Platform app (if enabled for tenant and include_platform_apps=True)

        Args:
            tenant_id: The tenant's UUID
            provider: OAuth provider name (github, slack, gitlab, zoom, gmail)
            app_id: Optional specific app ID to retrieve
            auth_method: Optional filter by auth method (oauth, api_token)
            include_platform_apps: Whether to fallback to platform apps (default True)

        Returns:
            OAuthApp or None if not found
        """
        provider = provider.lower()

        # If specific app_id provided, get that app
        if app_id is not None:
            result = await self.db.execute(select(OAuthApp).filter(OAuthApp.id == app_id))
            app = result.scalar_one_or_none()
            if app:
                # Verify tenant ownership or platform app
                if app.tenant_id == tenant_id or app.is_platform_app:
                    # Check if platform app is enabled for this tenant
                    if app.is_platform_app and not await self._is_platform_app_enabled(tenant_id, provider):
                        return None
                    return app
            return None

        # Try tenant's own apps first
        query = select(OAuthApp).filter(
            OAuthApp.tenant_id == tenant_id,
            OAuthApp.provider == provider,
            OAuthApp.is_active.is_(True),
        )

        if auth_method:
            query = query.filter(OAuthApp.auth_method == auth_method)

        # Prefer default app
        result = await self.db.execute(query.filter(OAuthApp.is_default.is_(True)))
        tenant_app = result.scalar_one_or_none()
        if not tenant_app:
            result = await self.db.execute(query)
            tenant_app = result.scalar_one_or_none()

        if tenant_app:
            return tenant_app

        # Fallback to platform app if enabled
        if include_platform_apps and await self._is_platform_app_enabled(tenant_id, provider):
            return await self.get_platform_app(provider, auth_method=auth_method)

        return None

    async def get_platform_app(
        self,
        provider: str,
        *,
        auth_method: str | None = None,
    ) -> OAuthApp | None:
        """
        Get a platform-level OAuth app.

        Args:
            provider: OAuth provider name
            auth_method: Optional filter by auth method

        Returns:
            Platform OAuthApp or None
        """
        provider = provider.lower()

        query = select(OAuthApp).filter(
            OAuthApp.is_platform_app.is_(True),
            OAuthApp.tenant_id.is_(None),
            OAuthApp.provider == provider,
            OAuthApp.is_active.is_(True),
        )

        if auth_method:
            query = query.filter(OAuthApp.auth_method == auth_method)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_available_apps(
        self,
        tenant_id: UUID,
        provider: str | None = None,
    ) -> list[dict]:
        """
        List all OAuth apps available to a tenant (tenant's own + enabled platform apps).

        Args:
            tenant_id: The tenant's UUID
            provider: Optional filter by provider

        Returns:
            List of OAuth app dicts with 'source' field indicating 'tenant' or 'platform'
        """
        apps = []

        # Get tenant's own apps
        tenant_query = select(OAuthApp).filter(
            OAuthApp.tenant_id == tenant_id,
            OAuthApp.is_active.is_(True),
        )
        if provider:
            tenant_query = tenant_query.filter(OAuthApp.provider == provider.lower())

        result = await self.db.execute(tenant_query)
        for app in result.scalars().all():
            app_dict = app.to_dict()
            app_dict["source"] = "tenant"
            apps.append(app_dict)

        # Get enabled platform apps
        platform_query = select(OAuthApp).filter(
            OAuthApp.is_platform_app.is_(True),
            OAuthApp.tenant_id.is_(None),
            OAuthApp.is_active.is_(True),
        )
        if provider:
            platform_query = platform_query.filter(OAuthApp.provider == provider.lower())

        # Get disabled providers for this tenant
        disabled_providers = await self._get_disabled_providers(tenant_id)

        result = await self.db.execute(platform_query)
        for app in result.scalars().all():
            if app.provider not in disabled_providers:
                app_dict = app.to_dict()
                app_dict["source"] = "platform"
                apps.append(app_dict)

        return apps

    async def list_platform_apps(self, provider: str | None = None) -> list[OAuthApp]:
        """
        List all platform OAuth apps.

        Args:
            provider: Optional filter by provider

        Returns:
            List of platform OAuthApp instances
        """
        query = select(OAuthApp).filter(
            OAuthApp.is_platform_app.is_(True),
            OAuthApp.tenant_id.is_(None),
            OAuthApp.is_active.is_(True),
        )

        if provider:
            query = query.filter(OAuthApp.provider == provider.lower())

        result = await self.db.execute(query)
        return result.scalars().all()

    async def toggle_platform_app(
        self,
        tenant_id: UUID,
        provider: str,
        enabled: bool,
    ) -> bool:
        """
        Enable or disable a platform OAuth app for a specific tenant.

        Args:
            tenant_id: The tenant's UUID
            provider: OAuth provider name
            enabled: True to enable, False to disable

        Returns:
            True if operation succeeded
        """
        provider = provider.lower()
        result = await self.db.execute(select(Tenant).filter(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()

        if not tenant:
            return False

        disabled_providers = tenant.disabled_platform_oauth_providers or []

        if enabled:
            # Remove from disabled list
            if provider in disabled_providers:
                disabled_providers.remove(provider)
        else:
            # Add to disabled list
            if provider not in disabled_providers:
                disabled_providers.append(provider)

        tenant.disabled_platform_oauth_providers = disabled_providers
        await self.db.commit()

        return True

    async def get_platform_app_status(self, tenant_id: UUID) -> dict[str, bool]:
        """
        Get the enabled/disabled status of all platform apps for a tenant.

        Args:
            tenant_id: The tenant's UUID

        Returns:
            Dict mapping provider name to enabled status
        """
        platform_apps = await self.list_platform_apps()
        disabled_providers = await self._get_disabled_providers(tenant_id)

        return {app.provider: app.provider not in disabled_providers for app in platform_apps}

    async def _is_platform_app_enabled(self, tenant_id: UUID, provider: str) -> bool:
        """Check if a platform app is enabled for a tenant."""
        disabled_providers = await self._get_disabled_providers(tenant_id)
        return provider.lower() not in disabled_providers

    async def _get_disabled_providers(self, tenant_id: UUID) -> list[str]:
        """Get list of disabled platform providers for a tenant."""
        result = await self.db.execute(select(Tenant).filter(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()
        if not tenant or not tenant.disabled_platform_oauth_providers:
            return []
        return [p.lower() for p in tenant.disabled_platform_oauth_providers]

    async def create_platform_app(
        self,
        provider: str,
        app_name: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scopes: list[str] | None = None,
        description: str | None = None,
        config: dict | None = None,
    ) -> OAuthApp:
        """
        Create a platform-level OAuth app (admin only).

        Args:
            provider: OAuth provider name
            app_name: Display name for the app
            client_id: OAuth client ID
            client_secret: OAuth client secret (will be encrypted by caller)
            redirect_uri: OAuth redirect URI
            scopes: List of OAuth scopes
            description: Optional description
            config: Optional provider-specific config

        Returns:
            Created OAuthApp instance
        """
        from ...config.security import encrypt_value

        app = OAuthApp(
            tenant_id=None,
            provider=provider.lower(),
            app_name=app_name,
            is_platform_app=True,
            auth_method="oauth",
            client_id=client_id,
            client_secret=encrypt_value(client_secret),
            redirect_uri=redirect_uri,
            scopes=scopes or [],
            description=description,
            config=config,
            is_active=True,
            is_default=True,
        )

        self.db.add(app)
        await self.db.commit()
        await self.db.refresh(app)

        return app

    async def update_platform_app(
        self,
        app_id: int,
        **kwargs,
    ) -> OAuthApp | None:
        """
        Update a platform OAuth app.

        Args:
            app_id: The app ID
            **kwargs: Fields to update

        Returns:
            Updated OAuthApp or None
        """
        from ...config.security import encrypt_value

        result = await self.db.execute(
            select(OAuthApp).filter(
                OAuthApp.id == app_id,
                OAuthApp.is_platform_app.is_(True),
            )
        )
        app = result.scalar_one_or_none()

        if not app:
            return None

        for key, value in kwargs.items():
            if key == "client_secret" and value:
                value = encrypt_value(value)
            if hasattr(app, key):
                setattr(app, key, value)

        await self.db.commit()
        await self.db.refresh(app)

        return app

    async def delete_platform_app(self, app_id: int) -> bool:
        """
        Delete a platform OAuth app.

        Args:
            app_id: The app ID

        Returns:
            True if deleted, False if not found
        """
        result = await self.db.execute(
            select(OAuthApp).filter(
                OAuthApp.id == app_id,
                OAuthApp.is_platform_app.is_(True),
            )
        )
        app = result.scalar_one_or_none()

        if not app:
            return False

        await self.db.delete(app)
        await self.db.commit()

        return True
