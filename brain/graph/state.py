from typing import Annotated, TypedDict

from langgraph.graph import add_messages


class CortexState(TypedDict):
    messages: Annotated[list, add_messages(format="langchain-openai")]
    intent: str
    source: str
    event_id: str
    next_agent: str
    result: str
