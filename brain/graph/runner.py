import asyncio
import logging

from langgraph.graph.state import CompiledStateGraph
from brain.graph.state import CortexState

logger = logging.getLogger(__name__)


class GraphRunner:
    def __init__(self, graph: CompiledStateGraph) -> None:
        self._graph = graph
        self._tasks: set[asyncio.Task] = set()

    def dispatch(self, state: CortexState) -> None:
        task = asyncio.create_task(self._run(state))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _run(self, state: CortexState) -> None:
        result = await self._graph.ainvoke(state)
        logger.info("Graph completed: %s", result.get("result", ""))

    async def shutdown(self) -> None:
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
