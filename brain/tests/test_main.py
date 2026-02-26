from fastapi.testclient import TestClient

from brain.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "The Brain is active"
    assert "python" in data
