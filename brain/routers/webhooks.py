import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hooks", tags=["webhooks"])


class WebhookEvent(BaseModel):
    intent: str
    payload: dict[str, Any] = {}
    source: str = "unknown"


class WebhookResponse(BaseModel):
    status: str
    event_id: str


class SearchQuery(BaseModel):
    query: str
    n_results: int = 5


@router.post("/event", response_model=WebhookResponse, status_code=201)
async def receive_event(event: WebhookEvent, request: Request):
    event_store = request.app.state.event_store
    try:
        event_id = event_store.store_event(
            intent=event.intent,
            payload=event.payload,
            source=event.source,
        )
    except Exception:
        logger.exception("Failed to store event (intent=%s, source=%s)", event.intent, event.source)
        raise HTTPException(status_code=503, detail="Event storage unavailable")
    logger.info("Webhook received: intent=%s source=%s id=%s", event.intent, event.source, event_id)
    return WebhookResponse(status="received", event_id=event_id)


@router.post("/search")
async def search_events(search: SearchQuery, request: Request):
    event_store = request.app.state.event_store
    try:
        results = event_store.search_events(query=search.query, n_results=search.n_results)
    except Exception:
        logger.exception("Failed to search events")
        raise HTTPException(status_code=503, detail="Event search unavailable")
    return {"results": results}
