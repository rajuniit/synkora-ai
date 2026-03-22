"""
Voice service module for speech-to-text and text-to-speech functionality.
Supports multiple providers: Web Speech API, OpenAI Whisper, OpenAI TTS, ElevenLabs.
"""

from .base_provider import BaseSTTProvider, BaseTTSProvider
from .elevenlabs_provider import ElevenLabsProvider
from .openai_provider import OpenAITTSProvider, OpenAIWhisperProvider
from .voice_service import VoiceService

__all__ = [
    "BaseSTTProvider",
    "BaseTTSProvider",
    "OpenAIWhisperProvider",
    "OpenAITTSProvider",
    "ElevenLabsProvider",
    "VoiceService",
]
