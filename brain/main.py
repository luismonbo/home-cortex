import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI

from brain.config import settings
from brain.mqtt import MQTTListener

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    mqtt_listener = MQTTListener(settings)
    await mqtt_listener.start()
    yield
    await mqtt_listener.stop()


app = FastAPI(title="The Brain", lifespan=lifespan)


@app.get("/")
async def health():
    return {
        "status": "The Brain is active",
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    }
