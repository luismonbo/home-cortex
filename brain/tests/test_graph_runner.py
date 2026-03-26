import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from brain.graph.runner import GraphRunner
from brain.graph.state import CortexState


@pytest.fixture
def mock_graph():
    graph = AsyncMock()
    graph.ainvoke.return_value = {"result": "light toggled"}
    return graph


@pytest.fixture
def mock_notifier():
    notifier = MagicMock()
    notifier.send = AsyncMock()
    return notifier


@pytest.fixture
def runner(mock_graph):
    return GraphRunner(graph=mock_graph)


@pytest.fixture
def runner_with_notifier(mock_graph, mock_notifier):
    return GraphRunner(graph=mock_graph, notifier=mock_notifier)


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


class TestDispatchNotifier:
    async def test_dispatch_calls_notifier_with_result(self, runner_with_notifier, mock_graph, mock_notifier):
        state = {
            "messages": [],
            "intent": "toggle_light",
            "source": "webhook",
            "event_id": "abc-123",
            "next_agent": "",
            "result": "",
        }
        runner_with_notifier.dispatch(state)
        await asyncio.gather(*runner_with_notifier._tasks)
        mock_notifier.send.assert_called_once_with("light toggled")

    async def test_dispatch_skips_notifier_when_result_empty(self, runner_with_notifier, mock_graph, mock_notifier):
        mock_graph.ainvoke.return_value = {"result": ""}
        state = {
            "messages": [],
            "intent": "toggle_light",
            "source": "webhook",
            "event_id": "abc-123",
            "next_agent": "",
            "result": "",
        }
        runner_with_notifier.dispatch(state)
        await asyncio.gather(*runner_with_notifier._tasks)
        mock_notifier.send.assert_not_called()

    async def test_dispatch_works_without_notifier(self, runner, mock_graph):
        state = {
            "messages": [],
            "intent": "toggle_light",
            "source": "webhook",
            "event_id": "abc-123",
            "next_agent": "",
            "result": "",
        }
        runner.dispatch(state)
        await asyncio.gather(*runner._tasks)
        mock_graph.ainvoke.assert_called_once()
