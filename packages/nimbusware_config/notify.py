"""Config document change notifications (Lane D / fo203)."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from nimbusware_config.materializer import ConfigMaterializer

NOTIFY_CHANNEL = "hermes_config_document"
NOTIFY_EVENT_TYPE = "config.document.updated"


@dataclass(frozen=True)
class ConfigDocumentUpdated:
    namespace: str
    document_key: str
    version: int
    event_type: str = NOTIFY_EVENT_TYPE


def parse_notify_payload(payload: str | None) -> ConfigDocumentUpdated | None:
    if not payload or not str(payload).strip():
        return None
    try:
        raw = json.loads(payload)
    except json.JSONDecodeError:
        return None
    if not isinstance(raw, dict):
        return None
    ns = raw.get("namespace")
    key = raw.get("document_key")
    ver = raw.get("version")
    if not isinstance(ns, str) or not isinstance(key, str):
        return None
    try:
        version = int(ver)
    except (TypeError, ValueError):
        return None
    return ConfigDocumentUpdated(namespace=ns, document_key=key, version=version)


def encode_notify_payload(
    *,
    namespace: str,
    document_key: str,
    version: int,
) -> str:
    return json.dumps(
        {
            "type": NOTIFY_EVENT_TYPE,
            "namespace": namespace,
            "document_key": document_key,
            "version": version,
        },
        separators=(",", ":"),
    )


class ConfigNotifyHub:
    """Fan-out config.document.updated to registered materializers."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._materializers: list[ConfigMaterializer] = []
        self._last_event: ConfigDocumentUpdated | None = None
        self._delivery_count = 0

    def register(self, materializer: ConfigMaterializer) -> None:
        with self._lock:
            if materializer not in self._materializers:
                self._materializers.append(materializer)

    def unregister(self, materializer: ConfigMaterializer) -> None:
        with self._lock:
            self._materializers = [m for m in self._materializers if m is not materializer]

    @property
    def last_event(self) -> ConfigDocumentUpdated | None:
        return self._last_event

    @property
    def delivery_count(self) -> int:
        return self._delivery_count

    def handle_payload(self, payload: str | None) -> ConfigDocumentUpdated | None:
        event = parse_notify_payload(payload)
        if event is None:
            return None
        self._dispatch(event)
        return event

    def publish_local(
        self,
        *,
        namespace: str,
        document_key: str,
        version: int,
    ) -> ConfigDocumentUpdated:
        """In-process notify (tests + same-process writers without LISTEN)."""
        event = ConfigDocumentUpdated(
            namespace=namespace,
            document_key=document_key,
            version=version,
        )
        self._dispatch(event)
        return event

    def _dispatch(self, event: ConfigDocumentUpdated) -> None:
        with self._lock:
            targets = list(self._materializers)
        for mat in targets:
            mat.refresh(event.namespace)
        with self._lock:
            self._last_event = event
            self._delivery_count += 1


_HUB: ConfigNotifyHub | None = None
_HUB_LOCK = threading.Lock()


def get_config_notify_hub() -> ConfigNotifyHub:
    global _HUB
    with _HUB_LOCK:
        if _HUB is None:
            _HUB = ConfigNotifyHub()
        return _HUB
