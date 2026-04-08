from datetime import datetime, timezone

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from brain.agents.base import AgentDefinition
from brain.agents.memory.prompts import ROUTING_DESCRIPTION, build_system_prompt
from brain.agents.memory.tools import make_tools
from brain.chromadb_store import EventStore
from brain.config import settings


def build_memory_agent(
    event_store: EventStore,
    model_name: str = settings.ha_model,
) -> AgentDefinition:
    tools = make_tools(event_store)
    llm = ChatOpenAI(model=model_name)

    async def node(state):
        current_dt = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
        react_agent = create_agent(llm, tools, system_prompt=build_system_prompt(current_dt))
        result = await react_agent.ainvoke({"messages": state["messages"]})
        return {"result": result["messages"][-1].content, "messages": result["messages"]}

    return AgentDefinition(
        name="memory",
        description=ROUTING_DESCRIPTION,
        node_fn=node,
        tools=tools,
        model_name=model_name,
    )
