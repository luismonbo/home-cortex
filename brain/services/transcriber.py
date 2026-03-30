from openai import AsyncOpenAI

from brain.config import Settings


class VoiceTranscriber:
    """Transcribes audio bytes to text using the OpenAI Whisper API."""

    def __init__(self, settings: Settings) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def transcribe(self, audio_bytes: bytes, filename: str = "voice.ogg") -> str:
        response = await self._client.audio.transcriptions.create(
            model="whisper-1",
            file=(filename, audio_bytes),
        )
        return response.text
