import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import chromadb

from brain.config import Settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "webhook_events"


class EventStore:
    """Stores webhook events in ChromaDB for semantic search."""

    def __init__(self, settings: Settings) -> None:
        self._client = chromadb.HttpClient(
            host=settings.chromadb_host,
            port=settings.chromadb_port,
        )
        try:
            self._collection = self._client.get_or_create_collection(COLLECTION_NAME)
        except Exception as exc:
            logger.error(
                "EventStore failed to connect to ChromaDB at %s:%s: %s",
                settings.chromadb_host,
                settings.chromadb_port,
                exc,
            )
            raise
        logger.info(
            "EventStore connected (host=%s:%s)",
            settings.chromadb_host,
            settings.chromadb_port,
        )

    def store_event(self, intent: str, payload: dict[str, Any], source: str) -> str:
        event_id = str(uuid.uuid4())
        document = f"intent: {intent} | source: {source} | payload: {json.dumps(payload)}"
        metadata = {
            "intent": intent,
            "source": source,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self._collection.add(
            ids=[event_id],
            documents=[document],
            metadatas=[metadata],
        )

        logger.info("Stored event %s (intent=%s, source=%s)", event_id, intent, source)
        return event_id

    def search_events(self, query: str, n_results: int = 5) -> list[dict[str, Any]]:
        results = self._collection.query(query_texts=[query], n_results=n_results)
        if not results["ids"]:
            return []
        return [
            {**meta, "id": id_, "document": doc}
            for id_, doc, meta in zip(
                results["ids"][0],
                results["documents"][0],
                results["metadatas"][0],
            )
        ]
