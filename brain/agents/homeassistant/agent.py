from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from brain.agents.base import AgentDefinition
from brain.agents.homeassistant.prompts import ROUTING_DESCRIPTION, SYSTEM_PROMPT
from brain.agents.homeassistant.tools import make_tools
from brain.chromadb_store import EventStore
from brain.config import settings
from brain.services.ha_client import HAClient


def build_ha_agent(
    ha_client: HAClient,
    event_store: EventStore | None = None,
    model_name: str = settings.ha_model,
) -> AgentDefinition:
    tools = make_tools(ha_client, event_store=event_store)
    llm = ChatOpenAI(model=model_name)
    agent = create_agent(llm, tools, system_prompt=SYSTEM_PROMPT)

    async def node(state):
        result = await agent.ainvoke({"messages": state["messages"]})
        return {"result": result["messages"][-1].content, "messages": result["messages"]}

    return AgentDefinition(
        name="homeassistant",
        description=ROUTING_DESCRIPTION,
        node_fn=node,
        tools=tools,
        model_name=model_name,
    )