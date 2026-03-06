import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI

from brain.agents.homeassistant.agent import build_ha_agent
from brain.chromadb_store import EventStore
from brain.config import settings
from brain.graph.factory import build_supervisor_graph
from brain.graph.runner import GraphRunner
from brain.mqtt import MQTTListener
from brain.routers.webhooks import router as webhooks_router
from brain.services.ha_client import HAClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    event_store = EventStore(settings)
    app.state.event_store = event_store

    ha_client = HAClient(settings)
    ha_agent = build_ha_agent(ha_client, model_name=settings.ha_model)
    graph = build_supervisor_graph([ha_agent], router_model=settings.router_model)
    runner = GraphRunner(graph)
    app.state.runner = runner

    mqtt_listener = MQTTListener(settings)
    await mqtt_listener.start()
    yield
    await mqtt_listener.stop()
    await runner.shutdown()


app = FastAPI(title="The Brain", lifespan=lifespan)
app.include_router(webhooks_router)


@app.get("/")
async def health():
    return {
        "status": "The Brain is active",
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    }
