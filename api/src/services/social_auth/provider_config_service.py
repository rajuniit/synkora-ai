"""
Social Auth Provider Configuration Service.

Manages CRUD operations for social login provider configurations at the tenant level.
"""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.social_auth_provider import SocialAuthProvider
from src.services.agents.security import decrypt_value, encrypt_value

logger = logging.getLogger(__name__)


class SocialAuthProviderConfigService:
    """Service for managing social auth provider configurations."""

    SUPPORTED_PROVIDERS = ["google", "microsoft", "apple"]

    def __init__(self, db: AsyncSession):
        """Initialize the service.

        Args:
            db: Async database session
        """
        self.db = db

    async def list_providers(self, tenant_id: UUID) -> list[dict]:
        """List all social auth providers for a tenant.

        Args:
            tenant_id: Tenant ID

        Returns:
            List of provider dictionaries
        """
        try:
            stmt = (
                select(SocialAuthProvider)
                .where(SocialAuthProvider.tenant_id == tenant_id)
                .order_by(SocialAuthProvider.provider_name)
            )

            result = await self.db.execute(stmt)
            providers = result.scalars().all()

            return [
                {
                    "id": str(provider.id),
                    "provider_name": provider.provider_name,
                    "client_id": provider.client_id,
                    "client_secret": self._mask_secret(provider.client_secret),
                    "redirect_uri": provider.redirect_uri,
                    "config": provider.config,
                    "enabled": provider.enabled,
                    "created_at": provider.created_at.isoformat() if provider.created_at else None,
                    "updated_at": provider.updated_at.isoformat() if provider.updated_at else None,
                }
                for provider in providers
            ]
        except Exception as e:
            logger.error(f"Error listing providers for tenant {tenant_id}: {e}")
            raise

    async def get_provider(self, tenant_id: UUID, provider_name: str, decrypt_secret: bool = False) -> dict | None:
        """Get a specific provider configuration.

        Args:
            tenant_id: Tenant ID
            provider_name: Provider name (google, microsoft, apple)
            decrypt_secret: Whether to decrypt the client secret

        Returns:
            Provider configuration or None if not found
        """
        try:
            stmt = select(SocialAuthProvider).where(
                SocialAuthProvider.tenant_id == tenant_id, SocialAuthProvider.provider_name == provider_name
            )

            result = await self.db.execute(stmt)
            provider = result.scalar_one_or_none()

            if not provider:
                return None

            client_secret = provider.client_secret
            if decrypt_secret and client_secret:
                try:
                    client_secret = decrypt_value(client_secret)
                except Exception as e:
                    logger.error(f"Error decrypting client secret: {e}")
                    client_secret = None
            else:
                client_secret = self._mask_secret(client_secret)

            return {
                "id": str(provider.id),
                "provider_name": provider.provider_name,
                "client_id": provider.client_id,
                "client_secret": client_secret,
                "redirect_uri": provider.redirect_uri,
                "config": provider.config,
                "enabled": provider.enabled,
                "created_at": provider.created_at.isoformat() if provider.created_at else None,
                "updated_at": provider.updated_at.isoformat() if provider.updated_at else None,
            }
        except Exception as e:
            logger.error(f"Error getting provider {provider_name} for tenant {tenant_id}: {e}")
            raise

    async def create_provider(
        self,
        tenant_id: UUID,
        provider_name: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        config: dict | None = None,
        enabled: str = "true",
    ) -> dict:
        """Create a new provider configuration.

        Args:
            tenant_id: Tenant ID
            provider_name: Provider name (google, microsoft, apple)
            client_id: OAuth client ID
            client_secret: OAuth client secret (will be encrypted)
            redirect_uri: OAuth redirect URI
            config: Additional configuration (JSON)
            enabled: Whether the provider is enabled

        Returns:
            Created provider configuration

        Raises:
            ValueError: If provider name is not supported or already exists
        """
        if provider_name not in self.SUPPORTED_PROVIDERS:
            raise ValueError(
                f"Unsupported provider: {provider_name}. Supported providers: {', '.join(self.SUPPORTED_PROVIDERS)}"
            )

        try:
            # Check if provider already exists
            stmt = select(SocialAuthProvider).where(
                SocialAuthProvider.tenant_id == tenant_id, SocialAuthProvider.provider_name == provider_name
            )
            result = await self.db.execute(stmt)
            if result.scalar_one_or_none():
                raise ValueError(f"Provider {provider_name} already exists for this tenant")

            # Encrypt client secret
            encrypted_secret = encrypt_value(client_secret)

            # Create provider
            provider = SocialAuthProvider(
                tenant_id=tenant_id,
                provider_name=provider_name,
                client_id=client_id,
                client_secret=encrypted_secret,
                redirect_uri=redirect_uri,
                config=config,
                enabled=enabled,
            )

            self.db.add(provider)
            await self.db.commit()
            await self.db.refresh(provider)

            logger.info(f"Created provider {provider_name} for tenant {tenant_id}")

            return {
                "id": str(provider.id),
                "provider_name": provider.provider_name,
                "client_id": provider.client_id,
                "client_secret": self._mask_secret(provider.client_secret),
                "redirect_uri": provider.redirect_uri,
                "config": provider.config,
                "enabled": provider.enabled,
                "created_at": provider.created_at.isoformat() if provider.created_at else None,
                "updated_at": provider.updated_at.isoformat() if provider.updated_at else None,
            }
        except ValueError:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating provider {provider_name} for tenant {tenant_id}: {e}")
            raise

    async def update_provider(
        self,
        tenant_id: UUID,
        provider_name: str,
        client_id: str | None = None,
        client_secret: str | None = None,
        redirect_uri: str | None = None,
        config: dict | None = None,
        enabled: str | None = None,
    ) -> dict:
        """Update an existing provider configuration.

        Args:
            tenant_id: Tenant ID
            provider_name: Provider name (google, microsoft, apple)
            client_id: OAuth client ID (optional)
            client_secret: OAuth client secret (optional, will be encrypted)
            redirect_uri: OAuth redirect URI (optional)
            config: Additional configuration (optional)
            enabled: Whether the provider is enabled (optional)

        Returns:
            Updated provider configuration

        Raises:
            ValueError: If provider not found
        """
        try:
            stmt = select(SocialAuthProvider).where(
                SocialAuthProvider.tenant_id == tenant_id, SocialAuthProvider.provider_name == provider_name
            )
            result = await self.db.execute(stmt)
            provider = result.scalar_one_or_none()

            if not provider:
                raise ValueError(f"Provider {provider_name} not found for tenant {tenant_id}")

            # Update fields if provided
            if client_id is not None:
                provider.client_id = client_id
            if client_secret is not None:
                provider.client_secret = encrypt_value(client_secret)
            if redirect_uri is not None:
                provider.redirect_uri = redirect_uri
            if config is not None:
                provider.config = config
            if enabled is not None:
                provider.enabled = enabled

            await self.db.commit()
            await self.db.refresh(provider)

            logger.info(f"Updated provider {provider_name} for tenant {tenant_id}")

            return {
                "id": str(provider.id),
                "provider_name": provider.provider_name,
                "client_id": provider.client_id,
                "client_secret": self._mask_secret(provider.client_secret),
                "redirect_uri": provider.redirect_uri,
                "config": provider.config,
                "enabled": provider.enabled,
                "created_at": provider.created_at.isoformat() if provider.created_at else None,
                "updated_at": provider.updated_at.isoformat() if provider.updated_at else None,
            }
        except ValueError:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating provider {provider_name} for tenant {tenant_id}: {e}")
            raise

    async def delete_provider(self, tenant_id: UUID, provider_name: str) -> bool:
        """Delete a provider configuration.

        Args:
            tenant_id: Tenant ID
            provider_name: Provider name (google, microsoft, apple)

        Returns:
            True if deleted, False if not found
        """
        try:
            stmt = select(SocialAuthProvider).where(
                SocialAuthProvider.tenant_id == tenant_id, SocialAuthProvider.provider_name == provider_name
            )
            result = await self.db.execute(stmt)
            provider = result.scalar_one_or_none()

            if not provider:
                return False

            await self.db.delete(provider)
            await self.db.commit()

            logger.info(f"Deleted provider {provider_name} for tenant {tenant_id}")

            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting provider {provider_name} for tenant {tenant_id}: {e}")
            raise

    async def test_provider(self, tenant_id: UUID, provider_name: str) -> dict:
        """Test a provider configuration by validating credentials.

        Args:
            tenant_id: Tenant ID
            provider_name: Provider name (google, microsoft, apple)

        Returns:
            Test result with status and message
        """
        try:
            provider_config = await self.get_provider(tenant_id, provider_name, decrypt_secret=True)

            if not provider_config:
                return {"success": False, "message": f"Provider {provider_name} not found"}

            if provider_config["enabled"] != "true":
                return {"success": False, "message": f"Provider {provider_name} is disabled"}

            # Basic validation
            if not provider_config["client_id"]:
                return {"success": False, "message": "Client ID is missing"}

            if not provider_config["client_secret"]:
                return {"success": False, "message": "Client Secret is missing"}

            if not provider_config["redirect_uri"]:
                return {"success": False, "message": "Redirect URI is missing"}

            # Full OAuth validation would require making a test request
            # For now, validating that all required fields are present

            return {"success": True, "message": f"Provider {provider_name} configuration is valid"}
        except Exception as e:
            logger.error(f"Error testing provider {provider_name} for tenant {tenant_id}: {e}")
            return {"success": False, "message": f"Error testing provider: {str(e)}"}

    @staticmethod
    def _mask_secret(secret: str, visible_chars: int = 4) -> str:
        """Mask a secret for display purposes.

        Args:
            secret: Secret to mask
            visible_chars: Number of characters to show at the end

        Returns:
            Masked secret
        """
        if not secret:
            return ""

        if len(secret) <= visible_chars:
            return "*" * len(secret)

        return f"{'*' * (len(secret) - visible_chars)}{secret[-visible_chars:]}"
