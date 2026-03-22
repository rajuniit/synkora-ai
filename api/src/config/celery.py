"""Celery configuration."""

import os

from celery import Celery
from pydantic import Field, RedisDsn
from pydantic_settings import BaseSettings


class CeleryConfig(BaseSettings):
    """Celery configuration settings."""

    celery_broker_url: RedisDsn = Field(
        ...,
        description="Celery broker URL",
    )

    celery_result_backend: RedisDsn = Field(
        ...,
        description="Celery result backend URL",
    )

    @property
    def celery_broker_url_str(self) -> str:
        """Get Celery broker URL as string."""
        return str(self.celery_broker_url)

    @property
    def celery_result_backend_str(self) -> str:
        """Get Celery result backend URL as string."""
        return str(self.celery_result_backend)


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
