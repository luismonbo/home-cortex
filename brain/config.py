from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mqtt_broker: str = "mosquitto"
    mqtt_port: int = 1883
    mqtt_topic: str = "homeassistant/#"
    pi_host_ip: str = ""
    ha_token: str = ""
    chromadb_host: str = "chromadb"
    chromadb_port: int = 8000
    openai_api_key: str = ""
    ha_base_url: str = "http://homeassistant:8123"
    graph_pattern: str = "supervisor"


settings = Settings()
