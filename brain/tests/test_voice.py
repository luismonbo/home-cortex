from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from brain.main import app


@contextmanager
def make_test_client(mock_event_store=None, mock_runner=None):
    if mock_event_store is None:
        mock_event_store = MagicMock()
        mock_event_store.store_event.return_value = "voice-uuid-123"

    if mock_runner is None:
        mock_runner = MagicMock()
        mock_runner.dispatch = MagicMock()
        mock_runner.invoke = AsyncMock(
            return_value={
                "result": "The temperature is 23.4°C.",
                "messages": [],
                "intent": "",
                "source": "",
                "event_id": "",
                "next_agent": "",
            }
        )
        mock_runner.shutdown = AsyncMock()

    mock_bot = MagicMock()
    mock_bot.start = AsyncMock()
    mock_bot.stop = AsyncMock()

    with patch("brain.main.MQTTListener") as MockListener, \
         patch("brain.main.EventStore", return_value=mock_event_store), \
         patch("brain.main.HAClient"), \
         patch("brain.main.build_ha_agent"), \
         patch("brain.main.build_memory_agent"), \
         patch("brain.main.build_supervisor_graph"), \
         patch("brain.main.GraphRunner", return_value=mock_runner), \
         patch("brain.main.Notifier"), \
         patch("brain.main.TelegramBot", return_value=mock_bot):
        instance = MockListener.return_value
        instance.start = AsyncMock()
        instance.stop = AsyncMock()

        with TestClient(app) as client:
            yield client, mock_event_store, mock_runner


class TestPostVoice:
    def test_returns_200_with_agent_response(self):
        with make_test_client() as (client, _, __):
            response = client.post("/voice", json={"query": "what is the temperature"})
        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "The temperature is 23.4°C."
        assert data["event_id"] == "voice-uuid-123"

    def test_missing_query_returns_422(self):
        with make_test_client() as (client, _, __):
            response = client.post("/voice", json={})
        assert response.status_code == 422

    def test_empty_string_query_returns_422(self):
        with make_test_client() as (client, _, __):
            response = client.post("/voice", json={"query": ""})
        assert response.status_code == 422

    def test_stores_event_in_chromadb(self):
        with make_test_client() as (client, mock_store, _):
            client.post("/voice", json={"query": "turn on the lights", "source": "siri"})
        mock_store.store_event.assert_called_once_with(
            intent="turn on the lights",
            payload={},
            source="siri",
        )

    def test_default_source_is_siri(self):
        with make_test_client() as (client, mock_store, _):
            client.post("/voice", json={"query": "turn on the lights"})
        mock_store.store_event.assert_called_once_with(
            intent="turn on the lights",
            payload={},
            source="siri",
        )

    def test_returns_sorry_when_graph_raises(self):
        mock_runner = MagicMock()
        mock_runner.dispatch = MagicMock()
        mock_runner.invoke = AsyncMock(side_effect=Exception("LLM timeout"))
        mock_runner.shutdown = AsyncMock()
        with make_test_client(mock_runner=mock_runner) as (client, _, __):
            response = client.post("/voice", json={"query": "turn on the lights"})
        assert response.status_code == 200
        assert response.json()["response"] == "Sorry, something went wrong. Please try again."

    def test_returns_sorry_when_result_is_empty(self):
        mock_runner = MagicMock()
        mock_runner.dispatch = MagicMock()
        mock_runner.invoke = AsyncMock(return_value={"result": "", "messages": []})
        mock_runner.shutdown = AsyncMock()
        with make_test_client(mock_runner=mock_runner) as (client, _, __):
            response = client.post("/voice", json={"query": "gibberish unknown intent"})
        assert response.status_code == 200
        assert response.json()["response"] == "Sorry, something went wrong. Please try again."

    def test_continues_and_invokes_graph_when_event_store_fails(self):
        mock_store = MagicMock()
        mock_store.store_event.side_effect = Exception("ChromaDB unreachable")
        with make_test_client(mock_event_store=mock_store) as (client, _, mock_runner):
            response = client.post("/voice", json={"query": "turn on the lights"})
        assert response.status_code == 200
        mock_runner.invoke.assert_called_once()

    def test_event_id_empty_string_when_store_fails(self):
        mock_store = MagicMock()
        mock_store.store_event.side_effect = Exception("ChromaDB unreachable")
        with make_test_client(mock_event_store=mock_store) as (client, _, __):
            response = client.post("/voice", json={"query": "turn on the lights"})
        assert response.json()["event_id"] == ""
