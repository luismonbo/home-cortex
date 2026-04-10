import json
import logging
from dataclasses import dataclass, field
from operator import eq, ge, gt, le, lt
from pathlib import Path
from time import monotonic
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from brain.services.notifier import Notifier

logger = logging.getLogger(__name__)

_OPS = {">": gt, "<": lt, ">=": ge, "<=": le, "==": eq}


@dataclass(frozen=True)
class AlertRule:
    topic: str
    condition: str
    threshold: float
    message: str
    cooldown_minutes: float = 30.0


class AlertMonitor:
    def __init__(self, rules: list[AlertRule], notifier: "Notifier") -> None:
        self._rules = rules
        self._notifier = notifier
        self._last_alerted: dict[str, float] = {}

    async def handle_message(self, topic: str, payload: str) -> None:
        value = _parse_value(payload)
        if value is None:
            return
        for rule in self._rules:
            if rule.topic == topic and _matches(value, rule):
                await self._maybe_alert(rule, value)

    async def _maybe_alert(self, rule: AlertRule, value: float) -> None:
        key = f"{rule.topic}:{rule.condition}:{rule.threshold}"
        now = monotonic()
        if now - self._last_alerted.get(key, 0.0) >= rule.cooldown_minutes * 60:
            self._last_alerted[key] = now
            message = rule.message.format(value=value)
            logger.info("Alert triggered: %s", message)
            await self._notifier.send(message)
        else:
            logger.debug("Alert suppressed (cooldown active): %s", key)


def load_alert_rules(path: str | Path) -> list[AlertRule]:
    path = Path(path)
    if not path.exists():
        logger.warning("Alerts config not found at %s — running with no alert rules", path)
        return []
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    rules = [
        AlertRule(
            topic=item["topic"],
            condition=item["condition"],
            threshold=float(item["threshold"]),
            message=item["message"],
            cooldown_minutes=float(item.get("cooldown_minutes", 30)),
        )
        for item in data.get("rules", [])
    ]
    logger.info("Loaded %d alert rule(s) from %s", len(rules), path)
    return rules


def _matches(value: float, rule: AlertRule) -> bool:
    op = _OPS.get(rule.condition)
    if op is None:
        logger.warning("Unknown condition %r in rule for topic %s", rule.condition, rule.topic)
        return False
    return op(value, rule.threshold)


def _parse_value(payload: str) -> float | None:
    stripped = payload.strip()
    try:
        return float(stripped)
    except ValueError:
        pass
    try:
        data = json.loads(stripped)
        if isinstance(data, dict):
            for key in ("value", "state", "temperature", "moisture"):
                if key in data:
                    return float(data[key])
    except (json.JSONDecodeError, ValueError, TypeError):
        pass
    logger.debug("Could not parse numeric value from payload: %r", payload)
    return None
