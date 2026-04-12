"""WidgetAgentRoute model — maps org IDs to agents for per-org routing."""

from sqlalchemy import Column, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.models.base import BaseModel


class WidgetAgentRoute(BaseModel):
    """
    Maps an external org ID to a specific agent for a given widget.

    When a widget has enable_agent_routing=True, incoming chat requests
    with a user.org_id are looked up here to determine which agent to use.
    Falls back to the widget's default agent_id if no route is found.
    """

    __tablename__ = "widget_agent_routes"

    widget_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agent_widgets.id", ondelete="CASCADE"),
        nullable=False,
        comment="Widget this route belongs to",
    )

    external_org_id = Column(
        String(255),
        nullable=False,
        comment="SaaS platform org ID to match on incoming chat requests",
    )

    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        comment="Agent to use for this org (must belong to same tenant as the widget)",
    )

    __table_args__ = (
        UniqueConstraint("widget_id", "external_org_id", name="uq_widget_org_route"),
        Index("ix_widget_agent_routes_lookup", "widget_id", "external_org_id"),
    )

    # Relationships
    widget = relationship("AgentWidget", back_populates="routes")
    agent = relationship("Agent")

    def __repr__(self) -> str:
        return f"<WidgetAgentRoute(widget_id={self.widget_id}, org={self.external_org_id}, agent={self.agent_id})>"
