import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

from langgraph.graph.state import CompiledStateGraph
from brain.graph.events import StreamEvent
from brain.graph.state import CortexState

if TYPE_CHECKING:
    from brain.services.notifier import Notifier

logger = logging.getLogger(__name__)

# Nodes to skip when emitting node_start events (internal routing, not user-facing)
_SKIP_NODES = frozenset({"__start__", "__end__"})


class GraphRunner:
    def __init__(self, graph: CompiledStateGraph, notifier: "Notifier | None" = None) -> None:
        self._graph = graph
        self._notifier = notifier
        self._tasks: set[asyncio.Task] = set()

    def dispatch(self, state: CortexState) -> None:
        task = asyncio.create_task(self._run(state))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _run(self, state: CortexState) -> None:
        result = await self._graph.ainvoke(state)
        result_text = result.get("result", "")
        logger.info("Graph completed: %s", result_text)
        if self._notifier and result_text:
            await self._notifier.send(result_text)

    async def invoke(self, state: CortexState) -> CortexState:
        result = await self._graph.ainvoke(state)
        logger.info("Graph completed (invoke): %s", result.get("result", ""))
        return result

    async def stream(self, state: CortexState) -> AsyncGenerator[StreamEvent]:
        current_agent = ""
        yielded_result = False
        async for event in self._graph.astream_events(state, version="v2"):
            kind = event.get("event", "")
            name = event.get("name", "")
            metadata = event.get("metadata", {})
            node = metadata.get("langgraph_node", "")

            if kind == "on_chain_start" and node and node not in _SKIP_NODES and node != current_agent:
                current_agent = node
                yield StreamEvent(kind="node_start", agent=current_agent)

            elif kind == "on_tool_start":
                yield StreamEvent(kind="tool_start", agent=node or current_agent, tool=name)

            elif kind == "on_tool_end":
                yield StreamEvent(kind="tool_end", agent=node or current_agent, tool=name)

            elif kind == "on_chain_end" and not yielded_result:
                output = event.get("data", {}).get("output", {})
                result_text = output.get("result", "") if isinstance(output, dict) else ""
                if result_text:
                    yielded_result = True
                    yield StreamEvent(kind="result", agent=current_agent, content=result_text)

    async def shutdown(self) -> None:
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
