"""Chart model for storing chart configurations and data."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from .base import Base


class Chart(Base):
    """Chart model for storing chart configurations."""

    __tablename__ = "charts"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    agent_id = Column(PGUUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)
    conversation_id = Column(PGUUID(as_uuid=True), ForeignKey("conversations.id"), nullable=True)
    message_id = Column(PGUUID(as_uuid=True), ForeignKey("messages.id"), nullable=True)

    # Chart metadata
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    chart_type = Column(String(50), nullable=False)  # bar, line, pie, scatter, etc.
    library = Column(String(50), nullable=False, default="chartjs")  # chartjs, plotly

    # Chart configuration and data
    config = Column(JSON, nullable=False)  # Chart.js or Plotly configuration
    data = Column(JSON, nullable=False)  # Chart data
    query = Column(Text, nullable=True)  # Original query that generated the data

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="charts")
    agent = relationship("Agent", back_populates="charts")
    conversation = relationship("Conversation", back_populates="charts")
    message = relationship("Message", back_populates="charts")

    def to_dict(self):
        """Convert chart to dictionary."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "agent_id": str(self.agent_id) if self.agent_id else None,
            "conversation_id": str(self.conversation_id) if self.conversation_id else None,
            "message_id": str(self.message_id) if self.message_id else None,
            "title": self.title,
            "description": self.description,
            "chart_type": self.chart_type,
            "library": self.library,
            "config": self.config,
            "data": self.data,
            "query": self.query,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
