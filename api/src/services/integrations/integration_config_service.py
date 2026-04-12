"""Service for managing integration configurations."""

import json
import logging
import os
from typing import Any
from uuid import UUID

from cryptography.fernet import Fernet
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...config.security import get_encryption_key
from ...models.integration_config import IntegrationConfig

logger = logging.getLogger(__name__)


class IntegrationConfigService:
    """Service for managing integration configurations with encryption support."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._cipher = Fernet(get_encryption_key())

    def _encrypt_config(self, config_data: dict[str, Any]) -> str:
        """Encrypt configuration data."""
        json_str = json.dumps(config_data)
        encrypted = self._cipher.encrypt(json_str.encode())
        return encrypted.decode()

    def _decrypt_config(self, encrypted_data: str) -> dict[str, Any]:
        """Decrypt configuration data."""
        decrypted = self._cipher.decrypt(encrypted_data.encode())
        return json.loads(decrypted.decode())

    async def create_config(
        self,
        tenant_id: UUID | None,
        integration_type: str,
        provider: str,
        config_data: dict[str, Any],
        is_active: bool = True,
        is_default: bool = False,
        is_platform_config: bool | None = None,
        created_by: UUID | None = None,
    ) -> IntegrationConfig:
        """
        Create a new integration configuration.

        Args:
            tenant_id: Tenant ID (None for platform-wide config)
            integration_type: Type of integration (email, payment, storage, etc.)
            provider: Provider name (smtp, sendgrid, stripe, etc.)
            config_data: Configuration data (will be encrypted)
            is_active: Whether this configuration is active
            is_default: Whether this is the default config for this integration type
            created_by: User who created this configuration

        Returns:
            Created IntegrationConfig instance

        Raises:
            ValueError: If a platform config already exists for this provider
        """
        # For platform configs (tenant_id=None), check if one already exists for this provider
        if tenant_id is None:
            stmt = select(IntegrationConfig).filter(
                IntegrationConfig.tenant_id.is_(None),
                IntegrationConfig.integration_type == integration_type,
                IntegrationConfig.provider == provider,
            )
            result = await self.db.execute(stmt)
            existing_platform_config = result.scalar_one_or_none()

            if existing_platform_config:
                raise ValueError(
                    f"A platform configuration already exists for {provider}. "
                    f"Please update the existing configuration or delete it first."
                )

        # If setting as default, unset other defaults for this tenant/type
        if is_default:
            stmt = select(IntegrationConfig).filter(
                IntegrationConfig.tenant_id == tenant_id,
                IntegrationConfig.integration_type == integration_type,
                IntegrationConfig.is_default,
            )
            result = await self.db.execute(stmt)
            for config in result.scalars().all():
                config.is_default = False

        # Encrypt the configuration data
        encrypted_data = self._encrypt_config(config_data)

        # Determine is_platform_config: use provided value, or infer from tenant_id
        if is_platform_config is None:
            is_platform_config = tenant_id is None

        config = IntegrationConfig(
            tenant_id=tenant_id,
            integration_type=integration_type,
            provider=provider,
            config_data=encrypted_data,
            is_active=is_active,
            is_default=is_default,
            is_platform_config=is_platform_config,
            created_by=created_by,
        )

        self.db.add(config)
        await self.db.commit()
        await self.db.refresh(config)

        return config

    async def get_config(self, config_id: UUID) -> IntegrationConfig | None:
        """Get a configuration by ID."""
        stmt = select(IntegrationConfig).filter(IntegrationConfig.id == config_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_config_data(self, config_id: UUID) -> dict[str, Any] | None:
        """Get decrypted configuration data by ID with provider information."""
        config = await self.get_config(config_id)
        if config:
            config_data = self._decrypt_config(config.config_data)
            # Include provider in the returned data so services know which provider to use
            config_data["provider"] = config.provider
            return config_data
        return None

    async def get_active_config(
        self, tenant_id: UUID | None, integration_type: str, provider: str | None = None
    ) -> IntegrationConfig | None:
        """
        Get the active configuration for a tenant and integration type.
        Falls back to platform config (tenant_id=None) if no tenant-specific config exists.

        Args:
            tenant_id: Tenant ID (None for platform-wide config)
            integration_type: Type of integration
            provider: Optional provider name to filter by

        Returns:
            Active IntegrationConfig or None
        """
        # First, try to get tenant-specific config
        if tenant_id is not None:
            stmt = select(IntegrationConfig).filter(
                IntegrationConfig.tenant_id == tenant_id,
                IntegrationConfig.integration_type == integration_type,
                IntegrationConfig.is_active.is_(True),
            )

            if provider:
                stmt = stmt.filter(IntegrationConfig.provider == provider)

            # Try to get default first
            default_stmt = stmt.filter(IntegrationConfig.is_default)
            result = await self.db.execute(default_stmt)
            config = result.scalar_one_or_none()

            # If no default, get any active config
            if not config:
                result = await self.db.execute(stmt)
                config = result.scalar_one_or_none()

            if config:
                return config

        # Fall back to platform config (tenant_id=None)
        stmt = select(IntegrationConfig).filter(
            IntegrationConfig.tenant_id.is_(None),
            IntegrationConfig.integration_type == integration_type,
            IntegrationConfig.is_active.is_(True),
        )

        if provider:
            stmt = stmt.filter(IntegrationConfig.provider == provider)

        # Try to get default first
        default_stmt = stmt.filter(IntegrationConfig.is_default)
        result = await self.db.execute(default_stmt)
        config = result.scalar_one_or_none()

        # If no default, get any active config
        if not config:
            result = await self.db.execute(stmt)
            config = result.scalar_one_or_none()

        return config

    async def get_active_config_data(
        self, tenant_id: UUID | None, integration_type: str, provider: str | None = None
    ) -> dict[str, Any] | None:
        """Get decrypted active configuration data with provider information."""
        config = await self.get_active_config(tenant_id, integration_type, provider)
        if config:
            config_data = self._decrypt_config(config.config_data)
            # Include provider in the returned data so email service knows which provider to use
            config_data["provider"] = config.provider
            return config_data
        return None

    async def list_configs(
        self,
        tenant_id: UUID | None = None,
        integration_type: str | None = None,
        provider: str | None = None,
        is_active: bool | None = None,
    ) -> list[IntegrationConfig]:
        """
        List integration configurations with optional filters.
        Includes both tenant-specific and platform-wide configs.

        Args:
            tenant_id: Filter by tenant ID (also includes platform configs with tenant_id=None)
            integration_type: Filter by integration type
            provider: Filter by provider
            is_active: Filter by active status

        Returns:
            List of IntegrationConfig instances
        """
        stmt = select(IntegrationConfig)

        if tenant_id is not None:
            # Include both tenant-specific configs AND platform configs (tenant_id=None)
            stmt = stmt.filter(or_(IntegrationConfig.tenant_id == tenant_id, IntegrationConfig.tenant_id.is_(None)))

        if integration_type:
            stmt = stmt.filter(IntegrationConfig.integration_type == integration_type)

        if provider:
            stmt = stmt.filter(IntegrationConfig.provider == provider)

        if is_active is not None:
            stmt = stmt.filter(IntegrationConfig.is_active == is_active)

        stmt = stmt.order_by(IntegrationConfig.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_config(
        self,
        config_id: UUID,
        config_data: dict[str, Any] | None = None,
        is_active: bool | None = None,
        is_default: bool | None = None,
    ) -> IntegrationConfig | None:
        """
        Update an integration configuration.

        Args:
            config_id: Configuration ID
            config_data: New configuration data (will be encrypted)
            is_active: New active status
            is_default: New default status

        Returns:
            Updated IntegrationConfig or None
        """
        config = await self.get_config(config_id)
        if not config:
            return None

        # If setting as default, unset other defaults
        if is_default and not config.is_default:
            stmt = select(IntegrationConfig).filter(
                IntegrationConfig.tenant_id == config.tenant_id,
                IntegrationConfig.integration_type == config.integration_type,
                IntegrationConfig.is_default,
                IntegrationConfig.id != config_id,
            )
            result = await self.db.execute(stmt)
            for other_config in result.scalars().all():
                other_config.is_default = False

        if config_data is not None:
            config.config_data = self._encrypt_config(config_data)

        if is_active is not None:
            config.is_active = is_active

        if is_default is not None:
            config.is_default = is_default

        await self.db.commit()
        await self.db.refresh(config)

        return config

    async def delete_config(self, config_id: UUID) -> bool:
        """
        Delete an integration configuration.

        Args:
            config_id: Configuration ID

        Returns:
            True if deleted, False if not found
        """
        config = await self.get_config(config_id)
        if not config:
            return False

        await self.db.delete(config)
        await self.db.commit()

        return True

    def test_config(self, integration_type: str, provider: str, config_data: dict[str, Any]) -> dict[str, Any]:
        """
        Test an integration configuration without saving it.

        Args:
            integration_type: Type of integration
            provider: Provider name
            config_data: Configuration data to test

        Returns:
            Dict with test results
        """
        # This will be implemented by specific integration services
        # For now, just validate that we can encrypt/decrypt
        try:
            encrypted = self._encrypt_config(config_data)
            self._decrypt_config(encrypted)

            return {
                "success": True,
                "message": "Configuration is valid and can be encrypted/decrypted",
                "provider": provider,
                "integration_type": integration_type,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Configuration test failed: {str(e)}",
                "provider": provider,
                "integration_type": integration_type,
            }

    async def get_app_base_url(self, tenant_id: UUID | None = None) -> str:
        """
        Get the application base URL from integration config.

        The app_base_url should be stored in integration_configs with:
        - integration_type: "platform"
        - provider: "app_config"
        - config_data: {"app_base_url": "https://app.example.com"}

        Args:
            tenant_id: Optional tenant ID for tenant-specific settings

        Returns:
            Base URL string
        """
        try:
            # Get config from integration_configs
            config_data = await self.get_active_config_data(
                tenant_id=tenant_id, integration_type="platform", provider="app_config"
            )

            if config_data and "app_base_url" in config_data:
                return config_data["app_base_url"].rstrip("/")

            env_url = os.getenv("APP_BASE_URL")
            if env_url:
                return env_url.rstrip("/")

            return "/"

        except Exception as e:
            # Log error and return default
            logger.warning(f"Error retrieving app base URL: {e}")
            return os.getenv("APP_BASE_URL", "https://synkora.ai").rstrip("/")
