import logging

from telegram import Bot

from brain.config import Settings

logger = logging.getLogger(__name__)


class Notifier:
    """Sends messages to a Telegram chat. No-op when unconfigured."""

    def __init__(self, settings: Settings) -> None:
        self._chat_id = settings.telegram_chat_id
        if settings.telegram_bot_token:
            self._bot = Bot(token=settings.telegram_bot_token)
        else:
            self._bot = None

    async def send(self, text: str) -> None:
        if self._bot is None:
            return
        try:
            await self._bot.send_message(chat_id=self._chat_id, text=text)
        except Exception:
            logger.exception("Failed to send Telegram notification")
