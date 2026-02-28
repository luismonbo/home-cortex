import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from brain.config import Settings
from brain.mqtt import MQTTListener


@pytest.fixture
def test_settings():
    return Settings(mqtt_broker="localhost", mqtt_port=1883, mqtt_topic="test/#")


class TestMQTTListenerLifecycle:
    def test_stores_settings(self, test_settings):
        listener = MQTTListener(test_settings)
        assert listener.settings.mqtt_broker == "localhost"
        assert listener.settings.mqtt_topic == "test/#"

    def test_task_is_none_before_start(self, test_settings):
        listener = MQTTListener(test_settings)
        assert listener._task is None

    async def test_start_creates_background_task(self, test_settings):
        listener = MQTTListener(test_settings)
        with patch.object(listener, "_listen_forever", new_callable=AsyncMock):
            await listener.start()
            assert listener._task is not None
            assert not listener._task.done()
            await listener.stop()

    async def test_stop_cancels_task(self, test_settings):
        listener = MQTTListener(test_settings)
        with patch.object(listener, "_listen_forever", new_callable=AsyncMock) as mock:
            mock.side_effect = asyncio.CancelledError
            await listener.start()
            await listener.stop()
            assert listener._task.cancelled() or listener._task.done()

    async def test_stop_is_safe_when_not_started(self, test_settings):
        listener = MQTTListener(test_settings)
        await listener.stop()  # Should not raise


class TestMQTTListenerMessages:
    async def test_subscribes_and_logs_message(self, test_settings, caplog):
        fake_message = MagicMock()
        fake_message.topic = "homeassistant/input_boolean/test_switch/state"
        fake_message.payload = b"on"

        received = asyncio.Event()

        mock_client = AsyncMock()
        mock_client.subscribe = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        async def fake_messages(_self):
            yield fake_message
            received.set()
            await asyncio.Event().wait()  # Block until cancelled

        mock_client.messages.__aiter__ = fake_messages

        listener = MQTTListener(test_settings)

        with (
            patch("brain.mqtt.aiomqtt.Client", return_value=mock_client),
            caplog.at_level(logging.INFO, logger="brain.mqtt"),
        ):
            task = asyncio.create_task(listener._listen_forever())
            await received.wait()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

            mock_client.subscribe.assert_called_once_with("test/#")
            assert "test_switch" in caplog.text
            assert "on" in caplog.text

    async def test_reconnects_on_mqtt_error(self, test_settings, caplog):
        from aiomqtt import MqttError

        call_count = 0
        mock_client = AsyncMock()

        async def failing_connect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise MqttError("Connection refused")
            await asyncio.Event().wait()

        mock_client.__aenter__ = failing_connect
        mock_client.__aexit__ = AsyncMock(return_value=False)

        listener = MQTTListener(test_settings)

        with (
            patch("brain.mqtt.aiomqtt.Client", return_value=mock_client),
            patch("brain.mqtt.RECONNECT_INTERVAL", 0.01),
            caplog.at_level(logging.WARNING, logger="brain.mqtt"),
        ):
            task = asyncio.create_task(listener._listen_forever())
            await asyncio.sleep(0.1)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

            assert call_count >= 2
            assert "Connection lost" in caplog.text