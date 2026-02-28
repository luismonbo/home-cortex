import json
from unittest.mock import MagicMock, patch

import pytest

from brain.config import Settings


@pytest.fixture
def test_settings():
    return Settings(chromadb_host="localhost", chromadb_port=8000)


@pytest.fixture
def mock_collection():
    return MagicMock()


@pytest.fixture
def mock_chroma_client(mock_collection):
    client = MagicMock()
    client.get_or_create_collection.return_value = mock_collection
    return client


class TestEventStoreInit:
    def test_creates_http_client_with_settings(self, test_settings, mock_chroma_client):
        with patch("brain.chromadb_store.chromadb.HttpClient", return_value=mock_chroma_client) as mock_cls:
            from brain.chromadb_store import EventStore

            store = EventStore(test_settings)
            mock_cls.assert_called_once_with(host="localhost", port=8000)

    def test_gets_or_creates_collection(self, test_settings, mock_chroma_client):
        with patch("brain.chromadb_store.chromadb.HttpClient", return_value=mock_chroma_client):
            from brain.chromadb_store import EventStore

            store = EventStore(test_settings)
            mock_chroma_client.get_or_create_collection.assert_called_once_with("webhook_events")


class TestEventStoreStoreEvent:
    def test_store_event_returns_string_id(self, test_settings, mock_chroma_client):
        with patch("brain.chromadb_store.chromadb.HttpClient", return_value=mock_chroma_client):
            from brain.chromadb_store import EventStore

            store = EventStore(test_settings)
            event_id = store.store_event(intent="toggle_light", payload={"entity": "light.bedroom"}, source="voice")
            assert isinstance(event_id, str)
            assert len(event_id) > 0

    def test_store_event_adds_to_collection(self, test_settings, mock_chroma_client, mock_collection):
        with patch("brain.chromadb_store.chromadb.HttpClient", return_value=mock_chroma_client):
            from brain.chromadb_store import EventStore

            store = EventStore(test_settings)
            event_id = store.store_event(intent="toggle_light", payload={"entity": "light.bedroom"}, source="voice")

            mock_collection.add.assert_called_once()
            call_kwargs = mock_collection.add.call_args[1]

            assert call_kwargs["ids"] == [event_id]
            assert "toggle_light" in call_kwargs["documents"][0]
            assert "voice" in call_kwargs["documents"][0]
            assert call_kwargs["metadatas"][0]["intent"] == "toggle_light"
            assert call_kwargs["metadatas"][0]["source"] == "voice"
            assert "timestamp" in call_kwargs["metadatas"][0]


class TestEventStoreSearchEvents:
    def test_search_events_queries_collection(self, test_settings, mock_chroma_client, mock_collection):
        mock_collection.query.return_value = {
            "ids": [["id1"]],
            "documents": [["intent: toggle_light | source: voice"]],
            "metadatas": [[{"intent": "toggle_light", "source": "voice", "timestamp": "2026-02-28T12:00:00Z"}]],
        }

        with patch("brain.chromadb_store.chromadb.HttpClient", return_value=mock_chroma_client):
            from brain.chromadb_store import EventStore

            store = EventStore(test_settings)
            results = store.search_events("light", n_results=3)

            mock_collection.query.assert_called_once_with(query_texts=["light"], n_results=3)
            assert len(results) == 1
            assert results[0]["intent"] == "toggle_light"
