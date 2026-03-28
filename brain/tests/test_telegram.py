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


class TestTelegramBotAuth:
    async def test_ignores_message_from_wrong_chat_id(self, telegram_settings, mock_event_store, mock_runner):
        from brain.telegram_bot import TelegramBot

        bot = TelegramBot(telegram_settings, mock_event_store, mock_runner)

        update = MagicMock()
        update.effective_chat.id = 999999  # wrong chat ID
        update.message.text = "hello"
        context = MagicMock()

        await bot._handle_message(update, context)
        mock_runner.stream.assert_not_called()

    async def test_processes_message_from_correct_chat_id(self, telegram_settings, mock_event_store, mock_runner):
        from brain.telegram_bot import TelegramBot

        bot = TelegramBot(telegram_settings, mock_event_store, mock_runner)

        update = MagicMock()
        update.effective_chat.id = 123456
        update.message.text = "turn on the lights"
        update.message.reply_text = AsyncMock(return_value=MagicMock(edit_text=AsyncMock()))
        context = MagicMock()

        await bot._handle_message(update, context)
        mock_runner.stream.assert_called_once()


class TestTelegramBotMessageFlow:
    async def test_stores_event_in_chromadb(self, telegram_settings, mock_event_store, mock_runner):
        from brain.telegram_bot import TelegramBot

        bot = TelegramBot(telegram_settings, mock_event_store, mock_runner)

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

    async def test_sends_placeholder_then_streams(self, telegram_settings, mock_event_store, mock_runner):
        from brain.telegram_bot import TelegramBot

        mock_placeholder = MagicMock()
        mock_placeholder.edit_text = AsyncMock()

        mock_runner.stream = MagicMock(return_value=_async_iter([
            StreamEvent(kind="node_start", agent="router"),
            StreamEvent(kind="result", agent="homeassistant", content="The light is on."),
        ]))

        bot = TelegramBot(telegram_settings, mock_event_store, mock_runner)

        update = MagicMock()
        update.effective_chat.id = 123456
        update.message.text = "turn on the lights"
        update.message.reply_text = AsyncMock(return_value=mock_placeholder)
        context = MagicMock()

        await bot._handle_message(update, context)
        update.message.reply_text.assert_called_once_with("Thinking...")
        mock_placeholder.edit_text.assert_called_with("The light is on.")

    async def test_replies_with_sorry_on_stream_failure(self, telegram_settings, mock_event_store, mock_runner):
        from brain.telegram_bot import TelegramBot

        async def _failing_stream(state):
            raise Exception("LLM timeout")
            yield  # make it a generator

        mock_runner.stream = MagicMock(side_effect=_failing_stream)

        mock_placeholder = MagicMock()
        mock_placeholder.edit_text = AsyncMock()

        bot = TelegramBot(telegram_settings, mock_event_store, mock_runner)

        update = MagicMock()
        update.effective_chat.id = 123456
        update.message.text = "turn on the lights"
        update.message.reply_text = AsyncMock(return_value=mock_placeholder)
        context = MagicMock()

        await bot._handle_message(update, context)
        mock_placeholder.edit_text.assert_called_with(
            "Sorry, something went wrong. Please try again."
        )

    async def test_replies_with_sorry_when_no_result_event(self, telegram_settings, mock_event_store, mock_runner):
        from brain.telegram_bot import TelegramBot

        mock_runner.stream = MagicMock(return_value=_async_iter([
            StreamEvent(kind="node_start", agent="router"),
        ]))

        mock_placeholder = MagicMock()
        mock_placeholder.edit_text = AsyncMock()

        bot = TelegramBot(telegram_settings, mock_event_store, mock_runner)

        update = MagicMock()
        update.effective_chat.id = 123456
        update.message.text = "gibberish"
        update.message.reply_text = AsyncMock(return_value=mock_placeholder)
        context = MagicMock()

        await bot._handle_message(update, context)
        mock_placeholder.edit_text.assert_called_with(
            "Sorry, something went wrong. Please try again."
        )
