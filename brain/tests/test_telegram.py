from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from brain.config import Settings


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
    runner.invoke = AsyncMock(return_value={
        "result": "The light is on.",
        "messages": [],
        "intent": "",
        "source": "",
        "event_id": "",
        "next_agent": "",
    })
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
        mock_runner.invoke.assert_not_called()

    async def test_processes_message_from_correct_chat_id(self, telegram_settings, mock_event_store, mock_runner):
        from brain.telegram_bot import TelegramBot

        bot = TelegramBot(telegram_settings, mock_event_store, mock_runner)

        update = MagicMock()
        update.effective_chat.id = 123456
        update.message.text = "turn on the lights"
        update.message.reply_text = AsyncMock()
        context = MagicMock()

        await bot._handle_message(update, context)
        mock_runner.invoke.assert_called_once()


class TestTelegramBotMessageFlow:
    async def test_stores_event_in_chromadb(self, telegram_settings, mock_event_store, mock_runner):
        from brain.telegram_bot import TelegramBot

        bot = TelegramBot(telegram_settings, mock_event_store, mock_runner)

        update = MagicMock()
        update.effective_chat.id = 123456
        update.message.text = "what is the temperature"
        update.message.reply_text = AsyncMock()
        context = MagicMock()

        await bot._handle_message(update, context)
        mock_event_store.store_event.assert_called_once_with(
            intent="what is the temperature",
            payload={},
            source="telegram",
        )

    async def test_invokes_graph_with_correct_state(self, telegram_settings, mock_event_store, mock_runner):
        from brain.telegram_bot import TelegramBot

        bot = TelegramBot(telegram_settings, mock_event_store, mock_runner)

        update = MagicMock()
        update.effective_chat.id = 123456
        update.message.text = "turn on the lights"
        update.message.reply_text = AsyncMock()
        context = MagicMock()

        await bot._handle_message(update, context)

        call_args = mock_runner.invoke.call_args[0][0]
        assert call_args["intent"] == "turn on the lights"
        assert call_args["source"] == "telegram"
        assert call_args["event_id"] == "tg-event-123"

    async def test_replies_with_graph_result(self, telegram_settings, mock_event_store, mock_runner):
        from brain.telegram_bot import TelegramBot

        bot = TelegramBot(telegram_settings, mock_event_store, mock_runner)

        update = MagicMock()
        update.effective_chat.id = 123456
        update.message.text = "what is the temperature"
        update.message.reply_text = AsyncMock()
        context = MagicMock()

        await bot._handle_message(update, context)
        update.message.reply_text.assert_called_once_with("The light is on.")

    async def test_replies_with_sorry_on_graph_failure(self, telegram_settings, mock_event_store, mock_runner):
        mock_runner.invoke = AsyncMock(side_effect=Exception("LLM timeout"))
        from brain.telegram_bot import TelegramBot

        bot = TelegramBot(telegram_settings, mock_event_store, mock_runner)

        update = MagicMock()
        update.effective_chat.id = 123456
        update.message.text = "turn on the lights"
        update.message.reply_text = AsyncMock()
        context = MagicMock()

        await bot._handle_message(update, context)
        update.message.reply_text.assert_called_once_with(
            "Sorry, something went wrong. Please try again."
        )

    async def test_replies_with_sorry_on_empty_result(self, telegram_settings, mock_event_store, mock_runner):
        mock_runner.invoke = AsyncMock(return_value={"result": ""})
        from brain.telegram_bot import TelegramBot

        bot = TelegramBot(telegram_settings, mock_event_store, mock_runner)

        update = MagicMock()
        update.effective_chat.id = 123456
        update.message.text = "gibberish"
        update.message.reply_text = AsyncMock()
        context = MagicMock()

        await bot._handle_message(update, context)
        update.message.reply_text.assert_called_once_with(
            "Sorry, something went wrong. Please try again."
        )
