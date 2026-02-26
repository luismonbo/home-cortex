import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: connect MQTT, ChromaDB, etc.
    yield
    # Shutdown: disconnect


app = FastAPI(title="The Brain", lifespan=lifespan)


@app.get("/")
async def health():
    return {
        "status": "The Brain is active",
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    }
