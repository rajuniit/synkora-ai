"""
Writing Style Profile model.

Stores analyzed writing style characteristics for individuals.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.core.database import Base


class WritingStyleProfile(Base):
    """
    Writing style profile for a person.

    Stores analyzed characteristics of a person's writing style
    including tone, vocabulary, sentence structure, and communication patterns.
    """

    __tablename__ = "writing_style_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

    # Person identification
    person_identifier = Column(String, nullable=False)  # email or user_id
    person_name = Column(String)
    person_role = Column(String)

    # Style characteristics (JSON)
    tone_characteristics = Column(
        JSON, default=dict
    )  # {formal_score, professional_score, friendly_score, enthusiasm_level}
    vocabulary_patterns = Column(
        JSON, default=dict
    )  # {common_phrases, technical_terms, jargon, greeting_patterns, closing_patterns}
    sentence_metrics = Column(
        JSON, default=dict
    )  # {avg_length, complexity_score, paragraph_style, bullet_point_usage, question_frequency}
    communication_patterns = Column(
        JSON, default=dict
    )  # {email_subject_style, opening_style, closing_style, emoji_usage, signature_style}

    # Metadata
    sample_count = Column(Integer, default=0)
    confidence_score = Column(Float, default=0.0)  # 0-1, based on sample count and consistency
    last_analyzed_at = Column(DateTime)

    # Note: Embeddings are stored in the vector database (Qdrant/Pinecone/etc.)
    # not in PostgreSQL. Use the embedding service to generate and store embeddings.

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    drafts = relationship("GhostwriterDraft", back_populates="style_profile")

    # Indexes
    __table_args__ = (
        Index("idx_writing_style_tenant_person", "tenant_id", "person_identifier"),
        Index("idx_writing_style_tenant", "tenant_id"),
        Index("idx_writing_style_person", "person_identifier"),
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<WritingStyleProfile "
            f"id={self.id} "
            f"person={self.person_identifier} "
            f"samples={self.sample_count} "
            f"confidence={self.confidence_score:.2f}>"
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "person_identifier": self.person_identifier,
            "person_name": self.person_name,
            "person_role": self.person_role,
            "tone_characteristics": self.tone_characteristics,
            "vocabulary_patterns": self.vocabulary_patterns,
            "sentence_metrics": self.sentence_metrics,
            "communication_patterns": self.communication_patterns,
            "sample_count": self.sample_count,
            "confidence_score": self.confidence_score,
            "last_analyzed_at": self.last_analyzed_at.isoformat() if self.last_analyzed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
