from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from brain.main import app


@contextmanager
def make_test_client(mock_event_store=None):
    if mock_event_store is None:
        mock_event_store = MagicMock()
        mock_event_store.store_event.return_value = "test-uuid-123"

    mock_runner = MagicMock()
    mock_runner.dispatch = MagicMock()
    mock_runner.shutdown = AsyncMock()

    with patch("brain.main.MQTTListener") as MockListener, \
         patch("brain.main.EventStore", return_value=mock_event_store), \
         patch("brain.main.HAClient"), \
         patch("brain.main.build_ha_agent"), \
         patch("brain.main.build_supervisor_graph"), \
         patch("brain.main.GraphRunner", return_value=mock_runner):
        instance = MockListener.return_value
        instance.start = AsyncMock()
        instance.stop = AsyncMock()

        with TestClient(app) as client:
            yield client, mock_event_store, mock_runner


class TestPostHooksEvent:
    def test_valid_event_returns_201(self):
        with make_test_client() as (client, _, __):
            response = client.post("/hooks/event", json={
                "intent": "toggle_light",
                "payload": {"entity": "light.bedroom"},
                "source": "voice",
            })
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "received"
        assert "event_id" in data

    def test_calls_event_store(self):
        with make_test_client() as (client, mock_store, _):
            client.post("/hooks/event", json={
                "intent": "toggle_light",
                "payload": {"entity": "light.bedroom"},
                "source": "voice",
            })
        mock_store.store_event.assert_called_once_with(
            intent="toggle_light",
            payload={"entity": "light.bedroom"},
            source="voice",
        )

    def test_minimal_payload_uses_defaults(self):
        with make_test_client() as (client, mock_store, _):
            response = client.post("/hooks/event", json={"intent": "ping"})
        assert response.status_code == 201
        mock_store.store_event.assert_called_once_with(
            intent="ping",
            payload={},
            source="unknown",
        )

    def test_missing_intent_returns_422(self):
        with make_test_client() as (client, _, __):
            response = client.post("/hooks/event", json={"source": "voice"})
        assert response.status_code == 422

    def test_returns_503_when_store_fails(self):
        mock_store = MagicMock()
        mock_store.store_event.side_effect = Exception("ChromaDB unreachable")
        with make_test_client(mock_event_store=mock_store) as (client, _, __):
            response = client.post("/hooks/event", json={"intent": "toggle_light"})
        assert response.status_code == 503
        assert response.json()["detail"] == "Event storage unavailable"

    def test_dispatches_to_runner_after_store(self):
        with make_test_client() as (client, _, mock_runner):
            client.post("/hooks/event", json={
                "intent": "Turn on the lights",
                "payload": {"entity": "light.bedroom"},
                "source": "voice",
            })
        mock_runner.dispatch.assert_called_once()
        state = mock_runner.dispatch.call_args[0][0]
        assert state["intent"] == "Turn on the lights"
        assert state["source"] == "voice"
        assert state["next_agent"] == ""
        assert state["result"] == ""
        assert len(state["messages"]) == 1
        assert state["event_id"] == "test-uuid-123"

    def test_does_not_dispatch_when_store_fails(self):
        mock_store = MagicMock()
        mock_store.store_event.side_effect = Exception("ChromaDB unreachable")
        with make_test_client(mock_event_store=mock_store) as (client, _, mock_runner):
            client.post("/hooks/event", json={"intent": "toggle_light"})
        mock_runner.dispatch.assert_not_called()


class TestPostHooksSearch:
    def test_search_returns_results(self):
        mock_store = MagicMock()
        mock_store.store_event.return_value = "test-uuid-123"
        mock_store.search_events.return_value = [
            {"id": "id1", "intent": "toggle_light", "source": "voice",
             "timestamp": "2026-02-28T12:00:00Z", "document": "intent: toggle_light"}
        ]
        with make_test_client(mock_event_store=mock_store) as (client, _, __):
            response = client.post("/hooks/search", json={"query": "light"})
        assert response.status_code == 200
        assert len(response.json()["results"]) == 1
        mock_store.search_events.assert_called_once_with(query="light", n_results=5)

    def test_search_returns_503_on_failure(self):
        mock_store = MagicMock()
        mock_store.store_event.return_value = "test-uuid-123"
        mock_store.search_events.side_effect = Exception("ChromaDB down")
        with make_test_client(mock_event_store=mock_store) as (client, _, __):
            response = client.post("/hooks/search", json={"query": "light"})
        assert response.status_code == 503

    def test_search_missing_query_returns_422(self):
        with make_test_client() as (client, _, __):
            response = client.post("/hooks/search", json={})
        assert response.status_code == 422
