from unittest.mock import MagicMock, patch

import pytest

from brain.config import Settings
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction


@pytest.fixture
def test_settings():
    return Settings(
        chromadb_host="localhost",
        chromadb_port=8000,
        openai_api_key="test-key",
        embedding_model="text-embedding-3-small",
    )


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
        with patch("brain.chromadb_store.chromadb.HttpClient", return_value=mock_chroma_client), \
             patch("brain.chromadb_store.OpenAIEmbeddingFunction"):
            from brain.chromadb_store import EventStore

            store = EventStore(test_settings)

    def test_gets_or_creates_collection_with_embedding_function(self, test_settings, mock_chroma_client):
        mock_ef = MagicMock()
        with patch("brain.chromadb_store.chromadb.HttpClient", return_value=mock_chroma_client), \
             patch("brain.chromadb_store.OpenAIEmbeddingFunction", return_value=mock_ef) as mock_ef_cls:
            from brain.chromadb_store import EventStore

            store = EventStore(test_settings)
            mock_ef_cls.assert_called_once_with(
                api_key="test-key",
                model_name="text-embedding-3-small",
            )
            mock_chroma_client.get_or_create_collection.assert_called_once_with(
                "webhook_events",
                embedding_function=mock_ef,
            )

    def test_raises_and_logs_on_connection_failure(self, test_settings, caplog):
        failing_client = MagicMock()
        failing_client.get_or_create_collection.side_effect = Exception("Connection refused")

        with patch("brain.chromadb_store.chromadb.HttpClient", return_value=failing_client), \
             patch("brain.chromadb_store.OpenAIEmbeddingFunction"):
            from brain.chromadb_store import EventStore

            with pytest.raises(Exception, match="Connection refused"):
                EventStore(test_settings)

            assert "failed to connect to ChromaDB" in caplog.text


class TestEventStoreStoreEvent:
    def test_store_event_returns_string_id(self, test_settings, mock_chroma_client):
        with patch("brain.chromadb_store.chromadb.HttpClient", return_value=mock_chroma_client), \
             patch("brain.chromadb_store.OpenAIEmbeddingFunction"):
            from brain.chromadb_store import EventStore

            store = EventStore(test_settings)
            event_id = store.store_event(intent="toggle_light", payload={"entity": "light.bedroom"}, source="voice")
            assert isinstance(event_id, str)
            assert len(event_id) > 0

    def test_store_event_adds_to_collection(self, test_settings, mock_chroma_client, mock_collection):
        with patch("brain.chromadb_store.chromadb.HttpClient", return_value=mock_chroma_client), \
             patch("brain.chromadb_store.OpenAIEmbeddingFunction"):
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
            assert "timestamp_unix" in call_kwargs["metadatas"][0]
            assert isinstance(call_kwargs["metadatas"][0]["timestamp_unix"], float)


class TestEventStoreSearchEvents:
    def test_search_events_queries_collection(self, test_settings, mock_chroma_client, mock_collection):
        mock_collection.query.return_value = {
            "ids": [["id1"]],
            "documents": [["intent: toggle_light | source: voice"]],
            "metadatas": [[{"intent": "toggle_light", "source": "voice", "timestamp": "2026-02-28T12:00:00Z"}]],
        }

        with patch("brain.chromadb_store.chromadb.HttpClient", return_value=mock_chroma_client), \
             patch("brain.chromadb_store.OpenAIEmbeddingFunction"):
            from brain.chromadb_store import EventStore

            store = EventStore(test_settings)
            results = store.search_events("light", n_results=3)

            mock_collection.query.assert_called_once_with(query_texts=["light"], n_results=3, where=None)
            assert len(results) == 1
            assert results[0]["intent"] == "toggle_light"

    def test_search_events_returns_empty_list_when_no_results(self, test_settings, mock_chroma_client, mock_collection):
        mock_collection.query.return_value = {
            "ids": [],
            "documents": [],
            "metadatas": [],
        }

        with patch("brain.chromadb_store.chromadb.HttpClient", return_value=mock_chroma_client), \
             patch("brain.chromadb_store.OpenAIEmbeddingFunction"):
            from brain.chromadb_store import EventStore

            store = EventStore(test_settings)
            results = store.search_events("nonexistent")

            assert results == []

    def test_search_events_filters_by_date_from(self, test_settings, mock_chroma_client, mock_collection):
        from datetime import datetime, timezone
        mock_collection.query.return_value = {"ids": [[]], "documents": [[]], "metadatas": [[]]}

        with patch("brain.chromadb_store.chromadb.HttpClient", return_value=mock_chroma_client), \
             patch("brain.chromadb_store.OpenAIEmbeddingFunction"):
            from brain.chromadb_store import EventStore

            store = EventStore(test_settings)
            store.search_events("light", date_from="2026-04-07T00:00:00+00:00")

            expected_unix = datetime.fromisoformat("2026-04-07T00:00:00+00:00").timestamp()
            mock_collection.query.assert_called_once_with(
                query_texts=["light"],
                n_results=5,
                where={"timestamp_unix": {"$gte": expected_unix}},
            )

    def test_search_events_filters_by_date_to(self, test_settings, mock_chroma_client, mock_collection):
        from datetime import datetime, timezone
        mock_collection.query.return_value = {"ids": [[]], "documents": [[]], "metadatas": [[]]}

        with patch("brain.chromadb_store.chromadb.HttpClient", return_value=mock_chroma_client), \
             patch("brain.chromadb_store.OpenAIEmbeddingFunction"):
            from brain.chromadb_store import EventStore

            store = EventStore(test_settings)
            store.search_events("light", date_to="2026-04-07T23:59:59+00:00")

            expected_unix = datetime.fromisoformat("2026-04-07T23:59:59+00:00").timestamp()
            mock_collection.query.assert_called_once_with(
                query_texts=["light"],
                n_results=5,
                where={"timestamp_unix": {"$lte": expected_unix}},
            )

    def test_search_events_filters_by_date_range(self, test_settings, mock_chroma_client, mock_collection):
        from datetime import datetime, timezone
        mock_collection.query.return_value = {"ids": [[]], "documents": [[]], "metadatas": [[]]}

        with patch("brain.chromadb_store.chromadb.HttpClient", return_value=mock_chroma_client), \
             patch("brain.chromadb_store.OpenAIEmbeddingFunction"):
            from brain.chromadb_store import EventStore

            store = EventStore(test_settings)
            store.search_events(
                "light",
                date_from="2026-03-01T00:00:00+00:00",
                date_to="2026-03-31T23:59:59+00:00",
            )

            expected_from = datetime.fromisoformat("2026-03-01T00:00:00+00:00").timestamp()
            expected_to = datetime.fromisoformat("2026-03-31T23:59:59+00:00").timestamp()
            mock_collection.query.assert_called_once_with(
                query_texts=["light"],
                n_results=5,
                where={"$and": [
                    {"timestamp_unix": {"$gte": expected_from}},
                    {"timestamp_unix": {"$lte": expected_to}},
                ]},
            )
