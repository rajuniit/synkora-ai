"""
Voice API Key Model

Database model for storing encrypted voice provider API keys.
"""

import enum

from sqlalchemy import Boolean, Column, String, Text

from src.models.base import BaseModel, TenantMixin


class VoiceProvider(enum.StrEnum):
    """Voice provider types."""

    OPENAI_WHISPER = "openai_whisper"
    OPENAI_TTS = "openai_tts"
    ELEVENLABS = "elevenlabs"


class VoiceApiKey(BaseModel, TenantMixin):
    """
    Voice API Key model for storing encrypted API keys for voice providers.

    Attributes:
        tenant_id: Tenant identifier for multi-tenancy
        provider: Voice provider name (openai_whisper, openai_tts, elevenlabs)
        api_key_encrypted: Encrypted API key
        is_active: Whether the API key is currently active
    """

    __tablename__ = "voice_api_keys"

    provider = Column(String(50), nullable=False, comment="Voice provider (openai_whisper, openai_tts, elevenlabs)")

    api_key_encrypted = Column(Text, nullable=False, comment="Encrypted API key")

    is_active = Column(Boolean, nullable=False, default=True, comment="Whether the API key is active")

    def __repr__(self) -> str:
        return f"<VoiceApiKey(id={self.id}, provider='{self.provider}', is_active={self.is_active})>"

    def to_dict(self, exclude: set[str] | None = None) -> dict:
        exclude = exclude or set()
        exclude.add("api_key_encrypted")
        return super().to_dict(exclude=exclude)
