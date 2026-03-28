import logging

from langchain_core.messages import HumanMessage
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from brain.chromadb_store import EventStore
from brain.config import Settings
from brain.graph.runner import GraphRunner
from brain.graph.state import CortexState
from brain.reporters.telegram import TelegramReporter

logger = logging.getLogger(__name__)

SORRY_MESSAGE = "Sorry, something went wrong. Please try again."


class TelegramBot:
    """Bidirectional Telegram bot for chatting with Cortex."""

    def __init__(self, settings: Settings, event_store: EventStore, runner: GraphRunner) -> None:
        self._chat_id = settings.telegram_chat_id
        self._event_store = event_store
        self._runner = runner
        self._app = Application.builder().token(settings.telegram_bot_token).build()
        self._app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_chat or update.effective_chat.id != self._chat_id:
            return

        text = update.message.text

        event_id = ""
        try:
            event_id = self._event_store.store_event(
                intent=text,
                payload={},
                source="telegram",
            )
        except Exception:
            logger.exception("Failed to store Telegram event")

        state = CortexState(
            messages=[HumanMessage(content=text)],
            intent=text,
            source="telegram",
            event_id=event_id,
            next_agent="",
            result="",
        )

        placeholder = await update.message.reply_text("Thinking...")
        reporter = TelegramReporter(placeholder)
        got_result = False

        try:
            async for event in self._runner.stream(state):
                await reporter.on_event(event)
                if event.kind == "result":
                    got_result = True
        except Exception:
            logger.exception("Graph execution failed for Telegram message")
            await placeholder.edit_text(SORRY_MESSAGE)
            return

        if not got_result:
            await placeholder.edit_text(SORRY_MESSAGE)

    async def start(self) -> None:
        await self._app.initialize()
        await self._app.start()
        await self._app.updater.start_polling()
        logger.info("TelegramBot started polling")

    async def stop(self) -> None:
        await self._app.updater.stop()
        await self._app.stop()
        await self._app.shutdown()
        logger.info("TelegramBot stopped")
