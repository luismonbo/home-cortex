import asyncio
from unittest.mock import AsyncMock

import pytest

from brain.graph.runner import GraphRunner
from brain.graph.state import CortexState


@pytest.fixture
def mock_graph():
    graph = AsyncMock()
    graph.ainvoke.return_value = {"result": "light toggled"}
    return graph


@pytest.fixture
def runner(mock_graph):
    return GraphRunner(graph=mock_graph)


class TestDispatch:
    async def test_creates_background_task(self, runner):
        state = {
            "messages": [],
            "intent": "toggle_light",
            "source": "voice",
            "event_id": "abc-123",
            "next_agent": "",
            "result": "",
        }
        runner.dispatch(state)
        assert len(runner._tasks) == 1
        await asyncio.gather(*runner._tasks)

    async def test_invokes_graph_with_state(self, runner, mock_graph):
        state = {
            "messages": [],
            "intent": "toggle_light",
            "source": "voice",
            "event_id": "abc-123",
            "next_agent": "",
            "result": "",
        }
        runner.dispatch(state)
        await asyncio.gather(*runner._tasks)
        mock_graph.ainvoke.assert_called_once_with(state)

    async def test_task_removed_after_completion(self, runner):
        state = {
            "messages": [],
            "intent": "toggle_light",
            "source": "voice",
            "event_id": "abc-123",
            "next_agent": "",
            "result": "",
        }
        runner.dispatch(state)
        await asyncio.gather(*runner._tasks)
        assert len(runner._tasks) == 0


class TestShutdown:
    async def test_cancels_in_flight_tasks(self, runner):
        slow_graph = AsyncMock()
        slow_graph.ainvoke = AsyncMock(side_effect=lambda s: asyncio.sleep(10))
        runner._graph = slow_graph

        state = {
            "messages": [],
            "intent": "toggle_light",
            "source": "voice",
            "event_id": "abc-123",
            "next_agent": "",
            "result": "",
        }
        runner.dispatch(state)
        assert len(runner._tasks) == 1
        await runner.shutdown()
        assert len(runner._tasks) == 0


class TestGraphRunnerInvoke:
    async def test_invoke_returns_completed_state(self):
        expected_state = {
            "result": "The temperature is 23.4°C.",
            "messages": [],
            "intent": "temperature query",
            "source": "siri",
            "event_id": "abc",
            "next_agent": "homeassistant",
        }
        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = expected_state
        runner = GraphRunner(mock_graph)

        state = CortexState(
            messages=[],
            intent="temperature query",
            source="siri",
            event_id="abc",
            next_agent="",
            result="",
        )
        result = await runner.invoke(state)

        assert result["result"] == "The temperature is 23.4°C."
        mock_graph.ainvoke.assert_called_once_with(state)
