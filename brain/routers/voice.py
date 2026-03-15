import logging

from fastapi import APIRouter, Request
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from brain.graph.state import CortexState

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["voice"])

SORRY_MESSAGE = "Sorry, something went wrong. Please try again."


class VoiceRequest(BaseModel):
    query: str
    source: str = "siri"


class VoiceResponse(BaseModel):
    response: str
    event_id: str


@router.post("", response_model=VoiceResponse)
async def voice_query(request_body: VoiceRequest, request: Request):
    event_store = request.app.state.event_store
    runner = request.app.state.runner

    event_id = ""
    try:
        event_id = event_store.store_event(
            intent=request_body.query,
            payload={},
            source=request_body.source,
        )
    except Exception:
        logger.exception(
            "Failed to store voice event (source=%s)", request_body.source
        )

    state = CortexState(
        messages=[HumanMessage(content=request_body.query)],
        intent=request_body.query,
        source=request_body.source,
        event_id=event_id,
        next_agent="",
        result="",
    )

    try:
        final_state = await runner.invoke(state)
        response_text = final_state.get("result", "")
        if not response_text:
            response_text = SORRY_MESSAGE
    except Exception:
        logger.exception("Graph execution failed for voice query")
        response_text = SORRY_MESSAGE

    return VoiceResponse(response=response_text, event_id=event_id)
