"""
Knowledge Base Brain models.

These extend every KnowledgeBase with auto-sync cursor state,
canonical entity resolution, and a knowledge graph — the same
infrastructure the "Company Brain" concept needed, but scoped
to an existing KnowledgeBase instead of a parallel concept.

Tables:
  kb_sync_cursors       — per DataSource incremental sync cursor
  kb_entities           — canonical cross-source entities (person/project/repo/team)
  kb_relationships      — typed edges between entities or entity+document
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel, TimestampMixin


class KBSyncCursor(BaseModel, TimestampMixin):
    """
    Persistent incremental sync cursor for each DataSource feeding a KnowledgeBase.

    Stores the opaque cursor value returned by the upstream API so that
    incremental syncs resume exactly where they left off.
    """

    __tablename__ = "kb_sync_cursors"
    __table_args__ = (UniqueConstraint("data_source_id", "cursor_type", name="uq_kb_cursor_source_type"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    knowledge_base_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    data_source_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # "since_ts" | "page_token" | "event_id" | "checkpoint"
    cursor_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # Opaque value — connector-specific (ISO timestamp, token, integer offset…)
    cursor_value: Mapped[str] = mapped_column(Text, nullable=False)
    docs_seen: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    tenant: Mapped["Tenant"] = relationship("Tenant")
    knowledge_base: Mapped["KnowledgeBase"] = relationship("KnowledgeBase")
    data_source: Mapped["DataSource"] = relationship("DataSource")

    def __repr__(self) -> str:
        return f"<KBSyncCursor(kb={self.knowledge_base_id}, ds={self.data_source_id}, type={self.cursor_type})>"


class KBEntity(BaseModel, TimestampMixin):
    """
    Canonical entity resolved across multiple data sources within a KnowledgeBase.

    The same person can appear across Slack, GitHub, Jira, Linear, etc.
    This table holds one canonical row per person/project/repo/team,
    keyed by (knowledge_base_id, email) or (knowledge_base_id, type, name).
    """

    __tablename__ = "kb_entities"
    __table_args__ = (UniqueConstraint("knowledge_base_id", "email", name="uq_kb_entity_kb_email"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    knowledge_base_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # "person" | "project" | "repo" | "team" | "channel"
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Primary dedup key for person entities; nullable for non-person
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    # {"slack_user_id": "U012AB3CD", "github_login": "alice-dev", "jira_account_id": "5b109..."}
    identifiers: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    display_names: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    tenant: Mapped["Tenant"] = relationship("Tenant")
    knowledge_base: Mapped["KnowledgeBase"] = relationship("KnowledgeBase")
    source_relationships: Mapped[list["KBRelationship"]] = relationship(
        "KBRelationship",
        foreign_keys="KBRelationship.source_entity_id",
        back_populates="source_entity",
        cascade="all, delete-orphan",
    )
    target_relationships: Mapped[list["KBRelationship"]] = relationship(
        "KBRelationship",
        foreign_keys="KBRelationship.target_entity_id",
        back_populates="target_entity",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<KBEntity(kb={self.knowledge_base_id}, type={self.entity_type}, name={self.canonical_name})>"


class KBRelationship(BaseModel, TimestampMixin):
    """
    Typed directional edge in the knowledge graph for a KnowledgeBase.

    Examples:
      alice --authored--> PR #847          (entity → document)
      alice --assigned_to--> ticket BE-234 (entity → document)
    """

    __tablename__ = "kb_relationships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    knowledge_base_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_entity_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("kb_entities.id", ondelete="CASCADE"), nullable=True, index=True
    )
    target_entity_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("kb_entities.id", ondelete="CASCADE"), nullable=True, index=True
    )
    source_doc_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("data_source_documents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # "authored" | "assigned_to" | "mentioned_in" | "resolved_by" | "reviewed" | "commented_on"
    relation_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    rel_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tenant: Mapped["Tenant"] = relationship("Tenant")
    knowledge_base: Mapped["KnowledgeBase"] = relationship("KnowledgeBase")
    source_entity: Mapped[Optional["KBEntity"]] = relationship(
        "KBEntity", foreign_keys=[source_entity_id], back_populates="source_relationships"
    )
    target_entity: Mapped[Optional["KBEntity"]] = relationship(
        "KBEntity", foreign_keys=[target_entity_id], back_populates="target_relationships"
    )

    def __repr__(self) -> str:
        return f"<KBRelationship(kb={self.knowledge_base_id}, rel={self.relation_type})>"
