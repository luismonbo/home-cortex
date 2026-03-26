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
        try:
            result = await ha_client.get_state(entity_id)
        except Exception:
            return f"Entity '{entity_id}' not found. Use search_ha_entities to find the correct entity ID."
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

    @tool
    async def search_ha_entities(query: str) -> str:
        """Search Home Assistant entities by name or keyword to find their entity IDs.
        Use this before calling get_entity_state or toggle_entity when you don't know
        the exact entity ID. Returns up to 5 matching entities with their current state."""
        try:
            all_states = await ha_client.get_all_states()
        except Exception as exc:
            return f"Entity search failed: {exc}"

        query_terms = query.lower().split()
        matches = []
        for entity in all_states:
            entity_id = entity.get("entity_id", "")
            attrs = entity.get("attributes", {})
            friendly_name = attrs.get("friendly_name", "")
            searchable = f"{entity_id} {friendly_name}".lower()
            score = sum(1 for term in query_terms if term in searchable)
            if score > 0:
                matches.append((score, entity))

        matches.sort(key=lambda x: x[0], reverse=True)
        top = matches[:5]

        if not top:
            return f"No entities found matching '{query}'"

        lines = []
        for _, entity in top:
            entity_id = entity["entity_id"]
            attrs = entity.get("attributes", {})
            friendly_name = attrs.get("friendly_name", entity_id)
            state = entity.get("state", "unknown")
            unit = attrs.get("unit_of_measurement", "")
            unit_str = f" {unit}" if unit else ""
            lines.append(f"{entity_id} ({friendly_name}): {state}{unit_str}")

        return "\n".join(lines)

    tools.append(search_ha_entities)
    return tools
