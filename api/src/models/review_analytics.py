"""Review Analytics model for storing aggregated review metrics."""

from enum import StrEnum

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from src.models.base import BaseModel


class PeriodType(StrEnum):
    """Analytics period types."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class SentimentTrend(StrEnum):
    """Sentiment trend directions."""

    IMPROVING = "improving"
    DECLINING = "declining"
    STABLE = "stable"


class ReviewAnalytics(BaseModel):
    """
    Review Analytics model.

    Stores aggregated analytics for app reviews over specific time periods.
    """

    __tablename__ = "review_analytics"

    # Foreign key
    app_store_source_id = Column(
        UUID(as_uuid=True),
        ForeignKey("app_store_sources.id", ondelete="CASCADE"),
        nullable=False,
        comment="Reference to app store source",
    )

    # Period definition
    period_type = Column(String(50), nullable=False, comment="Period type: daily, weekly, or monthly")

    period_start = Column(DateTime(timezone=True), nullable=False, comment="Period start timestamp")

    period_end = Column(DateTime(timezone=True), nullable=False, comment="Period end timestamp")

    # Basic metrics
    total_reviews = Column(Integer, nullable=False, default=0, comment="Total reviews in this period")

    average_rating = Column(Float, nullable=True, comment="Average rating in this period")

    # Rating distribution
    rating_distribution = Column(
        JSONB, nullable=True, comment="Distribution of ratings (e.g., {'1': 5, '2': 10, '3': 20, '4': 30, '5': 35})"
    )

    # Sentiment analysis
    sentiment_distribution = Column(
        JSONB,
        nullable=True,
        comment="Distribution of sentiments (e.g., {'positive': 60, 'negative': 20, 'neutral': 15, 'mixed': 5})",
    )

    sentiment_trend = Column(String(50), nullable=True, comment="Sentiment trend: improving, declining, or stable")

    # Topic analysis
    top_topics = Column(
        JSONB, nullable=True, comment="Most mentioned topics with counts (e.g., [{'topic': 'ui_ux', 'count': 45}, ...])"
    )

    top_issues = Column(
        JSONB,
        nullable=True,
        comment="Most reported issues with severity (e.g., [{'issue': 'crash', 'count': 12, 'severity': 'high'}, ...])",
    )

    top_features = Column(
        JSONB, nullable=True, comment="Most mentioned features (e.g., [{'feature': 'dark_mode', 'count': 30}, ...])"
    )

    # Trend metrics
    rating_change = Column(Float, nullable=True, comment="Change in average rating from previous period")

    review_volume_change = Column(
        Float, nullable=True, comment="Percentage change in review volume from previous period"
    )

    # Relationships
    source = relationship("AppStoreSource", back_populates="analytics", foreign_keys=[app_store_source_id])

    def __repr__(self) -> str:
        """String representation."""
        return f"<ReviewAnalytics(id={self.id}, period_type='{self.period_type}', total_reviews={self.total_reviews})>"

    def to_dict(self, exclude: set | None = None) -> dict:
        """Convert to dictionary."""
        data = super().to_dict(exclude=exclude)

        # Add computed fields
        data["has_positive_trend"] = self.sentiment_trend == SentimentTrend.IMPROVING.value
        data["has_negative_trend"] = self.sentiment_trend == SentimentTrend.DECLINING.value
        data["rating_improved"] = self.rating_change is not None and self.rating_change > 0
        data["volume_increased"] = self.review_volume_change is not None and self.review_volume_change > 0

        # Format dates
        if self.period_start:
            data["period_start"] = self.period_start.isoformat()
        if self.period_end:
            data["period_end"] = self.period_end.isoformat()

        return data

    @property
    def positive_percentage(self) -> float | None:
        """Calculate percentage of positive reviews."""
        if not self.sentiment_distribution:
            return None

        positive = self.sentiment_distribution.get("positive", 0)
        if self.total_reviews == 0:
            return 0.0

        return (positive / self.total_reviews) * 100

    @property
    def negative_percentage(self) -> float | None:
        """Calculate percentage of negative reviews."""
        if not self.sentiment_distribution:
            return None

        negative = self.sentiment_distribution.get("negative", 0)
        if self.total_reviews == 0:
            return 0.0

        return (negative / self.total_reviews) * 100
