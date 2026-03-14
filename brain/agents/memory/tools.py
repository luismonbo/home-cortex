from langchain_core.tools import tool

from brain.chromadb_store import EventStore


def make_tools(event_store: EventStore) -> list:
    @tool
    async def search_past_events(query: str, n_results: int = 5) -> str:
        """Search past webhook events by semantic similarity to the query."""
        results = event_store.search_events(query, n_results)
        if not results:
            return "No past events found matching your query."
        lines = []
        for r in results:
            lines.append(
                f"[{r['timestamp']}] intent={r['intent']} source={r['source']}"
            )
        return "\n".join(lines)

    return [search_past_events]
