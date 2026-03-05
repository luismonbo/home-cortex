import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from brain.agents.base import AgentDefinition
from brain.graph.state import CortexState

logger = logging.getLogger(__name__)

ROUTER_SYSTEM_PROMPT = """\
You are a routing agent. Given a user intent, pick the best agent to handle it.

Available agents:
{agent_list}

Reply with only the agent name. If no agent fits, reply with "unknown".
"""


def build_supervisor(
    agents: list[AgentDefinition],
    router_model: str = "gpt-5-nano",
) -> CompiledStateGraph:
    agent_map = {a.name: a for a in agents}
    agent_list = "\n".join(f"- {a.name}: {a.description}" for a in agents)
    system_prompt = ROUTER_SYSTEM_PROMPT.format(agent_list=agent_list)
    llm = ChatOpenAI(model=router_model)

    async def router(state: CortexState) -> dict:
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=state["intent"]),
        ])
        name = response.content.strip().lower()
        if name not in agent_map:
            logger.warning("Router returned unrecognized agent: %r", name)
            name = "unknown"
        return {"next_agent": name}

    def route(state: CortexState) -> str:
        return state["next_agent"]

    graph = StateGraph(CortexState)
    graph.add_node("router", router)
    for agent in agents:
        graph.add_node(agent.name, agent.node_fn)

    graph.add_edge(START, "router")
    graph.add_conditional_edges(
        "router",
        route,
        {a.name: a.name for a in agents} | {"unknown": END},
    )
    for agent in agents:
        graph.add_edge(agent.name, END)

    return graph.compile()
