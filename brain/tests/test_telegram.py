from unittest.mock import AsyncMock, MagicMock

import pytest

from brain.config import Settings
from brain.graph.events import StreamEvent


async def _async_iter(items):
    for item in items:
        yield item


@pytest.fixture
def telegram_settings():
    return Settings(
        telegram_bot_token="fake-token",
        telegram_chat_id=123456,
    )


@pytest.fixture
def mock_event_store():
    store = MagicMock()
    store.store_event.return_value = "tg-event-123"
    return store


@pytest.fixture
def mock_runner():
    runner = MagicMock()
    runner.stream = MagicMock(return_value=_async_iter([
        StreamEvent(kind="node_start", agent="router"),
        StreamEvent(kind="result", agent="homeassistant", content="The light is on."),
    ]))
    return runner


@pytest.fixture
def mock_transcriber():
    transcriber = MagicMock()
    transcriber.transcribe = AsyncMock(return_value="what is the temperature")
    return transcriber


class TestTelegramBotAuth:
    async def test_ignores_message_from_wrong_chat_id(self, telegram_settings, mock_event_store, mock_runner, mock_transcriber):
        from brain.telegram_bot import TelegramBot

        bot = TelegramBot(telegram_settings, mock_event_store, mock_runner, mock_transcriber)

        update = MagicMock()
        update.effective_chat.id = 999999  # wrong chat ID
        update.message.text = "hello"
        context = MagicMock()

        await bot._handle_message(update, context)
        mock_runner.stream.assert_not_called()

    async def test_processes_message_from_correct_chat_id(self, telegram_settings, mock_event_store, mock_runner, mock_transcriber):
        from brain.telegram_bot import TelegramBot

        bot = TelegramBot(telegram_settings, mock_event_store, mock_runner, mock_transcriber)

        update = MagicMock()
        update.effective_chat.id = 123456
        update.message.text = "turn on the lights"
        update.message.reply_text = AsyncMock(return_value=MagicMock(edit_text=AsyncMock()))
        context = MagicMock()

        await bot._handle_message(update, context)
        mock_runner.stream.assert_called_once()


class TestTelegramBotMessageFlow:
    async def test_stores_event_in_chromadb(self, telegram_settings, mock_event_store, mock_runner, mock_transcriber):
        from brain.telegram_bot import TelegramBot

        bot = TelegramBot(telegram_settings, mock_event_store, mock_runner, mock_transcriber)

        update = MagicMock()
        update.effective_chat.id = 123456
        update.message.text = "what is the temperature"
        update.message.reply_text = AsyncMock(return_value=MagicMock(edit_text=AsyncMock()))
        context = MagicMock()

        await bot._handle_message(update, context)
        mock_event_store.store_event.assert_called_once_with(
            intent="what is the temperature",
            payload={},
            source="telegram",
        )

    async def test_sends_placeholder_then_streams(self, telegram_settings, mock_event_store, mock_runner, mock_transcriber):
        from brain.telegram_bot import TelegramBot

        mock_placeholder = MagicMock()
        mock_placeholder.edit_text = AsyncMock()

        mock_runner.stream = MagicMock(return_value=_async_iter([
            StreamEvent(kind="node_start", agent="router"),
            StreamEvent(kind="result", agent="homeassistant", content="The light is on."),
        ]))

        bot = TelegramBot(telegram_settings, mock_event_store, mock_runner, mock_transcriber)

        update = MagicMock()
        update.effective_chat.id = 123456
        update.message.text = "turn on the lights"
        update.message.reply_text = AsyncMock(return_value=mock_placeholder)
        context = MagicMock()

        await bot._handle_message(update, context)
        update.message.reply_text.assert_called_once_with("Thinking...")
        mock_placeholder.edit_text.assert_called_with("The light is on.")

    async def test_replies_with_sorry_on_stream_failure(self, telegram_settings, mock_event_store, mock_runner, mock_transcriber):
        from brain.telegram_bot import TelegramBot

        async def _failing_stream(state):
            raise Exception("LLM timeout")
            yield  # make it a generator

        mock_runner.stream = MagicMock(side_effect=_failing_stream)

        mock_placeholder = MagicMock()
        mock_placeholder.edit_text = AsyncMock()

        bot = TelegramBot(telegram_settings, mock_event_store, mock_runner, mock_transcriber)

        update = MagicMock()
        update.effective_chat.id = 123456
        update.message.text = "turn on the lights"
        update.message.reply_text = AsyncMock(return_value=mock_placeholder)
        context = MagicMock()

        await bot._handle_message(update, context)
        mock_placeholder.edit_text.assert_called_with(
            "Sorry, something went wrong. Please try again."
        )

    async def test_replies_with_sorry_when_no_result_event(self, telegram_settings, mock_event_store, mock_runner, mock_transcriber):
        from brain.telegram_bot import TelegramBot

        mock_runner.stream = MagicMock(return_value=_async_iter([
            StreamEvent(kind="node_start", agent="router"),
        ]))

        mock_placeholder = MagicMock()
        mock_placeholder.edit_text = AsyncMock()

        bot = TelegramBot(telegram_settings, mock_event_store, mock_runner, mock_transcriber)

        update = MagicMock()
        update.effective_chat.id = 123456
        update.message.text = "gibberish"
        update.message.reply_text = AsyncMock(return_value=mock_placeholder)
        context = MagicMock()

        await bot._handle_message(update, context)
        mock_placeholder.edit_text.assert_called_with(
            "Sorry, something went wrong. Please try again."
        )


class TestTelegramBotVoice:
    async def test_ignores_voice_from_wrong_chat_id(
        self, telegram_settings, mock_event_store, mock_runner, mock_transcriber
    ):
        from brain.telegram_bot import TelegramBot

        bot = TelegramBot(telegram_settings, mock_event_store, mock_runner, mock_transcriber)

        update = MagicMock()
        update.effective_chat.id = 999999
        context = MagicMock()

        await bot._handle_voice(update, context)
        mock_transcriber.transcribe.assert_not_called()

    async def test_voice_transcribes_and_runs_agent(
        self, telegram_settings, mock_event_store, mock_runner, mock_transcriber
    ):
        from brain.telegram_bot import TelegramBot

        mock_placeholder = MagicMock()
        mock_placeholder.edit_text = AsyncMock()

        mock_voice_file = AsyncMock()
        mock_voice_file.download_as_bytearray = AsyncMock(return_value=bytearray(b"audio-data"))

        update = MagicMock()
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock(return_value=mock_placeholder)
        update.message.voice.get_file = AsyncMock(return_value=mock_voice_file)
        context = MagicMock()

        bot = TelegramBot(telegram_settings, mock_event_store, mock_runner, mock_transcriber)
        await bot._handle_voice(update, context)

        mock_transcriber.transcribe.assert_called_once_with(b"audio-data")
        mock_runner.stream.assert_called_once()

    async def test_voice_stores_event_with_telegram_voice_source(
        self, telegram_settings, mock_event_store, mock_runner, mock_transcriber
    ):
        from brain.telegram_bot import TelegramBot

        mock_placeholder = MagicMock()
        mock_placeholder.edit_text = AsyncMock()

        mock_voice_file = AsyncMock()
        mock_voice_file.download_as_bytearray = AsyncMock(return_value=bytearray(b"audio-data"))

        update = MagicMock()
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock(return_value=mock_placeholder)
        update.message.voice.get_file = AsyncMock(return_value=mock_voice_file)
        context = MagicMock()

        bot = TelegramBot(telegram_settings, mock_event_store, mock_runner, mock_transcriber)
        await bot._handle_voice(update, context)

        mock_event_store.store_event.assert_called_once_with(
            intent="what is the temperature",
            payload={},
            source="telegram_voice",
        )

    async def test_voice_transcription_failure_replies_sorry(
        self, telegram_settings, mock_event_store, mock_runner, mock_transcriber
    ):
        from brain.telegram_bot import TelegramBot

        mock_placeholder = MagicMock()
        mock_placeholder.edit_text = AsyncMock()

        mock_voice_file = AsyncMock()
        mock_voice_file.download_as_bytearray = AsyncMock(return_value=bytearray(b"audio-data"))
        mock_transcriber.transcribe = AsyncMock(side_effect=Exception("Whisper API error"))

        update = MagicMock()
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock(return_value=mock_placeholder)
        update.message.voice.get_file = AsyncMock(return_value=mock_voice_file)
        context = MagicMock()

        bot = TelegramBot(telegram_settings, mock_event_store, mock_runner, mock_transcriber)
        await bot._handle_voice(update, context)

        mock_placeholder.edit_text.assert_called_with("Sorry, something went wrong. Please try again.")
        mock_runner.stream.assert_not_called()

    async def test_voice_empty_transcript_replies_cannot_understand(
        self, telegram_settings, mock_event_store, mock_runner, mock_transcriber
    ):
        from brain.telegram_bot import TelegramBot

        mock_placeholder = MagicMock()
        mock_placeholder.edit_text = AsyncMock()

        mock_voice_file = AsyncMock()
        mock_voice_file.download_as_bytearray = AsyncMock(return_value=bytearray(b"silence"))
        mock_transcriber.transcribe = AsyncMock(return_value="")

        update = MagicMock()
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock(return_value=mock_placeholder)
        update.message.voice.get_file = AsyncMock(return_value=mock_voice_file)
        context = MagicMock()

        bot = TelegramBot(telegram_settings, mock_event_store, mock_runner, mock_transcriber)
        await bot._handle_voice(update, context)

        mock_placeholder.edit_text.assert_called_with("Sorry, I couldn't understand that. Please try again.")
        mock_runner.stream.assert_not_called()

    async def test_voice_download_failure_replies_sorry(
        self, telegram_settings, mock_event_store, mock_runner, mock_transcriber
    ):
        from brain.telegram_bot import TelegramBot

        mock_placeholder = MagicMock()
        mock_placeholder.edit_text = AsyncMock()

        mock_voice_file = AsyncMock()
        mock_voice_file.download_as_bytearray = AsyncMock(side_effect=Exception("Telegram download error"))

        update = MagicMock()
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock(return_value=mock_placeholder)
        update.message.voice.get_file = AsyncMock(return_value=mock_voice_file)
        context = MagicMock()

        bot = TelegramBot(telegram_settings, mock_event_store, mock_runner, mock_transcriber)
        await bot._handle_voice(update, context)

        mock_placeholder.edit_text.assert_called_with("Sorry, something went wrong. Please try again.")
        mock_transcriber.transcribe.assert_not_called()
