from brain.config import Settings
from brain.agents.homeassistant.prompts import ROUTING_DESCRIPTION, SYSTEM_PROMPT


class TestSettings:
    def test_router_model_default(self):
        s = Settings()
        assert s.router_model == "gpt-5-nano"

    def test_ha_model_default(self):
        s = Settings()
        assert s.ha_model == "gpt-5-nano"

    def test_embedding_model_defaults_to_text_embedding_3_small(self):
        s = Settings(openai_api_key="test")
        assert s.embedding_model == "text-embedding-3-small"

    def test_telegram_bot_token_defaults_to_empty(self):
        s = Settings()
        assert s.telegram_bot_token == ""

    def test_telegram_chat_id_defaults_to_zero(self):
        s = Settings()
        assert s.telegram_chat_id == 0


class TestHAPrompts:
    def test_routing_description_exists(self):
        assert isinstance(ROUTING_DESCRIPTION, str)
        assert len(ROUTING_DESCRIPTION) > 0

    def test_system_prompt_exists(self):
        assert isinstance(SYSTEM_PROMPT, str)
