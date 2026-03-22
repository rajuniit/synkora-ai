"""
Voice Usage Model

Database model for tracking voice provider usage and costs.
"""

import enum

from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID

from src.models.base import BaseModel, TenantMixin


class VoiceProvider(enum.StrEnum):
    """Voice provider types."""

    OPENAI_WHISPER = "openai_whisper"
    OPENAI_TTS = "openai_tts"
    ELEVENLABS = "elevenlabs"


class OperationType(enum.StrEnum):
    """Voice operation types."""

    STT = "stt"  # Speech-to-text
    TTS = "tts"  # Text-to-speech


class VoiceUsage(BaseModel, TenantMixin):
    """
    Voice Usage model for tracking voice provider usage and costs.

    Attributes:
        tenant_id: Tenant identifier for multi-tenancy
        agent_id: Agent that used the voice service
        conversation_id: Conversation where voice was used (optional)
        provider: Voice provider used
        operation_type: Type of operation (stt, tts)
        input_length: Input length (audio duration in seconds for STT, text length for TTS)
        output_length: Output length (text length for STT, audio duration for TTS)
        cost: Estimated cost in USD
    """

    __tablename__ = "voice_usage"

    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        comment="Agent that used the voice service",
    )

    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=True,
        comment="Conversation where voice was used",
    )

    provider = Column(String(50), nullable=False, comment="Voice provider used")

    operation_type = Column(String(20), nullable=False, comment="Operation type (stt, tts)")

    input_length = Column(
        Integer, nullable=True, comment="Input length (audio duration in seconds for STT, text length for TTS)"
    )

    output_length = Column(
        Integer, nullable=True, comment="Output length (text length for STT, audio duration for TTS)"
    )

    cost = Column(Float, nullable=True, comment="Estimated cost in USD")

    def __repr__(self) -> str:
        """String representation of voice usage."""
        return f"<VoiceUsage(id={self.id}, provider='{self.provider}', operation='{self.operation_type}', cost={self.cost})>"
