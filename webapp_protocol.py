"""Pure Telegram WebApp payload validation for isolated tests and bot handlers."""
from __future__ import annotations

import json
from typing import Any

ALLOWED_WEBAPP_ACTIONS = frozenset({"open_service", "open_section", "request_health"})


def parse_webapp_payload(raw: str | None) -> tuple[str, dict[str, Any]]:
    """Parse a WebApp payload and reject malformed or privileged actions."""
    try:
        payload = json.loads(raw or "")
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid_payload") from exc
    if not isinstance(payload, dict):
        raise ValueError("invalid_payload")
    action = str(payload.get("action", ""))
    if action not in ALLOWED_WEBAPP_ACTIONS:
        raise ValueError("unsupported_action")
    data = payload.get("payload", {})
    if not isinstance(data, dict):
        raise ValueError("invalid_payload")
    return action, data


def webapp_payload(action: str, payload: dict[str, Any] | None = None) -> str:
    """Create a small, JSON-safe payload for frontend integration tests."""
    if action not in ALLOWED_WEBAPP_ACTIONS:
        raise ValueError("unsupported_action")
    return json.dumps({"action": action, "payload": payload or {}}, ensure_ascii=False)


__all__ = ["ALLOWED_WEBAPP_ACTIONS", "parse_webapp_payload", "webapp_payload"]

MALICIOUS_ACTIONS = frozenset({"mute", "ban", "promote_admin", "prepare_505f", "prepare_505c"})
