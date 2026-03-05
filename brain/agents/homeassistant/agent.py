from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from brain.agents.base import AgentDefinition
from brain.agents.homeassistant.prompts import ROUTING_DESCRIPTION, SYSTEM_PROMPT
from brain.agents.homeassistant.tools import make_tools
from brain.services.ha_client import HAClient


def build_ha_agent(ha_client: HAClient, model_name: str = "gpt-4o-mini") -> AgentDefinition:
    tools = make_tools(ha_client)
    llm = ChatOpenAI(model=model_name)
    react_agent = create_react_agent(llm, tools, prompt=SYSTEM_PROMPT)

    async def node(state):
        result = await react_agent.ainvoke({"messages": state["messages"]})
        return {"result": result["messages"][-1].content, "messages": result["messages"]}

    return AgentDefinition(
        name="homeassistant",
        description=ROUTING_DESCRIPTION,
        node_fn=node,
        tools=tools,
        model_name=model_name,
    )