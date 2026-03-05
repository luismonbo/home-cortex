from brain.config import Settings
from brain.agents.homeassistant.prompts import ROUTING_DESCRIPTION, SYSTEM_PROMPT


class TestSettings:
    def test_router_model_default(self):
        s = Settings()
        assert s.router_model == "gpt-5-nano"

    def test_ha_model_default(self):
        s = Settings()
        assert s.ha_model == "gpt-5-nano"


class TestHAPrompts:
    def test_routing_description_exists(self):
        assert isinstance(ROUTING_DESCRIPTION, str)
        assert len(ROUTING_DESCRIPTION) > 0

    def test_system_prompt_exists(self):
        assert isinstance(SYSTEM_PROMPT, str)
