from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from brain.config import Settings
from brain.services.transcriber import VoiceTranscriber


@pytest.fixture
def settings():
    return Settings(openai_api_key="test-key")


class TestVoiceTranscriber:
    async def test_returns_transcript_on_success(self, settings):
        transcriber = VoiceTranscriber(settings)
        mock_response = MagicMock()
        mock_response.text = "what is the temperature"

        with patch.object(
            transcriber._client.audio.transcriptions,
            "create",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.return_value = mock_response
            result = await transcriber.transcribe(b"fake-audio", "voice.ogg")

        assert result == "what is the temperature"
        mock_create.assert_called_once_with(
            model="whisper-1",
            file=("voice.ogg", b"fake-audio"),
        )

    async def test_propagates_api_error(self, settings):
        transcriber = VoiceTranscriber(settings)

        with patch.object(
            transcriber._client.audio.transcriptions,
            "create",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.side_effect = Exception("API unavailable")
            with pytest.raises(Exception, match="API unavailable"):
                await transcriber.transcribe(b"fake-audio", "voice.ogg")

    async def test_returns_empty_string_when_whisper_returns_no_text(self, settings):
        transcriber = VoiceTranscriber(settings)
        mock_response = MagicMock()
        mock_response.text = ""

        with patch.object(
            transcriber._client.audio.transcriptions,
            "create",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.return_value = mock_response
            result = await transcriber.transcribe(b"silence", "voice.ogg")

        assert result == ""
