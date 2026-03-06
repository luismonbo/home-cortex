from unittest.mock import patch

from langgraph.graph.state import CompiledStateGraph

from brain.agents.base import AgentDefinition
from brain.graph.factory import build_supervisor_graph


def make_agent(name: str) -> AgentDefinition:
    async def node_fn(state):
        return {"result": "done"}

    return AgentDefinition(
        name=name,
        description="A test agent.",
        node_fn=node_fn,
    )


class TestBuildSupervisorGraph:
    def test_returns_compiled_graph(self):
        agent = make_agent("homeassistant")
        with patch("brain.graph.patterns.supervisor.ChatOpenAI"):
            graph = build_supervisor_graph([agent])
        assert isinstance(graph, CompiledStateGraph)

    def test_accepts_custom_router_model(self):
        agent = make_agent("homeassistant")
        with patch("brain.graph.patterns.supervisor.ChatOpenAI") as MockLLM:
            build_supervisor_graph([agent], router_model="gpt-5-nano")
        MockLLM.assert_called_once_with(model="gpt-5-nano")
