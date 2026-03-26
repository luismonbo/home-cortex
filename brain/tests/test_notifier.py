from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from brain.config import Settings


class TestNotifierSend:
    async def test_sends_message_to_configured_chat_id(self):
        settings = Settings(
            telegram_bot_token="fake-token",
            telegram_chat_id=123456,
        )
        from brain.services.notifier import Notifier

        notifier = Notifier(settings)

        with patch.object(notifier, "_bot", new_callable=MagicMock) as mock_bot:
            mock_bot.send_message = AsyncMock()
            await notifier.send("Hello from Cortex")
            mock_bot.send_message.assert_called_once_with(
                chat_id=123456,
                text="Hello from Cortex",
            )

    async def test_noop_when_token_is_empty(self):
        settings = Settings(telegram_bot_token="", telegram_chat_id=0)
        from brain.services.notifier import Notifier

        notifier = Notifier(settings)
        # Should not raise, should do nothing
        await notifier.send("Hello")

    async def test_logs_error_on_send_failure(self, caplog):
        settings = Settings(
            telegram_bot_token="fake-token",
            telegram_chat_id=123456,
        )
        from brain.services.notifier import Notifier

        notifier = Notifier(settings)

        with patch.object(notifier, "_bot", new_callable=MagicMock) as mock_bot:
            mock_bot.send_message = AsyncMock(side_effect=Exception("Network error"))
            await notifier.send("Hello")
            assert "Failed to send Telegram notification" in caplog.text
