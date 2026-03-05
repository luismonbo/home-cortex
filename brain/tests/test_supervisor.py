from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import HumanMessage
from langgraph.graph.state import CompiledStateGraph

from brain.agents.base import AgentDefinition
from brain.graph.patterns.supervisor import build_supervisor


def make_agent(name: str, description: str) -> AgentDefinition:
    async def node_fn(state):
        return {"result": f"{name} handled it"}

    return AgentDefinition(
        name=name,
        description=description,
        node_fn=node_fn,
    )


class TestBuildSupervisor:
    def test_returns_compiled_graph(self):
        agent = make_agent("homeassistant", "Controls smart home devices.")
        with patch("brain.graph.patterns.supervisor.ChatOpenAI"):
            graph = build_supervisor([agent])
        assert isinstance(graph, CompiledStateGraph)


class TestRouterNode:
    async def test_sets_next_agent_on_known_response(self):
        agent = make_agent("homeassistant", "Controls smart home devices.")
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(content="homeassistant")

        with patch("brain.graph.patterns.supervisor.ChatOpenAI", return_value=mock_llm):
            graph = build_supervisor([agent])

        state = {
            "messages": [HumanMessage(content="Turn on the lights")],
            "intent": "Turn on the lights",
            "source": "voice",
            "event_id": "abc",
            "next_agent": "",
            "result": "",
        }
        result = await graph.ainvoke(state)
        assert result["next_agent"] == "homeassistant"

    async def test_routes_to_end_on_unknown_response(self):
        agent = make_agent("homeassistant", "Controls smart home devices.")
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(content="nonexistent_agent")

        with patch("brain.graph.patterns.supervisor.ChatOpenAI", return_value=mock_llm):
            graph = build_supervisor([agent])

        state = {
            "messages": [HumanMessage(content="Do something weird")],
            "intent": "Do something weird",
            "source": "voice",
            "event_id": "abc",
            "next_agent": "",
            "result": "",
        }
        result = await graph.ainvoke(state)
        assert result["next_agent"] == "unknown"
