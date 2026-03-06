from langgraph.graph.state import CompiledStateGraph

from brain.agents.base import AgentDefinition
from brain.graph.patterns.supervisor import build_supervisor


def build_supervisor_graph(
    agents: list[AgentDefinition],
    router_model: str = "gpt-5-nano",
) -> CompiledStateGraph:
    return build_supervisor(agents, router_model=router_model)
