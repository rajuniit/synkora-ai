"""Agent version snapshot for rollback and audit history."""

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import BaseModel


class AgentVersion(BaseModel):
    __tablename__ = "agent_versions"

    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
    )

    version_number = Column(Integer, nullable=False)  # auto-incremented per agent
    change_description = Column(String(500), nullable=True)  # optional commit message

    # Snapshot of agent configuration at this point in time
    # Store exactly what changed — full snapshot of mutable fields
    snapshot = Column(JSONB, nullable=False)
    # Which fields changed from previous version
    changed_fields = Column(JSONB, nullable=True)

    agent = relationship("Agent", foreign_keys=[agent_id])
    created_by_account = relationship("Account", foreign_keys=[created_by])
