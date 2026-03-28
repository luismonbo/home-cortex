import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from brain.graph.events import StreamEvent
from brain.reporters.telegram import TelegramReporter, TOOL_DISPLAY_NAMES


@pytest.fixture
def mock_message():
    msg = MagicMock()
    msg.edit_text = AsyncMock()
    return msg


@pytest.fixture
def reporter(mock_message):
    return TelegramReporter(mock_message)


class TestTelegramReporterNodeStart:
    async def test_router_shows_thinking(self, reporter, mock_message):
        event = StreamEvent(kind="node_start", agent="router")
        await reporter.on_event(event)
        mock_message.edit_text.assert_called_once_with("Thinking...")

    async def test_ha_agent_shows_asking_home_assistant(self, reporter, mock_message):
        event = StreamEvent(kind="node_start", agent="homeassistant")
        await reporter.on_event(event)
        mock_message.edit_text.assert_called_with("Asking Home Assistant...")

    async def test_memory_agent_shows_searching_memory(self, reporter, mock_message):
        event = StreamEvent(kind="node_start", agent="memory")
        await reporter.on_event(event)
        mock_message.edit_text.assert_called_with("Searching memory...")

    async def test_unknown_agent_shows_thinking(self, reporter, mock_message):
        event = StreamEvent(kind="node_start", agent="unknown")
        await reporter.on_event(event)
        mock_message.edit_text.assert_called_with("Thinking...")

    async def test_new_agent_falls_back_to_generic(self, reporter, mock_message):
        event = StreamEvent(kind="node_start", agent="notion")
        await reporter.on_event(event)
        # Should not crash; uses a generic fallback
        mock_message.edit_text.assert_called()


class TestTelegramReporterToolStart:
    async def test_known_tool_shows_display_name(self, reporter, mock_message):
        event = StreamEvent(kind="tool_start", agent="homeassistant", tool="get_entity_state")
        await reporter.on_event(event)
        mock_message.edit_text.assert_called_with(TOOL_DISPLAY_NAMES["get_entity_state"])

    async def test_unknown_tool_shows_working(self, reporter, mock_message):
        event = StreamEvent(kind="tool_start", agent="homeassistant", tool="some_future_tool")
        await reporter.on_event(event)
        mock_message.edit_text.assert_called_with("Working...")


class TestTelegramReporterResult:
    async def test_result_edits_with_final_content(self, reporter, mock_message):
        event = StreamEvent(kind="result", agent="homeassistant", content="Soil moisture is 42%")
        await reporter.on_event(event)
        mock_message.edit_text.assert_called_with("Soil moisture is 42%")


class TestTelegramReporterThrottling:
    async def test_skips_rapid_intermediate_edits(self, reporter, mock_message):
        event1 = StreamEvent(kind="tool_start", agent="homeassistant", tool="search_ha_entities")
        event2 = StreamEvent(kind="tool_start", agent="homeassistant", tool="get_entity_state")
        await reporter.on_event(event1)
        await reporter.on_event(event2)
        # Second call should be throttled — only 1 edit_text call
        assert mock_message.edit_text.call_count == 1

    async def test_result_bypasses_throttle(self, reporter, mock_message):
        event1 = StreamEvent(kind="tool_start", agent="homeassistant", tool="search_ha_entities")
        result = StreamEvent(kind="result", agent="homeassistant", content="Done")
        await reporter.on_event(event1)
        await reporter.on_event(result)
        # Result should always go through
        assert mock_message.edit_text.call_count == 2
        mock_message.edit_text.assert_called_with("Done")


class TestTelegramReporterDuplicateText:
    async def test_skips_edit_when_text_unchanged(self, reporter, mock_message):
        """Telegram rejects editing a message to the same text — skip it."""
        event1 = StreamEvent(kind="node_start", agent="router")
        event2 = StreamEvent(kind="node_start", agent="unknown")  # also resolves to "Thinking..."
        await reporter.on_event(event1)
        await reporter.on_event(event2)
        # Only one edit — second was skipped because text is identical
        mock_message.edit_text.assert_called_once_with("Thinking...")


class TestTelegramReporterErrorHandling:
    async def test_edit_failure_is_logged_not_raised(self, reporter, mock_message):
        mock_message.edit_text = AsyncMock(side_effect=Exception("Telegram API error"))
        event = StreamEvent(kind="node_start", agent="router")
        # Should not raise
        await reporter.on_event(event)
