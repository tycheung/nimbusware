from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

from env.env_flags import env_str

_lock = threading.Lock()
_subscriptions: dict[str, dict[str, Any]] = {}
_loaded = False


def _store_path() -> Path:
    raw = env_str("NIMBUSWARE_MAKER_PUSH_SUBSCRIPTIONS_FILE").strip()
    if raw:
        return Path(raw)
    base = env_str("NIMBUSWARE_DATA_DIR").strip()
    if base:
        return Path(base) / "maker" / "push_subscriptions.json"
    return Path(".nimbusware") / "maker" / "push_subscriptions.json"


def vapid_public_key() -> str:
    return env_str("NIMBUSWARE_MAKER_VAPID_PUBLIC_KEY").strip()


def vapid_private_key() -> str:
    return env_str("NIMBUSWARE_MAKER_VAPID_PRIVATE_KEY").strip()


def vapid_subject() -> str:
    raw = env_str("NIMBUSWARE_MAKER_VAPID_SUBJECT").strip()
    if raw:
        return raw if raw.startswith("mailto:") else f"mailto:{raw}"
    return "mailto:nimbusware@localhost"


def push_web_enabled() -> bool:
    return bool(vapid_public_key())


def push_send_enabled() -> bool:
    return bool(vapid_public_key() and vapid_private_key())


def _load_from_disk() -> None:
    global _loaded
    if _loaded:
        return
    path = _store_path()
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        endpoint = str(item.get("endpoint") or "").strip()
                        if endpoint:
                            _subscriptions[endpoint] = item
        except (OSError, json.JSONDecodeError):
            pass
    _loaded = True


def _persist_to_disk() -> None:
    path = _store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(list(_subscriptions.values()), indent=2),
        encoding="utf-8",
    )


def register_push_subscription(
    subscription: dict[str, Any],
    *,
    run_id: str | None = None,
) -> dict[str, Any]:
    endpoint = str(subscription.get("endpoint") or "").strip()
    if not endpoint:
        raise ValueError("subscription endpoint required")
    with _lock:
        _load_from_disk()
        record = dict(subscription)
        if run_id:
            record["run_id"] = run_id.strip()
        _subscriptions[endpoint] = record
        _persist_to_disk()
    return {"endpoint": endpoint, "registered": True}


def unregister_push_subscription(endpoint: str) -> bool:
    with _lock:
        _load_from_disk()
        removed = _subscriptions.pop(endpoint.strip(), None) is not None
        if removed:
            _persist_to_disk()
        return removed


def list_push_subscriptions(*, run_id: str | None = None) -> list[dict[str, Any]]:
    with _lock:
        _load_from_disk()
        rows = list(_subscriptions.values())
    if run_id is None:
        return rows
    key = run_id.strip()
    scoped = [s for s in rows if str(s.get("run_id") or "").strip() == key]
    return scoped if scoped else rows


def clear_push_subscriptions() -> None:
    global _loaded
    with _lock:
        _subscriptions.clear()
        _loaded = True
        path = _store_path()
        if path.is_file():
            try:
                os.remove(path)
            except OSError:
                pass
