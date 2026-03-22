"""
Agent API Usage model for tracking API key usage and analytics.

This module defines the database model for tracking usage statistics
of agent API keys for analytics, billing, and rate limiting.
"""

from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from src.models.base import BaseModel

if TYPE_CHECKING:
    pass


class AgentApiUsage(BaseModel):
    """
    Agent API Usage model for tracking API key usage.

    Attributes:
        api_key_id: UUID of the API key used
        endpoint: API endpoint that was called
        method: HTTP method (GET, POST, etc.)
        status_code: HTTP response status code
        response_time_ms: Response time in milliseconds
        tokens_used: Number of tokens consumed (if applicable)
        ip_address: IP address of the requester
        user_agent: User agent string of the requester
        request_metadata: Additional request metadata (headers, params, etc.)
        error_message: Error message if request failed
    """

    __tablename__ = "agent_api_usages"

    api_key_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agent_api_keys.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="API key that was used",
    )

    endpoint = Column(
        String(255),
        nullable=False,
        index=True,
        comment="API endpoint that was called (e.g., /api/v1/agents/{id}/chat)",
    )

    method = Column(
        String(10),
        nullable=False,
        comment="HTTP method (GET, POST, PUT, DELETE, etc.)",
    )

    status_code = Column(
        Integer,
        nullable=False,
        index=True,
        comment="HTTP response status code",
    )

    response_time_ms = Column(
        Integer,
        nullable=True,
        comment="Response time in milliseconds",
    )

    tokens_used = Column(
        Integer,
        nullable=True,
        comment="Number of tokens consumed (for LLM calls)",
    )

    ip_address = Column(
        String(45),  # IPv6 max length
        nullable=True,
        index=True,
        comment="IP address of the requester",
    )

    user_agent = Column(
        Text,
        nullable=True,
        comment="User agent string of the requester",
    )

    request_metadata = Column(
        JSONB,
        nullable=True,
        comment="Additional request metadata (headers, query params, body size, etc.)",
    )

    error_message = Column(
        Text,
        nullable=True,
        comment="Error message if request failed",
    )

    # Relationships
    api_key = relationship("AgentApiKey", back_populates="usage_records")

    @property
    def is_success(self) -> bool:
        """Check if the request was successful (2xx status code)."""
        return 200 <= self.status_code < 300

    @property
    def is_error(self) -> bool:
        """Check if the request resulted in an error (4xx or 5xx status code)."""
        return self.status_code >= 400

    def to_dict(self, exclude: set[str] | None = None) -> dict:
        """
        Convert model instance to dictionary.

        Args:
            exclude: Set of field names to exclude from output

        Returns:
            dict: Model data as dictionary
        """
        data = super().to_dict(exclude=exclude)

        # Ensure request_metadata is a dict
        if data.get("request_metadata") is None:
            data["request_metadata"] = {}

        # Add computed properties
        data["is_success"] = self.is_success
        data["is_error"] = self.is_error

        return data

    def __repr__(self) -> str:
        """String representation of model instance."""
        return f"<AgentApiUsage(id={self.id}, endpoint={self.endpoint}, status={self.status_code})>"
