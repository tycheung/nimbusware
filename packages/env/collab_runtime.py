from __future__ import annotations

from threading import Lock

_lock = Lock()
_runtime_collab_enabled: bool | None = None


def runtime_collab_override() -> bool | None:
    return _runtime_collab_enabled


def set_runtime_collab_enabled(enabled: bool) -> bool:
    global _runtime_collab_enabled
    with _lock:
        _runtime_collab_enabled = enabled
    return enabled


def clear_runtime_collab_override() -> None:
    global _runtime_collab_enabled
    with _lock:
        _runtime_collab_enabled = None


def collab_settings_snapshot() -> dict[str, object]:
    from env.env_flags import nimbusware_collab_enabled

    source = "runtime" if _runtime_collab_enabled is not None else "env"
    return {"collab_enabled": nimbusware_collab_enabled(), "source": source}
