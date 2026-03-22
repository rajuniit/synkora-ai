"""
Base provider classes for speech-to-text and text-to-speech services.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseSTTProvider(ABC):
    """Base class for Speech-to-Text providers."""

    def __init__(self, api_key: str | None = None, config: dict[str, Any] | None = None):
        """
        Initialize STT provider.

        Args:
            api_key: API key for the provider
            config: Additional configuration options
        """
        self.api_key = api_key
        self.config = config or {}

    @abstractmethod
    async def transcribe(self, audio_data: bytes, language: str | None = None, **kwargs) -> dict[str, Any]:
        """
        Transcribe audio to text.

        Args:
            audio_data: Audio file bytes
            language: Language code (e.g., 'en', 'es', 'fr')
            **kwargs: Additional provider-specific options

        Returns:
            Dict containing:
                - text: Transcribed text
                - language: Detected/specified language
                - confidence: Confidence score (0-1)
                - duration: Audio duration in seconds
                - segments: Optional list of timestamped segments
        """
        pass

    @abstractmethod
    def get_supported_languages(self) -> list[str]:
        """
        Get list of supported language codes.

        Returns:
            List of ISO language codes
        """
        pass

    @abstractmethod
    def get_supported_formats(self) -> list[str]:
        """
        Get list of supported audio formats.

        Returns:
            List of format extensions (e.g., ['mp3', 'wav', 'ogg'])
        """
        pass


class BaseTTSProvider(ABC):
    """Base class for Text-to-Speech providers."""

    def __init__(self, api_key: str | None = None, config: dict[str, Any] | None = None):
        """
        Initialize TTS provider.

        Args:
            api_key: API key for the provider
            config: Additional configuration options
        """
        self.api_key = api_key
        self.config = config or {}

    @abstractmethod
    async def synthesize(self, text: str, voice_id: str | None = None, language: str | None = None, **kwargs) -> bytes:
        """
        Synthesize text to speech.

        Args:
            text: Text to convert to speech
            voice_id: Voice identifier
            language: Language code
            **kwargs: Additional provider-specific options (rate, pitch, etc.)

        Returns:
            Audio data as bytes
        """
        pass

    @abstractmethod
    async def get_voices(self, language: str | None = None) -> list[dict[str, Any]]:
        """
        Get available voices.

        Args:
            language: Filter by language code

        Returns:
            List of voice dictionaries containing:
                - id: Voice identifier
                - name: Voice name
                - language: Language code
                - gender: Voice gender (male/female/neutral)
                - description: Voice description
        """
        pass

    @abstractmethod
    def get_supported_languages(self) -> list[str]:
        """
        Get list of supported language codes.

        Returns:
            List of ISO language codes
        """
        pass

    @abstractmethod
    def get_output_format(self) -> str:
        """
        Get the output audio format.

        Returns:
            Format string (e.g., 'mp3', 'wav', 'ogg')
        """
        pass
