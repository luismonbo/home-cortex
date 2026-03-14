from unittest.mock import MagicMock, patch

import pytest

from brain.agents.base import AgentDefinition
from brain.agents.memory.agent import build_memory_agent


@pytest.fixture
def mock_event_store():
    return MagicMock()


class TestBuildMemoryAgent:
    def test_returns_agent_definition(self, mock_event_store):
        with patch("brain.agents.memory.agent.ChatOpenAI"), \
             patch("brain.agents.memory.agent.create_agent"):
            agent = build_memory_agent(mock_event_store)
        assert isinstance(agent, AgentDefinition)

    def test_agent_name(self, mock_event_store):
        with patch("brain.agents.memory.agent.ChatOpenAI"), \
             patch("brain.agents.memory.agent.create_agent"):
            agent = build_memory_agent(mock_event_store)
        assert agent.name == "memory"

    def test_agent_has_search_tool(self, mock_event_store):
        with patch("brain.agents.memory.agent.ChatOpenAI"), \
             patch("brain.agents.memory.agent.create_agent"):
            agent = build_memory_agent(mock_event_store)
        assert len(agent.tools) == 1
        assert agent.tools[0].name == "search_past_events"

    def test_agent_description_mentions_history(self, mock_event_store):
        with patch("brain.agents.memory.agent.ChatOpenAI"), \
             patch("brain.agents.memory.agent.create_agent"):
            agent = build_memory_agent(mock_event_store)
        assert "past" in agent.description.lower() or "history" in agent.description.lower()
