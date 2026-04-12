"""
Configuration Helper Utilities

Centralized utilities for retrieving configuration values across the application.
"""

import logging
import os
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..services.integrations.integration_config_service import IntegrationConfigService

logger = logging.getLogger(__name__)


async def get_app_base_url(db: AsyncSession, tenant_id: UUID | None = None) -> str:
    """
    Get the application base URL for use in redirects, emails, etc.

    This is a convenience wrapper around IntegrationConfigService.get_app_base_url()
    that can be easily imported and used throughout the application.

    The base URL is retrieved from integration_configs with:
    - integration_type: "platform"
    - provider: "app_config"
    - config_data: {"app_base_url": "https://app.example.com"}

    Args:
        db: Async database session
        tenant_id: Optional tenant ID for tenant-specific settings

    Returns:
        Base URL string (without trailing slash)

    Example:
        ```python
        from src.utils.config_helper import get_app_base_url

        # In your endpoint/function
        base_url = await get_app_base_url(db, tenant_id)
        redirect_url = f"{base_url}/oauth/callback"
        ```
    """
    try:
        config_service = IntegrationConfigService(db)
        return await config_service.get_app_base_url(tenant_id)
    except Exception as e:
        logger.warning(f"Error getting app base URL: {e}")
        return os.getenv("APP_BASE_URL", "https://synkora.ai").rstrip("/")
