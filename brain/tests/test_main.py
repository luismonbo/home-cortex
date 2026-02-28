from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from brain.main import app


def test_health_endpoint():
    with patch("brain.main.MQTTListener") as MockListener, \
         patch("brain.main.EventStore", return_value=MagicMock()):
        instance = MockListener.return_value
        instance.start = AsyncMock()
        instance.stop = AsyncMock()

        with TestClient(app) as client:
            response = client.get("/")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "The Brain is active"
            assert "python" in data
