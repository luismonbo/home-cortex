from __future__ import annotations

import logging
import time

from telegram import Message

from brain.graph.events import StreamEvent

logger = logging.getLogger(__name__)

AGENT_DISPLAY_NAMES: dict[str, str] = {
    "router": "Thinking...",
    "homeassistant": "Asking Home Assistant...",
    "memory": "Searching memory...",
    "fallback": "Thinking...",
    "unknown": "Thinking...",
}
DEFAULT_AGENT_LABEL = "Working..."

TOOL_DISPLAY_NAMES: dict[str, str] = {
    "search_ha_entities": "Searching for devices...",
    "get_entity_state": "Reading sensor...",
    "toggle_entity": "Toggling device...",
    "call_service": "Calling service...",
    "search_past_events": "Searching memory...",
}
DEFAULT_TOOL_LABEL = "Working..."

_THROTTLE_SECONDS = 1.0


class TelegramReporter:
    """Edits a single Telegram message to show agent progress."""

    def __init__(self, message: Message, initial_text: str = "") -> None:
        self._message = message
        self._last_edit: float = 0.0
        self._last_text: str = initial_text

    async def on_event(self, event: StreamEvent) -> None:
        text = self._resolve_text(event)
        if text is None or text == self._last_text:
            return

        is_final = event.kind == "result"
        if not is_final and not self._throttle_ok():
            return

        try:
            await self._message.edit_text(text)
            self._last_edit = time.monotonic()
            self._last_text = text
        except Exception:
            logger.exception("Failed to edit Telegram message")

    def _resolve_text(self, event: StreamEvent) -> str | None:
        if event.kind == "node_start":
            return AGENT_DISPLAY_NAMES.get(event.agent, DEFAULT_AGENT_LABEL)
        if event.kind == "tool_start":
            return TOOL_DISPLAY_NAMES.get(event.tool or "", DEFAULT_TOOL_LABEL)
        if event.kind == "result":
            return event.content
        return None

    def _throttle_ok(self) -> bool:
        return (time.monotonic() - self._last_edit) >= _THROTTLE_SECONDS
