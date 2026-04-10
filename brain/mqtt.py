import asyncio
import logging
from collections.abc import Awaitable, Callable

import aiomqtt

from brain.config import Settings

logger = logging.getLogger(__name__)

RECONNECT_INTERVAL = 5


class MQTTListener:
    """Background MQTT subscriber that reconnects automatically."""

    def __init__(
        self,
        settings: Settings,
        message_handler: Callable[[str, str], Awaitable[None]] | None = None,
    ) -> None:
        self.settings = settings
        self._message_handler = message_handler
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self._task = asyncio.create_task(self._listen_forever())
        logger.info(
            "MQTT listener started (broker=%s:%s, topic=%s)",
            self.settings.mqtt_broker,
            self.settings.mqtt_port,
            self.settings.mqtt_topic,
        )

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        logger.info("MQTT listener stopped")

    async def _listen_forever(self) -> None:
        while True:
            try:
                async with aiomqtt.Client(
                    hostname=self.settings.mqtt_broker,
                    port=self.settings.mqtt_port,
                ) as client:
                    await client.subscribe(self.settings.mqtt_topic)
                    logger.info("Subscribed to %s", self.settings.mqtt_topic)
                    async for message in client.messages:
                        payload = message.payload.decode(errors="replace")
                        logger.info("[%s] %s", message.topic, payload)
                        if self._message_handler:
                            await self._message_handler(str(message.topic), payload)
            except aiomqtt.MqttError as e:
                logger.warning(
                    "Connection lost (%s). Reconnecting in %ds...",
                    e,
                    RECONNECT_INTERVAL,
                )
                await asyncio.sleep(RECONNECT_INTERVAL)
