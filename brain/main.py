import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI

from brain.agents.homeassistant.agent import build_ha_agent
from brain.agents.memory.agent import build_memory_agent
from brain.chromadb_store import EventStore
from brain.config import settings
from brain.graph.factory import build_supervisor_graph
from brain.graph.runner import GraphRunner
from brain.mqtt import MQTTListener
from brain.routers.voice import router as voice_router
from brain.routers.webhooks import router as webhooks_router
from brain.services.ha_client import HAClient
from brain.services.notifier import Notifier
from brain.services.transcriber import VoiceTranscriber
from brain.telegram_bot import TelegramBot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)


class SecretRedactFilter(logging.Filter):
    """Redacts sensitive tokens from log messages."""

    def __init__(self, secrets: list[str]) -> None:
        super().__init__()
        self._secrets = [s for s in secrets if s]

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        for secret in self._secrets:
            if secret in msg:
                record.msg = str(record.msg).replace(secret, "***REDACTED***")
                record.args = None
        return True


logging.getLogger().addFilter(
    SecretRedactFilter([settings.telegram_bot_token, settings.ha_token, settings.openai_api_key])
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    event_store = EventStore(settings)
    app.state.event_store = event_store

    ha_client = HAClient(settings.ha_base_url, settings.ha_token)
    ha_agent = build_ha_agent(ha_client, event_store=event_store, model_name=settings.ha_model)
    memory_agent = build_memory_agent(event_store)
    graph = build_supervisor_graph([ha_agent, memory_agent], router_model=settings.router_model)
    notifier = Notifier(settings)
    runner = GraphRunner(graph, notifier)
    app.state.runner = runner

    mqtt_listener = MQTTListener(settings)
    await mqtt_listener.start()

    if settings.telegram_bot_token:
        transcriber = VoiceTranscriber(settings)
        bot = TelegramBot(settings, event_store, runner, transcriber)
        await bot.start()
    else:
        bot = None

    yield

    if bot:
        await bot.stop()
    await mqtt_listener.stop()
    await runner.shutdown()


app = FastAPI(title="The Brain", lifespan=lifespan)
app.include_router(webhooks_router)
app.include_router(voice_router)


@app.get("/")
async def health():
    return {
        "status": "The Brain is active",
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    }
