from unittest.mock import AsyncMock

import pytest

from brain.agents.homeassistant.tools import make_tools


@pytest.fixture
def mock_ha_client():
    client = AsyncMock()
    client.get_state.return_value = {"entity_id": "light.bedroom", "state": "on"}
    client.call_service.return_value = [{"entity_id": "light.bedroom", "state": "on"}]
    return client


@pytest.fixture
def tools(mock_ha_client):
    return make_tools(mock_ha_client)


class TestToggleEntity:
    async def test_calls_toggle_service(self, tools, mock_ha_client):
        toggle = tools[0]
        result = await toggle.ainvoke({"entity_id": "light.bedroom"})
        mock_ha_client.call_service.assert_called_once_with(
            domain="light", service="toggle", entity_id="light.bedroom"
        )
        assert "Toggled light.bedroom" in result

    async def test_extracts_domain_from_entity_id(self, tools, mock_ha_client):
        toggle = tools[0]
        await toggle.ainvoke({"entity_id": "switch.fan"})
        mock_ha_client.call_service.assert_called_once_with(
            domain="switch", service="toggle", entity_id="switch.fan"
        )


class TestGetEntityState:
    async def test_returns_state(self, tools, mock_ha_client):
        get_state = tools[1]
        result = await get_state.ainvoke({"entity_id": "light.bedroom"})
        mock_ha_client.get_state.assert_called_once_with("light.bedroom")
        assert "light.bedroom is on" in result


class TestCallService:
    async def test_calls_service_without_data(self, tools, mock_ha_client):
        call_svc = tools[2]
        await call_svc.ainvoke({
            "domain": "light",
            "service": "turn_off",
            "entity_id": "light.bedroom",
        })
        mock_ha_client.call_service.assert_called_once_with(
            "light", "turn_off", "light.bedroom", None
        )

    async def test_calls_service_with_json_data(self, tools, mock_ha_client):
        call_svc = tools[2]
        await call_svc.ainvoke({
            "domain": "light",
            "service": "turn_on",
            "entity_id": "light.bedroom",
            "data": '{"brightness": 128}',
        })
        mock_ha_client.call_service.assert_called_once_with(
            "light", "turn_on", "light.bedroom", {"brightness": 128}
        )
