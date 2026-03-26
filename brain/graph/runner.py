import asyncio
import logging
from typing import TYPE_CHECKING

from langgraph.graph.state import CompiledStateGraph
from brain.graph.state import CortexState

if TYPE_CHECKING:
    from brain.services.notifier import Notifier

logger = logging.getLogger(__name__)


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

    async def shutdown(self) -> None:
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
