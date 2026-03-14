from unittest.mock import MagicMock

import pytest

from brain.agents.memory.tools import make_tools


@pytest.fixture
def mock_event_store():
    store = MagicMock()
    store.search_events.return_value = [
        {
            "id": "abc-123",
            "intent": "toggle light.bedroom",
            "source": "manual-test",
            "timestamp": "2026-03-14T02:00:00+00:00",
            "document": "intent: toggle light.bedroom | source: manual-test | payload: {}",
        }
    ]
    return store


@pytest.fixture
def tools(mock_event_store):
    return make_tools(mock_event_store)


class TestSearchPastEvents:
    async def test_calls_search_events(self, tools, mock_event_store):
        search = tools[0]
        await search.ainvoke({"query": "bedroom light", "n_results": 3})
        mock_event_store.search_events.assert_called_once_with("bedroom light", 3)

    async def test_returns_formatted_string(self, tools, mock_event_store):
        search = tools[0]
        result = await search.ainvoke({"query": "bedroom light"})
        assert "toggle light.bedroom" in result
        assert "manual-test" in result

    async def test_empty_results(self, tools, mock_event_store):
        mock_event_store.search_events.return_value = []
        search = tools[0]
        result = await search.ainvoke({"query": "nothing"})
        assert "no past events" in result.lower()

    async def test_default_n_results(self, tools, mock_event_store):
        search = tools[0]
        await search.ainvoke({"query": "anything"})
        mock_event_store.search_events.assert_called_once_with("anything", 5)
