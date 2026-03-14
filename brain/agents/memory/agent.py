from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from brain.agents.base import AgentDefinition
from brain.agents.memory.prompts import ROUTING_DESCRIPTION, SYSTEM_PROMPT
from brain.agents.memory.tools import make_tools
from brain.chromadb_store import EventStore
from brain.config import settings


def build_memory_agent(
    event_store: EventStore,
    model_name: str = settings.ha_model,
) -> AgentDefinition:
    tools = make_tools(event_store)
    llm = ChatOpenAI(model=model_name)
    react_agent = create_agent(llm, tools, system_prompt=SYSTEM_PROMPT)

    async def node(state):
        result = await react_agent.ainvoke({"messages": state["messages"]})
        return {"result": result["messages"][-1].content, "messages": result["messages"]}

    return AgentDefinition(
        name="memory",
        description=ROUTING_DESCRIPTION,
        node_fn=node,
        tools=tools,
        model_name=model_name,
    )
