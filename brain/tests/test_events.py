from brain.graph.events import StreamEvent


class TestStreamEvent:
    def test_node_start_event(self):
        event = StreamEvent(kind="node_start", agent="homeassistant")
        assert event.kind == "node_start"
        assert event.agent == "homeassistant"
        assert event.tool is None
        assert event.content is None

    def test_tool_start_event(self):
        event = StreamEvent(kind="tool_start", agent="homeassistant", tool="get_entity_state")
        assert event.tool == "get_entity_state"

    def test_result_event(self):
        event = StreamEvent(kind="result", agent="homeassistant", content="Soil moisture is 42%")
        assert event.content == "Soil moisture is 42%"
