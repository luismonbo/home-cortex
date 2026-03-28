from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True, slots=True)
class StreamEvent:
    kind: Literal["node_start", "tool_start", "tool_end", "result"]
    agent: str
    tool: str | None = None
    content: str | None = None


class StreamReporter(Protocol):
    async def on_event(self, event: StreamEvent) -> None: ...
