import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from brain.agents.base import AgentDefinition
from brain.graph.state import CortexState

logger = logging.getLogger(__name__)

ROUTER_SYSTEM_PROMPT = """\
You are a routing agent. Given a user message, select the single best agent
to handle it. Routing must work regardless of the input language.

Available agents:
{agent_list}

## Examples
- "Turn off the kitchen light" → homeassistant
- "What's the temperature in the bedroom?" → homeassistant
- "Apaga la luz del salón" → homeassistant
- "What did I ask you to do this morning?" → memory
- "Show me recent actions" → memory
- "Did I turn off the lights last night?" → memory
- "Hey, how's it going?" → unknown
- "What time is it?" → unknown

## Rules
- Reply with ONLY the agent name (lowercase). Nothing else.
- If the message is conversational with no home automation intent, reply: unknown
- When in doubt between two agents, prefer homeassistant.
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
    async def fallback(state: CortexState) -> dict:
        response = await llm.ainvoke([
            SystemMessage(
                content="You are Cortex, a smart home assistant. The user sent a "
                "conversational message that doesn't require any home automation action. "
                "Reply briefly and naturally in the same language the user used. "
                "Do not offer to do things you cannot do."
            ),
            HumanMessage(content=state["intent"]),
        ])
        return {"result": response.content}

    graph.add_node("fallback", fallback)
    graph.add_conditional_edges(
        "router",
        route,
        {a.name: a.name for a in agents} | {"unknown": "fallback"},
    )
    for agent in agents:
        graph.add_edge(agent.name, END)
    graph.add_edge("fallback", END)

    return graph.compile()
