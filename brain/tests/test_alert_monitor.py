from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import yaml

from brain.services.alert_monitor import (
    AlertMonitor,
    AlertRule,
    _matches,
    _parse_value,
    load_alert_rules,
)


# ---------------------------------------------------------------------------
# _parse_value
# ---------------------------------------------------------------------------


class TestParseValue:
    def test_plain_float(self):
        assert _parse_value("23.5") == 23.5

    def test_plain_integer(self):
        assert _parse_value("18") == 18.0

    def test_strips_whitespace(self):
        assert _parse_value("  26.0  ") == 26.0

    def test_json_value_key(self):
        assert _parse_value('{"value": 21.3}') == 21.3

    def test_json_state_key(self):
        assert _parse_value('{"state": "19.0"}') == 19.0

    def test_json_temperature_key(self):
        assert _parse_value('{"temperature": 27.1}') == 27.1

    def test_json_moisture_key(self):
        assert _parse_value('{"moisture": 15.0}') == 15.0

    def test_returns_none_for_text(self):
        assert _parse_value("unavailable") is None

    def test_returns_none_for_empty(self):
        assert _parse_value("") is None

    def test_returns_none_for_unrecognised_json(self):
        assert _parse_value('{"unit": "°C"}') is None


# ---------------------------------------------------------------------------
# _matches
# ---------------------------------------------------------------------------


class TestMatches:
    def test_greater_than_true(self):
        rule = AlertRule(topic="t", condition=">", threshold=26.0, message="")
        assert _matches(27.0, rule) is True

    def test_greater_than_false(self):
        rule = AlertRule(topic="t", condition=">", threshold=26.0, message="")
        assert _matches(26.0, rule) is False

    def test_less_than_true(self):
        rule = AlertRule(topic="t", condition="<", threshold=18.0, message="")
        assert _matches(17.9, rule) is True

    def test_less_than_false(self):
        rule = AlertRule(topic="t", condition="<", threshold=18.0, message="")
        assert _matches(18.0, rule) is False

    def test_greater_equal(self):
        rule = AlertRule(topic="t", condition=">=", threshold=26.0, message="")
        assert _matches(26.0, rule) is True

    def test_less_equal(self):
        rule = AlertRule(topic="t", condition="<=", threshold=18.0, message="")
        assert _matches(18.0, rule) is True

    def test_equal(self):
        rule = AlertRule(topic="t", condition="==", threshold=20.0, message="")
        assert _matches(20.0, rule) is True

    def test_unknown_condition_returns_false(self):
        rule = AlertRule(topic="t", condition="!=", threshold=20.0, message="")
        assert _matches(20.0, rule) is False


# ---------------------------------------------------------------------------
# AlertMonitor.handle_message
# ---------------------------------------------------------------------------


class TestAlertMonitorHandleMessage:
    def _make_notifier(self):
        notifier = AsyncMock()
        notifier.send = AsyncMock()
        return notifier

    async def test_sends_alert_when_condition_met(self):
        rule = AlertRule(
            topic="sensors/temperature",
            condition=">",
            threshold=26.0,
            message="Too hot: {value:.1f}°C",
        )
        notifier = self._make_notifier()
        monitor = AlertMonitor([rule], notifier)

        await monitor.handle_message("sensors/temperature", "27.0")

        notifier.send.assert_called_once_with("Too hot: 27.0°C")

    async def test_no_alert_when_condition_not_met(self):
        rule = AlertRule(
            topic="sensors/temperature",
            condition=">",
            threshold=26.0,
            message="Too hot: {value:.1f}°C",
        )
        notifier = self._make_notifier()
        monitor = AlertMonitor([rule], notifier)

        await monitor.handle_message("sensors/temperature", "25.0")

        notifier.send.assert_not_called()

    async def test_no_alert_for_unrelated_topic(self):
        rule = AlertRule(
            topic="sensors/temperature",
            condition=">",
            threshold=26.0,
            message="Too hot",
        )
        notifier = self._make_notifier()
        monitor = AlertMonitor([rule], notifier)

        await monitor.handle_message("sensors/humidity", "27.0")

        notifier.send.assert_not_called()

    async def test_no_alert_for_unparseable_payload(self):
        rule = AlertRule(
            topic="sensors/temperature",
            condition=">",
            threshold=26.0,
            message="Too hot",
        )
        notifier = self._make_notifier()
        monitor = AlertMonitor([rule], notifier)

        await monitor.handle_message("sensors/temperature", "unavailable")

        notifier.send.assert_not_called()

    async def test_cooldown_suppresses_repeat_alert(self):
        rule = AlertRule(
            topic="sensors/temperature",
            condition=">",
            threshold=26.0,
            message="Too hot",
            cooldown_minutes=30.0,
        )
        notifier = self._make_notifier()
        monitor = AlertMonitor([rule], notifier)

        await monitor.handle_message("sensors/temperature", "27.0")
        await monitor.handle_message("sensors/temperature", "27.0")

        notifier.send.assert_called_once()

    async def test_alert_fires_again_after_cooldown_expires(self):
        rule = AlertRule(
            topic="sensors/temperature",
            condition=">",
            threshold=26.0,
            message="Too hot",
            cooldown_minutes=30.0,
        )
        notifier = self._make_notifier()
        monitor = AlertMonitor([rule], notifier)

        await monitor.handle_message("sensors/temperature", "27.0")

        # Simulate cooldown expiry by zeroing the last-alerted timestamp
        key = "sensors/temperature:>:26.0"
        monitor._last_alerted[key] = 0.0

        await monitor.handle_message("sensors/temperature", "27.0")

        assert notifier.send.call_count == 2

    async def test_independent_rules_have_separate_cooldowns(self):
        rules = [
            AlertRule(topic="t", condition=">", threshold=26.0, message="High"),
            AlertRule(topic="t", condition="<", threshold=18.0, message="Low"),
        ]
        notifier = self._make_notifier()
        monitor = AlertMonitor(rules, notifier)

        await monitor.handle_message("t", "27.0")  # triggers rule[0]
        await monitor.handle_message("t", "17.0")  # triggers rule[1]

        assert notifier.send.call_count == 2

    async def test_multiple_matching_rules_all_fire(self):
        rules = [
            AlertRule(topic="t", condition=">", threshold=25.0, message="Above 25"),
            AlertRule(topic="t", condition=">", threshold=24.0, message="Above 24"),
        ]
        notifier = self._make_notifier()
        monitor = AlertMonitor(rules, notifier)

        await monitor.handle_message("t", "26.0")

        assert notifier.send.call_count == 2


# ---------------------------------------------------------------------------
# load_alert_rules
# ---------------------------------------------------------------------------


class TestLoadAlertRules:
    def test_loads_rules_from_valid_file(self, tmp_path):
        config = tmp_path / "alerts.yaml"
        config.write_text(
            "rules:\n"
            "  - topic: sensors/temp\n"
            "    condition: '>'\n"
            "    threshold: 26\n"
            "    message: Too hot\n"
            "    cooldown_minutes: 15\n"
        )

        rules = load_alert_rules(config)

        assert len(rules) == 1
        assert rules[0].topic == "sensors/temp"
        assert rules[0].condition == ">"
        assert rules[0].threshold == 26.0
        assert rules[0].message == "Too hot"
        assert rules[0].cooldown_minutes == 15.0

    def test_returns_empty_list_when_file_missing(self, tmp_path):
        rules = load_alert_rules(tmp_path / "nonexistent.yaml")
        assert rules == []

    def test_returns_empty_list_for_empty_file(self, tmp_path):
        config = tmp_path / "alerts.yaml"
        config.write_text("")
        rules = load_alert_rules(config)
        assert rules == []

    def test_default_cooldown_is_30_minutes(self, tmp_path):
        config = tmp_path / "alerts.yaml"
        config.write_text(
            "rules:\n"
            "  - topic: t\n"
            "    condition: '>'\n"
            "    threshold: 10\n"
            "    message: msg\n"
        )
        rules = load_alert_rules(config)
        assert rules[0].cooldown_minutes == 30.0

    def test_loads_multiple_rules(self, tmp_path):
        config = tmp_path / "alerts.yaml"
        config.write_text(
            "rules:\n"
            "  - topic: t\n"
            "    condition: '>'\n"
            "    threshold: 26\n"
            "    message: High\n"
            "  - topic: t\n"
            "    condition: '<'\n"
            "    threshold: 18\n"
            "    message: Low\n"
        )
        rules = load_alert_rules(config)
        assert len(rules) == 2
