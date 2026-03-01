from langchain_core.tools import tool

from brain.services.ha_client import HAClient


def make_tools(ha_client: HAClient) -> list:
    @tool
    async def toggle_entity(entity_id: str) -> str:
        """Toggle a Home Assistant entity on or off."""
        result = await ha_client.call_service(
            domain=entity_id.split(".")[0],
            service="toggle",
            entity_id=entity_id,
        )
        return f"Toggled {entity_id}: {result}"

    @tool
    async def get_entity_state(entity_id: str) -> str:
        """Get the current state of a Home Assistant entity."""
        result = await ha_client.get_state(entity_id)
        return f"{entity_id} is {result['state']}"

    @tool
    async def call_service(
        domain: str, service: str, entity_id: str, data: str = ""
    ) -> str:
        """Call any Home Assistant service. Pass data as JSON string if needed."""
        import json

        extra = json.loads(data) if data else None
        result = await ha_client.call_service(domain, service, entity_id, extra)
        return f"Called {domain}/{service} on {entity_id}: {result}"

    return [toggle_entity, get_entity_state, call_service]