import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI

from brain.chromadb_store import EventStore
from brain.config import settings
from brain.mqtt import MQTTListener
from brain.routers.webhooks import router as webhooks_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    event_store = EventStore(settings)
    app.state.event_store = event_store

    mqtt_listener = MQTTListener(settings)
    await mqtt_listener.start()
    yield
    await mqtt_listener.stop()


app = FastAPI(title="The Brain", lifespan=lifespan)
app.include_router(webhooks_router)


@app.get("/")
async def health():
    return {
        "status": "The Brain is active",
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    }
