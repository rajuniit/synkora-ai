"""App Store review connectors."""

from typing import Dict, Type

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.app_store_source import AppStoreSource, StoreType
from src.services.app_store.apple_app_store_connector import AppleAppStoreConnector
from src.services.app_store.google_play_connector import GooglePlayConnector
from src.services.app_store.review_analysis_service import ReviewAnalysisService
from src.services.app_store.review_sync_service import ReviewSyncService

# Connector registry
CONNECTOR_REGISTRY: dict[StoreType, type] = {
    StoreType.GOOGLE_PLAY: GooglePlayConnector,
    StoreType.APPLE_APP_STORE: AppleAppStoreConnector,
}


def get_connector(app_store_source: AppStoreSource, db: AsyncSession):
    """
    Get the appropriate connector for an app store source.

    Args:
        app_store_source: AppStoreSource model instance
        db: Database session

    Returns:
        Connector instance (GooglePlayConnector or AppleAppStoreConnector)

    Raises:
        ValueError: If store type is not supported
    """
    connector_class = CONNECTOR_REGISTRY.get(app_store_source.store_type)

    if not connector_class:
        raise ValueError(f"Unsupported store type: {app_store_source.store_type}")

    return connector_class(app_store_source, db)


__all__ = [
    "GooglePlayConnector",
    "AppleAppStoreConnector",
    "ReviewSyncService",
    "ReviewAnalysisService",
    "get_connector",
    "CONNECTOR_REGISTRY",
]
