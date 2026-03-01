import httpx
import pytest

from brain.services.ha_client import HAClient


@pytest.fixture
def ha_client(httpx_mock):
    client = HAClient(base_url="http://ha-test:8123", token="test-token")
    yield client


class TestGetState:
    async def test_returns_entity_state(self, ha_client, httpx_mock):
        httpx_mock.add_response(
            url="http://ha-test:8123/api/states/light.bedroom",
            json={"entity_id": "light.bedroom", "state": "on"},
        )
        result = await ha_client.get_state("light.bedroom")
        assert result["state"] == "on"

    async def test_sends_auth_header(self, ha_client, httpx_mock):
        httpx_mock.add_response(
            url="http://ha-test:8123/api/states/light.bedroom",
            json={"state": "off"},
        )
        await ha_client.get_state("light.bedroom")
        request = httpx_mock.get_request()
        assert request.headers["Authorization"] == "Bearer test-token"

    async def test_raises_on_404(self, ha_client, httpx_mock):
        httpx_mock.add_response(
            url="http://ha-test:8123/api/states/light.nonexistent",
            status_code=404,
        )
        with pytest.raises(httpx.HTTPStatusError):
            await ha_client.get_state("light.nonexistent")


class TestCallService:
    async def test_calls_service(self, ha_client, httpx_mock):
        httpx_mock.add_response(
            url="http://ha-test:8123/api/services/light/toggle",
            json=[{"entity_id": "light.bedroom", "state": "on"}],
        )
        result = await ha_client.call_service("light", "toggle", "light.bedroom")
        assert result[0]["state"] == "on"

    async def test_sends_entity_id_in_body(self, ha_client, httpx_mock):
        httpx_mock.add_response(
            url="http://ha-test:8123/api/services/light/toggle",
            json=[],
        )
        await ha_client.call_service("light", "toggle", "light.bedroom")
        request = httpx_mock.get_request()
        import json
        body = json.loads(request.content)
        assert body["entity_id"] == "light.bedroom"

    async def test_merges_extra_data(self, ha_client, httpx_mock):
        httpx_mock.add_response(
            url="http://ha-test:8123/api/services/light/turn_on",
            json=[],
        )
        await ha_client.call_service(
            "light", "turn_on", "light.bedroom", data={"brightness": 128}
        )
        request = httpx_mock.get_request()
        import json
        body = json.loads(request.content)
        assert body["entity_id"] == "light.bedroom"
        assert body["brightness"] == 128

    async def test_raises_on_error(self, ha_client, httpx_mock):
        httpx_mock.add_response(
            url="http://ha-test:8123/api/services/light/toggle",
            status_code=500,
        )
        with pytest.raises(httpx.HTTPStatusError):
            await ha_client.call_service("light", "toggle", "light.bedroom")