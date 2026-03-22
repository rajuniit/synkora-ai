"""
Document segment model for RAG.

Following Synkora's exact architecture for document segments.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .dataset import Dataset
    from .document import Document


class DocumentSegment(BaseModel):
    """
    Document segment model for storing chunked text.

    Follows Synkora's exact structure - embeddings are stored in external vector databases,
    not in PostgreSQL. This model stores content, metadata, and indexing information.
    """

    __tablename__ = "document_segments"

    # Initial fields
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    dataset_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    document_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Position in document
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    # Segment content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Statistics
    word_count: Mapped[int] = mapped_column(Integer, nullable=False)
    tokens: Mapped[int] = mapped_column(Integer, nullable=False)

    # Indexing fields (for vector database reference)
    keywords: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    index_node_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    index_node_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Basic fields
    hit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disabled_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(String(255), nullable=False, default="waiting")

    # Audit fields
    created_by: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        index=True,
    )
    updated_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
    )
    indexing_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="segments")
    dataset: Mapped["Dataset"] = relationship("Dataset")

    def __repr__(self) -> str:
        """String representation."""
        return f"<DocumentSegment {self.id} (pos: {self.position})>"

    def to_dict(self, _exclude: set[str] | None = None) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "dataset_id": str(self.dataset_id),
            "document_id": str(self.document_id),
            "position": self.position,
            "content": self.content,
            "answer": self.answer,
            "word_count": self.word_count,
            "tokens": self.tokens,
            "keywords": self.keywords,
            "index_node_id": self.index_node_id,
            "index_node_hash": self.index_node_hash,
            "hit_count": self.hit_count,
            "enabled": self.enabled,
            "disabled_at": self.disabled_at.isoformat() if self.disabled_at else None,
            "disabled_by": str(self.disabled_by) if self.disabled_by else None,
            "status": self.status,
            "created_by": str(self.created_by),
            "created_at": self.created_at.isoformat(),
            "updated_by": str(self.updated_by) if self.updated_by else None,
            "updated_at": self.updated_at.isoformat(),
            "indexing_at": self.indexing_at.isoformat() if self.indexing_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "stopped_at": self.stopped_at.isoformat() if self.stopped_at else None,
        }
