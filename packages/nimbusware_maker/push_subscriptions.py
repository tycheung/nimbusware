from __future__ import annotations

from typing import Any

from nimbusware_env.env_flags import env_str

_subscriptions: dict[str, dict[str, Any]] = {}


def vapid_public_key() -> str:
    return env_str("NIMBUSWARE_MAKER_VAPID_PUBLIC_KEY").strip()


def push_web_enabled() -> bool:
    return bool(vapid_public_key())


def register_push_subscription(subscription: dict[str, Any]) -> dict[str, Any]:
    endpoint = str(subscription.get("endpoint") or "").strip()
    if not endpoint:
        raise ValueError("subscription endpoint required")
    _subscriptions[endpoint] = dict(subscription)
    return {"endpoint": endpoint, "registered": True}


def unregister_push_subscription(endpoint: str) -> bool:
    return _subscriptions.pop(endpoint.strip(), None) is not None


def list_push_subscriptions() -> list[dict[str, Any]]:
    return list(_subscriptions.values())


def clear_push_subscriptions() -> None:
    _subscriptions.clear()
