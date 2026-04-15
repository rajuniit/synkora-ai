"""Diagram model for storing generated diagram specs and assets."""

from sqlalchemy import JSON, Column, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from .base import BaseModel


class Diagram(BaseModel):
    """Diagram model for storing generated technical diagrams."""

    __tablename__ = "diagrams"

    tenant_id = Column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    agent_id = Column(PGUUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)
    conversation_id = Column(PGUUID(as_uuid=True), ForeignKey("conversations.id"), nullable=True)
    message_id = Column(PGUUID(as_uuid=True), ForeignKey("messages.id"), nullable=True)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    diagram_type = Column(String(50), nullable=False)  # architecture, flowchart, sequence, etc.
    style = Column(Integer, nullable=True)  # 1-7
    spec = Column(JSON, nullable=False)  # Full JSON spec
    svg_key = Column(String(500), nullable=True)  # S3 object key
    png_key = Column(String(500), nullable=True)  # S3 object key

    def to_dict(self):
        """Convert diagram to dictionary."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "agent_id": str(self.agent_id) if self.agent_id else None,
            "conversation_id": str(self.conversation_id) if self.conversation_id else None,
            "message_id": str(self.message_id) if self.message_id else None,
            "title": self.title,
            "description": self.description,
            "diagram_type": self.diagram_type,
            "style": self.style,
            "spec": self.spec,
            "svg_key": self.svg_key,
            "png_key": self.png_key,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
