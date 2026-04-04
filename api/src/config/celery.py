"""Celery configuration."""

import os

from celery import Celery
from pydantic import Field
from pydantic_settings import BaseSettings


class CeleryConfig(BaseSettings):
    """Celery configuration settings."""

    # str instead of RedisDsn so sentinel:// URLs are accepted alongside redis://
    celery_broker_url: str = Field(
        ...,
        description="Celery broker URL (redis://, rediss://, or sentinel://)",
    )

    celery_result_backend: str = Field(
        ...,
        description="Celery result backend URL (redis://, rediss://, or sentinel://)",
    )

    @property
    def celery_broker_url_str(self) -> str:
        """Get Celery broker URL as string."""
        return self.celery_broker_url

    @property
    def celery_result_backend_str(self) -> str:
        """Get Celery result backend URL as string."""
        return self.celery_result_backend


# Get broker/backend URLs from environment (K8s compatible)
# Falls back to localhost for local development only
_broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
_backend_url = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# Create Celery app instance with environment-based configuration
celery_app = Celery(
    "synkora",
    broker=_broker_url,
    backend=_backend_url,
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
)

# Sentinel requires master_name transport option — safe to set for all sentinel:// URLs.
# For redis:// or rediss:// URLs this block is skipped entirely.
if _broker_url.startswith("sentinel://"):
    _sentinel_master = os.getenv("REDIS_SENTINEL_MASTER", "mymaster")
    celery_app.conf.update(
        broker_transport_options={"master_name": _sentinel_master},
        result_backend_transport_options={"master_name": _sentinel_master},
    )
