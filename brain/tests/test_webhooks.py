from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from brain.main import app


class TestPostHooksEvent:
    def _make_client(self, mock_event_store=None):
        """Create a test client with mocked lifespan dependencies."""
        if mock_event_store is None:
            mock_event_store = MagicMock()
            mock_event_store.store_event.return_value = "test-uuid-123"

        with patch("brain.main.MQTTListener") as MockListener, \
             patch("brain.main.EventStore", return_value=mock_event_store):
            instance = MockListener.return_value
            instance.start = AsyncMock()
            instance.stop = AsyncMock()

            with TestClient(app) as client:
                return client, mock_event_store

    def test_valid_event_returns_201(self):
        client, _ = self._make_client()
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
        client, mock_store = self._make_client()
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
        client, mock_store = self._make_client()
        response = client.post("/hooks/event", json={"intent": "ping"})
        assert response.status_code == 201
        mock_store.store_event.assert_called_once_with(
            intent="ping",
            payload={},
            source="unknown",
        )

    def test_missing_intent_returns_422(self):
        client, _ = self._make_client()
        response = client.post("/hooks/event", json={"source": "voice"})
        assert response.status_code == 422
