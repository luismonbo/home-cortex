import logging
from typing import Any

from fastapi import APIRouter, Request
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


@router.post("/event", response_model=WebhookResponse, status_code=201)
async def receive_event(event: WebhookEvent, request: Request):
    event_store = request.app.state.event_store
    event_id = event_store.store_event(
        intent=event.intent,
        payload=event.payload,
        source=event.source,
    )
    logger.info("Webhook received: intent=%s source=%s id=%s", event.intent, event.source, event_id)
    return WebhookResponse(status="received", event_id=event_id)
