from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from langchain_core.tools import BaseTool


@dataclass
class AgentDefinition:
    name: str
    description: str
    node_fn: Callable
    tools: Sequence[BaseTool] = field(default_factory=list)
    model_name: str = "gpt-5-nano"
