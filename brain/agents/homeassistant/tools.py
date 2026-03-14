from langchain_core.tools import tool

from brain.chromadb_store import EventStore
from brain.services.ha_client import HAClient


def make_tools(ha_client: HAClient, event_store: EventStore | None = None) -> list:
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

    tools = [toggle_entity, get_entity_state, call_service]

    if event_store is not None:
        from brain.agents.memory.tools import make_tools as make_memory_tools
        tools.extend(make_memory_tools(event_store))

    return tools