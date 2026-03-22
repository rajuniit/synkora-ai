"""App Review model for storing individual app reviews."""

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from src.models.base import BaseModel


class ReviewSentiment(StrEnum):
    """Review sentiment categories."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class AppReview(BaseModel):
    """
    App Review model.

    Stores individual app reviews with metadata and analysis results.
    """

    __tablename__ = "app_reviews"

    # Foreign key
    app_store_source_id = Column(
        UUID(as_uuid=True),
        ForeignKey("app_store_sources.id", ondelete="CASCADE"),
        nullable=False,
        comment="Reference to app store source",
    )

    # Review identification
    review_id = Column(String(255), nullable=False, comment="Store-specific review ID")

    author_name = Column(String(255), nullable=True, comment="Review author name")

    # Review content
    rating = Column(Integer, nullable=False, comment="Rating from 1-5 stars")

    title = Column(Text, nullable=True, comment="Review title")

    content = Column(Text, nullable=False, comment="Review content/text")

    # Metadata
    language = Column(String(10), nullable=True, comment="Review language code (e.g., 'en', 'es')")

    country = Column(String(10), nullable=True, comment="Country code (e.g., 'US', 'GB')")

    app_version = Column(String(50), nullable=True, comment="App version being reviewed")

    device_type = Column(String(100), nullable=True, comment="Device type used (e.g., 'iPhone 12', 'Pixel 5')")

    review_date = Column(DateTime(timezone=True), nullable=False, comment="When the review was posted")

    thumbs_up_count = Column(Integer, nullable=True, default=0, comment="Number of thumbs up/helpful votes")

    # Analysis results
    sentiment = Column(String(50), nullable=True, comment="Sentiment: positive, negative, neutral, or mixed")

    sentiment_score = Column(Float, nullable=True, comment="Sentiment score from -1 (negative) to 1 (positive)")

    topics = Column(JSONB, nullable=True, comment="Extracted topics (e.g., ['ui_ux', 'performance'])")

    issues = Column(JSONB, nullable=True, comment="Identified issues with severity levels")

    features_mentioned = Column(JSONB, nullable=True, comment="Features mentioned in the review")

    # Developer response
    has_response = Column(Boolean, nullable=False, default=False, comment="Whether developer responded to review")

    response_text = Column(Text, nullable=True, comment="Developer response text")

    response_date = Column(DateTime(timezone=True), nullable=True, comment="When developer responded")

    # Relationships
    source = relationship("AppStoreSource", back_populates="reviews", foreign_keys=[app_store_source_id])

    def __repr__(self) -> str:
        """String representation."""
        return f"<AppReview(id={self.id}, rating={self.rating}, sentiment='{self.sentiment}')>"

    def to_dict(self, exclude: set | None = None) -> dict:
        """Convert to dictionary."""
        data = super().to_dict(exclude=exclude)

        # Add computed fields
        data["is_positive"] = self.rating >= 4
        data["is_negative"] = self.rating <= 2
        data["has_developer_response"] = self.has_response

        # Format dates
        if self.review_date:
            data["review_date"] = self.review_date.isoformat()
        if self.response_date:
            data["response_date"] = self.response_date.isoformat()

        return data

    @property
    def is_recent(self) -> bool:
        """Check if review is recent (within last 30 days)."""
        if not self.review_date:
            return False
        days_old = (datetime.now(UTC) - self.review_date).days
        return days_old <= 30

    @property
    def needs_response(self) -> bool:
        """Check if review needs a developer response."""
        return not self.has_response and self.rating <= 3 and self.is_recent
