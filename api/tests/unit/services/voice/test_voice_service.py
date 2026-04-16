from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.voice_api_key import VoiceApiKey, VoiceProvider
from src.models.voice_usage import OperationType, VoiceUsage
from src.services.voice.base_provider import BaseSTTProvider, BaseTTSProvider
from src.services.voice.voice_service import VoiceService


class TestVoiceService:
    @pytest.fixture
    def mock_db(self):
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        return session

    @pytest.fixture
    def service(self, mock_db):
        return VoiceService(mock_db, tenant_id=uuid4())

    @pytest.fixture
    def mock_stt_provider(self):
        provider = MagicMock(spec=BaseSTTProvider)
        provider.transcribe = AsyncMock(return_value={"text": "Hello"})
        return provider

    @pytest.fixture
    def mock_tts_provider(self):
        provider = MagicMock(spec=BaseTTSProvider)
        provider.synthesize = AsyncMock(return_value=b"audio_data")
        provider.get_voices = AsyncMock(return_value=[{"id": "v1"}])
        return provider

    async def test_transcribe_success(self, service, mock_stt_provider, mock_db):
        # Mock _get_stt_provider
        with (
            patch.object(service, "_get_stt_provider", new_callable=AsyncMock) as mock_get_provider,
            patch.object(service, "_track_usage", new_callable=AsyncMock) as mock_track,
        ):
            mock_get_provider.return_value = mock_stt_provider

            result = await service.transcribe(b"audio", provider="test_stt")

            assert result == {"text": "Hello"}
            mock_stt_provider.transcribe.assert_called_once()
            mock_track.assert_called_once()

    async def test_synthesize_success(self, service, mock_tts_provider):
        with (
            patch.object(service, "_get_tts_provider", new_callable=AsyncMock) as mock_get_provider,
            patch.object(service, "_track_usage", new_callable=AsyncMock) as mock_track,
        ):
            mock_get_provider.return_value = mock_tts_provider

            result = await service.synthesize("Hello", provider="test_tts")

            assert result == b"audio_data"
            mock_tts_provider.synthesize.assert_called_once()
            mock_track.assert_called_once()

    async def test_get_voices(self, service, mock_tts_provider):
        with patch.object(service, "_get_tts_provider", new_callable=AsyncMock) as mock_get_provider:
            mock_get_provider.return_value = mock_tts_provider

            result = await service.get_voices(provider="test_tts")

            assert result == [{"id": "v1"}]
            mock_tts_provider.get_voices.assert_called_once()

    async def test_get_api_key_success(self, service, mock_db):
        # Mock DB result for API key
        mock_result = MagicMock()
        mock_key = MagicMock(spec=VoiceApiKey)
        mock_key.api_key_encrypted = "enc_key"
        mock_result.scalar_one_or_none.return_value = mock_key
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("src.services.voice.voice_service.decrypt_value", return_value="dec_key"):
            key = await service._get_api_key(VoiceProvider.OPENAI_WHISPER)
            assert key == "dec_key"

    async def test_get_api_key_none(self, service, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        key = await service._get_api_key(VoiceProvider.OPENAI_WHISPER)
        assert key is None

    async def test_track_usage(self, service, mock_db):
        # Use a valid provider enum
        await service._track_usage("openai_whisper", OperationType.STT, 10)

        mock_db.add.assert_called_once()
        args = mock_db.add.call_args[0]
        assert isinstance(args[0], VoiceUsage)
        assert args[0].provider == VoiceProvider.OPENAI_WHISPER
        mock_db.commit.assert_called_once()
