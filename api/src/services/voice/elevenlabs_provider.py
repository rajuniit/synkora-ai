"""
ElevenLabs text-to-speech provider.
"""

import logging
from typing import Any

import httpx

from .base_provider import BaseTTSProvider

logger = logging.getLogger(__name__)


class ElevenLabsProvider(BaseTTSProvider):
    """ElevenLabs premium text-to-speech provider."""

    BASE_URL = "https://api.elevenlabs.io/v1"

    def __init__(self, api_key: str | None = None, config: dict[str, Any] | None = None):
        super().__init__(api_key, config)
        self.model_id = config.get("model_id", "eleven_monolingual_v1") if config else "eleven_monolingual_v1"
        self.output_format = config.get("format", "mp3_44100_128") if config else "mp3_44100_128"

    async def synthesize(self, text: str, voice_id: str | None = None, language: str | None = None, **kwargs) -> bytes:
        """
        Synthesize text to speech using ElevenLabs API.

        Args:
            text: Text to convert to speech
            voice_id: Voice identifier from ElevenLabs
            language: Language code (not directly used, voice determines language)
            **kwargs: Additional options (stability, similarity_boost, style, etc.)

        Returns:
            Audio data as bytes
        """
        if not self.api_key:
            raise ValueError("ElevenLabs API key is required")

        if not voice_id:
            # Default to Rachel voice
            voice_id = "21m00Tcm4TlvDq8ikWAM"

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # Prepare voice settings
                voice_settings = {
                    "stability": kwargs.get("stability", 0.5),
                    "similarity_boost": kwargs.get("similarity_boost", 0.75),
                }

                # Add optional style parameter if provided
                if "style" in kwargs:
                    voice_settings["style"] = kwargs["style"]

                # Add optional use_speaker_boost if provided
                if "use_speaker_boost" in kwargs:
                    voice_settings["use_speaker_boost"] = kwargs["use_speaker_boost"]

                data = {"text": text, "model_id": self.model_id, "voice_settings": voice_settings}

                headers = {"xi-api-key": self.api_key, "Content-Type": "application/json"}

                response = await client.post(
                    f"{self.BASE_URL}/text-to-speech/{voice_id}",
                    headers=headers,
                    json=data,
                    params={"output_format": self.output_format},
                )

                response.raise_for_status()
                return response.content

        except httpx.HTTPStatusError as e:
            logger.warning(f"ElevenLabs API error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Speech synthesis failed: {e.response.text}")
        except Exception as e:
            logger.warning(f"ElevenLabs synthesis error: {str(e)}")
            raise

    async def get_voices(self, language: str | None = None) -> list[dict[str, Any]]:
        """
        Get available voices from ElevenLabs.

        Args:
            language: Filter by language (optional)

        Returns:
            List of voice dictionaries
        """
        if not self.api_key:
            raise ValueError("ElevenLabs API key is required")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {"xi-api-key": self.api_key}

                response = await client.get(f"{self.BASE_URL}/voices", headers=headers)

                response.raise_for_status()
                result = response.json()

                voices = []
                for voice in result.get("voices", []):
                    # Extract voice information
                    voice_data = {
                        "id": voice.get("voice_id"),
                        "name": voice.get("name"),
                        "language": voice.get("labels", {}).get("language", "multi"),
                        "gender": voice.get("labels", {}).get("gender", "neutral"),
                        "description": voice.get("description", ""),
                        "category": voice.get("category", "premade"),
                        "preview_url": voice.get("preview_url"),
                    }

                    # Filter by language if specified
                    if language:
                        voice_lang = voice_data["language"].lower()
                        if language.lower() in voice_lang or voice_lang == "multi":
                            voices.append(voice_data)
                    else:
                        voices.append(voice_data)

                return voices

        except httpx.HTTPStatusError as e:
            logger.warning(f"ElevenLabs API error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Failed to fetch voices: {e.response.text}")
        except Exception as e:
            logger.warning(f"ElevenLabs get voices error: {str(e)}")
            raise

    def get_supported_languages(self) -> list[str]:
        """Get list of supported language codes."""
        # ElevenLabs supports many languages, varies by voice
        return [
            "en",
            "es",
            "fr",
            "de",
            "it",
            "pt",
            "pl",
            "nl",
            "ja",
            "zh",
            "ko",
            "ar",
            "hi",
            "ru",
            "tr",
            "sv",
            "da",
            "no",
            "fi",
            "cs",
            "ro",
            "uk",
            "el",
            "bg",
            "hr",
            "sk",
            "ta",
            "id",
            "ms",
            "th",
            "vi",
        ]

    def get_output_format(self) -> str:
        """Get the output audio format."""
        # Extract format from output_format string (e.g., "mp3_44100_128" -> "mp3")
        return self.output_format.split("_")[0]

    async def get_models(self) -> list[dict[str, Any]]:
        """
        Get available models from ElevenLabs.

        Returns:
            List of model dictionaries
        """
        if not self.api_key:
            raise ValueError("ElevenLabs API key is required")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {"xi-api-key": self.api_key}

                response = await client.get(f"{self.BASE_URL}/models", headers=headers)

                response.raise_for_status()
                result = response.json()

                models = []
                for model in result:
                    models.append(
                        {
                            "id": model.get("model_id"),
                            "name": model.get("name"),
                            "description": model.get("description", ""),
                            "languages": model.get("languages", []),
                            "can_do_text_to_speech": model.get("can_do_text_to_speech", False),
                            "can_do_voice_conversion": model.get("can_do_voice_conversion", False),
                        }
                    )

                return models

        except httpx.HTTPStatusError as e:
            logger.warning(f"ElevenLabs API error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Failed to fetch models: {e.response.text}")
        except Exception as e:
            logger.warning(f"ElevenLabs get models error: {str(e)}")
            raise

    async def get_user_info(self) -> dict[str, Any]:
        """
        Get user subscription information.

        Returns:
            Dict with user info including character limits and usage
        """
        if not self.api_key:
            raise ValueError("ElevenLabs API key is required")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {"xi-api-key": self.api_key}

                response = await client.get(f"{self.BASE_URL}/user", headers=headers)

                response.raise_for_status()
                result = response.json()

                subscription = result.get("subscription", {})

                return {
                    "character_count": subscription.get("character_count", 0),
                    "character_limit": subscription.get("character_limit", 0),
                    "can_extend_character_limit": subscription.get("can_extend_character_limit", False),
                    "tier": subscription.get("tier", "free"),
                    "status": subscription.get("status", "active"),
                }

        except httpx.HTTPStatusError as e:
            logger.warning(f"ElevenLabs API error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Failed to fetch user info: {e.response.text}")
        except Exception as e:
            logger.warning(f"ElevenLabs get user info error: {str(e)}")
            raise
