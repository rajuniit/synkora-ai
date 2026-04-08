"""
Voice service orchestrator for managing STT and TTS providers.
"""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.voice_api_key import VoiceApiKey, VoiceProvider
from src.models.voice_usage import OperationType, VoiceUsage
from src.services.agents.security import decrypt_value

from .base_provider import BaseSTTProvider, BaseTTSProvider
from .elevenlabs_provider import ElevenLabsProvider
from .openai_provider import OpenAITTSProvider, OpenAIWhisperProvider

logger = logging.getLogger(__name__)


class VoiceService:
    """Main service for managing voice operations."""

    def __init__(self, db: AsyncSession, tenant_id: UUID):
        """
        Initialize voice service.

        Args:
            db: Database session
            tenant_id: Tenant ID for API key retrieval
        """
        self.db = db
        self.tenant_id = tenant_id
        self._stt_providers: dict[str, BaseSTTProvider] = {}
        self._tts_providers: dict[str, BaseTTSProvider] = {}

    async def _get_api_key(self, provider: VoiceProvider) -> str | None:
        """
        Retrieve and decrypt API key for a provider.

        Args:
            provider: Voice provider enum

        Returns:
            Decrypted API key or None
        """
        try:
            result = await self.db.execute(
                select(VoiceApiKey).where(
                    VoiceApiKey.tenant_id == self.tenant_id, VoiceApiKey.provider == provider, VoiceApiKey.is_active
                )
            )
            api_key_record = result.scalar_one_or_none()

            if not api_key_record:
                logger.warning(f"No active API key found for provider {provider.value}")
                return None

            # Decrypt the API key
            decrypted_key = decrypt_value(api_key_record.api_key_encrypted)
            return decrypted_key

        except Exception as e:
            logger.warning(f"Error retrieving API key for {provider.value}: {str(e)}")
            return None

    async def _get_stt_provider(self, provider_name: str, config: dict[str, Any] | None = None) -> BaseSTTProvider:
        """
        Get or create STT provider instance.

        Args:
            provider_name: Provider name (openai_whisper)
            config: Optional provider configuration

        Returns:
            STT provider instance
        """
        if provider_name in self._stt_providers:
            return self._stt_providers[provider_name]

        # Map provider name to enum
        provider_map = {
            "openai_whisper": VoiceProvider.OPENAI_WHISPER,
        }

        if provider_name not in provider_map:
            raise ValueError(f"Unknown STT provider: {provider_name}")

        provider_enum = provider_map[provider_name]
        api_key = await self._get_api_key(provider_enum)

        # Create provider instance
        if provider_name == "openai_whisper":
            provider = OpenAIWhisperProvider(api_key=api_key, config=config)
        else:
            raise ValueError(f"Provider {provider_name} not implemented")

        self._stt_providers[provider_name] = provider
        return provider

    async def _get_tts_provider(self, provider_name: str, config: dict[str, Any] | None = None) -> BaseTTSProvider:
        """
        Get or create TTS provider instance.

        Args:
            provider_name: Provider name (openai_tts, elevenlabs)
            config: Optional provider configuration

        Returns:
            TTS provider instance
        """
        if provider_name in self._tts_providers:
            return self._tts_providers[provider_name]

        # Map provider name to enum
        provider_map = {
            "openai_tts": VoiceProvider.OPENAI_TTS,
            "elevenlabs": VoiceProvider.ELEVENLABS,
        }

        if provider_name not in provider_map:
            raise ValueError(f"Unknown TTS provider: {provider_name}")

        provider_enum = provider_map[provider_name]
        api_key = await self._get_api_key(provider_enum)

        # Create provider instance
        if provider_name == "openai_tts":
            provider = OpenAITTSProvider(api_key=api_key, config=config)
        elif provider_name == "elevenlabs":
            provider = ElevenLabsProvider(api_key=api_key, config=config)
        else:
            raise ValueError(f"Provider {provider_name} not implemented")

        self._tts_providers[provider_name] = provider
        return provider

    async def transcribe(
        self,
        audio_data: bytes,
        provider: str = "openai_whisper",
        language: str | None = None,
        agent_id: UUID | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Transcribe audio to text.

        Args:
            audio_data: Audio file bytes
            provider: STT provider name
            language: Language code
            agent_id: Optional agent ID for usage tracking
            **kwargs: Additional provider-specific options

        Returns:
            Transcription result
        """
        try:
            stt_provider = await self._get_stt_provider(provider, kwargs.get("config"))
            result = await stt_provider.transcribe(audio_data, language, **kwargs)

            # Track usage
            await self._track_usage(
                provider=provider,
                operation_type=OperationType.STT,
                characters_processed=len(result.get("text", "")),
                duration_seconds=result.get("duration", 0),
                agent_id=agent_id,
            )

            return result

        except Exception as e:
            logger.warning(f"Transcription error with {provider}: {str(e)}")
            raise

    async def synthesize(
        self,
        text: str,
        provider: str = "openai_tts",
        voice_id: str | None = None,
        language: str | None = None,
        agent_id: UUID | None = None,
        **kwargs,
    ) -> bytes:
        """
        Synthesize text to speech.

        Args:
            text: Text to convert to speech
            provider: TTS provider name
            voice_id: Voice identifier
            language: Language code
            agent_id: Optional agent ID for usage tracking
            **kwargs: Additional provider-specific options

        Returns:
            Audio data as bytes
        """
        try:
            tts_provider = await self._get_tts_provider(provider, kwargs.get("config"))
            audio_data = await tts_provider.synthesize(text, voice_id, language, **kwargs)

            # Track usage
            await self._track_usage(
                provider=provider, operation_type=OperationType.TTS, characters_processed=len(text), agent_id=agent_id
            )

            return audio_data

        except Exception as e:
            logger.warning(f"Synthesis error with {provider}: {str(e)}")
            raise

    async def get_voices(self, provider: str = "openai_tts", language: str | None = None) -> list[dict[str, Any]]:
        """
        Get available voices for a TTS provider.

        Args:
            provider: TTS provider name
            language: Optional language filter

        Returns:
            List of available voices
        """
        try:
            tts_provider = await self._get_tts_provider(provider)
            return await tts_provider.get_voices(language)

        except Exception as e:
            logger.warning(f"Error getting voices from {provider}: {str(e)}")
            raise

    async def get_supported_providers(self) -> dict[str, Any]:
        """
        Get list of supported providers and their capabilities.

        Returns:
            Dict with STT and TTS providers
        """
        return {
            "stt": [
                {
                    "id": "openai_whisper",
                    "name": "OpenAI Whisper",
                    "description": "High-accuracy speech recognition",
                    "requires_api_key": True,
                }
            ],
            "tts": [
                {
                    "id": "openai_tts",
                    "name": "OpenAI TTS",
                    "description": "Natural text-to-speech",
                    "requires_api_key": True,
                },
                {
                    "id": "elevenlabs",
                    "name": "ElevenLabs",
                    "description": "Premium voice synthesis",
                    "requires_api_key": True,
                },
            ],
        }

    async def _track_usage(
        self,
        provider: str,
        operation_type: OperationType,
        characters_processed: int,
        duration_seconds: float = 0,
        agent_id: UUID | None = None,
    ):
        """
        Track voice usage for billing and analytics.

        Args:
            provider: Provider name
            operation_type: Type of operation
            characters_processed: Number of characters
            duration_seconds: Audio duration
            agent_id: Optional agent ID
        """
        try:
            # Map provider name to enum
            provider_map = {
                "openai_whisper": VoiceProvider.OPENAI_WHISPER,
                "openai_tts": VoiceProvider.OPENAI_TTS,
                "elevenlabs": VoiceProvider.ELEVENLABS,
            }

            provider_enum = provider_map.get(provider)
            if not provider_enum:
                logger.warning(f"Unknown provider for usage tracking: {provider}")
                return

            # Calculate estimated cost (simplified)
            cost = self._calculate_cost(provider_enum, operation_type, characters_processed)

            input_length = 0
            output_length = 0

            if operation_type == OperationType.STT:
                input_length = int(duration_seconds) if duration_seconds else 0
                output_length = characters_processed
            else:  # TTS
                input_length = characters_processed
                output_length = int(duration_seconds) if duration_seconds else 0

            usage = VoiceUsage(
                tenant_id=self.tenant_id,
                agent_id=agent_id,
                provider=provider_enum,
                operation_type=operation_type,
                input_length=input_length,
                output_length=output_length,
                cost=cost,
            )

            self.db.add(usage)
            await self.db.commit()

        except Exception as e:
            logger.error(f"Error tracking usage: {str(e)}")
            # Don't fail the request if usage tracking fails

    def _calculate_cost(self, provider: VoiceProvider, operation_type: OperationType, characters: int) -> float:
        """
        Calculate estimated cost for voice operation.

        Args:
            provider: Voice provider
            operation_type: Operation type
            characters: Number of characters

        Returns:
            Estimated cost in USD
        """
        # Simplified cost calculation (update with actual pricing)
        pricing = {
            VoiceProvider.OPENAI_WHISPER: {
                OperationType.STT: 0.006 / 60  # $0.006 per minute
            },
            VoiceProvider.OPENAI_TTS: {
                OperationType.TTS: 0.015 / 1000  # $0.015 per 1K characters
            },
            VoiceProvider.ELEVENLABS: {
                OperationType.TTS: 0.30 / 1000  # ~$0.30 per 1K characters (varies by tier)
            },
        }

        rate = pricing.get(provider, {}).get(operation_type, 0)

        if operation_type == OperationType.STT:
            # Estimate: ~150 words per minute, ~5 chars per word
            estimated_minutes = characters / 750
            return rate * estimated_minutes
        else:
            return rate * characters
