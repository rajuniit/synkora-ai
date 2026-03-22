"""App Store Source model for managing app review sources."""

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from src.models.base import BaseModel, TenantMixin


class StoreType(StrEnum):
    """App store types."""

    GOOGLE_PLAY = "google_play"
    APPLE_APP_STORE = "apple_app_store"


class SyncFrequency(StrEnum):
    """Sync frequency options."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class SourceStatus(StrEnum):
    """App store source status."""

    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"


class AppStoreSource(BaseModel, TenantMixin):
    """
    App Store Source model.

    Represents a configured app store source for collecting reviews.
    Links to a knowledge base for storing and analyzing reviews.
    """

    __tablename__ = "app_store_sources"

    # Foreign keys
    knowledge_base_id = Column(
        Integer,
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=True,
        comment="Optional knowledge base for storing reviews",
    )

    # App identification
    store_type = Column(String(50), nullable=False, comment="google_play or apple_app_store")

    app_id = Column(String(255), nullable=False, comment="Package name (Google Play) or App ID (Apple)")

    app_name = Column(String(255), nullable=False, comment="Human-readable app name")

    # Sync configuration
    sync_frequency = Column(
        String(50),
        nullable=False,
        default=SyncFrequency.DAILY.value,
        comment="Sync frequency: daily, weekly, or monthly",
    )

    last_sync_at = Column(DateTime(timezone=True), nullable=True, comment="Last successful sync timestamp")

    next_sync_at = Column(DateTime(timezone=True), nullable=True, comment="Next scheduled sync timestamp")

    # Filter configuration
    min_rating = Column(Integer, nullable=True, comment="Filter reviews by minimum rating (1-5)")

    languages = Column(JSONB, nullable=True, comment="List of languages to collect (e.g., ['en', 'es'])")

    countries = Column(JSONB, nullable=True, comment="List of countries to collect from (e.g., ['US', 'GB'])")

    # Status and metrics
    status = Column(
        String(50), nullable=False, default=SourceStatus.ACTIVE.value, comment="Source status: active, paused, or error"
    )

    total_reviews_collected = Column(Integer, nullable=False, default=0, comment="Total number of reviews collected")

    # Additional configuration
    config = Column(JSONB, nullable=True, comment="Additional configuration options")

    last_error = Column(Text, nullable=True, comment="Last error message if any")

    # Relationships
    knowledge_base = relationship("KnowledgeBase", back_populates="app_store_sources", foreign_keys=[knowledge_base_id])

    reviews = relationship("AppReview", back_populates="source", cascade="all, delete-orphan")

    analytics = relationship("ReviewAnalytics", back_populates="source", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        """String representation."""
        return f"<AppStoreSource(id={self.id}, app_name='{self.app_name}', store_type='{self.store_type}')>"

    def to_dict(self, exclude: set | None = None) -> dict:
        """Convert to dictionary."""
        data = super().to_dict(exclude=exclude)

        # Add computed fields
        data["is_active"] = self.status == SourceStatus.ACTIVE.value
        data["needs_sync"] = self.next_sync_at is not None and self.next_sync_at <= datetime.now(UTC)

        return data
